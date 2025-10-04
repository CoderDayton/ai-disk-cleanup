// API client for communicating with the FastAPI backend
import type {
  AnalysisSession,
  AnalysisOptions,
  FileInfo,
  ApiResponse,
  PaginatedResponse
} from '@/types'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

class ApiClient {
  private baseUrl: string

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const url = `${this.baseUrl}${endpoint}`

    try {
      const response = await fetch(url, {
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
        ...options,
      })

      if (!response.ok) {
        throw new Error(`API request failed: ${response.status} ${response.statusText}`)
      }

      const data = await response.json()
      return {
        success: true,
        data,
        timestamp: new Date(),
      }
    } catch (error) {
      return {
        success: false,
        error: {
          code: 'NETWORK_ERROR',
          message: error instanceof Error ? error.message : 'Unknown error',
        },
        timestamp: new Date(),
      }
    }
  }

  // Analysis endpoints
  async startAnalysis(
    directoryPath: string,
    options: AnalysisOptions
  ): Promise<ApiResponse<{ analysis_id: string; file_count: number; estimated_duration: number }>> {
    return this.request('/api/v1/analysis/start', {
      method: 'POST',
      body: JSON.stringify({
        directory_path: directoryPath,
        options,
      }),
    })
  }

  async getAnalysisStatus(analysisId: string): Promise<ApiResponse<{
    status: string
    progress: number
    files_processed: number
    current_file?: string
    estimated_remaining?: number
  }>> {
    return this.request(`/api/v1/analysis/${analysisId}/status`)
  }

  async getAnalysisFiles(
    analysisId: string,
    page: number = 1,
    pageSize: number = 100,
    filters?: {
      category?: string
      minSize?: number
      maxSize?: string
      search?: string
    }
  ): Promise<ApiResponse<PaginatedResponse<FileInfo>>> {
    const params = new URLSearchParams({
      page: page.toString(),
      page_size: pageSize.toString(),
      ...filters,
    })

    return this.request(`/api/v1/analysis/${analysisId}/files?${params}`)
  }

  async cancelAnalysis(analysisId: string): Promise<ApiResponse<{ success: boolean }>> {
    return this.request(`/api/v1/analysis/${analysisId}/cancel`, {
      method: 'POST',
    })
  }

  async deleteFiles(analysisId: string, fileIds: string[]): Promise<ApiResponse<{
    success: boolean
    deleted_count: number
    space_saved: number
  }>> {
    return this.request(`/api/v1/analysis/${analysisId}/delete`, {
      method: 'POST',
      body: JSON.stringify({ file_ids: fileIds }),
    })
  }

  // Settings endpoints
  async getSettings(): Promise<ApiResponse<{
    openai_api_key: string
    analysis_preferences: any
    safety_settings: any
  }>> {
    return this.request('/api/v1/settings')
  }

  async updateSettings(settings: any): Promise<ApiResponse<{
    updated_fields: string[]
    validation_warnings: string[]
  }>> {
    return this.request('/api/v1/settings', {
      method: 'PUT',
      body: JSON.stringify(settings),
    })
  }

  // File operations
  async getFilePreview(analysisId: string, fileId: string): Promise<ApiResponse<{
    type: string
    content?: string
    url?: string
    metadata?: any
  }>> {
    return this.request(`/api/v1/analysis/${analysisId}/files/${fileId}/preview`)
  }

  // Health check
  async healthCheck(): Promise<ApiResponse<{
    status: string
    version: string
    timestamp: string
  }>> {
    return this.request('/api/v1/health')
  }
}

export const apiClient = new ApiClient()
export default ApiClient