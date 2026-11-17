import logging
import json
import sys
import time
from typing import Any, Dict, Optional
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """Format logs as structured JSON objects for production ingestion."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Include custom extra fields if present
        for key in ("request_id", "method", "path", "status_code", "duration_ms", "provider", "item_id", "chunks_count"):
            val = getattr(record, key, None)
            if val is not None:
                log_data[key] = val

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


class ReadableFormatter(logging.Formatter):
    """Formatted human-readable output for development."""

    COLORS = {
        "DEBUG": "\033[36m",    # Cyan
        "INFO": "\033[32m",     # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",    # Red
        "CRITICAL": "\033[35m", # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        req_id = getattr(record, "request_id", None)
        req_part = f" [{req_id[:8]}]" if req_id else ""
        dur = getattr(record, "duration_ms", None)
        dur_part = f" ({dur:.1f}ms)" if dur is not None else ""

        return f"{color}[{timestamp}] [{record.levelname:<7}]{self.RESET}{req_part} {record.name}: {record.getMessage()}{dur_part}"


def setup_logger(name: str = "turium_inbox", use_json: bool = False) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter() if use_json else ReadableFormatter())
        logger.addHandler(handler)

    return logger


logger = setup_logger()
