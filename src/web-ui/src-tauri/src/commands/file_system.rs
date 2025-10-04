use crate::AppResult;
use serde::Serialize;
use tauri::{command, Manager, Runtime};
use tauri_plugin_dialog::{DialogExt, MessageDialogKind};
use std::path::PathBuf;

#[derive(Debug, Serialize)]
pub struct DirectoryInfo {
    pub path: String,
    pub name: String,
    pub is_readable: bool,
    pub is_writable: bool,
    pub file_count: Option<u64>,
    pub total_size: Option<u64>,
}

#[command]
pub async fn select_directory<R: Runtime>(
    app: tauri::AppHandle<R>,
    title: Option<String>,
    default_path: Option<String>,
) -> Result<Option<String>, String> {
    let dialog_title = title.unwrap_or_else(|| "Select Directory to Analyze".to_string());

    let dialog_path = if let Some(path) = default_path {
        PathBuf::from(path)
    } else {
        home::home_dir().unwrap_or_else(|| PathBuf::from("/"))
    };

    let file_dialog = app.dialog()
        .file()
        .set_title(dialog_title)
        .set_directory(dialog_path)
        .pick_folder();

    match file_dialog {
        Some(path) => {
            let path_str = path.to_string_lossy().to_string();
            Ok(Some(path_str))
        }
        None => Ok(None),
    }
}

#[command]
pub async fn validate_directory_access(path: String) -> AppResult<DirectoryInfo> {
    let path_buf = PathBuf::from(&path);

    if !path_buf.exists() {
        return Err(crate::AppError::FileSystemError(
            "Directory does not exist".to_string()
        ));
    }

    if !path_buf.is_dir() {
        return Err(crate::AppError::FileSystemError(
            "Path is not a directory".to_string()
        ));
    }

    let name = path_buf
        .file_name()
        .and_then(|n| n.to_str())
        .unwrap_or(&path)
        .to_string();

    // Check read/write permissions
    let is_readable = std::fs::read_dir(&path_buf).is_ok();
    let is_writable = std::fs::write(path_buf.join(".write_test"), "").is_ok();

    // Clean up test file if created
    if is_writable {
        let _ = std::fs::remove_file(path_buf.join(".write_test"));
    }

    // Count files and calculate size (quick scan for large directories)
    let (file_count, total_size) = if is_readable {
        count_directory_contents(&path_buf).await
    } else {
        (None, None)
    };

    Ok(DirectoryInfo {
        path,
        name,
        is_readable,
        is_writable,
        file_count,
        total_size,
    })
}

async fn count_directory_contents(path: &PathBuf) -> (Option<u64>, Option<u64>) {
    let mut file_count = 0u64;
    let mut total_size = 0u64;

    match std::fs::read_dir(path) {
        Ok(entries) => {
            for entry in entries.take(10000) { // Limit scan for performance
                match entry {
                    Ok(entry) => {
                        file_count += 1;
                        if let Ok(metadata) = entry.metadata() {
                            if metadata.is_file() {
                                total_size += metadata.len();
                            }
                        }
                    }
                    Err(_) => continue,
                }
            }
        }
        Err(_) => return (None, None),
    }

    (Some(file_count), Some(total_size))
}