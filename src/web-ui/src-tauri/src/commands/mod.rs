// Tauri command modules organized by functionality
// Each module contains related Tauri commands exposed to the frontend

pub mod file_system;
pub mod system_integration;
pub mod security;
pub mod notifications;

// Re-export all command functions for easy registration
pub use file_system::select_directory;
pub use system_integration::{get_system_info, get_platform_info};
pub use security::validate_path_safety;
pub use notifications::show_notification;