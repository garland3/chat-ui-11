"""
Utility functions for MCP Enhanced tools.

Server-side helpers for common operations.
"""

from pathlib import Path
from typing import List

from .sandbox import normalize_filename


def secure_output_path(username: str, filename: str) -> str:
    """
    Create a secure output path for generated files.

    This is the main utility that tools should use for creating output files.
    The path will be within the user's isolated temporary directory.

    Args:
        username: User identity (already injected by client)
        filename: Desired filename

    Returns:
        Secure path in /tmp/{username}/ directory

    Example:
        output_path = secure_output_path(username, "analysis.csv")
        df.to_csv(output_path)
    """
    safe_user = normalize_filename(username)
    safe_filename = normalize_filename(filename)

    # Ensure the user's temp directory exists
    user_temp_dir = Path(f"/tmp/{safe_user}")
    user_temp_dir.mkdir(parents=True, exist_ok=True)

    return str(user_temp_dir / safe_filename)


def list_user_files(username: str, pattern: str = "*") -> List[str]:
    """
    List files in the user's temporary directory.

    Useful for auto-scanning generated files.

    Args:
        username: User identity
        pattern: Glob pattern for files to match

    Returns:
        List of file paths
    """
    safe_user = normalize_filename(username)
    user_temp_dir = Path(f"/tmp/{safe_user}")

    if not user_temp_dir.exists():
        return []

    try:
        return [str(p) for p in user_temp_dir.glob(pattern) if p.is_file()]
    except OSError:
        return []


def cleanup_user_files(username: str, keep_recent_hours: int = 0):
    """
    Clean up old files in user's temporary directory.

    Args:
        username: User identity
        keep_recent_hours: Keep files modified within this many hours (0 = delete all)
    """
    import time

    safe_user = normalize_filename(username)
    user_temp_dir = Path(f"/tmp/{safe_user}")

    if not user_temp_dir.exists():
        return

    cutoff_time = time.time() - (keep_recent_hours * 3600)

    try:
        for file_path in user_temp_dir.rglob("*"):
            if file_path.is_file():
                if keep_recent_hours == 0 or file_path.stat().st_mtime < cutoff_time:
                    try:
                        file_path.unlink()
                    except OSError:
                        pass

        # Remove empty directories
        try:
            if not any(user_temp_dir.iterdir()):
                user_temp_dir.rmdir()
        except OSError:
            pass

    except OSError:
        pass


def get_file_info(file_path: str) -> dict:
    """
    Get basic information about a file.

    Args:
        file_path: Path to the file

    Returns:
        Dictionary with file metadata
    """
    try:
        path_obj = Path(file_path)
        if not path_obj.exists():
            return {"error": "File not found"}

        stat = path_obj.stat()

        return {
            "name": path_obj.name,
            "size_bytes": stat.st_size,
            "modified_time": stat.st_mtime,
            "is_file": path_obj.is_file(),
            "suffix": path_obj.suffix,
        }

    except Exception as e:
        return {"error": str(e)}


def ensure_user_directory(username: str) -> str:
    """
    Ensure the user's temporary directory exists.

    Args:
        username: User identity

    Returns:
        Path to the user's directory
    """
    safe_user = normalize_filename(username)
    user_dir = Path(f"/tmp/{safe_user}")
    user_dir.mkdir(parents=True, exist_ok=True)
    return str(user_dir)
