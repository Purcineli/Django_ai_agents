"""
logger.py
---------
Centralised logging configuration for the AI Django Factory.

Log files are written to ``logs/factory.log``.
Console output is colourised by level.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

_LOG_DIR = Path(__file__).resolve().parent
_LOG_FILE = _LOG_DIR / "factory.log"
_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

_COLOURS = {
    logging.DEBUG:    "\033[37m",    # white
    logging.INFO:     "\033[36m",    # cyan
    logging.WARNING:  "\033[33m",    # yellow
    logging.ERROR:    "\033[31m",    # red
    logging.CRITICAL: "\033[35m",    # magenta
}
_RESET = "\033[0m"


class _ColourFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        colour = _COLOURS.get(record.levelno, _RESET)
        record.levelname = f"{colour}{record.levelname}{_RESET}"
        return super().format(record)


def get_logger(name: str, level: int = logging.DEBUG) -> logging.Logger:
    """Return a named logger, configuring handlers on first call."""
    logger = logging.getLogger(f"factory.{name}")
    if logger.handlers:
        return logger  # already configured

    logger.setLevel(level)

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(
        _ColourFormatter("%(levelname)-8s %(name)s  %(message)s")
    )
    logger.addHandler(ch)

    # File handler (full debug log)
    fh = logging.FileHandler(_LOG_FILE, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)-8s %(name)s  %(message)s")
    )
    logger.addHandler(fh)

    logger.propagate = False
    return logger
