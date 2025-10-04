// Tauri command wrappers for type-safe IPC communication

import { invoke } from '@tauri-apps/api/core'

// File system commands
export interface DirectoryInfo {
  path: string
  name: string
  is_readable: boolean
  is_writable: boolean
  file_count?: number
  total_size?: number
}

export interface SelectDirectoryOptions {
  title?: string
  defaultPath?: string
}

export async function selectDirectory(options?: SelectDirectoryOptions): Promise<string | null> {
  try {
    return await invoke<string | null>('select_directory', {
      title: options?.title,
      default_path: options?.defaultPath
    })
  } catch (error) {
    console.error('Failed to select directory:', error)
    throw error
  }
}

export async function validateDirectoryAccess(path: string): Promise<DirectoryInfo> {
  try {
    return await invoke<DirectoryInfo>('validate_directory_access', { path })
  } catch (error) {
    console.error('Failed to validate directory access:', error)
    throw error
  }
}

// System integration commands
export interface SystemInfo {
  os_type: string
  os_version: string
  arch: string
  hostname: string
  total_memory?: number
  available_memory?: number
  disk_space?: {
    total: number
    available: number
    used: number
  }
}

export interface PlatformInfo {
  is_desktop: boolean
  supports_notifications: boolean
  supports_file_dialogs: boolean
  supports_system_theme: boolean
  platform_specific: {
    windows: {
      is_windows: boolean
      version?: string
      build_number?: string
    }
    macos: {
      is_macos: boolean
      version?: string
      darwin_version?: string
    }
    linux: {
      is_linux: boolean
      distribution?: string
      desktop_environment?: string
    }
  }
}

export async function getSystemInfo(): Promise<SystemInfo> {
  try {
    return await invoke<SystemInfo>('get_system_info')
  } catch (error) {
    console.error('Failed to get system info:', error)
    throw error
  }
}

export async function getPlatformInfo(): Promise<PlatformInfo> {
  try {
    return await invoke<PlatformInfo>('get_platform_info')
  } catch (error) {
    console.error('Failed to get platform info:', error)
    throw error
  }
}

// Security commands
export interface SafetyValidation {
  is_safe: boolean
  risk_level: 'Safe' | 'Low' | 'Medium' | 'High' | 'Critical'
  warnings: string[]
  blocked_reasons: string[]
}

export async function validatePathSafety(path: string): Promise<SafetyValidation> {
  try {
    return await invoke<SafetyValidation>('validate_path_safety', { path })
  } catch (error) {
    console.error('Failed to validate path safety:', error)
    throw error
  }
}

// Notification commands
export interface NotificationConfig {
  title: string
  body: string
  icon?: string
  sound?: string
  duration?: number
}

export interface NotificationResult {
  success: boolean
  message: string
}

export async function showNotification(config: NotificationConfig): Promise<NotificationResult> {
  try {
    return await invoke<NotificationResult>('show_notification', { config })
  } catch (error) {
    console.error('Failed to show notification:', error)
    throw error
  }
}

export async function checkNotificationPermissions(): Promise<boolean> {
  try {
    return await invoke<boolean>('check_notification_permissions')
  } catch (error) {
    console.error('Failed to check notification permissions:', error)
    return false
  }
}

export async function requestNotificationPermissions(): Promise<boolean> {
  try {
    return await invoke<boolean>('request_notification_permissions')
  } catch (error) {
    console.error('Failed to request notification permissions:', error)
    return false
  }
}

// File operations
export interface FileOperationResult {
  success: boolean
  message: string
  affected_files?: number
  space_saved?: number
}

export async function deleteFiles(filePaths: string[]): Promise<FileOperationResult> {
  // This would be implemented as a Tauri command
  // For now, we'll return a mock implementation
  return {
    success: true,
    message: `Deleted ${filePaths.length} files`,
    affected_files: filePaths.length,
    space_saved: 0
  }
}

export async function moveFiles(filePaths: string[], destination: string): Promise<FileOperationResult> {
  // This would be implemented as a Tauri command
  return {
    success: true,
    message: `Moved ${filePaths.length} files to ${destination}`,
    affected_files: filePaths.length,
    space_saved: 0
  }
}

export async function copyFiles(filePaths: string[], destination: string): Promise<FileOperationResult> {
  // This would be implemented as a Tauri command
  return {
    success: true,
    message: `Copied ${filePaths.length} files to ${destination}`,
    affected_files: filePaths.length,
    space_saved: 0
  }
}

// Application lifecycle
export async function minimizeApp(): Promise<void> {
  try {
    await invoke('minimize_app')
  } catch (error) {
    console.error('Failed to minimize app:', error)
  }
}

export async function maximizeApp(): Promise<void> {
  try {
    await invoke('maximize_app')
  } catch (error) {
    console.error('Failed to maximize app:', error)
  }
}

export async function closeApp(): Promise<void> {
  try {
    await invoke('close_app')
  } catch (error) {
    console.error('Failed to close app:', error)
  }
}

export async function showAppInFolder(): Promise<void> {
  try {
    await invoke('show_app_in_folder')
  } catch (error) {
    console.error('Failed to show app in folder:', error)
  }
}

// Theme handling
export async function getSystemTheme(): Promise<'light' | 'dark'> {
  try {
    return await invoke<'light' | 'dark'>('get_system_theme')
  } catch (error) {
    console.error('Failed to get system theme:', error)
    return 'light'
  }
}

export async function setWindowTitle(title: string): Promise<void> {
  try {
    await invoke('set_window_title', { title })
  } catch (error) {
    console.error('Failed to set window title:', error)
  }
}

export async function setWindowAlwaysOnTop(alwaysOnTop: boolean): Promise<void> {
  try {
    await invoke('set_window_always_on_top', { alwaysOnTop })
  } catch (error) {
    console.error('Failed to set window always on top:', error)
  }
}