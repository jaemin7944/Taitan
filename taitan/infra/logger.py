from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler


def init_logger(
    log_dir: Path,
    name: str = "taitan",
    level: str = "INFO",
):
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "titan.log"

    logger = logging.getLogger(name)

    # 중복 핸들러 방지
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    formatter = logging.Formatter(
        "[%(asctime)s][%(levelname)s][%(name)s] %(message)s"
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger
