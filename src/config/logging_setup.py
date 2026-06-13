"""
SNTO — Structured logging setup (F6)
====================================
A single place to configure consistent, level-controlled logging for all
runners and scripts, replacing ad-hoc ``logging.basicConfig`` calls scattered
across the pipeline entry points.

Usage::

    from src.config.logging_setup import configure_logging
    logger = configure_logging()           # level from LOG_LEVEL env, default INFO
    logger = configure_logging("DEBUG")    # explicit override

Idempotent: calling it more than once does not stack duplicate handlers.
"""
from __future__ import annotations

import logging
import os

_LOG_FORMAT = "%(asctime)s  %(levelname)-8s  %(name)s — %(message)s"
_DATE_FORMAT = "%H:%M:%S"
_CONFIGURED = False


def resolve_level(level: str | int | None = None) -> int:
    """Resolve a logging level from an explicit value or the LOG_LEVEL env var."""
    if isinstance(level, int):
        return level
    name = (level or os.environ.get("LOG_LEVEL") or "INFO").upper()
    return getattr(logging, name, logging.INFO)


def configure_logging(
    level: str | int | None = None, force: bool = False
) -> logging.Logger:
    """Configure root logging once with a consistent format; return root logger.

    Args:
        level: explicit level name/int; falls back to LOG_LEVEL env, then INFO.
        force: reconfigure even if already configured (e.g. to change level).
    """
    global _CONFIGURED
    resolved = resolve_level(level)
    root = logging.getLogger()
    if _CONFIGURED and not force:
        root.setLevel(resolved)
        return root

    for handler in list(root.handlers):
        root.removeHandler(handler)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))
    root.addHandler(handler)
    root.setLevel(resolved)
    _CONFIGURED = True
    return root
