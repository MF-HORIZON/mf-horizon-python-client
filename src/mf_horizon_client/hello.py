import logging

logger = logging.getLogger(__name__)


def greeting_text(name: str) -> str:
    logger.info(f"Making a greeting for {name}")
    return f"Hello, {name}!"
