"""
Linux AppImage builder using PyInstaller and AppImageTool.

This module provides a Linux-specific builder that can create AppImage installers
with proper dependency management, GPG signing, and distribution compatibility.
"""

import sys
import shutil
import subprocess
import tempfile
import stat
import platform
from pathlib import Path
from typing import Dict, Any, Optional, List

from .base_builder import BaseBuilder
from ..config import InstallerConfig
from ..orchestrator import BuildError


class LinuxBuilder(BaseBuilder):
    """
    Linux AppImage builder using PyInstaller and AppImageTool.

    This builder creates Linux AppImage installers with proper dependency
    management, GPG signing, and distribution-specific optimizations.
    """

    def _get_platform_name(self) -> str:
        """Get the platform name this builder handles."""
        return "linux"

    def validate_dependencies(self) -> None:
        """
        Validate that all required dependencies are available.

        Raises:
            BuildError: If required dependencies are missing
        """
        self._log_info("Validating Linux build dependencies...")

        # Check PyInstaller availability
        try:
            result = subprocess.run(
                ["pyinstaller", "--version"],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode != 0:
                raise BuildError("PyInstaller check failed. Make sure PyInstaller is installed.")
            self._log_info(f"✓ PyInstaller found: {result.stdout.strip()}")
        except FileNotFoundError:
            raise BuildError("PyInstaller is required but not found in PATH")
        except subprocess.TimeoutExpired:
            raise BuildError("PyInstaller check timed out")

        # Check for AppImageTool (optional)
        try:
            result = subprocess.run(
                ["appimagetool", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                self._log_info(f"✓ AppImageTool found: {result.stdout.strip()}")
            else:
                self._log_warning("AppImageTool not found, will use fallback method")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            self._log_warning("AppImageTool not found, will use fallback method")

    def build(self) -> Path:
        """
        Build the Linux AppImage.

        Returns:
            Path to the generated AppImage

        Raises:
            BuildError: If the build fails
        """
        self._log_info("Starting Linux AppImage build...")

        # Validate dependencies
        self.validate_dependencies()

        # Ensure output directory exists
        self._ensure_output_directory()

        # Create temporary build directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            try:
                # Step 1: Detect Linux distribution
                distro = self._detect_linux_distribution()
                self._log_info(f"Detected distribution: {distro}")

                # Step 2: Create executable with PyInstaller
                self._log_info("Step 1: Creating executable with PyInstaller...")
                executable_path = self._run_pyinstaller(temp_path)

                # Step 3: Create AppImage structure
                self._log_info("Step 2: Creating AppImage structure...")
                appdir_path = temp_path / f"{self.config.project_name}.AppDir"
                self._create_appimage_structure(executable_path, appdir_path)

                # Step 4: Create AppImage using AppImageTool or fallback
                self._log_info("Step 3: Creating AppImage...")
                appimage_path = self._create_appimage(appdir_path, temp_path)

                # Step 5: GPG signing (if enabled)
                final_appimage_path = self._sign_appimage(appimage_path)

                # Copy to final output location
                output_path = self.get_output_path()
                shutil.copy2(final_appimage_path, output_path)

                self._log_info(f"✓ Linux AppImage created: {output_path}")
                return output_path

            except Exception as e:
                raise BuildError(f"Linux build failed: {e}") from e

    def _detect_linux_distribution(self) -> str:
        """
        Detect the Linux distribution.

        Returns:
            Distribution identifier (ubuntu, centos, fedora, debian, arch, generic)
        """
        try:
            # Try lsb_release first (most common)
            result = subprocess.run(
                ["lsb_release", "-si"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                distro = result.stdout.strip().lower()
                # Normalize common distributions
                if "ubuntu" in distro:
                    return "ubuntu"
                elif "centos" in distro or "rhel" in distro:
                    return "centos"
                elif "fedora" in distro:
                    return "fedora"
                elif "debian" in distro:
                    return "debian"
                elif "arch" in distro:
                    return "arch"

            # Try reading /etc/os-release
            if Path("/etc/os-release").exists():
                with open("/etc/os-release", "r") as f:
                    content = f.read().lower()
                    if "ubuntu" in content:
                        return "ubuntu"
                    elif "centos" in content or "rhel" in content:
                        return "centos"
                    elif "fedora" in content:
                        return "fedora"
                    elif "debian" in content:
                        return "debian"
                    elif "arch" in content:
                        return "arch"

        except (subprocess.CalledProcessError, FileNotFoundError, OSError):
            pass

        return "generic"

    def _get_dependencies_for_distribution(self, distro: str) -> List[str]:
        """
        Get distribution-specific dependencies.

        Args:
            distro: Linux distribution identifier

        Returns:
            List of required dependencies
        """
        platform_config = self.get_platform_config()
        base_deps = platform_config.get("dependencies", [])

        # Distribution-specific dependency mapping
        distro_deps = {
            "ubuntu": {
                "python3-tk": base_deps[0] if base_deps else "python3",
                "python3-pip": base_deps[0] if base_deps else "python3",
            },
            "debian": {
                "python3-tk": base_deps[0] if base_deps else "python3",
                "python3-pip": base_deps[0] if base_deps else "python3",
            },
            "centos": {
                "python3-tkinter": base_deps[0] if base_deps else "python3",
                "python3-pip": base_deps[0] if base_deps else "python3",
            },
            "fedora": {
                "python3-tkinter": base_deps[0] if base_deps else "python3",
                "python3-pip": base_deps[0] if base_deps else "python3",
            },
            "arch": {
                "tk": base_deps[0] if base_deps else "python",
                "python-pip": base_deps[0] if base_deps else "python",
            }
        }

        # Add distribution-specific dependencies
        distro_specific = distro_deps.get(distro, {})
        all_deps = list(base_deps) + list(distro_specific.values())

        return all_deps

    def _run_pyinstaller(self, build_dir: Path) -> Path:
        """
        Run PyInstaller to create the executable.

        Args:
            build_dir: Directory to build in

        Returns:
            Path to the created executable

        Raises:
            BuildError: If PyInstaller fails
        """
        build_config = self.config._config.get("build", {})
        pyinstaller_options = build_config.get("pyinstaller_options", [])

        # Default PyInstaller options for Linux
        default_options = [
            "--onefile",
            "--name=ai-disk-cleanup",
            "--distpath=dist",
            f"--workpath={build_dir}/build",
            f"--specpath={build_dir}"
        ]

        # Add source path
        main_script = Path("src/ai_disk_cleanup/__init__.py")
        if not main_script.exists():
            main_script = Path("src/ai_disk_cleanup")

        command = ["pyinstaller"] + default_options + pyinstaller_options + [str(main_script)]

        self._log_info(f"Running PyInstaller: {' '.join(command)}")

        try:
            build_parent = Path(build_dir).parent if isinstance(build_dir, str) else build_dir.parent
            result = subprocess.run(
                command,
                cwd=build_parent,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )

            if result.returncode != 0:
                self._log_error(f"PyInstaller failed: {result.stderr}")
                raise BuildError(f"PyInstaller build failed: {result.stderr}")

            executable_path = build_dir.parent / "dist" / "ai-disk-cleanup"
            if not executable_path.exists():
                raise BuildError("PyInstaller did not create expected executable")

            self._log_info(f"✓ Executable created: {executable_path}")
            return executable_path

        except subprocess.TimeoutExpired:
            raise BuildError("PyInstaller build timed out after 10 minutes")
        except Exception as e:
            raise BuildError(f"PyInstaller execution failed: {e}") from e

    def _create_appimage_structure(self, executable_path: Path, appdir_path: Path) -> None:
        """
        Create the AppImage directory structure.

        Args:
            executable_path: Path to the executable
            appdir_path: Path where to create the AppDir structure
        """
        # Create AppDir structure
        appdir_path.mkdir(parents=True, exist_ok=True)

        # Create usr/bin directory
        usr_bin = appdir_path / "usr" / "bin"
        usr_bin.mkdir(parents=True, exist_ok=True)

        # Copy executable to usr/bin
        shutil.copy2(executable_path, usr_bin / "ai-disk-cleanup")

        # Create AppRun script
        apprun_path = appdir_path / "AppRun"
        self._create_appimage_script(apprun_path)

        # Create .desktop file
        desktop_path = appdir_path / "ai-disk-cleanup.desktop"
        self._create_appimage_desktop_file(desktop_path)

        # Create icon directory and copy icon
        icon_dir = appdir_path / "usr" / "share" / "icons"
        icon_dir.mkdir(parents=True, exist_ok=True)

        platform_config = self.get_platform_config()
        icon_path = platform_config.get("icon", "assets/icon.png")
        if Path(icon_path).exists():
            shutil.copy2(icon_path, appdir_path / "ai-disk-cleanup.png")
        else:
            # Create a simple placeholder icon
            placeholder_icon = appdir_path / "ai-disk-cleanup.png"
            self._create_placeholder_icon(placeholder_icon)

        self._log_info(f"✓ AppImage structure created: {appdir_path}")

    def _create_appimage_script(self, script_path: Path) -> None:
        """
        Create the AppRun script for the AppImage.

        Args:
            script_path: Path where to write the AppRun script
        """
        script_content = '''#!/bin/bash

HERE="$(dirname "$(readlink -f "${0}")")"
EXEC="$HERE/usr/bin/ai-disk-cleanup"

# Export environment variables
export APPDIR="$HERE"
export PATH="$HERE/usr/bin:$PATH"
export LD_LIBRARY_PATH="$HERE/usr/lib:$LD_LIBRARY_PATH"

# Run the application
exec "$EXEC" "$@"
'''

        script_path.write_text(script_content, encoding='utf-8')
        script_path.chmod(0o755)  # Make executable

    def _create_appimage_desktop_file(self, desktop_path: Path) -> None:
        """
        Create the .desktop file for the AppImage.

        Args:
            desktop_path: Path where to write the desktop file
        """
        project_config = self.config._config.get("project", {})

        desktop_content = f'''[Desktop Entry]
Name={project_config.get('name', 'AI Disk Cleanup')}
Comment={project_config.get('description', 'AI-powered disk cleanup tool')}
Exec=ai-disk-cleanup
Icon=ai-disk-cleanup
Type=Application
Categories=System;FileTools;Utility;
StartupNotify=true
'''

        desktop_path.write_text(desktop_content, encoding='utf-8')

    def _create_placeholder_icon(self, icon_path: Path) -> None:
        """
        Create a placeholder icon if none is available.

        Args:
            icon_path: Path where to create the placeholder icon
        """
        # Create a simple 32x32 PNG placeholder (base64 encoded minimal PNG)
        # This is a tiny 1x1 pixel transparent PNG
        png_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc```\x00\x00\x00\x02\x00\x01\xe2!\xbc\x33\x00\x00\x00\x00IEND\xaeB`\x82'
        icon_path.write_bytes(png_data)

    def _create_appimage(self, appdir_path: Path, build_dir: Path) -> Path:
        """
        Create the AppImage using AppImageTool or fallback method.

        Args:
            appdir_path: Path to the AppDir structure
            build_dir: Build directory

        Returns:
            Path to the created AppImage
        """
        try:
            # Try to use AppImageTool
            return self._create_appimage_with_appimagetool(appdir_path, build_dir)
        except Exception as e:
            self._log_warning(f"AppImageTool failed: {e}")
            return self._create_fallback_appimage(appdir_path, build_dir)

    def _create_appimage_with_appimagetool(self, appdir_path: Path, build_dir: Path) -> Path:
        """
        Create AppImage using AppImageTool.

        Args:
            appdir_path: Path to the AppDir structure
            build_dir: Build directory

        Returns:
            Path to the created AppImage

        Raises:
            BuildError: If AppImageTool fails
        """
        appimage_name = f"{self.config.project_name}.AppImage"
        appimage_path = build_dir / appimage_name

        command = ["appimagetool", str(appdir_path), str(appimage_path)]

        self._log_info(f"Running AppImageTool: {' '.join(command)}")

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode != 0:
                self._log_error(f"AppImageTool failed: {result.stderr}")
                raise BuildError(f"AppImage creation failed: {result.stderr}")

            if not appimage_path.exists():
                raise BuildError("AppImageTool did not create expected AppImage")

            self._log_info(f"✓ AppImage created: {appimage_path}")
            return appimage_path

        except subprocess.TimeoutExpired:
            raise BuildError("AppImage creation timed out after 5 minutes")
        except Exception as e:
            raise BuildError(f"AppImageTool execution failed: {e}") from e

    def _create_fallback_appimage(self, appdir_path: Path, build_dir: Path) -> Path:
        """
        Create a fallback AppImage without AppImageTool.

        Args:
            appdir_path: Path to the AppDir structure
            build_dir: Build directory

        Returns:
            Path to the created AppImage
        """
        appimage_name = f"{self.config.project_name}.AppImage"
        appimage_path = build_dir / appimage_name

        self._log_info("Creating fallback AppImage...")

        # For Phase 1, create a simple wrapper that points to the AppDir
        # In a real implementation, this would require more complex binary packaging
        apprun_content = f'''#!/bin/bash
HERE="$(dirname "$(readlink -f "${{0}}")")"
APPDIR="$HERE/{appdir_path.name}"

# Export environment variables
export APPDIR="$APPDIR"
export PATH="$APPDIR/usr/bin:$PATH"
export LD_LIBRARY_PATH="$APPDIR/usr/lib:$LD_LIBRARY_PATH"

# Run the application
exec "$APPDIR/usr/bin/ai-disk-cleanup" "$@"
'''

        appimage_path.write_text(apprun_content, encoding='utf-8')
        appimage_path.chmod(0o755)

        self._log_info(f"✓ Fallback AppImage created: {appimage_path}")
        return appimage_path

    def _sign_appimage(self, appimage_path: Path) -> Path:
        """
        Sign the AppImage with GPG.

        Args:
            appimage_path: Path to the AppImage to sign

        Returns:
            Path to the signed AppImage (same as input if signing disabled)
        """
        code_signing_config = self.get_code_signing_config()

        if not code_signing_config.get("enabled", False):
            self._log_info("GPG signing disabled, skipping signing")
            return appimage_path

        self._log_info("GPG signing AppImage...")

        try:
            gpg_key_id = code_signing_config.get("gpg_key_id")
            gpg_key_path = code_signing_config.get("gpg_key_path")

            if not gpg_key_id:
                self._log_warning("GPG key ID not specified, skipping signing")
                return appimage_path

            # Build GPG command
            sign_command = ["gpg", "--detach-sign", "--armor"]

            if gpg_key_path and Path(gpg_key_path).exists():
                sign_command.extend(["--local-user", gpg_key_path])

            sign_command.extend(["--default-key", gpg_key_id, str(appimage_path)])

            result = subprocess.run(
                sign_command,
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode != 0:
                self._log_error(f"GPG signing failed: {result.stderr}")
                raise BuildError(f"GPG signing failed: {result.stderr}")

            self._log_info(f"✓ AppImage signed successfully")
            return appimage_path

        except Exception as e:
            self._log_error(f"GPG signing failed: {e}")
            raise BuildError(f"GPG signing failed: {e}") from e