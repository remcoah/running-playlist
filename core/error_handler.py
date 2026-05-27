from __future__ import annotations

import logging
from typing import Any, Callable, TypeVar

logger = logging.getLogger("running_playlist")

T = TypeVar("T")


def configure_logging() -> None:
    """Configure application-wide logging to file. Call once at the start of main()."""
    import config.settings as settings
    settings.LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=str(settings.LOG_PATH),
        level=getattr(logging, settings.LOG_LEVEL, logging.DEBUG),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def safe_call(
    fn: Callable[..., T],
    *args: Any,
    fallback: T,
    label: str | None = None,
    **kwargs: Any,
) -> T:
    """Call fn(*args, **kwargs) and return its result, or log the error and return fallback if it raises."""
    name = label or fn.__name__
    try:
        return fn(*args, **kwargs)
    except Exception as exc:
        logger.error("%s failed: %s", name, exc)
        return fallback


def warn(message: str) -> None:
    """Log a warning message."""
    logger.warning(message)


def info(message: str) -> None:
    """Log an informational message."""
    logger.info(message)
