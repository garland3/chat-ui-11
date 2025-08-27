"""Logging manager for centralized structured logging.

Provides:
- Structured JSON logging to logs/app.jsonl
- OpenTelemetry integration when available
- Development and production logging configurations
- Central log file management
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
    from opentelemetry.instrumentation.logging import LoggingInstrumentor
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False


class JSONFormatter(logging.Formatter):
    """Format log records as JSON lines."""

    def format(self, record: logging.LogRecord) -> str:  # noqa: D401
        trace_id = span_id = None
        
        if OTEL_AVAILABLE:
            span = trace.get_current_span()
            if span and span.is_recording():
                sc = span.get_span_context()
                if sc.is_valid:
                    trace_id = f"{sc.trace_id:032x}"
                    span_id = f"{sc.span_id:016x}"

        entry: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "process_id": os.getpid(),
            "thread_id": record.thread,
            "thread_name": record.threadName,
        }
        if trace_id:
            entry["trace_id"] = trace_id
        if span_id:
            entry["span_id"] = span_id
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)

        # Add extra fields from log record
        excluded = {
            "name","msg","args","levelname","levelno","pathname","filename","module","lineno",
            "funcName","created","msecs","relativeCreated","thread","threadName","processName","process",
            "exc_info","exc_text","stack_info","getMessage"
        }
        for k, v in record.__dict__.items():
            if k not in excluded:
                entry[f"extra_{k}"] = v
        return json.dumps(entry, default=str)


class LoggingManager:
    """Manages centralized structured logging for the application."""

    def __init__(
        self, 
        service_name: str = "chat-ui-backend", 
        service_version: str = "1.0.0"
    ) -> None:
        self.service_name = service_name
        self.service_version = service_version
        self.is_development = self._is_development()
        self.log_level = self._get_log_level()
        self.logs_dir = self._get_logs_dir()
        self.log_file = self.logs_dir / "app.jsonl"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        if OTEL_AVAILABLE:
            self._setup_telemetry()
        self._setup_logging()

    def _is_development(self) -> bool:
        """Check if running in development mode."""
        return (
            os.getenv("DEBUG_MODE", "false").lower() == "true"
            or os.getenv("ENVIRONMENT", "production").lower() in {"dev", "development"}
        )

    def _get_log_level(self) -> int:
        """Get log level from config or environment."""
        try:
            from managers.config.config_manager import config_manager  # type: ignore
            level_name = getattr(config_manager.app_settings, "log_level", "INFO").upper()
        except Exception:  # noqa: BLE001
            level_name = os.getenv("LOG_LEVEL", "INFO").upper()
        level = getattr(logging, level_name, None)
        return level if isinstance(level, int) else logging.INFO

    def _get_logs_dir(self) -> Path:
        """Get the logs directory path."""
        if os.getenv("APP_LOG_DIR"):
            return Path(os.getenv("APP_LOG_DIR"))
        else:
            # This file: backend/managers/logging/logging_manager.py -> project root is 3 levels up
            project_root = Path(__file__).resolve().parents[3]
            return project_root / "logs"

    def _setup_telemetry(self) -> None:
        """Set up OpenTelemetry tracing."""
        if not OTEL_AVAILABLE:
            return
        resource = Resource.create(
            {
                SERVICE_NAME: self.service_name,
                SERVICE_VERSION: self.service_version,
                "environment": "development" if self.is_development else "production",
            }
        )
        trace.set_tracer_provider(TracerProvider(resource=resource))

    def _setup_logging(self) -> None:
        """Configure structured logging to JSON file."""
        root = logging.getLogger()
        # Remove all existing handlers to start fresh
        for h in root.handlers[:]:
            root.removeHandler(h)

        # Set up JSON file logging
        json_formatter = JSONFormatter()
        file_handler = logging.FileHandler(self.log_file, encoding="utf-8")
        file_handler.setFormatter(json_formatter)
        file_handler.setLevel(self.log_level)
        root.addHandler(file_handler)
        root.setLevel(self.log_level)

        # Suppress noisy third-party library logs
        self._suppress_noisy_loggers()

        # In development, also add console logging for warnings and above
        if self.is_development:
            console = logging.StreamHandler()
            console.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
            console.setLevel(logging.WARNING)
            root.addHandler(console)

        # Set up OpenTelemetry logging instrumentation
        if OTEL_AVAILABLE:
            LoggingInstrumentor().instrument(set_logging_format=False)

    def _suppress_noisy_loggers(self) -> None:
        """Suppress logs from noisy third-party libraries."""
        noisy_loggers = [
            "LiteLLM", "litellm",
            "httpx", "urllib3.connectionpool",
            "auth_utils", "message_processor",
            "session", "callbacks", "utils",
            "banner_client", "middleware", "mcp_client"
        ]
        
        for name in noisy_loggers:
            lg = logging.getLogger(name)
            lg.setLevel(logging.ERROR)
            lg.propagate = False
            for h in list(lg.handlers):
                lg.removeHandler(h)
            lg.addHandler(logging.NullHandler())

    def instrument_fastapi(self, app) -> None:  # noqa: ANN001
        """Add OpenTelemetry instrumentation to FastAPI app."""
        if OTEL_AVAILABLE:
            FastAPIInstrumentor.instrument_app(app)

    def instrument_httpx(self) -> None:
        """Add OpenTelemetry instrumentation to HTTPX."""
        if OTEL_AVAILABLE:
            HTTPXClientInstrumentor().instrument()

    def get_log_file_path(self) -> Path:
        """Get the path to the main log file."""
        return self.log_file

    def read_logs(self, lines: int = 100) -> list[Dict[str, Any]]:
        """Read the most recent log entries."""
        if not self.log_file.exists():
            return []
        
        entries: list[Dict[str, Any]] = []
        try:
            with self.log_file.open("r", encoding="utf-8") as f:
                data = f.readlines()[-lines:]
            for ln in data:
                ln = ln.strip()
                if not ln:
                    continue
                try:
                    entries.append(json.loads(ln))
                except json.JSONDecodeError:
                    continue
        except Exception as e:  # noqa: BLE001
            logging.getLogger(__name__).error(f"Error reading logs: {e}")
        return entries

    def get_log_stats(self) -> Dict[str, Any]:
        """Get statistics about the log file."""
        if not self.log_file.exists():
            return {"file_exists": False, "file_size": 0, "line_count": 0, "last_modified": None}
        
        try:
            stat = self.log_file.stat()
            with self.log_file.open("r", encoding="utf-8") as f:
                line_count = sum(1 for _ in f)
            return {
                "file_exists": True,
                "file_size": stat.st_size,
                "line_count": line_count,
                "last_modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                "file_path": str(self.log_file),
            }
        except Exception as e:  # noqa: BLE001
            logging.getLogger(__name__).error(f"Error getting log stats: {e}")
            return {"file_exists": True, "error": str(e)}

    def clear_logs(self) -> None:
        """Clear the current log file."""
        try:
            self.log_file.write_text("NEW LOG\n", encoding="utf-8")
            logging.getLogger(__name__).info("Log file cleared")
        except Exception as e:  # noqa: BLE001
            logging.getLogger(__name__).error(f"Error clearing log file: {e}")

    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """Get a logger instance. Use this instead of logging.getLogger()."""
        return logging.getLogger(name)