import sys

from loguru import logger


def set_up_logging():
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | ID: <cyan>{extra}</cyan> ",
    )
