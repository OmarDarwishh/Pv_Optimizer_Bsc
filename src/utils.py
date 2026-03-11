"""Utility functions for logging and application configuration."""
import logging
import os

def setup_logging(log_file: str = "logs/optimizer.log", level: int = logging.INFO) -> None:
    """
    Configures application-wide logging to output to both the console and a file.
    
    Args:
        log_file (str): The relative or absolute path to the log file.
        level (int): The logging threshold level (e.g., logging.INFO, logging.DEBUG).
    """
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(module)s] - %(message)s')

    file_handler = logging.FileHandler(log_file, mode='a')
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Get the root logger
    logger = logging.getLogger()
    logger.setLevel(level)
    
    # Prevent adding multiple handlers if setup_logging is called more than once
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)