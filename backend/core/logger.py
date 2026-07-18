import sys
import os
from loguru import logger
from backend.config import BASE_DIR

# Define the logs directory
LOGS_DIR = BASE_DIR / "backend" / "logs"
os.makedirs(LOGS_DIR, exist_ok=True)

# Define the log file path
LOG_FILE = LOGS_DIR / "sentix.log"

# Remove default logger that prints to stderr
logger.remove()

# Add a customized stdout logger (colorful and clear)
logger.add(
    sys.stdout,
    colorize=True,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level="INFO"
)

# Add a rotating file logger
# Max file size is set to 150 KB (approx 30k-50k LLM tokens) as requested
# It will keep a maximum of 2 rotated backup files.
logger.add(
    str(LOG_FILE),
    rotation="150 KB",
    retention=2,
    compression="zip",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}",
    level="DEBUG"
)

# Export the configured logger
__all__ = ["logger"]
