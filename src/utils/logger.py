import logging
import sys
from datetime import datetime

def setup_logger(name: str = "SAP_BRIM_AGENT", level: str = "INFO") -> logging.Logger:
    """
    Setup a simple logger with just log level, timestamp and message.
    
    Args:
        name: Logger name
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(name)
    
    # Set log level
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(log_level)
    
    # Avoid duplicate handlers if logger already exists
    if logger.hasHandlers():
        logger.handlers.clear()
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    # Create simple formatter: [LEVEL] TIMESTAMP - MESSAGE
    formatter = logging.Formatter(
        fmt='[%(levelname)s] %(asctime)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Add formatter to handler
    console_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(console_handler)
    
    # Prevent propagation to avoid duplicate logs
    logger.propagate = False
    
    return logger

# Create default logger instance
logger = setup_logger()

# Convenience functions for direct usage
def debug(message: str):
    logger.debug(message)

def info(message: str):
    logger.info(message)

def warning(message: str):
    logger.warning(message)

def error(message: str):
    logger.error(message)

def critical(message: str):
    logger.critical(message)