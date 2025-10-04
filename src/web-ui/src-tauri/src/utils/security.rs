use std::path::{Path, PathBuf};
use anyhow::Result;

pub struct SecurityValidator;

impl SecurityValidator {
    /// Validate that a path is safe for file operations
    pub fn validate_path(path: &str) -> Result<PathValidation> {
        let path_buf = PathBuf::from(path);
        Self::validate_path_buf(&path_buf)
    }

    /// Validate that a PathBuf is safe for file operations
    pub fn validate_path_buf(path: &Path) -> Result<PathValidation> {
        let mut warnings = Vec::new();
        let mut blocked_reasons = Vec::new();

        // Basic existence and type checks
        if !path.exists() {
            blocked_reasons.push("Path does not exist".to_string());
            return Ok(PathValidation {
                is_safe: false,
                risk_level: RiskLevel::Critical,
                warnings,
                blocked_reasons,
            });
        }

        if !path.is_dir() {
            blocked_reasons.push("Path is not a directory".to_string());
            return Ok(PathValidation {
                is_safe: false,
                risk_level: RiskLevel::Critical,
                warnings,
                blocked_reasons,
            });
        }

        // System directory protection
        if Self::is_system_directory(path) {
            blocked_reasons.push("System directory access is blocked".to_string());
            return Ok(PathValidation {
                is_safe: false,
                risk_level: RiskLevel::High,
                warnings,
                blocked_reasons,
            });
        }

        // User directory warnings
        if Self::is_user_sensitive_directory(path) {
            warnings.push("User sensitive directory - review operations carefully".to_string());
        }

        // Path traversal protection
        if Self::contains_path_traversal(path) {
            blocked_reasons.push("Path contains traversal patterns".to_string());
            return Ok(PathValidation {
                is_safe: false,
                risk_level: RiskLevel::Critical,
                warnings,
                blocked_reasons,
            });
        }

        // Character safety
        if Self::has_unsafe_characters(path) {
            warnings.push("Path contains special characters that may cause issues".to_string());
        }

        // Length checks
        if Self::is_path_too_long(path) {
            warnings.push("Very long path - may cause system limitations".to_string());
        }

        let (is_safe, risk_level) = Self::calculate_risk_level(&warnings, &blocked_reasons);

        Ok(PathValidation {
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
            let system_dirs = [
                "C:\\Windows",
                "C:\\Program Files",
                "C:\\Program Files (x86)",
                "C:\\ProgramData",
                "C:\\System32",
                "C:\\SysWOW64",
            ];

            for dir in &system_dirs {
                if path_str.starts_with(dir) {
                    return true;
                }
            }
        }

        // Unix-like system directories
        let system_dirs = [
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
            "/var/log",
        ];

        for dir in &system_dirs {
            if path_str.starts_with(dir) {
                return true;
            }
        }

        false
    }

    fn is_user_sensitive_directory(path: &Path) -> bool {
        if let Some(home) = home::home_dir() {
            let sensitive_subdirs = [
                "Documents",
                "Desktop",
                "Pictures",
                "Videos",
                "Music",
                "Downloads",
                ".ssh",
                ".gnupg",
                ".config",
                ".local",
            ];

            for subdir in &sensitive_subdirs {
                if path == home.join(subdir) {
                    return true;
                }
            }
        }

        false
    }

    fn contains_path_traversal(path: &Path) -> bool {
        let path_str = path.to_string_lossy();
        path_str.contains("..") || path_str.contains("./") || path_str.contains(".\\")
    }

    fn has_unsafe_characters(path: &Path) -> bool {
        let path_str = path.to_string_lossy();
        path_str.chars().any(|c| {
            !c.is_ascii() ||
            c == '<' || c == '>' || c == ':' || c == '"' ||
            c == '|' || c == '?' || c == '*''
        })
    }

    fn is_path_too_long(path: &Path) -> bool {
        // Windows has a 260 character limit for paths (without extended-length support)
        if cfg!(target_os = "windows") {
            path.to_string_lossy().len() > 250
        } else {
            // Unix systems generally support longer paths
            path.to_string_lossy().len() > 1000
        }
    }

    fn calculate_risk_level(
        warnings: &[String],
        blocked_reasons: &[String],
    ) -> (bool, RiskLevel) {
        if !blocked_reasons.is_empty() {
            return (false, RiskLevel::High);
        }

        if warnings.is_empty() {
            return (true, RiskLevel::Safe);
        }

        if warnings.len() <= 2 {
            (true, RiskLevel::Low)
        } else {
            (true, RiskLevel::Medium)
        }
    }
}

/// Convenience function for path validation
pub fn validate_path(path: &str) -> Result<PathValidation> {
    SecurityValidator::validate_path(path)
}

#[derive(Debug, Clone)]
pub struct PathValidation {
    pub is_safe: bool,
    pub risk_level: RiskLevel,
    pub warnings: Vec<String>,
    pub blocked_reasons: Vec<String>,
}

#[derive(Debug, Clone)]
pub enum RiskLevel {
    Safe,
    Low,
    Medium,
    High,
    Critical,
}