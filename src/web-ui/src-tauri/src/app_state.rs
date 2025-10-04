use crate::utils::config::AppConfig;
use std::sync::Arc;
use tokio::sync::RwLock;

/// Shared application state
#[derive(Debug, Clone)]
pub struct AppState {
    pub config: Arc<RwLock<AppConfig>>,
}

impl AppState {
    /// Create new application state
    pub fn new() -> Self {
        let config = AppConfig::load_or_create();
        Self {
            config: Arc::new(RwLock::new(config)),
        }
    }

    /// Get configuration reference
    pub async fn get_config(&self) -> AppConfig {
        self.config.read().await.clone()
    }

    /// Update configuration
    pub async fn update_config<F>(&self, updater: F) -> anyhow::Result<()>
    where
        F: FnOnce(&mut AppConfig),
    {
        let mut config = self.config.write().await;
        updater(&mut config);
        config.save()?;
        Ok(())
    }
}