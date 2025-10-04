// Global application state management with Zustand
import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import type { AnalysisSession, FileInfo, AppSettings } from '@/types'

interface AppState {
  // Current analysis
  currentAnalysis: AnalysisSession | null
  analysisHistory: AnalysisSession[]

  // File management
  files: FileInfo[]
  selectedFiles: Set<string>
  fileFilters: {
    category: string | null
    minSize: number | null
    maxSize: number | null
    searchQuery: string
  }

  // UI state
  isLoading: boolean
  error: string | null
  activeView: 'dashboard' | 'analysis' | 'files' | 'settings'

  // Settings
  settings: AppSettings

  // WebSocket connection
  isConnected: boolean
}

interface AppActions {
  // Analysis actions
  setCurrentAnalysis: (analysis: AnalysisSession | null) => void
  updateAnalysisProgress: (progress: number, currentFile?: string) => void
  completeAnalysis: (results: any) => void
  cancelAnalysis: () => void

  // File actions
  setFiles: (files: FileInfo[]) => void
  selectFiles: (fileIds: string[], selected: boolean) => void
  selectAllFiles: () => void
  deselectAllFiles: () => void
  updateFileFilters: (filters: Partial<AppState['fileFilters']>) => void

  // UI actions
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  setActiveView: (view: AppState['activeView']) => void

  // Settings actions
  updateSettings: (settings: Partial<AppSettings>) => void
  resetSettings: () => void

  // Connection actions
  setConnected: (connected: boolean) => void

  // Utility actions
  clearError: () => void
  reset: () => void
}

// Default settings
const defaultSettings: AppSettings = {
  theme: 'system',
  language: 'en',
  notifications: {
    enabled: true,
    progressUpdates: true,
    completionAlerts: true,
    errorAlerts: true,
    systemNotifications: true,
  },
  privacy: {
    telemetryEnabled: false,
    crashReporting: true,
    usageAnalytics: false,
    dataRetentionDays: 30,
  },
  performance: {
    virtualScrolling: true,
    previewGeneration: true,
    concurrentProcessing: true,
    memoryLimit: 1024, // 1GB
    cacheSize: 512, // 512MB
  },
  analysis: {
    includeHiddenFiles: false,
    maxFileSize: 1024 * 1024 * 1024, // 1GB
    excludePatterns: ['node_modules', '.git', '.vscode', '.idea'],
    aiAnalysisEnabled: true,
    autoStartAnalysis: false,
  },
}

export const useAppStore = create<AppState & AppActions>()(
  persist(
    (set, get) => ({
      // Initial state
      currentAnalysis: null,
      analysisHistory: [],
      files: [],
      selectedFiles: new Set(),
      fileFilters: {
        category: null,
        minSize: null,
        maxSize: null,
        searchQuery: '',
      },
      isLoading: false,
      error: null,
      activeView: 'dashboard',
      settings: defaultSettings,
      isConnected: false,

      // Analysis actions
      setCurrentAnalysis: (analysis) => {
        set({ currentAnalysis: analysis })
        if (analysis) {
          set((state) => ({
            analysisHistory: [analysis, ...state.analysisHistory.slice(0, 9)], // Keep last 10
          }))
        }
      },

      updateAnalysisProgress: (progress, currentFile) => {
        set((state) => {
          if (!state.currentAnalysis) return state

          return {
            currentAnalysis: {
              ...state.currentAnalysis,
              progress,
              currentFile,
              filesProcessed: Math.floor((progress / 100) * state.currentAnalysis.fileCount),
            },
          }
        })
      },

      completeAnalysis: (results) => {
        set((state) => ({
          currentAnalysis: state.currentAnalysis
            ? {
                ...state.currentAnalysis,
                status: 'completed',
                progress: 100,
                completedAt: new Date(),
                results,
              }
            : null,
          isLoading: false,
        }))
      },

      cancelAnalysis: () => {
        set((state) => ({
          currentAnalysis: state.currentAnalysis
            ? {
                ...state.currentAnalysis,
                status: 'cancelled',
              }
            : null,
          isLoading: false,
        }))
      },

      // File actions
      setFiles: (files) => {
        set({ files })
        // Reset selections when new files are loaded
        set({ selectedFiles: new Set() })
      },

      selectFiles: (fileIds, selected) => {
        set((state) => {
          const newSelected = new Set(state.selectedFiles)
          fileIds.forEach((id) => {
            if (selected) {
              newSelected.add(id)
            } else {
              newSelected.delete(id)
            }
          })
          return { selectedFiles: newSelected }
        })
      },

      selectAllFiles: () => {
        set((state) => ({
          selectedFiles: new Set(state.files.map((file) => file.id)),
        }))
      },

      deselectAllFiles: () => {
        set({ selectedFiles: new Set() })
      },

      updateFileFilters: (filters) => {
        set((state) => ({
          fileFilters: { ...state.fileFilters, ...filters },
        }))
      },

      // UI actions
      setLoading: (loading) => {
        set({ isLoading: loading })
      },

      setError: (error) => {
        set({ error })
      },

      setActiveView: (view) => {
        set({ activeView: view })
      },

      // Settings actions
      updateSettings: (newSettings) => {
        set((state) => ({
          settings: { ...state.settings, ...newSettings },
        }))
      },

      resetSettings: () => {
        set({ settings: defaultSettings })
      },

      // Connection actions
      setConnected: (connected) => {
        set({ isConnected: connected })
      },

      // Utility actions
      clearError: () => {
        set({ error: null })
      },

      reset: () => {
        set({
          currentAnalysis: null,
          files: [],
          selectedFiles: new Set(),
          fileFilters: {
            category: null,
            minSize: null,
            maxSize: null,
            searchQuery: '',
          },
          isLoading: false,
          error: null,
          activeView: 'dashboard',
        })
      },
    }),
    {
      name: 'ai-disk-cleaner-store',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        settings: state.settings,
        analysisHistory: state.analysisHistory,
        activeView: state.activeView,
      }),
    }
  )
)

// Selectors for common use cases
export const useCurrentAnalysis = () => useAppStore((state) => state.currentAnalysis)
export const useFiles = () => useAppStore((state) => state.files)
export const useSelectedFiles = () => useAppStore((state) => state.selectedFiles)
export const useFileFilters = () => useAppStore((state) => state.fileFilters)
export const useIsLoading = () => useAppStore((state) => state.isLoading)
export const useError = () => useAppStore((state) => state.error)
export const useSettings = () => useAppStore((state) => state.settings)
export const useIsConnected = () => useAppStore((state) => state.isConnected)
export const useActiveView = () => useAppStore((state) => state.activeView)