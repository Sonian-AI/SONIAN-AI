"""
Custom logging module for SONIAN AI.
Configures hierarchical logging with file rotation, console output, and formatters.
Extensive setup for production-grade logging.
"""

import logging
import logging.handlers
from datetime import datetime
from config import settings

# Create root logger
root_logger = logging.getLogger()
root_logger.setLevel(getattr(logging, settings.LOG_LEVEL))

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(getattr(logging, settings.LOG_LEVEL))
console_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
console_handler.setFormatter(console_formatter)
root_logger.addHandler(console_handler)

# File handler with rotation
file_handler = logging.handlers.RotatingFileHandler(
    settings.LOG_FILE,
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
file_handler.setLevel(getattr(logging, settings.LOG_LEVEL))
file_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
)
file_handler.setFormatter(file_formatter)
root_logger.addHandler(file_handler)

# Custom logger factories
def get_logger(name: str) -> logging.Logger:
    """
    Factory for module-specific loggers.
    Adds context like module name.
    """
    logger = logging.getLogger(name)
    logger.propagate = False  # Avoid double-logging
    return logger

# Module-specific loggers (pre-configured for massiveness)
fetcher_logger = get_logger("data_fetchers")
calculator_logger = get_logger("calculators")
ai_logger = get_logger("ai_models")
wallet_logger = get_logger("wallet_manager")
transfer_logger = get_logger("transfer_executor")
web_logger = get_logger("web_app")

# Custom log levels and filters (extended)
class VolumeFilter(logging.Filter):
    """
    Custom filter for volume-related logs.
    Only logs if volume > threshold.
    """
    def __init__(self, threshold: float = 0):
        super().__init__()
        self.threshold = threshold
    
    def filter(self, record):
        if hasattr(record, 'volume'):
            return record.volume > self.threshold
        return True

# Apply filter to fetcher logger
fetcher_logger.addFilter(VolumeFilter(settings.MIN_VOLUME_THRESHOLD))

# Error handler decorator (padding for utils)
def log_errors(logger: logging.Logger):
    """
    Decorator to log exceptions in functions.
    Usage: @log_errors(wallet_logger)
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.exception(f"Error in {func.__name__}: {e}")
                raise
        return wrapper
    return decorator

# Performance logger (unused but for future)
class PerfLogger:
    """
    Logs execution times.
    """
    def __init__(self, logger):
        self.logger = logger
    
    def timeit(self, func):
        def wrapper(*args, **kwargs):
            start = datetime.now()
            result = func(*args, **kwargs)
            duration = (datetime.now() - start).total_seconds()
            self.logger.info(f"{func.__name__} took {duration}s")
            return result
        return wrapper

perf_logger = PerfLogger(calculator_logger)

# Initialization log
root_logger.info("SONIAN AI Logger initialized with level: %s", settings.LOG_LEVEL)

# Padding: Additional handlers for emails, etc. (mock)
def setup_email_handler():
    """
    Sets up SMTP handler for critical errors.
    Placeholder for production.
    """
    # Would use smtplib here
    pass

setup_email_handler()

# Export for use
__all__ = ['root_logger', 'get_logger', 'log_errors', 'perf_logger']
