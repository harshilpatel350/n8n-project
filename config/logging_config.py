from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def configure_logging(log_dir: str, level: str = "INFO") -> None:
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    log_file = Path(log_dir) / "app.log"

    format_str = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    root_logger = logging.getLogger()
    # Avoid adding duplicate handlers across re-imports / Streamlit reruns
    existing_file = None
    for h in root_logger.handlers:
        if isinstance(h, RotatingFileHandler):
            try:
                if Path(getattr(h, "baseFilename", "")).resolve() == log_file.resolve():
                    existing_file = h
                    break
            except Exception:
                continue

    if existing_file is not None:
        # Ensure level is applied
        root_logger.setLevel(level.upper())
        existing_file.setLevel(level.upper())
        return

    root_logger.setLevel(level.upper())

    file_handler = RotatingFileHandler(
        log_file, maxBytes=2_000_000, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(logging.Formatter(format_str, datefmt=date_format))
    file_handler.setLevel(level.upper())

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(format_str, datefmt=date_format))
    console_handler.setLevel(level.upper())

    root_logger.addHandler(file_handler)
    # Avoid adding a duplicate console handler
    has_console = any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers)
    if not has_console:
        root_logger.addHandler(console_handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
