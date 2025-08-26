"""Unit tests for tool sanitizer utility."""

from managers.ui_callback.sanitizer import (
    sanitize_arguments,
    sanitize_tool_result,
    parse_tool_name,
)
from managers.tools.tool_models import ToolResult


class TestSanitizeArguments:
    """Test suite for argument sanitization."""

    def test_sanitize_normal_arguments(self):
        """Test sanitization of normal arguments."""
        args = {"param": "value", "number": 42, "flag": True}
        result = sanitize_arguments(args)

        assert result["param"] == "value"
        assert result["number"] == 42
        assert result["flag"] is True

    def test_sanitize_sensitive_keys(self):
        """Test that sensitive keys are masked."""
        args = {
            "password": "secret123",
            "API_KEY": "abc123",
            "authorization": "Bearer token123",
            "clientSecret": "supersecret",
            "normal_param": "safe_value",
        }
        result = sanitize_arguments(args)

        assert result["password"] == "***MASKED***"
        assert result["API_KEY"] == "***MASKED***"
        assert result["authorization"] == "***MASKED***"
        assert result["clientSecret"] == "***MASKED***"
        assert result["normal_param"] == "safe_value"

    def test_sanitize_long_strings(self):
        """Test truncation of long strings."""
        long_string = "a" * 300
        args = {"long_param": long_string}
        result = sanitize_arguments(args)

        assert len(result["long_param"]) < 300
        assert "truncated" in result["long_param"]
        assert "300 chars total" in result["long_param"]

    def test_sanitize_nested_structures(self):
        """Test sanitization of nested dicts and lists."""
        args = {
            "nested_dict": {"password": "secret", "safe_param": "safe_value"},
            "list_param": ["item1", "item2", {"secret": "hidden"}],
            "deep_nest": {"level2": {"token": "jwt123", "data": "normal"}},
        }
        result = sanitize_arguments(args)

        assert result["nested_dict"]["password"] == "***MASKED***"
        assert result["nested_dict"]["safe_param"] == "safe_value"
        assert result["list_param"][2]["secret"] == "***MASKED***"
        assert result["deep_nest"]["level2"]["token"] == "***MASKED***"
        assert result["deep_nest"]["level2"]["data"] == "normal"

    def test_sanitize_large_lists(self):
        """Test truncation of large lists."""
        large_list = [f"item_{i}" for i in range(30)]
        args = {"big_list": large_list}
        result = sanitize_arguments(args)

        assert len(result["big_list"]) == 26  # 25 items + truncation message
        assert "truncated list with 30 items" in str(result["big_list"][-1])

    def test_sanitize_non_serializable_objects(self):
        """Test handling of non-JSON-serializable objects."""

        class CustomObject:
            def __repr__(self):
                return "CustomObject()"

        args = {"custom": CustomObject()}
        result = sanitize_arguments(args)

        assert result["custom"] == "CustomObject()"

    def test_sanitize_invalid_input(self):
        """Test handling of non-dict input."""
        result = sanitize_arguments("not a dict")
        assert result["error"] == "Arguments not a dictionary"


