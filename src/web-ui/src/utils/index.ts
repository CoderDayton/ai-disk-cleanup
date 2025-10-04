// Utility functions and helpers

import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

// Class name utility for TailwindCSS
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// File size formatting
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 B"

  const k = 1024
  const sizes = ["B", "KB", "MB", "GB", "TB", "PB"]
  const i = Math.floor(Math.log(bytes) / Math.log(k))

  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`
}

// Date formatting
export function formatDate(date: Date | string): string {
  const d = new Date(date)
  return d.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  })
}

export function formatRelativeTime(date: Date | string): string {
  const d = new Date(date)
  const now = new Date()
  const diffInSeconds = Math.floor((now.getTime() - d.getTime()) / 1000)

  if (diffInSeconds < 60) {
    return "just now"
  }

  const diffInMinutes = Math.floor(diffInSeconds / 60)
  if (diffInMinutes < 60) {
    return `${diffInMinutes} minute${diffInMinutes > 1 ? 's' : ''} ago`
  }

  const diffInHours = Math.floor(diffInMinutes / 60)
  if (diffInHours < 24) {
    return `${diffInHours} hour${diffInHours > 1 ? 's' : ''} ago`
  }

  const diffInDays = Math.floor(diffInHours / 24)
  if (diffInDays < 30) {
    return `${diffInDays} day${diffInDays > 1 ? 's' : ''} ago`
  }

  return formatDate(date)
}

// File category detection
export function getFileCategory(extension: string, mimeType: string): import("@/types").FileCategory {
  const ext = extension.toLowerCase()
  const mime = mimeType.toLowerCase()

  // Document types
  if (['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt'].includes(ext) ||
      mime.includes('document') || mime.includes('text')) {
    return 'document'
  }

  // Image types
  if (['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp', '.ico'].includes(ext) ||
      mime.includes('image')) {
    return 'image'
  }

  // Video types
  if (['.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mkv'].includes(ext) ||
      mime.includes('video')) {
    return 'video'
  }

  // Audio types
  if (['.mp3', '.wav', '.ogg', '.flac', '.aac', '.m4a'].includes(ext) ||
      mime.includes('audio')) {
    return 'audio'
  }

  // Archive types
  if (['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2'].includes(ext) ||
      mime.includes('zip') || mime.includes('archive')) {
    return 'archive'
  }

  // Code types
  if (['.js', '.ts', '.jsx', '.tsx', '.html', '.css', '.py', '.java', '.cpp', '.c', '.cs', '.php', '.rb', '.go', '.rs', '.swift'].includes(ext) ||
      mime.includes('javascript') || mime.includes('json')) {
    return 'code'
  }

  // System types
  if (['.dll', '.exe', '.sys', '.bat', '.sh', '.app', '.deb', '.rpm'].includes(ext) ||
      mime.includes('application/x-executable')) {
    return 'system'
  }

  return 'other'
}

// File extension from filename
export function getFileExtension(filename: string): string {
  const lastDot = filename.lastIndexOf('.')
  return lastDot > 0 ? filename.substring(lastDot) : ''
}

// Validate file path
export function isValidPath(path: string): boolean {
  if (!path || path.trim().length === 0) {
    return false
  }

  // Check for invalid characters
  const invalidChars = /[<>:"|?*]/
  if (invalidChars.test(path)) {
    return false
  }

  // Check for path traversal attempts
  if (path.includes('..') || path.includes('~')) {
    return false
  }

  return true
}

// Calculate percentage
export function calculatePercentage(value: number, total: number): number {
  if (total === 0) return 0
  return Math.round((value / total) * 100)
}

// Debounce utility
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout | null = null

  return (...args: Parameters<T>) => {
    if (timeout) {
      clearTimeout(timeout)
    }

    timeout = setTimeout(() => {
      func(...args)
    }, wait)
  }
}

// Throttle utility
export function throttle<T extends (...args: any[]) => any>(
  func: T,
  limit: number
): (...args: Parameters<T>) => void {
  let inThrottle: boolean

  return (...args: Parameters<T>) => {
    if (!inThrottle) {
      func(...args)
      inThrottle = true
      setTimeout(() => inThrottle = false, limit)
    }
  }
}

// Generate unique ID
export function generateId(): string {
  return Math.random().toString(36).substring(2) + Date.now().toString(36)
}

// Deep clone utility
export function deepClone<T>(obj: T): T {
  if (obj === null || typeof obj !== 'object') {
    return obj
  }

  if (obj instanceof Date) {
    return new Date(obj.getTime()) as unknown as T
  }

  if (obj instanceof Array) {
    return obj.map(item => deepClone(item)) as unknown as T
  }

  if (typeof obj === 'object') {
    const clonedObj = {} as T
    for (const key in obj) {
      if (obj.hasOwnProperty(key)) {
        clonedObj[key] = deepClone(obj[key])
      }
    }
    return clonedObj
  }

  return obj
}

// Safe JSON parsing
export function safeJsonParse<T>(str: string, fallback: T): T {
  try {
    return JSON.parse(str) as T
  } catch {
    return fallback
  }
}

// Error handling utility
export function createError(message: string, code?: string): Error & { code?: string } {
  const error = new Error(message) as Error & { code?: string }
  if (code) {
    error.code = code
  }
  return error
}

// Retry utility
export async function retry<T>(
  fn: () => Promise<T>,
  maxAttempts: number = 3,
  delay: number = 1000
): Promise<T> {
  let lastError: Error

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await fn()
    } catch (error) {
      lastError = error as Error

      if (attempt === maxAttempts) {
        break
      }

      // Exponential backoff
      await new Promise(resolve => setTimeout(resolve, delay * Math.pow(2, attempt - 1)))
    }
  }

  throw lastError!
}

// Array utilities
export function chunk<T>(array: T[], size: number): T[][] {
  const chunks: T[][] = []
  for (let i = 0; i < array.length; i += size) {
    chunks.push(array.slice(i, i + size))
  }
  return chunks
}

export function groupBy<T, K extends keyof T>(array: T[], key: K): Record<string, T[]> {
  return array.reduce((groups, item) => {
    const group = String(item[key])
    groups[group] = groups[group] || []
    groups[group].push(item)
    return groups
  }, {} as Record<string, T[]>)
}

export function uniqueBy<T, K extends keyof T>(array: T[], key: K): T[] {
  const seen = new Set()
  return array.filter(item => {
    const value = item[key]
    if (seen.has(value)) {
      return false
    }
    seen.add(value)
    return true
  })
}