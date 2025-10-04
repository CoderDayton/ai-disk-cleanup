// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use anyhow::Result;
use tracing::{error, info, Level};
use tracing_subscriber;

mod commands;
mod utils;

// Tauri command modules
use commands::{
    file_system::select_directory,
    system_integration::{get_system_info, show_notification},
    security::validate_path_safety,
};

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize logging
    tracing_subscriber::fmt()
        .with_max_level(Level::INFO)
        .with_target(false)
        .init();

    info!("Starting AI Disk Cleaner Web UI");

    // Configure Tauri application
    tauri::Builder::default()
        // Tauri commands for file system operations
        .invoke_handler(tauri::generate_handler![
            select_directory,
            get_system_info,
            show_notification,
            validate_path_safety
        ])
        // Application state
        .manage( AppState::new() )
        .setup(|app| {
            info!("Application setup completed");
            Ok(())
        })
        .run(tauri::generate_context!())?;

    info!("Application shutdown complete");
    Ok(())
}

/// Application state shared across all Tauri commands
#[derive(Debug, Clone)]
pub struct AppState {
    pub config: AppConfig,
}

impl AppState {
    pub fn new() -> Self {
        Self {
            config: AppConfig::default(),
        }
    }
}

/// Application configuration
#[derive(Debug, Clone)]
pub struct AppConfig {
    pub max_file_size: u64,
    pub default_timeout: u64,
    pub enable_logging: bool,
}

impl Default for AppConfig {
    fn default() -> Self {
        Self {
            max_file_size: 1_000_000_000, // 1GB
            default_timeout: 30, // 30 seconds
            enable_logging: true,
        }
    }
}