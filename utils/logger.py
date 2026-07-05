"""utils/logger.py — structured logging"""
import sys
from loguru import logger
from config.settings import LOG_DIR

def setup_logger(name: str = "rppi"):
    logger.remove()
    fmt = ("<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
           "<level>{level: <8}</level> | "
           "<cyan>{name}</cyan>:<cyan>{function}</cyan> | "
           "<level>{message}</level>")
    logger.add(sys.stdout, format=fmt, level="INFO", colorize=True)
    logger.add(LOG_DIR / f"{name}.log", format=fmt, level="DEBUG",
               rotation="10 MB", retention="7 days", compression="zip")
    return logger

log = setup_logger()
