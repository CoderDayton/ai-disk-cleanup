// Utility modules for the AI Disk Cleaner Tauri backend
pub mod config;
pub mod platform;
pub mod security;
pub mod logging;

// Re-export commonly used utilities
pub use config::AppConfig;
pub use platform::{PlatformDetection, get_platform_info};
pub use security::{SecurityValidator, validate_path};
pub use logging::{init_logging, setup_tracing};