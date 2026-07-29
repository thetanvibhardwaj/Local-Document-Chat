import logging
import os
import sys
from backend.utils.config import settings

def setup_logger(name: str) -> logging.Logger:
    """
    Configures and returns a logger instance that logs to both
    stdout and the designated log file path.
    """
    logger = logging.getLogger(name)
    
    # Avoid duplicate handlers if already configured
    if logger.hasHandlers():
        return logger
        
    logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
    )
    
    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File Handler
    try:
        log_dir = os.path.dirname(settings.log_file_path)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
            
        file_handler = logging.FileHandler(settings.log_file_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Failed to setup file logging handler: {e}", file=sys.stderr)
        
    return logger

# Export a default logger for quick use
logger = setup_logger("cognify_docs")
