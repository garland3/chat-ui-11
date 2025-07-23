"""Authentication and authorization module."""

from typing import Optional


def is_user_in_group(user_id: str, group_id: str) -> bool:
    """
    Mock authorization function to check if user is in a group.
    
    Args:
        user_id: User email/identifier
        group_id: Group identifier
        
    Returns:
        True if user is authorized for the group
    """
    # Mock implementation - in production this would query actual auth system
    mock_groups = {
        # "test@test.com": ["admin", "users", "mcp_basic"],
        "test@test.com": ["mcp_basic"],
        "user@example.com": ["users", "mcp_basic"],
        "admin@example.com": ["admin", "users", "mcp_basic", "mcp_advanced"]
    }
    
    user_groups = mock_groups.get(user_id, [])
    return group_id in user_groups


def get_user_from_header(x_email_header: Optional[str]) -> Optional[str]:
    """Extract user email from x-email-header."""
    if not x_email_header:
        return None
    return x_email_header.strip()