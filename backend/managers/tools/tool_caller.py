"""Tool execution manager that integrates with MCP servers."""

import logging
from typing import Dict, List, Any, Callable
from managers.mcp.mcp_manager import MCPManager
from .tool_models import ToolCall, ToolResult

logger = logging.getLogger(__name__)


class ToolCaller:
    """Main tool execution manager."""

    def __init__(self, mcp_manager: MCPManager):
        self.mcp_manager = mcp_manager

    async def execute_tool(self, tool_call: ToolCall) -> ToolResult:
        """Execute a single tool call."""
        logger.debug(f"Executing tool: {tool_call.name}")

        try:
            # Get the tool from MCP manager
            tool = self.mcp_manager.get_tool_by_name(tool_call.name)
            if not tool:
                return ToolResult(
                    tool_call_id=tool_call.id,
                    success=False,
                    error=f"Tool not found: {tool_call.name}",
                )

            # Call the tool via MCP manager
            raw_result = await self.mcp_manager.call_tool(
                tool_call.name, tool_call.arguments
            )

            # Convert result to our format
            return self._convert_mcp_result(tool_call.id, raw_result)

        except Exception as e:
            logger.error(f"Error executing tool {tool_call.name}: {e}")
            return ToolResult(tool_call_id=tool_call.id, success=False, error=str(e))

    async def execute_tools(self, tool_calls: List[ToolCall]) -> List[ToolResult]:
        """Execute multiple tool calls."""
        results = []
        for tool_call in tool_calls:
            result = await self.execute_tool(tool_call)
            results.append(result)
        return results

    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools for LLM."""
        tools = self.mcp_manager.get_available_tools()
        return [tool.to_openai_schema() for tool in tools]

    def get_tools_for_servers(self, server_names: List[str]) -> List[Dict[str, Any]]:
        """Get tools for specific servers."""
        tools = self.mcp_manager.get_tools_for_servers(server_names)
        return [tool.to_openai_schema() for tool in tools]

    def get_authorized_tools_for_user(
        self,
        username: str,
        selected_tool_map: Dict[str, List[str]],
        is_user_in_group: Callable[[str, str], bool],
    ) -> List[Dict[str, Any]]:
        """Get tools that user is authorized to use, filtered by selection.

        Args:
            username: The username to check authorization for
            selected_tool_map: Mapping of server -> list of tool names user selected
            is_user_in_group: Function that checks if user is in a specific group

        Returns:
            List of tool schemas in OpenAI format
        """
        # Authorize servers using is_user_in_group exclusively
        all_servers = self.mcp_manager.get_available_servers()
        authorized_servers: List[str] = []

        for server_name in all_servers:
            server_info = self.mcp_manager.get_server_info(server_name)
            if not server_info:
                continue
            server_groups = server_info.get("groups", []) or []
            if not server_groups:
                authorized_servers.append(server_name)
                continue
            if any(is_user_in_group(username, group) for group in server_groups):
                authorized_servers.append(server_name)

        logger.debug(f"User {username} authorized for servers: {authorized_servers}")

        # Build set of fully-qualified tool names from selected_tool_map
        selected_fqns: set[str] = set()
        for server, tools in (selected_tool_map or {}).items():
            for tool in tools or []:
                selected_fqns.add(f"{server}_{tool}")

        # Get all tools from authorized servers
        tools_schema = self.get_tools_for_servers(authorized_servers)

        # Filter by selected tool fqns (if any). If none specified, return all tools from authorized servers
        if selected_fqns:
            filtered = [
                tool
                for tool in tools_schema
                if tool.get("function", {}).get("name") in selected_fqns
            ]
            logger.debug(
                "Filtered to %d tools from %d available for user %s",
                len(filtered),
                len(tools_schema),
                username,
            )
            return filtered

        logger.debug(
            f"Using all {len(tools_schema)} available tools for user {username}"
        )
        return tools_schema

    def _convert_mcp_result(self, tool_call_id: str, raw_result: Any) -> ToolResult:
        """Convert MCP result to ToolResult format."""
        try:
            # Extract content from FastMCP result
            content = ""
            artifacts = []
            meta_data = None

            if hasattr(raw_result, "content") and raw_result.content:
                # Handle content array
                contents = raw_result.content
                if isinstance(contents, list) and len(contents) > 0:
                    first_content = contents[0]
                    if hasattr(first_content, "text"):
                        content = first_content.text
                    elif hasattr(first_content, "content"):
                        content = first_content.content
                    else:
                        content = str(first_content)
                else:
                    content = str(contents)
            elif hasattr(raw_result, "data"):
                content = str(raw_result.data)
            else:
                content = str(raw_result)

            # Extract structured data if available
            if (
                hasattr(raw_result, "structured_content")
                and raw_result.structured_content
            ):
                structured = raw_result.structured_content
                if isinstance(structured, dict):
                    # Extract artifacts if present
                    if "artifacts" in structured and isinstance(
                        structured["artifacts"], list
                    ):
                        artifacts = structured["artifacts"]

                    # Extract metadata if present
                    if "meta_data" in structured:
                        meta_data = structured["meta_data"]

            return ToolResult(
                tool_call_id=tool_call_id,
                success=True,
                content=content,
                artifacts=artifacts,
                meta_data=meta_data,
            )

        except Exception as e:
            logger.error(f"Error converting MCP result: {e}")
            return ToolResult(
                tool_call_id=tool_call_id,
                success=False,
                error=f"Error processing result: {str(e)}",
            )
