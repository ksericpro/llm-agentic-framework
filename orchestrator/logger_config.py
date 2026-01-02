import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logger(name: str = "agentic_pipeline", log_file: str = "logs/app.log", level=logging.INFO):
    """
    Sets up a logger with both console and rotating file handlers.
    
    Args:
        name: Name of the logger
        log_file: Path to the log file
        level: Logging level (default: INFO)
    """
    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Prevent adding handlers multiple times if setup_logger is called again
    if logger.handlers:
        return logger

    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_formatter = logging.Formatter(
        '%(levelname)s: %(message)s'
    )

    # Rotating File Handler (Max 5MB per file, keep 5 backups)
    file_handler = RotatingFileHandler(
        log_file, 
        maxBytes=5 * 1024 * 1024, 
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(level)

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(level)

    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # If this is the root or main logger, prevent propagation to avoid duplicate logs 
    # if basicConfig has been called elsewhere
    logger.propagate = False

    return logger

# Create a default logger instance for convenience
logger = setup_logger()
