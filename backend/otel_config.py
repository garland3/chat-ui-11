"""OpenTelemetry configuration and setup for unified logging.

This module provides:
- Structured JSON logging with OpenTelemetry
- Environment-based log level configuration
- File-based logging to a common location
- Easy upgrade path to dedicated OpenTelemetry server
- Integration with existing admin dashboard
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        # Get span context if available
        span = trace.get_current_span()
        trace_id = None
        span_id = None
        
        if span and span.is_recording():
            span_context = span.get_span_context()
            if span_context.is_valid:
                trace_id = format(span_context.trace_id, '032x')
                span_id = format(span_context.span_id, '016x')
        
        # Build log entry
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'process_id': os.getpid(),
            'thread_id': record.thread,
            'thread_name': record.threadName,
        }
        
        # Add trace context if available
        if trace_id:
            log_entry['trace_id'] = trace_id
        if span_id:
            log_entry['span_id'] = span_id
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in {
                'name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 'filename',
                'module', 'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                'thread', 'threadName', 'processName', 'process', 'exc_info', 'exc_text',
                'stack_info', 'getMessage'
            }:
                log_entry[f'extra_{key}'] = value
        
        return json.dumps(log_entry, default=str)


class OpenTelemetryConfig:
    """Configuration and setup for OpenTelemetry logging."""
    
    def __init__(self, service_name: str = "chat-ui-backend", service_version: str = "1.0.0"):
        self.service_name = service_name
        self.service_version = service_version
        self.is_development = self._is_development()
        self.log_level = self._get_log_level()
        self.logs_dir = Path("logs")
        self.log_file = self.logs_dir / "app.jsonl"  # JSON Lines format
        
        # Ensure logs directory exists
        self.logs_dir.mkdir(exist_ok=True)
        
        self._setup_telemetry()
        self._setup_logging()
    
    def _is_development(self) -> bool:
        """Check if running in development mode."""
        return os.getenv("DEBUG_MODE", "false").lower() == "true" or \
               os.getenv("ENVIRONMENT", "production").lower() in ("dev", "development")
    
    def _get_log_level(self) -> int:
        """Get log level based on environment."""
        if self.is_development:
            # In development, log everything for debugging
            return logging.DEBUG
        else:
            # In production, only log info and above for performance
            return logging.INFO
    
    def _setup_telemetry(self):
        """Setup OpenTelemetry tracer."""
        resource = Resource.create({
            SERVICE_NAME: self.service_name,
            SERVICE_VERSION: self.service_version,
            "environment": "development" if self.is_development else "production"
        })
        
        tracer_provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(tracer_provider)
        
        # In the future, this can be easily extended to send to an OpenTelemetry server:
        # from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        # otlp_exporter = OTLPSpanExporter(endpoint="http://otel-server:4317")
        # tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
    
    def _setup_logging(self):
        """Setup structured logging with OpenTelemetry integration."""
        # Clear any existing handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Create JSON formatter
        json_formatter = JSONFormatter()
        
        # File handler for JSON logs
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setFormatter(json_formatter)
        file_handler.setLevel(self.log_level)
        
        # Add file handler to root (gets everything)
        root_logger.addHandler(file_handler)
        root_logger.setLevel(self.log_level)
        
        # Console handler for development
        console_handler = None
        if self.is_development:
            # In development, show human-readable logs on console with higher threshold
            console_handler = logging.StreamHandler()
            console_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(console_formatter)
            console_handler.setLevel(logging.WARNING)  # Only warnings+ to console
            root_logger.addHandler(console_handler)
            
            # Configure specific noisy loggers to be even quieter on console
            noisy_loggers = [
                'httpx', 'urllib3.connectionpool', 'auth_utils', 'message_processor',
                'session', 'callbacks', 'utils', 'banner_client', 'middleware', 'mcp_client'
            ]
            
            for logger_name in noisy_loggers:
                logger = logging.getLogger(logger_name)
                logger.setLevel(logging.DEBUG)  # Accept all for file logging
                # Don't add handlers - let them propagate to root for file, but filter console
        
        # Instrument logging with OpenTelemetry
        LoggingInstrumentor().instrument(set_logging_format=False)
    
    def instrument_fastapi(self, app):
        """Instrument FastAPI application with OpenTelemetry."""
        FastAPIInstrumentor.instrument_app(app)
    
    def instrument_httpx(self):
        """Instrument HTTPX client with OpenTelemetry."""
        HTTPXClientInstrumentor().instrument()
    
    def get_log_file_path(self) -> Path:
        """Get the path to the current log file."""
        return self.log_file
    
    def read_logs(self, lines: int = 100) -> list[Dict[str, Any]]:
        """Read recent logs from the JSON log file."""
        logs = []
        
        if not self.log_file.exists():
            return logs
        
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                # Read from the end of the file
                all_lines = f.readlines()
                recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
                
                for line in recent_lines:
                    line = line.strip()
                    if line:
                        try:
                            log_entry = json.loads(line)
                            logs.append(log_entry)
                        except json.JSONDecodeError:
                            # Skip malformed JSON lines
                            continue
        except Exception as e:
            # Log the error, but don't fail the whole operation
            logging.getLogger(__name__).error(f"Error reading logs: {e}")
        
        return logs
    
    def get_log_stats(self) -> Dict[str, Any]:
        """Get statistics about the log file."""
        if not self.log_file.exists():
            return {
                "file_exists": False,
                "file_size": 0,
                "line_count": 0,
                "last_modified": None
            }
        
        try:
            stat = self.log_file.stat()
            
            # Count lines
            line_count = 0
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for _ in f:
                    line_count += 1
            
            return {
                "file_exists": True,
                "file_size": stat.st_size,
                "line_count": line_count,
                "last_modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                "file_path": str(self.log_file)
            }
        except Exception as e:
            logging.getLogger(__name__).error(f"Error getting log stats: {e}")
            return {
                "file_exists": True,
                "error": str(e)
            }


# Global instance
otel_config: Optional[OpenTelemetryConfig] = None


def setup_opentelemetry(service_name: str = "chat-ui-backend", service_version: str = "1.0.0") -> OpenTelemetryConfig:
    """Setup OpenTelemetry configuration."""
    global otel_config
    otel_config = OpenTelemetryConfig(service_name, service_version)
    return otel_config


def get_otel_config() -> Optional[OpenTelemetryConfig]:
    """Get the global OpenTelemetry configuration."""
    return otel_config