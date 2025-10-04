use crate::AppResult;
use serde::Serialize;
use tauri::{command, Runtime};
use std::process::Command;

#[derive(Debug, Serialize)]
pub struct SystemInfo {
    pub os_type: String,
    pub os_version: String,
    pub arch: String,
    pub hostname: String,
    pub total_memory: Option<u64>,
    pub available_memory: Option<u64>,
    pub disk_space: Option<DiskSpaceInfo>,
}

#[derive(Debug, Serialize)]
pub struct DiskSpaceInfo {
    pub total: u64,
    pub available: u64,
    pub used: u64,
}

#[derive(Debug, Serialize)]
pub struct PlatformInfo {
    pub is_desktop: bool,
    pub supports_notifications: bool,
    pub supports_file_dialogs: bool,
    pub supports_system_theme: bool,
    pub platform_specific: PlatformSpecific,
}

#[derive(Debug, Serialize)]
pub struct PlatformSpecific {
    pub windows: WindowsInfo,
    pub macos: MacOSInfo,
    pub linux: LinuxInfo,
}

#[derive(Debug, Serialize)]
pub struct WindowsInfo {
    pub is_windows: bool,
    pub version: Option<String>,
    pub build_number: Option<String>,
}

#[derive(Debug, Serialize)]
pub struct MacOSInfo {
    pub is_macos: bool,
    pub version: Option<String>,
    pub darwin_version: Option<String>,
}

#[derive(Debug, Serialize)]
pub struct LinuxInfo {
    pub is_linux: bool,
    pub distribution: Option<String>,
    pub desktop_environment: Option<String>,
}

#[command]
pub async fn get_system_info() -> AppResult<SystemInfo> {
    let os_type = std::env::consts::OS.to_string();
    let arch = std::env::consts::ARCH.to_string();

    let hostname = gethostname::gethostname()
        .to_string_lossy()
        .to_string();

    let os_version = get_os_version().await?;
    let (total_memory, available_memory) = get_memory_info().await?;
    let disk_space = get_disk_space_info().await?;

    Ok(SystemInfo {
        os_type,
        os_version,
        arch,
        hostname,
        total_memory,
        available_memory,
        disk_space,
    })
}

#[command]
pub async fn get_platform_info() -> AppResult<PlatformInfo> {
    let is_windows = cfg!(target_os = "windows");
    let is_macos = cfg!(target_os = "macos");
    let is_linux = cfg!(target_os = "linux");

    let platform_specific = PlatformSpecific {
        windows: WindowsInfo {
            is_windows,
            version: if is_windows { get_windows_version().await } else { None },
            build_number: if is_windows { get_windows_build_number().await } else { None },
        },
        macos: MacOSInfo {
            is_macos,
            version: if is_macos { get_macos_version().await } else { None },
            darwin_version: if is_macos { get_darwin_version().await } else { None },
        },
        linux: LinuxInfo {
            is_linux,
            distribution: if is_linux { get_linux_distribution().await } else { None },
            desktop_environment: if is_linux { get_desktop_environment().await } else { None },
        },
    };

    Ok(PlatformInfo {
        is_desktop: true,
        supports_notifications: true,
        supports_file_dialogs: true,
        supports_system_theme: true,
        platform_specific,
    })
}

async fn get_os_version() -> AppResult<String> {
    let output = if cfg!(target_os = "windows") {
        Command::new("cmd")
            .args(&["/C", "ver"])
            .output()
    } else if cfg!(target_os = "macos") {
        Command::new("sw_vers")
            .args(&["-productVersion"])
            .output()
    } else {
        Command::new("lsb_release")
            .args(&["-d"])
            .output()
    };

    match output {
        Ok(result) => {
            let version = String::from_utf8_lossy(&result.stdout)
                .trim()
                .to_string();
            Ok(version)
        }
        Err(_) => Ok("Unknown".to_string()),
    }
}

async fn get_memory_info() -> AppResult<(Option<u64>, Option<u64>)> {
    // This is a simplified implementation
    // In production, you'd want platform-specific memory queries
    Ok((None, None))
}

async fn get_disk_space_info() -> AppResult<Option<DiskSpaceInfo>> {
    // Simplified disk space detection
    // In production, you'd want to query actual disk usage
    Ok(None)
}

// Platform-specific helper functions
async fn get_windows_version() -> Option<String> { None }
async fn get_windows_build_number() -> Option<String> { None }
async fn get_macos_version() -> Option<String> { None }
async fn get_darwin_version() -> Option<String> { None }
async fn get_linux_distribution() -> Option<String> { None }
async fn get_desktop_environment() -> Option<String> { None }