"""Log management handler for admin operations.

Handles log file operations including reading, parsing, clearing, and downloading.
"""

from __future__ import annotations

import json
import logging
import os
import re
from collections import deque
from pathlib import Path
from typing import List, Optional

from fastapi import HTTPException
from fastapi.responses import FileResponse

from managers.admin.admin_models import LogEntry, LogMetadata, EnhancedLogsResponse
from managers.config.config_manager import config_manager

logger = logging.getLogger(__name__)


class LogManager:
    """Handles log file operations for admin interface."""
    
    @staticmethod
    def _project_root() -> Path:
        """Get the project root directory."""
        # backend/managers/admin/log_manager.py -> project root is 4 levels up
        return Path(__file__).resolve().parents[4]

    @classmethod
    def _log_base_dir(cls) -> Path:
        """Get the base directory for log files."""
        # Prefer AppSettings.app_log_dir, fallback to env, then project_root/logs
        app_settings = config_manager.app_settings
        if getattr(app_settings, "app_log_dir", ""):
            base = Path(app_settings.app_log_dir)
            return base if base.is_absolute() else cls._project_root() / base
        env_path = os.getenv("APP_LOG_DIR")
        if env_path:
            base = Path(env_path)
            return base if base.is_absolute() else cls._project_root() / base
        return cls._project_root() / "logs"

    @classmethod
    def _locate_log_file(cls) -> Path:
        """Locate the log file with sensible defaults and legacy fallbacks."""
        base = cls._log_base_dir()
        candidates = [
            base / "app.jsonl",
            base / "app.log",
            cls._project_root() / "logs" / "app.jsonl",
            cls._project_root() / "logs" / "app.log",
            # legacy fallbacks
            cls._project_root() / "backend" / "logs" / "app.jsonl",
            cls._project_root() / "backend" / "logs" / "app.log",
            cls._project_root() / "runtime" / "logs" / "app.jsonl",
            cls._project_root() / "runtime" / "logs" / "app.log",
        ]
        for c in candidates:
            if c.exists():
                return c
        raise HTTPException(status_code=404, detail="Log file not found")

    @classmethod
    def _parse_log_entry(cls, raw: str) -> LogEntry:
        """Parse a raw log line into a structured LogEntry."""
        raw = raw.strip()
        if not raw or raw == "NEW LOG":
            return None

        try:
            # Try JSON parsing first (structured logs)
            entry = json.loads(raw)
            return LogEntry(
                timestamp=entry.get("timestamp", ""),
                level=entry.get("level", "UNKNOWN"),
                module=entry.get("module", entry.get("logger", "")),
                logger=entry.get("logger", ""),
                function=entry.get("function", ""),
                message=entry.get("message", ""),
                trace_id=entry.get("trace_id", ""),
                span_id=entry.get("span_id", ""),
                line=entry.get("line", ""),
                thread_name=entry.get("thread_name", ""),
                extras={k: v for k, v in entry.items() if k.startswith("extra_")},
            )
        except json.JSONDecodeError:
            # Try regex pattern matching for plain text logs
            pattern = re.compile(
                r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})[,\s-]*(\w+)[,\s-]*([^-]*)[,\s-]*(.*)"
            )
            m = pattern.match(raw)
            if m:
                ts, lvl, mod, msg = m.groups()
                return LogEntry(
                    timestamp=ts.strip(),
                    level=lvl.strip().upper(),
                    module=mod.strip(),
                    logger=mod.strip(),
                    function="",
                    message=msg.strip(),
                    trace_id="",
                    span_id="",
                    line="",
                    thread_name="",
                    extras={},
                )
            else:
                # Fallback for unstructured logs
                return LogEntry(
                    timestamp="",
                    level="INFO",
                    module="unknown",
                    logger="unknown",
                    function="",
                    message=raw,
                    trace_id="",
                    span_id="",
                    line="",
                    thread_name="",
                    extras={},
                )

    @classmethod
    def get_enhanced_logs(
        cls,
        lines: int = 500,
        level_filter: Optional[str] = None,
        module_filter: Optional[str] = None,
    ) -> EnhancedLogsResponse:
        """Get enhanced logs with filtering and metadata."""
        try:
            log_file = cls._locate_log_file()

            entries: List[LogEntry] = []
            modules: set[str] = set()
            levels: set[str] = set()

            try:
                recent_lines = deque(log_file.open("r", encoding="utf-8"), maxlen=lines + 200)
                
                for raw in recent_lines:
                    parsed_entry = cls._parse_log_entry(raw)
                    if parsed_entry is None:
                        continue
                        
                    # Apply filters
                    if level_filter and parsed_entry.level != level_filter:
                        continue
                    if module_filter and parsed_entry.module != module_filter:
                        continue
                        
                    entries.append(parsed_entry)
                    modules.add(parsed_entry.module)
                    levels.add(parsed_entry.level)
                    
                    if len(entries) >= lines:
                        break
                        
            except Exception as e:  # noqa: BLE001
                logger.error(f"Error reading log file {log_file}: {e}")
                # Return error entry instead of empty
                error_entry = LogEntry(
                    timestamp="",
                    level="ERROR",
                    module="admin",
                    logger="admin",
                    function="get_enhanced_logs",
                    message=f"Error reading log file: {e}",
                    trace_id="",
                    span_id="",
                    line="",
                    thread_name="",
                    extras={},
                )
                entries = [error_entry]
                modules = {"admin"}
                levels = {"ERROR"}

            metadata = LogMetadata(
                total_entries=len(entries),
                unique_modules=sorted(modules),
                unique_levels=sorted(levels),
                log_file_path=str(log_file),
                requested_lines=lines,
                filters_applied={"level": level_filter, "module": module_filter},
            )

            return EnhancedLogsResponse(entries=entries, metadata=metadata)
            
        except Exception as e:  # noqa: BLE001
            logger.error(f"Error getting enhanced logs: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @classmethod
    def clear_logs(cls) -> tuple[List[str], str]:
        """Clear all log files and return list of cleared files."""
        base = cls._log_base_dir()
        candidates = [
            base / "app.jsonl",
            base / "app.log",
            cls._project_root() / "logs" / "app.jsonl",
            cls._project_root() / "logs" / "app.log",
            cls._project_root() / "backend" / "logs" / "app.jsonl",
            cls._project_root() / "backend" / "logs" / "app.log",
            cls._project_root() / "runtime" / "logs" / "app.jsonl",
            cls._project_root() / "runtime" / "logs" / "app.log",
        ]
        
        cleared: List[str] = []
        for f in candidates:
            if f.exists():
                try:
                    f.write_text("NEW LOG\n", encoding="utf-8")
                    cleared.append(str(f))
                except Exception as e:  # noqa: BLE001
                    logger.error(f"Failed clearing {f}: {e}")
                    
        if not cleared:
            return cleared, "No log files found to clear"
        return cleared, "Log files cleared successfully"

    @classmethod
    def get_log_file_for_download(cls) -> FileResponse:
        """Get log file for download."""
        try:
            log_file = cls._locate_log_file()
            media_type = "application/json" if log_file.suffix == ".jsonl" else "text/plain"
            return FileResponse(
                path=str(log_file),
                media_type=media_type,
                filename=log_file.name
            )
        except HTTPException:
            raise
        except Exception as e:  # noqa: BLE001
            logger.error(f"Error preparing log download: {e}")
            raise HTTPException(status_code=500, detail="Error preparing log download")