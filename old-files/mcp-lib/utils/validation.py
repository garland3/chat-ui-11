"""Input validation helpers for MCP servers."""

import re
from typing import Any, Dict, List, Optional, Union, Type
from pathlib import Path


def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> Optional[str]:
    """Validate that all required fields are present in data.
    
    Returns:
        None if all required fields present, error message otherwise.
    """
    missing_fields = [field for field in required_fields if field not in data or data[field] is None]
    if missing_fields:
        return f"Missing required fields: {', '.join(missing_fields)}"
    return None


def validate_string_not_empty(value: Any, field_name: str) -> Optional[str]:
    """Validate that a value is a non-empty string.
    
    Returns:
        None if valid, error message otherwise.
    """
    if not isinstance(value, str):
        return f"{field_name} must be a string, got {type(value).__name__}"
    if not value.strip():
        return f"{field_name} cannot be empty"
    return None


def validate_integer_in_range(value: Any, field_name: str, min_val: Optional[int] = None, max_val: Optional[int] = None) -> Optional[str]:
    """Validate that a value is an integer within the specified range.
    
    Returns:
        None if valid, error message otherwise.
    """
    if not isinstance(value, int):
        return f"{field_name} must be an integer, got {type(value).__name__}"
    
    if min_val is not None and value < min_val:
        return f"{field_name} must be >= {min_val}, got {value}"
    
    if max_val is not None and value > max_val:
        return f"{field_name} must be <= {max_val}, got {value}"
    
    return None


def validate_filename(filename: str) -> Optional[str]:
    """Validate filename for security (no path traversal).
    
    Returns:
        None if valid, error message otherwise.
    """
    if not filename:
        return "Filename cannot be empty"
    
    if '..' in filename:
        return "Filename cannot contain path traversal sequences (..)"
    
    if filename.startswith('/') or filename.startswith('\\'):
        return "Filename cannot be an absolute path"
    
    # Check for invalid characters (basic set)
    invalid_chars = ['<', '>', ':', '"', '|', '?', '*']
    for char in invalid_chars:
        if char in filename:
            return f"Filename cannot contain invalid character: {char}"
    
    return None


def validate_email(email: str) -> Optional[str]:
    """Basic email validation.
    
    Returns:
        None if valid, error message otherwise.
    """
    if not isinstance(email, str):
        return "Email must be a string"
    
    # Very basic email regex
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        return "Invalid email format"
    
    return None


def validate_url(url: str) -> Optional[str]:
    """Basic URL validation.
    
    Returns:
        None if valid, error message otherwise.
    """
    if not isinstance(url, str):
        return "URL must be a string"
    
    if not url.startswith(('http://', 'https://')):
        return "URL must start with http:// or https://"
    
    return None


def validate_enum_choice(value: Any, field_name: str, valid_choices: List[str]) -> Optional[str]:
    """Validate that a value is one of the allowed choices.
    
    Returns:
        None if valid, error message otherwise.
    """
    if value not in valid_choices:
        return f"{field_name} must be one of {valid_choices}, got: {value}"
    return None


def sanitize_string(value: str, max_length: Optional[int] = None) -> str:
    """Sanitize string input by stripping whitespace and limiting length."""
    sanitized = value.strip()
    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    return sanitized


class ValidationError(Exception):
    """Exception raised when validation fails."""
    
    def __init__(self, message: str, field: Optional[str] = None):
        self.message = message
        self.field = field
        super().__init__(message)


def validate_and_raise(validation_result: Optional[str], field: Optional[str] = None) -> None:
    """Helper to raise ValidationError if validation fails."""
    if validation_result:
        raise ValidationError(validation_result, field)