class TestSanitizeToolResult:
    """Test suite for tool result sanitization."""

    def test_sanitize_successful_result(self):
        """Test sanitization of successful tool result."""
        tool_result = ToolResult(
            tool_call_id="call_123",
            success=True,
            content="Tool executed successfully",
            meta_data={"execution_time": "1.2s"},
        )

        result = sanitize_tool_result(tool_result)

        assert result["success"] is True
        assert result["tool_call_id"] == "call_123"
        assert result["content"] == "Tool executed successfully"
        assert result["meta_data"]["execution_time"] == "1.2s"

    def test_sanitize_failed_result(self):
        """Test sanitization of failed tool result."""
        tool_result = ToolResult(
            tool_call_id="call_456",
            success=False,
            content="",
            error="Tool execution failed with error details",
        )

        result = sanitize_tool_result(tool_result)

        assert result["success"] is False
        assert result["tool_call_id"] == "call_456"
        assert result["error"] == "Tool execution failed with error details"

    def test_sanitize_long_content(self):
        """Test truncation of long content."""
        long_content = "x" * 3000
        tool_result = ToolResult(
            tool_call_id="call_789", success=True, content=long_content
        )

        result = sanitize_tool_result(tool_result)

        assert len(result["content"]) < 3000
        assert "truncated" in result["content"]
        assert "3000 chars total" in result["content"]

    def test_sanitize_artifacts(self):
        """Test sanitization of artifacts."""
        artifacts = [
            {
                "filename": "test.txt",
                "content": "file content that should not be included",
                "content_type": "text/plain",
                "size": 1024,
                "secret_key": "hidden",
            },
            {"name": "image.png", "type": "image", "data": "base64encodeddata..."},
        ]

        tool_result = ToolResult(
            tool_call_id="call_artifacts",
            success=True,
            content="OK",
            artifacts=artifacts,
        )

        result = sanitize_tool_result(tool_result)

        # Should keep safe metadata only
        assert len(result["artifacts"]) == 2
        assert result["artifacts"][0]["filename"] == "test.txt"
        assert result["artifacts"][0]["content_type"] == "text/plain"
        assert result["artifacts"][0]["size"] == 1024
        assert "content" not in result["artifacts"][0]  # Content should be removed
        assert (
            "secret_key" not in result["artifacts"][0]
        )  # Sensitive key should be removed

        assert result["artifacts"][1]["name"] == "image.png"
        assert result["artifacts"][1]["type"] == "image"
        assert "data" not in result["artifacts"][1]  # Data should be removed

    def test_sanitize_many_artifacts(self):
        """Test truncation of many artifacts."""
        artifacts = [{"filename": f"file_{i}.txt"} for i in range(30)]

        tool_result = ToolResult(
            tool_call_id="call_many", success=True, content="OK", artifacts=artifacts
        )

        result = sanitize_tool_result(tool_result)

        assert len(result["artifacts"]) == 26  # 25 + truncation message
        assert "truncated, 30 artifacts total" in str(result["artifacts"][-1])

    def test_sanitize_empty_success_result(self):
        """Test sanitization of successful result with empty content."""
        tool_result = ToolResult(tool_call_id="call_empty", success=True, content="")

        result = sanitize_tool_result(tool_result)

        assert result["success"] is True
        assert result["content"] == "OK"  # Should get default success message

    def test_sanitize_sensitive_metadata(self):
        """Test sanitization of sensitive metadata."""
        tool_result = ToolResult(
            tool_call_id="call_meta",
            success=True,
            content="Done",
            meta_data={
                "execution_time": "1.5s",
                "api_key": "secret123",
                "user_token": "jwt456",
                "normal_data": "safe",
            },
        )

        result = sanitize_tool_result(tool_result)

        assert result["meta_data"]["execution_time"] == "1.5s"
        assert result["meta_data"]["api_key"] == "***MASKED***"
        assert result["meta_data"]["user_token"] == "***MASKED***"
        assert result["meta_data"]["normal_data"] == "safe"

    def test_sanitize_invalid_result(self):
        """Test handling of invalid tool result object."""
        result = sanitize_tool_result("not a tool result")
        assert result["error"] == "Invalid tool result object"


class TestParseToolName:
    """Test suite for tool name parsing."""

    def test_parse_qualified_tool_name(self):
        """Test parsing of server_toolName format."""
        server, tool = parse_tool_name("weather_get_forecast")
        assert server == "weather"
        assert tool == "get_forecast"

    def test_parse_tool_name_with_underscores(self):
        """Test parsing tool names with underscores in tool part."""
        server, tool = parse_tool_name("database_get_user_info")
        assert server == "database"
        assert tool == "get_user_info"

    def test_parse_simple_tool_name(self):
        """Test parsing tool name without server prefix."""
        server, tool = parse_tool_name("simple_tool")
        assert server == "simple"
        assert tool == "tool"

    def test_parse_tool_name_no_underscore(self):
        """Test parsing tool name with no underscore."""
        server, tool = parse_tool_name("singletool")
        assert server == ""
        assert tool == "singletool"
