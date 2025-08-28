"""Common authentication patterns for MCP servers."""

import os
from typing import Optional, Dict, Any


def get_auth_header(headers: Dict[str, str]) -> Optional[str]:
    """Extract authorization header from request headers."""
    # Check various common header formats
    auth_header = headers.get('Authorization')
    if auth_header:
        return auth_header
    
    # Check lowercase version
    auth_header = headers.get('authorization')
    if auth_header:
        return auth_header
    
    return None


def extract_bearer_token(auth_header: str) -> Optional[str]:
    """Extract bearer token from authorization header."""
    if not auth_header:
        return None
    
    if auth_header.startswith('Bearer '):
        return auth_header[7:]  # Remove 'Bearer ' prefix
    
    return None


def get_api_key_from_env(env_var_name: str) -> Optional[str]:
    """Get API key from environment variable."""
    return os.getenv(env_var_name)


def validate_api_key(provided_key: str, expected_key: Optional[str]) -> bool:
    """Validate provided API key against expected key."""
    if not expected_key:
        return False
    
    if not provided_key:
        return False
    
    return provided_key == expected_key


def create_basic_auth_response() -> Dict[str, Any]:
    """Create a basic authentication required response."""
    return {
        "error": "Authentication required",
        "message": "Please provide valid authentication credentials",
        "code": "AUTH_REQUIRED"
    }


def create_invalid_auth_response() -> Dict[str, Any]:
    """Create an invalid authentication response."""
    return {
        "error": "Invalid authentication",
        "message": "The provided authentication credentials are invalid",
        "code": "AUTH_INVALID"
    }


def is_authenticated(headers: Dict[str, str], required_api_key_env: str) -> bool:
    """Check if request is properly authenticated.
    
    Args:
        headers: Request headers
        required_api_key_env: Environment variable name containing the required API key
    
    Returns:
        True if authenticated, False otherwise
    """
    expected_key = get_api_key_from_env(required_api_key_env)
    if not expected_key:
        # If no API key is configured, authentication is not required
        return True
    
    auth_header = get_auth_header(headers)
    if not auth_header:
        return False
    
    provided_key = extract_bearer_token(auth_header)
    return validate_api_key(provided_key, expected_key)