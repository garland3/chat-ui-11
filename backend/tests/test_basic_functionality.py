"""
Basic functionality tests that should always pass.
"""
import os
import sys
import json
from unittest.mock import Mock, patch

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from file_config import FilePolicy, filter_files_for_llm_context


class TestFilePolicy:
    """Test file policy functionality."""
    
    def test_file_policy_initialization(self):
        """Test FilePolicy initializes correctly."""
        policy = FilePolicy()
        assert policy.max_llm_size > 0
        assert policy.max_upload_size > 0
        assert len(policy.tool_only_types) > 0
        assert len(policy.llm_visible_types) > 0
    
    def test_csv_files_are_tool_only(self):
        """Test that CSV files are marked as tool-only."""
        policy = FilePolicy()
        
        # CSV files should not be exposed to LLM
        assert not policy.should_expose_to_llm("test.csv", 1000)
        assert not policy.should_expose_to_llm("data.CSV", 500)
    
    def test_small_text_files_are_llm_visible(self):
        """Test that small text files are LLM visible."""
        policy = FilePolicy()
        
        # Small text files should be LLM visible
        assert policy.should_expose_to_llm("readme.txt", 500)
        assert policy.should_expose_to_llm("notes.md", 800)
    
    def test_large_files_are_tool_only(self):
        """Test that large files are tool-only regardless of type."""
        policy = FilePolicy()
        
        # Even text files should be tool-only if too large
        large_size = policy.max_llm_size + 1000
        assert not policy.should_expose_to_llm("large.txt", large_size)
    
    def test_get_file_category(self):
        """Test file categorization."""
        policy = FilePolicy()
        
        assert policy.get_file_category("data.csv") == "Data file"
        assert policy.get_file_category("document.pdf") == "Document"
        assert policy.get_file_category("image.png") == "Image"
        assert policy.get_file_category("readme.txt") == "Text file"


class TestUtilityFunctions:
    """Test basic utility functions."""
    
    def test_filter_files_for_llm_context_empty(self):
        """Test filtering with empty file dict."""
        result = filter_files_for_llm_context({})
        assert result == {}
    
    def test_filter_files_for_llm_context_mixed(self):
        """Test filtering with mixed file types."""
        # Create some test base64 data (small)
        small_text_b64 = "SGVsbG8gV29ybGQ="  # "Hello World" in base64
        large_csv_b64 = "Y29sLmEsY29sLmI=" * 1000  # Repeated CSV data
        
        files = {
            "small.txt": small_text_b64,
            "large.csv": large_csv_b64,
            "document.pdf": small_text_b64
        }
        
        result = filter_files_for_llm_context(files)
        
        # Small text should be included, CSV and PDF should not
        assert "small.txt" in result
        assert "large.csv" not in result
        assert "document.pdf" not in result


class TestBasicImports:
    """Test that critical modules can be imported."""
    
    def test_import_auth(self):
        """Test auth module imports."""
        from auth import is_user_in_group, get_user_from_header
        assert callable(is_user_in_group)
        assert callable(get_user_from_header)
    
    def test_import_config(self):
        """Test config module imports."""
        from config import AppSettings, ModelConfig, MCPServerConfig
        
        # Test that classes can be instantiated
        app_settings = AppSettings()
        assert hasattr(app_settings, 'app_name')
        
        model_config = ModelConfig(
            model_name="test-model",
            api_key="test-key", 
            model_url="http://test.com"
        )
        assert model_config.model_name == "test-model"
        
        mcp_config = MCPServerConfig(command=["test"])
        assert mcp_config.command == ["test"]
    
    def test_import_session(self):
        """Test session module imports."""
        from session import ChatSession, SessionManager
        assert ChatSession is not None
        assert SessionManager is not None