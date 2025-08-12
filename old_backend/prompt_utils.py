"""
Utilities for loading and managing system prompts.
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def load_system_prompt(user_email: str) -> str:
    """
    Load the system prompt from file and format it with user information.
    
    Args:
        user_email: The user's email address to personalize the prompt
        
    Returns:
        Formatted system prompt string
    """
    try:
        prompt_file = os.path.join(os.path.dirname(__file__), "prompts", "system_prompt.md")
        
        if not os.path.exists(prompt_file):
            logger.warning(f"System prompt file not found at {prompt_file}, using fallback")
            return f"You are helping {user_email}. Be helpful and concise."
        
        with open(prompt_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract just the content after the "# System Prompt" header
        lines = content.split('\n')
        prompt_lines = []
        in_prompt = False
        
        for line in lines:
            if line.strip() == "# System Prompt":
                in_prompt = True
                continue
            elif in_prompt:
                prompt_lines.append(line)
        
        # Join and format the prompt
        prompt_content = '\n'.join(prompt_lines).strip()
        formatted_prompt = prompt_content.format(user_email=user_email)
        
        logger.info(f"Loaded system prompt for user {user_email}")
        return formatted_prompt
        
    except Exception as e:
        logger.error(f"Error loading system prompt: {e}")
        # Fallback to simple prompt
        return f"You are helping {user_email}. Be helpful and concise."


def get_system_prompt_path() -> str:
    """Get the path to the system prompt file."""
    return os.path.join(os.path.dirname(__file__), "prompts", "system_prompt.md")


def validate_system_prompt() -> bool:
    """Validate that the system prompt file exists and is readable."""
    prompt_path = get_system_prompt_path()
    return os.path.exists(prompt_path) and os.path.isfile(prompt_path)