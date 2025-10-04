// Core application type definitions

// Base types
export interface BaseEntity {
  id: string;
  createdAt: Date;
  updatedAt: Date;
}

// File system types
export interface FileInfo extends BaseEntity {
  path: string;
  name: string;
  size: number;
  extension: string;
  mimeType: string;
  modifiedAt: Date;
  accessedAt: Date;
  isHidden: boolean;
  isSystem: boolean;
  isReadable: boolean;
  isWritable: boolean;
  category: FileCategory;
  aiRecommendation?: RecommendationInfo;
  safetyStatus: SafetyStatus;
  selectedForDeletion: boolean;
  preview?: FilePreview;
}

export interface FilePreview {
  type: 'image' | 'text' | 'binary' | 'unsupported';
  url?: string;
  content?: string;
  thumbnail?: string;
  metadata?: Record<string, any>;
}

export enum FileCategory {
  Document = 'document',
  Image = 'image',
  Video = 'video',
  Audio = 'audio',
  Archive = 'archive',
  Code = 'code',
  System = 'system',
  Other = 'other',
}

export enum SafetyStatus {
  Safe = 'safe',
  Caution = 'caution',
  Protected = 'protected',
  Dangerous = 'dangerous',
}

// AI Analysis types
export interface RecommendationInfo {
  action: 'delete' | 'keep' | 'review';
  confidence: number; // 0-100
  reasoning: string;
  category: string;
  estimatedSpaceSaved: number;
  riskFactors: string[];
  alternativeSuggestions?: string[];
}

export interface AnalysisSession extends BaseEntity {
  directoryPath: string;
  status: AnalysisStatus;
  startedAt: Date;
  completedAt?: Date;
  fileCount: number;
  filesProcessed: number;
  currentFile?: string;
  estimatedDuration?: number;
  estimatedRemaining?: number;
  progress: number; // 0-100
  options: AnalysisOptions;
  results?: AnalysisResults;
  error?: string;
}

export enum AnalysisStatus {
  Pending = 'pending',
  Running = 'running',
  Paused = 'paused',
  Completed = 'completed',
  Failed = 'failed',
  Cancelled = 'cancelled',
}

export interface AnalysisOptions {
  includeHiddenFiles: boolean;
  maxFileSize: number;
  excludePatterns: string[];
  includePatterns: string[];
  aiAnalysisEnabled: boolean;
  parallelProcessing: boolean;
  batchSize: number;
  enableCaching: boolean;
}

export interface AnalysisResults {
  totalFiles: number;
  totalSize: number;
  analyzedFiles: number;
  categories: CategorySummary[];
  recommendations: RecommendationSummary;
  largestFiles: FileInfo[];
  oldestFiles: FileInfo[];
  duplicates: FileGroup[];
  spaceAnalysis: SpaceAnalysis;
}

export interface CategorySummary {
  category: FileCategory;
  count: number;
  totalSize: number;
  averageSize: number;
  percentage: number;
}

export interface RecommendationSummary {
  safeToDelete: RecommendationGroup;
  reviewRecommended: RecommendationGroup;
  keepRecommended: RecommendationGroup;
  totalSpaceSaved: number;
  totalFilesAffected: number;
}

export interface RecommendationGroup {
  count: number;
  totalSize: number;
  files: FileInfo[];
  categories: string[];
}

export interface FileGroup {
  name: string;
  files: FileInfo[];
  totalSize: number;
  count: number;
}

export interface SpaceAnalysis {
  totalSpace: number;
  usedSpace: number;
  freeSpace: number;
  recoverableSpace: number;
  fileDistribution: CategorySummary[];
  sizeDistribution: SizeRange[];
}

export interface SizeRange {
  range: string;
  minSize: number;
  maxSize: number;
  count: number;
  totalSize: number;
  percentage: number;
}

// UI state types
export interface AppSettings {
  theme: 'light' | 'dark' | 'system';
  language: string;
  notifications: NotificationSettings;
  privacy: PrivacySettings;
  performance: PerformanceSettings;
  analysis: DefaultAnalysisSettings;
}

export interface NotificationSettings {
  enabled: boolean;
  progressUpdates: boolean;
  completionAlerts: boolean;
  errorAlerts: boolean;
  systemNotifications: boolean;
}

export interface PrivacySettings {
  telemetryEnabled: boolean;
  crashReporting: boolean;
  usageAnalytics: boolean;
  dataRetentionDays: number;
}

export interface PerformanceSettings {
  virtualScrolling: boolean;
  previewGeneration: boolean;
  concurrentProcessing: boolean;
  memoryLimit: number;
  cacheSize: number;
}

export interface DefaultAnalysisSettings {
  includeHiddenFiles: boolean;
  maxFileSize: number;
  excludePatterns: string[];
  aiAnalysisEnabled: boolean;
  autoStartAnalysis: boolean;
}

// API types
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: ApiError;
  message?: string;
  timestamp: Date;
}

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, any>;
  stack?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  totalCount: number;
  page: number;
  pageSize: number;
  totalPages: number;
  hasNext: boolean;
  hasPrevious: boolean;
}

// WebSocket types
export interface WebSocketMessage {
  type: string;
  data: any;
  timestamp: Date;
  sessionId?: string;
}

export interface ProgressUpdate extends WebSocketMessage {
  type: 'progress';
  data: {
    analysisId: string;
    progress: number;
    currentFile?: string;
    filesProcessed: number;
    totalFiles: number;
    estimatedRemaining?: number;
  };
}

export interface AnalysisComplete extends WebSocketMessage {
  type: 'complete';
  data: {
    analysisId: string;
    results: AnalysisResults;
  };
}

export interface AnalysisError extends WebSocketMessage {
  type: 'error';
  data: {
    analysisId: string;
    error: ApiError;
  };
}

// Component props types
export interface FileListProps {
  files: FileInfo[];
  loading?: boolean;
  selectedFiles: Set<string>;
  onFileSelect: (fileId: string, selected: boolean) => void;
  onFilePreview: (file: FileInfo) => void;
  onFileDelete: (fileId: string) => void;
  virtualScrolling?: boolean;
  height?: number;
  itemHeight?: number;
}

export interface AnalysisProgressProps {
  session: AnalysisSession;
  onCancel: () => void;
  onPause: () => void;
  onResume: () => void;
}

export interface RecommendationPanelProps {
  recommendations: RecommendationSummary;
  files: FileInfo[];
  onApplyRecommendations: (fileIds: string[]) => void;
  onRejectRecommendations: (fileIds: string[]) => void;
  onCustomSelection: (fileIds: string[]) => void;
}

// Store types
export interface AppState {
  currentAnalysis: AnalysisSession | null;
  files: FileInfo[];
  selectedFiles: Set<string>;
  settings: AppSettings;
  isLoading: boolean;
  error: string | null;
}

export interface AppActions {
  startAnalysis: (directory: string, options: AnalysisOptions) => Promise<void>;
  cancelAnalysis: () => Promise<void>;
  pauseAnalysis: () => Promise<void>;
  resumeAnalysis: () => Promise<void>;
  selectFiles: (fileIds: string[], selected: boolean) => void;
  selectAllFiles: () => void;
  deselectAllFiles: () => void;
  deleteFiles: (fileIds: string[]) => Promise<void>;
  updateSettings: (settings: Partial<AppSettings>) => void;
  clearError: () => void;
}

// Utility types
export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P];
};

export type Optional<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>;

export type RequiredBy<T, K extends keyof T> = T & Required<Pick<T, K>>;