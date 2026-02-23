import logging
import os
from datetime import datetime

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')

def setup_logging(log_level='INFO') -> logging.Logger:
    
    os.makedirs(LOG_DIR, exist_ok=True)

    log_filename = os.path.join(LOG_DIR, f'trading_bot_{datetime.now().strftime("%Y-%m-%d")}.log')

    log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Root logger
    logger=logging.getLogger("trading_bot")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Avoid duplicate handler on re-initialization
    if logger.handlers:
        return logger

    # File Handler
    fh = logging.FileHandler(log_filename,encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(log_format,datefmt = date_format))

    # Console Handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(logging.Formatter(log_format, datefmt=date_format))

    logger.addHandler(fh)
    logger.addHandler(ch)

    logger.info("Logging initialised → %s", log_filename)
    return logger