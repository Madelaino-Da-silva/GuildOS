"""
Centralized logging configuration for GuildOS.

Every component (API, Discord bot, AI services, scheduler) calls
`get_logger(__name__)` to obtain a properly configured logger. Logs are
written both to stdout (for `docker logs`) and to rotating files on disk,
split by category so staff can audit AI decisions, moderator actions, and
errors independently.
"""
from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.core.config import settings

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_CONFIGURED = False


def _build_file_handler(filename: str, level: int) -> RotatingFileHandler:
    log_dir = Path(settings.LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        log_dir / filename,
        maxBytes=5 * 1024 * 1024,  # 5 MB per file
        backupCount=5,
        encoding="utf-8",
    )
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT, _DATE_FORMAT))
    return handler


def configure_logging() -> None:
    """Configure the root logger once for the whole process."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    root = logging.getLogger()
    root.setLevel(settings.LOG_LEVEL)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(_LOG_FORMAT, _DATE_FORMAT))
    root.addHandler(console_handler)

    # General application log (everything)
    root.addHandler(_build_file_handler("guildos.log", logging.INFO))

    # Errors only, kept separately so ops can tail one small file
    root.addHandler(_build_file_handler("errors.log", logging.ERROR))

    # Dedicated logger for AI decisions (recruitment scores, mod flags, etc.)
    ai_logger = logging.getLogger("guildos.ai")
    ai_logger.addHandler(_build_file_handler("ai_decisions.log", logging.INFO))

    # Dedicated logger for moderator / staff actions
    mod_logger = logging.getLogger("guildos.moderation")
    mod_logger.addHandler(_build_file_handler("moderation.log", logging.INFO))

    # Dedicated logger for Discord command usage
    cmd_logger = logging.getLogger("guildos.commands")
    cmd_logger.addHandler(_build_file_handler("commands.log", logging.INFO))

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a module-level logger, ensuring logging is configured first."""
    configure_logging()
    return logging.getLogger(name)
