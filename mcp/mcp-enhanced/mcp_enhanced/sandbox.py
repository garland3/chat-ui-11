"""
Simplified filesystem sandboxing for MCP Enhanced tools.

Server-side only: provides secure filesystem isolation.
"""

import builtins
import os
from contextlib import contextmanager
from pathlib import Path

from .exceptions import SecurityViolationError


class FileSystemSandbox:
    """
    Filesystem sandbox that restricts write operations to a specific directory.

    This is the server-side security enforcement. The client handles:
    - Username injection
    - File path resolution
    - Input file provisioning
    """

    def __init__(self, allowed_path: str):
        self.allowed_path = Path(allowed_path).resolve()
        self.allowed_path.mkdir(parents=True, exist_ok=True)

        # Store original functions for restoration
        self.original_open = builtins.open
        self.original_os_open = os.open
        self.original_os_mkdir = os.mkdir
        self.original_os_makedirs = os.makedirs
        self.original_os_remove = os.remove
        self.original_os_unlink = os.unlink
        self.original_os_rename = os.rename
        self.original_os_replace = os.replace

    def _validate_write_path(self, path) -> str:
        """Validate that a write operation path is within allowed directory"""
        try:
            resolved = Path(path).resolve()
            resolved.relative_to(self.allowed_path)
            return str(resolved)
        except (ValueError, OSError):
            raise SecurityViolationError(
                f"Write access denied: {path} is outside allowed directory {self.allowed_path}",
                attempted_path=str(path),
                allowed_prefix=str(self.allowed_path),
            )

    def sandboxed_open(self, file, mode="r", **kwargs):
        """Sandboxed version of open() - restricts write operations only"""
        # Check if this is a write operation
        if any(write_mode in mode for write_mode in ["w", "a", "x", "+"]):
            safe_path = self._validate_write_path(file)
            return self.original_open(safe_path, mode, **kwargs)
        else:
            # Allow reads from anywhere (client provides secure input paths)
            return self.original_open(file, mode, **kwargs)

    def sandboxed_os_open(self, path, flags, mode=0o777):
        """Sandboxed version of os.open()"""
        # Check if flags indicate write operations
        write_flags = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
        if flags & write_flags:
            safe_path = self._validate_write_path(path)
            return self.original_os_open(safe_path, flags, mode)
        else:
            return self.original_os_open(path, flags, mode)

    def sandboxed_mkdir(self, path, mode=0o777):
        """Sandboxed version of os.mkdir()"""
        safe_path = self._validate_write_path(path)
        return self.original_os_mkdir(safe_path, mode)

    def sandboxed_makedirs(self, path, mode=0o777, exist_ok=False):
        """Sandboxed version of os.makedirs()"""
        safe_path = self._validate_write_path(path)
        return self.original_os_makedirs(safe_path, mode, exist_ok)

    def sandboxed_remove(self, path):
        """Sandboxed version of os.remove()"""
        safe_path = self._validate_write_path(path)
        return self.original_os_remove(safe_path)

    def sandboxed_rename(self, src, dst):
        """Sandboxed version of os.rename()"""
        safe_src = self._validate_write_path(src)
        safe_dst = self._validate_write_path(dst)
        return self.original_os_rename(safe_src, safe_dst)

    @contextmanager
    def sandbox_context(self):
        """Context manager that applies sandbox restrictions"""
        # Store current functions
        original_funcs = {
            "open": builtins.open,
            "os_open": os.open,
            "mkdir": os.mkdir,
            "makedirs": os.makedirs,
            "remove": os.remove,
            "unlink": os.unlink,
            "rename": os.rename,
            "replace": os.replace,
        }

        # Apply sandbox patches
        builtins.open = self.sandboxed_open
        os.open = self.sandboxed_os_open
        os.mkdir = self.sandboxed_mkdir
        os.makedirs = self.sandboxed_makedirs
        os.remove = self.sandboxed_remove
        os.unlink = self.sandboxed_remove  # unlink is alias for remove
        os.rename = self.sandboxed_rename
        os.replace = self.sandboxed_rename  # simplified - replace similar to rename

        try:
            yield self.allowed_path
        finally:
            # Restore original functions
            builtins.open = original_funcs["open"]
            os.open = original_funcs["os_open"]
            os.mkdir = original_funcs["mkdir"]
            os.makedirs = original_funcs["makedirs"]
            os.remove = original_funcs["remove"]
            os.unlink = original_funcs["unlink"]
            os.rename = original_funcs["rename"]
            os.replace = original_funcs["replace"]


def normalize_filename(filename: str) -> str:
    """
    Basic filename normalization for server-side validation.

    The client should do the heavy lifting of filename normalization,
    but this provides server-side validation as a safety net.
    """
    if not filename:
        return "unnamed_file"

    # Remove path separators
    clean_name = filename.replace("/", "_").replace("\\", "_")

    # Remove dangerous characters
    dangerous_chars = ["..", "\x00", "\r", "\n"]
    for char in dangerous_chars:
        clean_name = clean_name.replace(char, "_")

    # Limit length
    if len(clean_name) > 255:
        name, ext = os.path.splitext(clean_name)
        clean_name = name[:250] + ext

    return clean_name or "cleaned_file"
