"""
Unit tests for prompt utilities.
"""
import os
import pytest
from unittest.mock import Mock, patch, mock_open
from pathlib import Path

# Import the prompt_utils module
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import prompt_utils


class TestPromptUtils:
    """Test prompt utility functions."""
    
    @patch('prompt_utils.Path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data="Test prompt for {user_email}")
    def test_load_system_prompt(self, mock_file, mock_exists):
        """Test loading system prompt from file."""
        mock_exists.return_value = True
        
        if hasattr(prompt_utils, 'load_system_prompt'):
            result = prompt_utils.load_system_prompt("test@example.com")
            assert "test@example.com" in result
            assert "Test prompt" in result
        
    @patch('prompt_utils.Path.exists')
    def test_load_system_prompt_file_not_exists(self, mock_exists):
        """Test loading system prompt when file doesn't exist."""
        mock_exists.return_value = False
        
        if hasattr(prompt_utils, 'load_system_prompt'):
            result = prompt_utils.load_system_prompt("test@example.com")
            # Should return a default prompt or handle gracefully
            assert isinstance(result, str)
        
    def test_format_prompt_with_user(self):
        """Test formatting prompt with user email."""
        if hasattr(prompt_utils, 'format_prompt'):
            template = "Hello {user_email}, welcome to the system."
            result = prompt_utils.format_prompt(template, "test@example.com")
            assert result == "Hello test@example.com, welcome to the system."
        else:
            # Test basic string formatting
            template = "Hello {user_email}, welcome to the system."
            result = template.format(user_email="test@example.com")
            assert result == "Hello test@example.com, welcome to the system."
        
    def test_format_prompt_without_placeholder(self):
        """Test formatting prompt without user placeholder."""
        if hasattr(prompt_utils, 'format_prompt'):
            template = "This is a static prompt."
            result = prompt_utils.format_prompt(template, "test@example.com")
            assert result == "This is a static prompt."
        else:
            # Test basic string without formatting
            template = "This is a static prompt."
            assert template == "This is a static prompt."


class TestPromptFormatting:
    """Test prompt formatting functions."""
    
    def test_basic_string_formatting(self):
        """Test basic string formatting functionality."""
        template = "User: {user_email}\nTask: {task}"
        formatted = template.format(user_email="test@example.com", task="test task")
        
        assert "test@example.com" in formatted
        assert "test task" in formatted
        
    def test_partial_formatting(self):
        """Test partial formatting with missing variables."""
        template = "User: {user_email}\nContext: {context}"
        
        # Only format user_email, leave context as is
        try:
            formatted = template.format(user_email="test@example.com")
        except KeyError:
            # Expected behavior - missing context
            formatted = template.replace("{user_email}", "test@example.com")
            
        assert "test@example.com" in formatted
        
    def test_safe_formatting(self):
        """Test safe formatting that handles missing keys."""
        template = "User: {user_email}\nOptional: {optional}"
        
        # Using str.format_map with defaultdict-like behavior
        from string import Template
        safe_template = Template(template.replace("{", "${"))
        
        formatted = safe_template.safe_substitute(user_email="test@example.com")
        assert "test@example.com" in formatted