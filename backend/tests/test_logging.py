"""
Test module for the logging configuration and functionality.
"""

import asyncio
import logging
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


class TestLoggingConfig(unittest.TestCase):
    """Test cases for logging configuration."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.logs_dir = self.test_dir / "logs"
        self.logs_dir.mkdir()
        
        # Change to test directory
        self.original_cwd = os.getcwd()
        os.chdir(str(self.test_dir))
    
    def tearDown(self):
        """Clean up test environment."""
        os.chdir(self.original_cwd)
        # Clean up temp directory
        import shutil
        shutil.rmtree(str(self.test_dir), ignore_errors=True)
    
    @patch('logging_config.config_manager')
    def test_setup_logging(self, mock_config_manager):
        """Test that logging setup works correctly."""
        # Mock app settings
        mock_settings = MagicMock()
        mock_settings.log_level = "INFO"
        mock_config_manager.app_settings = mock_settings
        
        from logging_config import setup_logging
        
        # Test setup
        result = setup_logging()
        self.assertTrue(result)
        
        # Check that log files are created
        self.assertTrue((self.logs_dir / "app.log").exists())
        self.assertTrue((self.logs_dir / "errors.log").exists())
        self.assertTrue((self.logs_dir / "app_logs.db").exists())
        self.assertTrue((self.logs_dir / "llm_calls.db").exists())
    
    def test_database_handler(self):
        """Test the database logging handler."""
        from logging_config import DatabaseHandler
        
        db_path = str(self.logs_dir / "test_logs.db")
        handler = DatabaseHandler(db_path)
        
        # Check database is created with correct table
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='app_logs'"
            )
            self.assertIsNotNone(cursor.fetchone())
    
    def test_llm_call_logger(self):
        """Test the LLM call logger."""
        from logging_config import LLMCallLogger
        
        db_path = str(self.logs_dir / "test_llm_calls.db")
        llm_logger = LLMCallLogger(db_path)
        
        # Test logging an LLM call
        test_messages = [{"role": "user", "content": "test message"}]
        llm_logger.log_llm_call(
            user_email="test@example.com",
            model_name="gpt-3.5-turbo",
            input_messages=test_messages,
            output_response="test response",
            session_id="test-session-123",
            selected_tools=["tool1", "tool2"],
            processing_time_ms=150
        )
        
        # Verify the call was logged
        calls = llm_logger.get_llm_calls(limit=10)
        self.assertEqual(len(calls), 1)
        
        call = calls[0]
        self.assertEqual(call["user_email"], "test@example.com")
        self.assertEqual(call["model_name"], "gpt-3.5-turbo")
        self.assertEqual(call["output_response"], "test response")
        self.assertEqual(call["session_id"], "test-session-123")
        self.assertEqual(call["processing_time_ms"], 150)
    
    def test_llm_call_logger_with_filter(self):
        """Test filtering LLM call logs."""
        from logging_config import LLMCallLogger
        
        db_path = str(self.logs_dir / "test_llm_calls_filter.db")
        llm_logger = LLMCallLogger(db_path)
        
        # Log multiple calls for different users
        test_messages = [{"role": "user", "content": "test"}]
        
        llm_logger.log_llm_call("user1@example.com", "gpt-3.5", test_messages, "response1")
        llm_logger.log_llm_call("user2@example.com", "gpt-4", test_messages, "response2")
        llm_logger.log_llm_call("user1@example.com", "gpt-3.5", test_messages, "response3")
        
        # Test filtering by user
        user1_calls = llm_logger.get_llm_calls(user_email="user1@example.com")
        self.assertEqual(len(user1_calls), 2)
        
        # Test limiting results
        limited_calls = llm_logger.get_llm_calls(limit=1)
        self.assertEqual(len(limited_calls), 1)


@pytest.mark.asyncio
async def test_enhanced_call_llm():
    """Test that the enhanced call_llm function logs correctly."""
    with patch('utils.config_manager') as mock_config_manager:
        with patch('utils.requests') as mock_requests:
            with patch('logging_config.get_llm_call_logger') as mock_get_logger:
                # Setup mocks
                mock_model_config = MagicMock()
                mock_model_config.model_url = "http://test-api.com"
                mock_model_config.api_key = "test-key"
                mock_model_config.model_name = "test-model"
                
                mock_config_manager.llm_config.models = {"test-model": mock_model_config}
                
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "choices": [{"message": {"content": "test response"}}]
                }
                mock_requests.post.return_value = mock_response
                
                mock_llm_logger = MagicMock()
                mock_get_logger.return_value = mock_llm_logger
                
                # Import and test
                from utils import call_llm
                
                test_messages = [{"role": "user", "content": "test"}]
                result = await call_llm(
                    "test-model", 
                    test_messages, 
                    "test@example.com", 
                    "session-123"
                )
                
                # Verify result
                assert result == "test response"
                
                # Verify LLM call was logged
                mock_llm_logger.log_llm_call.assert_called_once()
                call_args = mock_llm_logger.log_llm_call.call_args[1]
                assert call_args["user_email"] == "test@example.com"
                assert call_args["model_name"] == "test-model"
                assert call_args["session_id"] == "session-123"
                assert call_args["output_response"] == "test response"


if __name__ == "__main__":
    unittest.main()