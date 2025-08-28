"""
Tests for the enhanced_tool decorator.
"""

import shutil
from pathlib import Path

from mcp_enhanced import create_mcp_response, enhanced_tool, secure_output_path


class TestEnhancedTool:
    def test_basic_decorator(self):
        """Test basic decorator functionality"""

        @enhanced_tool()
        def simple_tool(username: str) -> dict:
            return create_mcp_response(results={"status": "ok"})

        result = simple_tool(username="testuser")
        assert result["results"]["status"] == "ok"

    def test_missing_username_error(self):
        """Test that missing username parameter raises appropriate error"""

        @enhanced_tool()
        def tool_needing_username(filename: str, username: str) -> dict:
            return create_mcp_response(results={"status": "ok"})

        # Call without username
        result = tool_needing_username(filename="test.txt")
        assert "error" in result["results"]
        assert result["meta_data"]["is_error"] is True
        assert result["meta_data"]["error_code"] == "E_NO_USERNAME"

    def test_sandbox_functionality(self):
        """Test that sandboxing restricts file operations"""

        @enhanced_tool(enable_sandbox=True)
        def sandboxed_tool(username: str) -> dict:
            # This should work - writing to allowed directory
            safe_path = secure_output_path(username, "test.txt")
            with open(safe_path, "w") as f:
                f.write("test content")

            # This should fail - writing outside allowed directory
            try:
                with open("/tmp/outside_sandbox.txt", "w") as f:
                    f.write("should fail")
                return create_mcp_response(results={"status": "security_bypass"})
            except Exception:
                return create_mcp_response(results={"status": "security_enforced"})

        result = sandboxed_tool(username="testuser")
        assert result["results"]["status"] == "security_enforced"

    def test_disable_sandbox(self):
        """Test that sandboxing can be disabled"""

        @enhanced_tool(enable_sandbox=False)
        def unsandboxed_tool(username: str) -> dict:
            return create_mcp_response(results={"sandbox_disabled": True})

        result = unsandboxed_tool(username="testuser")
        assert result["results"]["sandbox_disabled"] is True

    def test_exception_handling(self):
        """Test that exceptions are properly caught and formatted"""

        @enhanced_tool()
        def failing_tool(username: str) -> dict:
            raise ValueError("Intentional test error")

        result = failing_tool(username="testuser")
        assert "error" in result["results"]
        assert result["meta_data"]["is_error"] is True
        assert result["meta_data"]["error_code"] == "E_EXECUTION_FAILED"
        assert "ValueError" in result["meta_data"]["details"]["exception_type"]

    def test_simple_return_conversion(self):
        """Test that simple returns are converted to MCP format"""

        @enhanced_tool()
        def simple_return_tool(username: str) -> str:
            return "simple string"

        result = simple_return_tool(username="testuser")
        assert result["results"]["status"] == "simple string"

    def teardown_method(self):
        """Clean up test files"""
        test_dir = Path("/tmp/testuser")
        if test_dir.exists():
            shutil.rmtree(test_dir)
