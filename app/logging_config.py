import logging
import sys

from app.config import settings


def setup_logging():
    level_name = settings.log_level.upper()
    log_level = getattr(logging, level_name, logging.INFO)

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    logger = logging.getLogger("aistreamradio")
    logger.setLevel(log_level)

    if not logger.handlers:
        logger.addHandler(handler)

    return logger


logger = setup_logging()
