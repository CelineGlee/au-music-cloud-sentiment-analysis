"""
===============================================================================
Team 81

Members:
- Adam McMillan (1393533)
- Ryan Kuang (1547320)
- Tim Shen (1673715)
- Yili Liu (883012)
- Yuting Cai (1492060)

===============================================================================
"""

import logging
import sys 

def get_logger(name, level=logging.INFO):
    """Configures and returns a logger instance. This ensures that all logs are consistent and formatted correctly."""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Only setup the handler if it doesn't already exist
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout) 
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger