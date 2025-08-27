"""Simplified log management handler for admin operations.

Handles log file operations with minimal complexity.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List

from fastapi import HTTPException
from fastapi.responses import FileResponse

from managers.admin.admin_models import LogEntry, LogMetadata, EnhancedLogsResponse

logger = logging.getLogger(__name__)


class LogManager:
    """Simple log file handler for admin interface."""
    
    @staticmethod
    def _get_log_file() -> Path:
        """Get the primary log file path."""
        # Try to find the log file by going back 2-4 parent directories
        for i in range(2, 5):
            project_root = Path(__file__).resolve().parents[i]
            log_file = project_root / "logs" / "app.jsonl"
            if log_file.exists():
                return log_file
        
        # If not found after checking all levels, raise an exception
        raise HTTPException(status_code=404, detail="Log file not found")

    @classmethod
    def _parse_json_log(cls, line: str) -> LogEntry | None:
        """Parse a JSON log line into LogEntry."""
        line = line.strip()
        if not line or line == "NEW LOG":
            return None
            
        try:
            data = json.loads(line)
            # Extract standard fields with defaults
            entry = LogEntry(
                timestamp=data.get("timestamp", ""),
                level=data.get("level", "INFO"),
                module=data.get("module", data.get("logger", "")),
                logger=data.get("logger", ""),
                function=data.get("function", ""),
                message=data.get("message", ""),
                trace_id=data.get("trace_id", ""),
                span_id=data.get("span_id", ""),
                line=data.get("line", ""),
                thread_name=data.get("thread_name", ""),
                extras={k: v for k, v in data.items() if k.startswith("extra_")},
            )
            return entry
        except (json.JSONDecodeError, Exception):
            # Return a simple error entry for malformed lines
            return LogEntry(
                timestamp="",
                level="ERROR",
                module="log_parser",
                logger="log_parser",
                function="parse",
                message=f"Failed to parse log line: {line[:100]}...",
            )

    @classmethod
    def get_enhanced_logs(
        cls,
        lines: int = 500,
        level_filter: str | None = None,
        module_filter: str | None = None,
    ) -> EnhancedLogsResponse:
        """Get enhanced logs with basic filtering."""
        try:
            log_file = cls._get_log_file()
            entries: List[LogEntry] = []
            modules: set[str] = set()
            levels: set[str] = set()

            # Read the last N lines efficiently
            with log_file.open("r", encoding="utf-8") as f:
                # Simple approach: read all lines and take the last ones
                all_lines = f.readlines()
                recent_lines = all_lines[-lines-50:] if len(all_lines) > lines + 50 else all_lines

            for line in recent_lines:
                entry = cls._parse_json_log(line)
                if not entry:
                    continue

                # Apply filters
                if level_filter and entry.level != level_filter:
                    continue
                if module_filter and entry.module != module_filter:
                    continue

                entries.append(entry)
                modules.add(entry.module)
                levels.add(entry.level)

                if len(entries) >= lines:
                    break

            metadata = LogMetadata(
                total_entries=len(entries),
                unique_modules=sorted(modules),
                unique_levels=sorted(levels),
                log_file_path=str(log_file),
                requested_lines=lines,
                filters_applied={"level": level_filter, "module": module_filter},
            )

            return EnhancedLogsResponse(entries=entries, metadata=metadata)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error reading logs: {e}")
            raise HTTPException(status_code=500, detail=f"Error reading logs: {e}")

    @classmethod
    def clear_logs(cls) -> tuple[List[str], str]:
        """Clear the log file."""
        try:
            log_file = cls._get_log_file()
            log_file.write_text("NEW LOG\n", encoding="utf-8")
            return [str(log_file)], "Log file cleared successfully"
        except HTTPException:
            return [], "No log file found to clear"
        except Exception as e:
            logger.error(f"Error clearing logs: {e}")
            return [], f"Error clearing logs: {e}"

    @classmethod
    def get_log_file_for_download(cls) -> FileResponse:
        """Get log file for download."""
        try:
            log_file = cls._get_log_file()
            return FileResponse(
                path=str(log_file),
                media_type="application/json",
                filename=log_file.name
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error preparing download: {e}")
            raise HTTPException(status_code=500, detail="Error preparing log download")
