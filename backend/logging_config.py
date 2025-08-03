"""
Comprehensive logging configuration module for chat-ui-11.

This module provides:
- Centralized logging setup with environment-based configuration
- SQLite database logging for LLM calls
- Enhanced error handling with tracebacks
- Admin access to logs and LLM call history
"""

import logging
import logging.handlers
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import config_manager


class DatabaseHandler(logging.Handler):
    """Custom logging handler that writes log records to SQLite database."""
    
    def __init__(self, db_path: str):
        super().__init__()
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize the logging database with required tables."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS app_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        level TEXT NOT NULL,
                        logger_name TEXT NOT NULL,
                        message TEXT NOT NULL,
                        module TEXT,
                        function TEXT,
                        line_number INTEGER,
                        traceback TEXT,
                        user_email TEXT,
                        session_id TEXT
                    )
                """)
                conn.commit()
        except Exception as e:
            # Fallback to console logging if database fails
            print(f"Failed to initialize logging database: {e}", file=sys.stderr)
    
    def emit(self, record):
        """Emit a log record to the database."""
        try:
            # Format the record
            msg = self.format(record)
            
            # Extract additional information
            traceback_text = None
            if record.exc_info:
                import traceback
                traceback_text = ''.join(traceback.format_exception(*record.exc_info))
            
            # Get user context if available
            user_email = getattr(record, 'user_email', None)
            session_id = getattr(record, 'session_id', None)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO app_logs 
                    (timestamp, level, logger_name, message, module, function, line_number, traceback, user_email, session_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    datetime.fromtimestamp(record.created).isoformat(),
                    record.levelname,
                    record.name,
                    msg,
                    record.module,
                    record.funcName,
                    record.lineno,
                    traceback_text,
                    user_email,
                    session_id
                ))
                conn.commit()
        except Exception:
            # Don't let logging errors break the application
            self.handleError(record)


class LLMCallLogger:
    """Logger for LLM API calls and responses."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize the LLM call logging database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS llm_calls (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        user_email TEXT NOT NULL,
                        session_id TEXT,
                        model_name TEXT NOT NULL,
                        input_messages TEXT NOT NULL,
                        output_response TEXT NOT NULL,
                        tool_calls TEXT,
                        selected_tools TEXT,
                        processing_time_ms INTEGER,
                        token_count_input INTEGER,
                        token_count_output INTEGER,
                        error_message TEXT,
                        api_endpoint TEXT
                    )
                """)
                conn.commit()
        except Exception as e:
            print(f"Failed to initialize LLM call database: {e}", file=sys.stderr)
    
    def log_llm_call(
        self,
        user_email: str,
        model_name: str,
        input_messages: List[Dict[str, Any]],
        output_response: str,
        session_id: Optional[str] = None,
        tool_calls: Optional[str] = None,
        selected_tools: Optional[List[str]] = None,
        processing_time_ms: Optional[int] = None,
        error_message: Optional[str] = None,
        api_endpoint: Optional[str] = None
    ):
        """Log an LLM API call with full input and output."""
        try:
            import json
            
            # Serialize complex data
            input_json = json.dumps(input_messages)
            selected_tools_json = json.dumps(selected_tools) if selected_tools else None
            
            # Estimate token counts (rough approximation)
            token_count_input = self._estimate_tokens(input_json)
            token_count_output = self._estimate_tokens(output_response)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO llm_calls 
                    (timestamp, user_email, session_id, model_name, input_messages, output_response,
                     tool_calls, selected_tools, processing_time_ms, token_count_input, 
                     token_count_output, error_message, api_endpoint)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    datetime.now().isoformat(),
                    user_email,
                    session_id,
                    model_name,
                    input_json,
                    output_response,
                    tool_calls,
                    selected_tools_json,
                    processing_time_ms,
                    token_count_input,
                    token_count_output,
                    error_message,
                    api_endpoint
                ))
                conn.commit()
        except Exception as e:
            # Log the error but don't break the main flow
            logging.getLogger(__name__).error(f"Failed to log LLM call: {e}", exc_info=True)
    
    def _estimate_tokens(self, text: str) -> int:
        """Rough token count estimation (4 characters per token average)."""
        if not text:
            return 0
        return len(text) // 4
    
    def get_llm_calls(
        self,
        user_email: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Retrieve LLM call logs with optional filtering."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                if user_email:
                    cursor = conn.execute("""
                        SELECT * FROM llm_calls 
                        WHERE user_email = ?
                        ORDER BY timestamp DESC 
                        LIMIT ? OFFSET ?
                    """, (user_email, limit, offset))
                else:
                    cursor = conn.execute("""
                        SELECT * FROM llm_calls 
                        ORDER BY timestamp DESC 
                        LIMIT ? OFFSET ?
                    """, (limit, offset))
                
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logging.getLogger(__name__).error(f"Failed to retrieve LLM calls: {e}", exc_info=True)
            return []


def setup_logging():
    """Setup comprehensive logging configuration."""
    try:
        # Get configuration
        app_settings = config_manager.app_settings
        log_level = getattr(logging, app_settings.log_level.upper(), logging.INFO)
        
        # Ensure logs directory exists
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)
        
        # Clear any existing handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s'
        )
        simple_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # File handler for main application logs
        file_handler = logging.handlers.RotatingFileHandler(
            logs_dir / "app.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(detailed_formatter)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(simple_formatter)
        
        # Database handler for persistent logging
        db_handler = DatabaseHandler(str(logs_dir / "app_logs.db"))
        db_handler.setLevel(logging.WARNING)  # Only log warnings and errors to DB
        db_handler.setFormatter(detailed_formatter)
        
        # Error file handler for critical errors
        error_handler = logging.FileHandler(logs_dir / "errors.log")
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(detailed_formatter)
        
        # Configure root logger
        root_logger.setLevel(log_level)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
        root_logger.addHandler(db_handler)
        root_logger.addHandler(error_handler)
        
        # Set up specific loggers
        setup_specific_loggers(log_level)
        
        # Initialize LLM call logger
        global llm_call_logger
        llm_call_logger = LLMCallLogger(str(logs_dir / "llm_calls.db"))
        
        logging.info(f"Logging configured successfully with level: {app_settings.log_level}")
        return True
        
    except Exception as e:
        print(f"Failed to setup logging: {e}", file=sys.stderr)
        return False


def setup_specific_loggers(log_level):
    """Configure specific loggers for different modules."""
    # FastAPI and Uvicorn loggers
    logging.getLogger("fastapi").setLevel(log_level)
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    
    # Reduce noise from HTTP libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("websockets").setLevel(logging.WARNING)


def get_llm_call_logger() -> LLMCallLogger:
    """Get the global LLM call logger instance."""
    return llm_call_logger


def log_with_context(logger, level, message, user_email=None, session_id=None, **kwargs):
    """Log a message with user and session context."""
    record = logger.makeRecord(
        logger.name, level, "", 0, message, (), None, 
        func="", extra={'user_email': user_email, 'session_id': session_id, **kwargs}
    )
    logger.handle(record)


# Global LLM call logger instance
llm_call_logger: Optional[LLMCallLogger] = None