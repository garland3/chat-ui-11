"""
Exception classes for MCP Enhanced library
"""


class MCPEnhancedError(Exception):
    """Base exception for MCP Enhanced library"""

    pass


class SecurityViolationError(MCPEnhancedError):
    """Raised when file operations violate security constraints"""

    def __init__(self, message: str, attempted_path: str = None, allowed_prefix: str = None):
        super().__init__(message)
        self.attempted_path = attempted_path
        self.allowed_prefix = allowed_prefix


class FileSizeExceededError(MCPEnhancedError):
    """Raised when files exceed processing limits"""

    def __init__(self, message: str, file_size: int = None, limit_size: int = None):
        super().__init__(message)
        self.file_size = file_size
        self.limit_size = limit_size


class TimeoutError(MCPEnhancedError):
    """Raised when operations exceed timeout limits"""

    def __init__(self, message: str, timeout_seconds: int = None, last_progress: str = None):
        super().__init__(message)
        self.timeout_seconds = timeout_seconds
        self.last_progress = last_progress
