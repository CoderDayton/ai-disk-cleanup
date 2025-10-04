use serde::{Deserialize, Serialize};
use std::path::PathBuf;

/// Application configuration structure
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppConfig {
    pub max_file_size: u64,
    pub default_timeout: u64,
    pub enable_logging: bool,
    pub log_level: String,
    pub cache_directory: PathBuf,
    pub temp_directory: PathBuf,
    pub enable_notifications: bool,
    pub theme: ThemePreference,
    pub analysis: AnalysisConfig,
    pub security: SecurityConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AnalysisConfig {
    pub batch_size: usize,
    pub parallel_processing: bool,
    pub ai_timeout: u64,
    pub max_concurrent_requests: usize,
    pub enable_caching: bool,
    pub cache_ttl_seconds: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SecurityConfig {
    pub allow_system_directories: bool,
    pub require_confirmation: bool,
    pub enable_audit_trail: bool,
    pub backup_before_delete: bool,
    pub protected_patterns: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ThemePreference {
    Light,
    Dark,
    System,
}

impl Default for AppConfig {
    fn default() -> Self {
        let cache_dir = std::env::temp_dir().join("ai-disk-cleaner-cache");
        let temp_dir = std::env::temp_dir().join("ai-disk-cleaner-temp");

        Self {
            max_file_size: 1_000_000_000, // 1GB
            default_timeout: 30, // 30 seconds
            enable_logging: true,
            log_level: "info".to_string(),
            cache_directory: cache_dir,
            temp_directory: temp_dir,
            enable_notifications: true,
            theme: ThemePreference::System,
            analysis: AnalysisConfig::default(),
            security: SecurityConfig::default(),
        }
    }
}

impl Default for AnalysisConfig {
    fn default() -> Self {
        Self {
            batch_size: 1000,
            parallel_processing: true,
            ai_timeout: 60, // 60 seconds
            max_concurrent_requests: 5,
            enable_caching: true,
            cache_ttl_seconds: 3600, // 1 hour
        }
    }
}

impl Default for SecurityConfig {
    fn default() -> Self {
        Self {
            allow_system_directories: false,
            require_confirmation: true,
            enable_audit_trail: true,
            backup_before_delete: true,
            protected_patterns: vec![
                "*.exe".to_string(),
                "*.dll".to_string(),
                "*.sys".to_string(),
                "*.app".to_string(),
            ],
        }
    }
}

impl AppConfig {
    /// Load configuration from file or create default
    pub fn load_or_create() -> Self {
        // For now, return default config
        // In production, this would load from a config file
        Self::default()
    }

    /// Save configuration to file
    pub fn save(&self) -> anyhow::Result<()> {
        // For now, this is a no-op
        // In production, this would save to a config file
        Ok(())
    }

    /// Validate configuration settings
    pub fn validate(&self) -> anyhow::Result<()> {
        if self.max_file_size == 0 {
            anyhow::bail!("max_file_size must be greater than 0");
        }

        if self.default_timeout == 0 {
            anyhow::bail!("default_timeout must be greater than 0");
        }

        if self.analysis.batch_size == 0 {
            anyhow::bail!("analysis.batch_size must be greater than 0");
        }

        Ok(())
    }
}