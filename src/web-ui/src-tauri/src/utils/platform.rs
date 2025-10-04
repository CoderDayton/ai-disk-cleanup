use serde::{Deserialize, Serialize};
use std::env;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PlatformInfo {
    pub os_type: String,
    pub arch: String,
    pub is_desktop: bool,
    pub is_mobile: bool,
    pub is_web: bool,
    pub supports_notifications: bool,
    pub supports_file_dialogs: bool,
    pub supports_system_theme: bool,
}

#[derive(Debug, Clone)]
pub struct PlatformDetection;

impl PlatformDetection {
    /// Detect current platform information
    pub fn detect() -> PlatformInfo {
        let os_type = env::consts::OS.to_string();
        let arch = env::consts::ARCH.to_string();

        PlatformInfo {
            os_type: os_type.clone(),
            arch,
            is_desktop: Self::is_desktop(&os_type),
            is_mobile: Self::is_mobile(&os_type),
            is_web: false, // We're in Tauri, so always native
            supports_notifications: Self::supports_notifications(&os_type),
            supports_file_dialogs: true,
            supports_system_theme: Self::supports_system_theme(&os_type),
        }
    }

    fn is_desktop(os_type: &str) -> bool {
        matches!(os_type, "windows" | "macos" | "linux")
    }

    fn is_mobile(_os_type: &str) -> bool {
        // Tauri doesn't target mobile platforms yet
        false
    }

    fn supports_notifications(os_type: &str) -> bool {
        // Most desktop platforms support notifications
        Self::is_desktop(os_type)
    }

    fn supports_system_theme(os_type: &str) -> bool {
        // Most modern desktop platforms support system theme detection
        matches!(os_type, "windows" | "macos" | "linux")
    }
}

/// Get platform-specific information
pub fn get_platform_info() -> PlatformInfo {
    PlatformDetection::detect()
}

/// Check if running on Windows
pub fn is_windows() -> bool {
    cfg!(target_os = "windows")
}

/// Check if running on macOS
pub fn is_macos() -> bool {
    cfg!(target_os = "macos")
}

/// Check if running on Linux
pub fn is_linux() -> bool {
    cfg!(target_os = "linux")
}

/// Get platform-specific file extensions
pub fn get_executable_extension() -> &'static str {
    match env::consts::OS {
        "windows" => ".exe",
        _ => "",
    }
}

/// Get platform-specific path separator
pub fn get_path_separator() -> &'static str {
    match env::consts::OS {
        "windows" => ";",
        _ => ":",
    }
}

/// Get platform-specific line ending
pub fn get_line_ending() -> &'static str {
    match env::consts::OS {
        "windows" => "\r\n",
        _ => "\n",
    }
}