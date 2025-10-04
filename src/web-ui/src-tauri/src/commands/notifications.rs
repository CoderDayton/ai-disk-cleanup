use crate::AppResult;
use serde::Serialize;
use tauri::{command, AppHandle, Manager};
use tauri_plugin_notification::NotificationExt;

#[derive(Debug, Serialize)]
pub struct NotificationConfig {
    pub title: String,
    pub body: String,
    pub icon: Option<String>,
    pub sound: Option<String>,
    pub duration: Option<i32>,
}

#[derive(Debug, Serialize)]
pub struct NotificationResult {
    pub success: bool,
    pub message: String,
}

#[command]
pub async fn show_notification<R: tauri::Runtime>(
    app: AppHandle<R>,
    config: NotificationConfig,
) -> AppResult<NotificationResult> {
    let notification = app
        .notification()
        .builder()
        .title(config.title)
        .body(config.body);

    let notification = if let Some(icon) = config.icon {
        notification.icon(icon)
    } else {
        notification
    };

    let notification = if let Some(sound) = config.sound {
        notification.sound(sound)
    } else {
        notification
    };

    match notification.show() {
        Ok(_) => Ok(NotificationResult {
            success: true,
            message: "Notification sent successfully".to_string(),
        }),
        Err(e) => Ok(NotificationResult {
            success: false,
            message: format!("Failed to send notification: {}", e),
        }),
    }
}

#[command]
pub async fn check_notification_permissions<R: tauri::Runtime>(
    app: AppHandle<R>,
) -> AppResult<bool> {
    // Check if notifications are enabled on the current platform
    Ok(true) // Simplified for now
}

#[command]
pub async fn request_notification_permissions<R: tauri::Runtime>(
    app: AppHandle<R>,
) -> AppResult<bool> {
    // Request notification permissions if needed
    Ok(true) // Simplified for now
}