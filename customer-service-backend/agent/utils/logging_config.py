import logging
import os
from logging.handlers import TimedRotatingFileHandler


def setup_logging(level: int = logging.INFO, log_dir: str = "./logs"):

    os.makedirs(log_dir, exist_ok=True)
    
    # log_filename = f"app_{datetime.now().strftime('%Y%m%d')}.log"
    # log_filepath = os.path.join(log_dir, log_filename)
    log_filepath = os.path.join(log_dir, "app.log")

    logger = logging.getLogger()
    logger.setLevel(level)
    
    if logger.hasHandlers():
        logger.handlers.clear()
    
    file_formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler = TimedRotatingFileHandler(
        log_filepath,
        when="midnight",
        interval=1,
        backupCount=30,
        encoding='utf-8'
    )
    file_handler.suffix = "%Y%m%d" # for backup files
    file_handler.setLevel(level)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # to be removed in prod
    class AnsiColorFormatter(logging.Formatter):
        from typing import ClassVar
        COLORS: ClassVar[dict[int, str]] = {
            logging.DEBUG: "\033[36m",      # cyan
            # logging.INFO: "\033[32m",       # green
            logging.WARNING: "\033[33m",    # yellow
            logging.ERROR: "\033[31m",      # red
            logging.CRITICAL: "\033[1;31m"  # bold red
        }
        RESET: ClassVar[str] = "\033[0m"

        def format(self, record):
            color = self.COLORS.get(record.levelno, "")
            msg = super().format(record)
            return f"{color}{msg}{self.RESET}"
        
    console_formatter = AnsiColorFormatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    logger.info(f"logging initialized: {log_filepath}")
    return logger