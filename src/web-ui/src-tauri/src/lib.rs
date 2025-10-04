// Library exports for AI Disk Cleaner Web UI
// This module structure provides clear organization for the Tauri backend

pub mod commands;
pub mod utils;
pub mod app_state;

// Re-export commonly used types and functions
pub use app_state::AppState;
pub use utils::config::AppConfig;

// Error types
pub type AppResult<T> = Result<T, AppError>;

#[derive(Debug, thiserror::Error)]
pub enum AppError {
    #[error("File system error: {0}")]
    FileSystemError(String),

    #[error("Security validation failed: {0}")]
    SecurityError(String),

    #[error("System integration error: {0}")]
    SystemError(String),

    #[error("Configuration error: {0}")]
    ConfigError(String),

    #[error("IO error: {0}")]
    IoError(#[from] std::io::Error),
}

impl serde::Serialize for AppError {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: serde::Serializer,
    {
        serializer.serialize_str(self.to_string().as_ref())
    }
}