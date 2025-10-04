use crate::AppResult;
use serde::Serialize;
use std::path::{Path, PathBuf};
use tauri::command;

#[derive(Debug, Serialize)]
pub struct SafetyValidation {
    pub is_safe: bool,
    pub risk_level: RiskLevel,
    pub warnings: Vec<String>,
    pub blocked_reasons: Vec<String>,
}

#[derive(Debug, Serialize, Clone, PartialEq)]
pub enum RiskLevel {
    Safe,
    Low,
    Medium,
    High,
    Critical,
}

#[command]
pub async fn validate_path_safety(path: String) -> AppResult<SafetyValidation> {
    let path_buf = PathBuf::from(&path);
    let mut warnings = Vec::new();
    let mut blocked_reasons = Vec::new();

    // Check if path exists
    if !path_buf.exists() {
        blocked_reasons.push("Path does not exist".to_string());
        return Ok(SafetyValidation {
            is_safe: false,
            risk_level: RiskLevel::Critical,
            warnings,
            blocked_reasons,
        });
    }

    // Check if it's a directory
    if !path_buf.is_dir() {
        blocked_reasons.push("Path is not a directory".to_string());
        return Ok(SafetyValidation {
            is_safe: false,
            risk_level: RiskLevel::Critical,
            warnings,
            blocked_reasons,
        });
    }

    // System directory checks
    if is_system_directory(&path_buf) {
        blocked_reasons.push("System directory - modification not recommended".to_string());
        return Ok(SafetyValidation {
            is_safe: false,
            risk_level: RiskLevel::High,
            warnings,
            blocked_reasons,
        });
    }

    // User home directory checks
    if is_user_home_directory(&path_buf) {
        warnings.push("User home directory - review carefully before operations".to_string());
    }

    // Application directory checks
    if is_application_directory(&path_buf) {
        warnings.push("Application directory - may affect installed programs".to_string());
    }

    // Check directory depth
    if path_buf.components().count() > 10 {
        warnings.push("Very deep directory path - may cause performance issues".to_string());
    }

    // Check for special characters
    if has_special_characters(&path) {
        warnings.push("Path contains special characters - some operations may be limited".to_string());
    }

    // Determine overall safety
    let (is_safe, risk_level) = if blocked_reasons.is_empty() {
        if warnings.is_empty() {
            (true, RiskLevel::Safe)
        } else if warnings.len() <= 2 {
            (true, RiskLevel::Low)
        } else {
            (true, RiskLevel::Medium)
        }
    } else {
        (false, RiskLevel::High)
    };

    Ok(SafetyValidation {
        is_safe,
        risk_level,
        warnings,
        blocked_reasons,
    })
}

fn is_system_directory(path: &Path) -> bool {
    let path_str = path.to_string_lossy();

    // Windows system directories
    if cfg!(target_os = "windows") {
        let system_paths = [
            "C:\\Windows",
            "C:\\Program Files",
            "C:\\Program Files (x86)",
            "C:\\ProgramData",
            "C:\\System32",
            "C:\\syswow64",
        ];

        for system_path in &system_paths {
            if path_str.starts_with(system_path) {
                return true;
            }
        }
    }

    // Unix-like system directories
    let unix_system_paths = [
        "/bin",
        "/sbin",
        "/usr/bin",
        "/usr/sbin",
        "/etc",
        "/boot",
        "/sys",
        "/proc",
        "/dev",
        "/lib",
        "/lib64",
        "/usr/lib",
        "/usr/lib64",
    ];

    for system_path in &unix_system_paths {
        if path_str.starts_with(system_path) {
            return true;
        }
    }

    false
}

fn is_user_home_directory(path: &Path) -> bool {
    if let Some(home_dir) = home::home_dir() {
        path == home_dir
    } else {
        false
    }
}

fn is_application_directory(path: &Path) -> bool {
    let path_str = path.to_string_lossy();

    // Common application directories
    let app_patterns = [
        "node_modules",
        ".git",
        "target",
        "build",
        "dist",
        ".vscode",
        ".idea",
    ];

    for pattern in &app_patterns {
        if path_str.contains(pattern) {
            return true;
        }
    }

    false
}

fn has_special_characters(path: &str) -> bool {
    // Check for characters that might cause issues in file operations
    path.chars().any(|c| {
        !c.is_ascii() ||
        c == '<' || c == '>' || c == ':' || c == '"' ||
        c == '|' || c == '?' || c == '*'
    })
}