use tracing::{Level, Subscriber};
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt, EnvFilter};

/// Initialize logging for the application
pub fn init_logging() -> anyhow::Result<()> {
    let filter = EnvFilter::try_from_default_env()
        .unwrap_or_else(|_| EnvFilter::new("info"));

    tracing_subscriber::registry()
        .with(filter)
        .with(tracing_subscriber::fmt::layer().with_target(false))
        .init();

    Ok(())
}

/// Setup tracing with custom configuration
pub fn setup_tracing(level: Level) -> anyhow::Result<()> {
    let filter = EnvFilter::from_default_env()
        .add_directive(level.into())
        .add_directive("ai_disk_cleaner=debug".parse()?);

    tracing_subscriber::registry()
        .with(filter)
        .with(tracing_subscriber::fmt::layer())
        .init();

    Ok(())
}

/// Get the current log level
pub fn get_log_level() -> Level {
    // This would read from configuration in a real implementation
    Level::INFO
}