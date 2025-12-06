"""Configuration helpers for the embedded telemetry toolkit."""

DEFAULT_LOG_DIR = "logs"
DEFAULT_LOG_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_default_config():
    """Return a placeholder default configuration mapping."""
    return {
        "log_dir": DEFAULT_LOG_DIR,
        "log_format": DEFAULT_LOG_FORMAT,
    }
