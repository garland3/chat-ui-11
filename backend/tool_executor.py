"""
Tool execution engine that handles MCP tool calls and special tools.

This module provides a clean interface for executing tools in different contexts:
- Regular MCP tool execution
- Special tools (completion, canvas)
- File handling and injection
- UI update notifications
"""

import json
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from mcp_client import MCPToolManager

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """Result from a single tool execution."""
    tool_call_id: str
    role: str = "tool"
    content: str = ""
    success: bool = True
    error: Optional[str] = None
    files_generated: List[str] = None
    
    def __post_init__(self):
        if self.files_generated is None:
            self.files_generated = []


@dataclass 
class ExecutionContext:
    """Context for tool execution including session and UI updates."""
    user_email: str
    session: Optional[Any] = None
    agent_mode: bool = False
    
    def should_send_ui_updates(self) -> bool:
        return self.session is not None


class FileManager:
    """Handles file injection and extraction for tools."""
    
    @staticmethod
    async def inject_file_data(function_args: Dict, session) -> Dict:
        """Inject file data into tool arguments if tool expects it and files are available."""
        logger.info(f"inject_file_data called with args: {list(function_args.keys())}")
        
        if not session or not hasattr(session, 'uploaded_files') or not session.uploaded_files:
            return function_args
        
        logger.info(f"Session has {len(session.uploaded_files)} files: {list(session.uploaded_files.keys())}")
        
        enhanced_args = function_args.copy()
        
        # Check if tool has filename parameter - if so, it might need file injection
        if 'filename' in function_args:
            filename = function_args.get('filename')
            logger.info(f"Tool has filename parameter: {filename}")
            
            if filename and filename in session.uploaded_files:
                # Get file content from S3
                file_content = await session.get_file_content_by_name(filename)
                if file_content:
                    enhanced_args['file_data_base64'] = file_content
                    logger.info(f"Successfully injected file data for '{filename}' (data length: {len(file_content)})")
                else:
                    logger.warning(f"Failed to retrieve file content from S3 for '{filename}'")
            else:
                logger.warning(f"File '{filename}' not found in uploaded files. Available: {list(session.uploaded_files.keys())}")
        
        return enhanced_args
    
    @staticmethod
    async def save_tool_files_to_session(tool_result: Dict[str, Any], session, tool_name: str) -> int:
        """Extract files from tool result and save them to the session via S3."""
        files_saved = 0
        
        # Check for returned_files array (preferred format)
        if "returned_files" in tool_result and isinstance(tool_result["returned_files"], list):
            for file_info in tool_result["returned_files"]:
                if isinstance(file_info, dict) and "filename" in file_info and "content_base64" in file_info:
                    # Don't add tool prefix for CSV/data files - keep original name for reuse
                    if file_info['filename'].endswith(('.csv', '.json', '.txt', '.xlsx')):
                        filename = file_info['filename']
                    else:
                        filename = f"{tool_name}_{file_info['filename']}"
                    
                    # Store file in S3
                    try:
                        await session.store_generated_file_in_s3(
                            filename, 
                            file_info["content_base64"],
                            tool_name
                        )
                        files_saved += 1
                        logger.info(f"Saved file {filename} from tool {tool_name} to S3 for session {session.session_id}")
                    except Exception as e:
                        logger.error(f"Failed to save file {filename} to S3: {e}")
        
        # Check for legacy single file format
        elif "returned_file_name" in tool_result and "returned_file_base64" in tool_result:
            if tool_result['returned_file_name'].endswith(('.csv', '.json', '.txt', '.xlsx')):
                filename = tool_result['returned_file_name']
            else:
                filename = f"{tool_name}_{tool_result['returned_file_name']}"
            
            # Store file in S3
            try:
                await session.store_generated_file_in_s3(
                    filename,
                    tool_result["returned_file_base64"],
                    tool_name
                )
                files_saved += 1
                logger.info(f"Saved file {filename} from tool {tool_name} to S3 for session {session.session_id}")
            except Exception as e:
                logger.error(f"Failed to save file {filename} to S3: {e}")
        
        if files_saved > 0:
            logger.info(f"Tool {tool_name} generated {files_saved} files now available for other tools in session")
        
        return files_saved
    
    @staticmethod
    def filter_large_base64_from_tool_result(content_text: str) -> str:
        """Filter out large base64 content from tool results to prevent LLM context overflow."""
        try:
            import re
            
            # logger.info(f"Filtering tool result content: {len(content_text)} chars")
            
            # Check if this looks like JSON
            if content_text.strip().startswith('{'):
                try:
                    data = json.loads(content_text)
                    if isinstance(data, dict):
                        filtered_data = data.copy()
                        
                        # Remove or truncate large base64 fields
                        large_base64_fields = [
                            'returned_file_contents', 'returned_file_base64', 
                            'content_base64', 'file_data_base64'
                        ]
                        
                        for field in large_base64_fields:
                            if field in filtered_data:
                                if isinstance(filtered_data[field], list):
                                    filtered_data[field] = [
                                        f"<file_content_removed_{i}_size_{len(content)}_bytes>" 
                                        if len(content) > 10000 else content
                                        for i, content in enumerate(filtered_data[field])
                                    ]
                                elif isinstance(filtered_data[field], str) and len(filtered_data[field]) > 10000:
                                    filtered_data[field] = f"<file_content_removed_size_{len(filtered_data[field])}_bytes>"
                        
                        # Remove large HTML content from LLM context (but preserve file references)
                        html_fields = ['custom_html', 'plot_html']
                        for field in html_fields:
                            if field in filtered_data:
                                content_size = len(str(filtered_data[field])) if filtered_data[field] else 0
                                if content_size > 5000:  # Only filter very large HTML content
                                    filtered_data[field] = f"<html_content_removed_size_{content_size}_bytes>"
                        
                        # Filter returned_files array
                        if 'returned_files' in filtered_data and isinstance(filtered_data['returned_files'], list):
                            for file_info in filtered_data['returned_files']:
                                if isinstance(file_info, dict) and 'content_base64' in file_info:
                                    content_size = len(file_info['content_base64'])
                                    if content_size > 10000:
                                        file_info['content_base64'] = f"<file_content_removed_size_{content_size}_bytes>"
                        
                        filtered_json = json.dumps(filtered_data, indent=2)
                        logger.info(f"Filtered JSON result: {len(filtered_json)} chars (was {len(content_text)} chars)")
                        return filtered_json
                        
                except json.JSONDecodeError:
                    pass
            
            # Fallback: Use regex to find and replace large base64-like strings
            base64_pattern = r'\b[A-Za-z0-9+/]{1000,}={0,2}\b'
            
            def replace_large_base64(match):
                content = match.group(0)
                return f"<large_base64_content_removed_size_{len(content)}_bytes>"
            
            filtered_content = re.sub(base64_pattern, replace_large_base64, content_text)
            
            if len(filtered_content) != len(content_text):
                logger.info(f"Regex filtered large base64 content: {len(content_text)} -> {len(filtered_content)} chars")
            
            return filtered_content
            
        except Exception as e:
            logger.warning(f"Error filtering base64 content from tool result: {e}")
            return content_text


class ToolExecutor:
    """Handles execution of MCP tools and special tools."""
    
    def __init__(self, mcp_manager: MCPToolManager):
        self.mcp_manager = mcp_manager
        self.file_manager = FileManager()
    
    async def execute_tool_calls(
        self, 
        tool_calls: List[Dict], 
        tool_mapping: Dict[str, Dict],
        context: ExecutionContext
    ) -> List[ToolResult]:
        """Execute all tool calls and return results."""
        if not tool_calls:
            logger.warning("No tool calls provided to execute")
            return []
            
        # logger.info(f"Executing {len(tool_calls)} tool calls for user {context.user_email}")
        results = []
        
        for i, tool_call in enumerate(tool_calls):
            logger.info(f"Processing tool call {i+1}/{len(tool_calls)}: {tool_call['function']['name']}")
            result = await self._execute_single_tool(tool_call, tool_mapping, context)
            results.append(result)
            
            # Send progress update for multiple tool calls
            if context.should_send_ui_updates() and len(tool_calls) > 1:
                await context.session.send_update_to_ui("tool_progress", {
                    "current": i + 1,
                    "total": len(tool_calls),
                    "completed_tool": tool_call['function']['name']
                })
        
        logger.info(f"Completed execution of {len(results)} tool calls")
        return results
    
    async def _execute_single_tool(
        self, 
        tool_call: Dict, 
        tool_mapping: Dict[str, Dict],
        context: ExecutionContext
    ) -> ToolResult:
        """Execute one tool call with proper error handling."""
        function_name = tool_call["function"]["name"]
        function_args = json.loads(tool_call["function"]["arguments"])
        
        logger.info(f"Processing tool call: {function_name} with args: {function_args}")
        
        # Handle special tools
        if function_name == "all_work_done":
            return await self._handle_completion_tool(tool_call, function_args, context)
        
        if function_name == "canvas_canvas":
            return await self._handle_canvas_tool(tool_call, function_args, context)
        
        # Handle regular MCP tools
        if function_name in tool_mapping:
            return await self._handle_mcp_tool(tool_call, function_args, tool_mapping[function_name], context)
        
        # Tool not found
        error_message = f"Unknown tool: {function_name}. Available tools: {', '.join(tool_mapping.keys())}"
        logger.error(f"Tool {function_name} not found in mapping")
        
        if context.should_send_ui_updates():
            await context.session.send_update_to_ui("tool_result", {
                "tool_name": function_name,
                "server_name": "unknown",
                "function_name": function_name,
                "tool_call_id": tool_call["id"],
                "result": error_message,
                "success": False,
                "error": f"Tool {function_name} not found",
                "agent_mode": context.agent_mode
            })
        
        return ToolResult(
            tool_call_id=tool_call["id"],
            content=json.dumps({"error": error_message}),
            success=False,
            error=f"Tool {function_name} not found"
        )
    
    async def _handle_completion_tool(self, tool_call: Dict, function_args: Dict, context: ExecutionContext) -> ToolResult:
        """Handle the agent completion tool call."""
        logger.info("Agent completion tool called by user %s", context.user_email)
        
        if context.agent_mode:
            logger.info("AGENT MODE: Work completion tool called")
        
        # Send UI updates if session available
        if context.should_send_ui_updates():
            await context.session.send_update_to_ui("tool_call", {
                "tool_name": "all_work_done",
                "server_name": "agent_completion",
                "function_name": "all_work_done",
                "parameters": function_args,
                "tool_call_id": tool_call["id"],
                "agent_mode": context.agent_mode
            })
            
            await context.session.send_update_to_ui("tool_result", {
                "tool_name": "all_work_done",
                "server_name": "agent_completion",
                "function_name": "all_work_done",
                "tool_call_id": tool_call["id"],
                "result": "Agent completion acknowledged: Work completed",
                "success": True,
                "agent_mode": context.agent_mode
            })
        
        return ToolResult(
            tool_call_id=tool_call["id"],
            content="Agent completion acknowledged: Work completed",
            success=True
        )
    
    async def _handle_canvas_tool(self, tool_call: Dict, function_args: Dict, context: ExecutionContext) -> ToolResult:
        """Handle the canvas tool call."""
        logger.info("Canvas tool called by user %s", context.user_email)
        content = function_args.get("content", "")
        
        # Send canvas content to UI
        if context.should_send_ui_updates():
            await context.session.send_update_to_ui("canvas_content", {
                "content": content,
                "tool_call_id": tool_call["id"]
            })
        
        return ToolResult(
            tool_call_id=tool_call["id"],
            content="Content displayed in canvas successfully.",
            success=True
        )
    
    async def _handle_mcp_tool(
        self, 
        tool_call: Dict, 
        function_args: Dict, 
        mapping: Dict[str, str],
        context: ExecutionContext
    ) -> ToolResult:
        """Handle regular MCP tool execution."""
        server_name = mapping["server"]
        tool_name = mapping["tool_name"]
        
        # logger.info(f"TOOL MAPPING: {tool_call['function']['name']} -> server: {server_name}, tool: {tool_name}")
        
        if context.agent_mode:
            logger.info(f"AGENT MODE: Executing tool {tool_name} on server {server_name}")
            logger.info(f"AGENT MODE: Tool parameters: {function_args}")
        
        # Send tool call notification to UI
        if context.should_send_ui_updates():
            await context.session.send_update_to_ui("tool_call", {
                "tool_name": tool_name,
                "server_name": server_name,
                "function_name": tool_call["function"]["name"],
                "parameters": function_args,
                "tool_call_id": tool_call["id"],
                "agent_mode": context.agent_mode
            })
        
        try:
            logger.info(f"Executing tool {tool_name} on server {server_name} for user {context.user_email}")
            logger.info(f"Original tool arguments: {function_args}")
            
            # Inject file data if tool expects it and session has uploaded files
            enhanced_args = await self.file_manager.inject_file_data(function_args, context.session)
            logger.info(f"Enhanced tool arguments: {list(enhanced_args.keys())}")
            
            # Execute the tool
            tool_result = await self.mcp_manager.call_tool(server_name, tool_name, enhanced_args)
            
            if context.agent_mode:
                logger.info(f"AGENT MODE: Tool {tool_name} executed successfully")
                logger.info(f"AGENT MODE: Tool result preview: {str(tool_result)[:200]}...")
            
            # Process the result
            return await self._process_tool_result(
                tool_result, tool_call, tool_name, server_name, context
            )
            
        except Exception as exc:
            logger.error("Error executing tool %s: %s", tool_name, exc)
            error_message = f"Tool execution failed: {exc}"
            
            # Send tool error notification to UI
            if context.should_send_ui_updates():
                await context.session.send_update_to_ui("tool_result", {
                    "tool_name": tool_name,
                    "server_name": server_name,
                    "function_name": tool_call["function"]["name"],
                    "tool_call_id": tool_call["id"],
                    "result": error_message,
                    "success": False,
                    "error": str(exc),
                    "agent_mode": context.agent_mode
                })
            
            return ToolResult(
                tool_call_id=tool_call["id"],
                content=json.dumps({"error": error_message}),
                success=False,
                error=str(exc)
            )
    
    async def _process_tool_result(
        self,
        tool_result,
        tool_call: Dict,
        tool_name: str,
        server_name: str,
        context: ExecutionContext
    ) -> ToolResult:
        """Process tool result, handle files, and send UI updates with unified canvas system."""
        
        parsed_result = None
        
        # Extract text content from CallToolResult
        if hasattr(tool_result, "content") and tool_result.content:
            text_content_item = tool_result.content[0]
            if hasattr(text_content_item, "text"):
                try:
                    parsed_result = json.loads(text_content_item.text)
                except json.JSONDecodeError:
                    pass
        
        # Check if tool_result is a dict (fallback)
        if parsed_result is None and isinstance(tool_result, dict):
            parsed_result = tool_result
        
        # Extract content text
        if hasattr(tool_result, "content"):
            if hasattr(tool_result.content, "__iter__") and not isinstance(tool_result.content, str):
                content_text = "\n".join(
                    [block.text if hasattr(block, "text") else str(block) for block in tool_result.content]
                )
            else:
                content_text = str(tool_result.content)
        else:
            content_text = str(tool_result)
        
        # Extract and save files from tool result to session
        files_saved = 0
        canvas_files = []  # Files that should be displayed in canvas
        
        if context.should_send_ui_updates() and parsed_result:
            # logger.info(f"About to save tool files to session for tool {tool_name}")
            files_saved = await self.file_manager.save_tool_files_to_session(parsed_result, context.session, tool_name)
            logger.info(f"Session now has {len(context.session.uploaded_files)} files: {list(context.session.uploaded_files.keys())}")
            
            # Check for canvas-displayable files
            canvas_files = self._get_canvas_files(parsed_result, context.session)
        
        # Send unified canvas update if there are displayable files
        if context.should_send_ui_updates() and canvas_files:
            await context.session.send_update_to_ui("canvas_files", {
                "files": canvas_files,
                "tool_name": tool_name,
                "server_name": server_name,
                "tool_call_id": tool_call["id"]
            })
            logger.info(f"Tool {tool_name} generated {len(canvas_files)} files for canvas display")
        
        # Send tool result notification to UI
        if context.should_send_ui_updates():
            # For agent mode, filter base64 content to improve UI experience
            if context.agent_mode:
                ui_content = self.file_manager.filter_large_base64_from_tool_result(content_text)
                if len(ui_content) != len(content_text):
                    logger.info(f"AGENT MODE: Filtered base64 content from UI update: {len(content_text)} -> {len(ui_content)} chars")
            else:
                ui_content = content_text
            
            await context.session.send_update_to_ui("tool_result", {
                "tool_name": tool_name,
                "server_name": server_name,
                "function_name": tool_call["function"]["name"],
                "tool_call_id": tool_call["id"],
                "result": ui_content,
                "success": True,
                "agent_mode": context.agent_mode
            })
        
        # Filter out large base64 content from tool results for LLM context
        # logger.info(f"About to filter content for LLM: {len(content_text)} chars")
        filtered_content_for_llm = self.file_manager.filter_large_base64_from_tool_result(content_text)
        logger.info(f"Filtered content for LLM: {len(filtered_content_for_llm)} chars")
        
        return ToolResult(
            tool_call_id=tool_call["id"],
            content=filtered_content_for_llm,
            success=True,
            files_generated=[f"Generated {files_saved} files"] if files_saved > 0 else []
        )
    
    def _get_canvas_files(self, result_dict: Dict, session) -> List[Dict]:
        """Extract files that should be displayed in canvas based on file type."""
        canvas_files = []
        
        # File extensions that should be displayed in canvas
        canvas_extensions = {
            # Images
            '.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.bmp', '.ico',
            # Documents
            '.pdf', '.html', '.htm',
            # Text/code files
            '.txt', '.md', '.rst', '.csv', '.json', '.xml', '.yaml', '.yml',
            '.py', '.js', '.css', '.ts', '.jsx', '.tsx', '.vue', '.sql'
        }
        
        # Check returned_files array (preferred format)
        if "returned_files" in result_dict and isinstance(result_dict["returned_files"], list):
            for file_info in result_dict["returned_files"]:
                if isinstance(file_info, dict) and "filename" in file_info:
                    filename = file_info["filename"]
                    file_ext = self._get_file_extension(filename).lower()
                    
                    if file_ext in canvas_extensions:
                        # Get the file content from session (it should be uploaded by now)
                        if hasattr(session, 'uploaded_files') and filename in session.uploaded_files:
                            canvas_files.append({
                                "filename": filename,
                                "type": self._get_canvas_file_type(file_ext),
                                "s3_key": session.uploaded_files[filename],
                                "size": file_info.get("size", 0),
                                "source": "tool_generated"
                            })
        
        # Check legacy single file format
        elif "returned_file_name" in result_dict and "returned_file_base64" in result_dict:
            filename = result_dict["returned_file_name"]
            file_ext = self._get_file_extension(filename).lower()
            
            if file_ext in canvas_extensions:
                if hasattr(session, 'uploaded_files') and filename in session.uploaded_files:
                    canvas_files.append({
                        "filename": filename,
                        "type": self._get_canvas_file_type(file_ext),
                        "s3_key": session.uploaded_files[filename],
                        "size": 0,  # Size not available in legacy format
                        "source": "tool_generated"
                    })
        
        logger.info(f"Found {len(canvas_files)} canvas-displayable files: {[f['filename'] for f in canvas_files]}")
        return canvas_files
    
    def _get_file_extension(self, filename: str) -> str:
        """Extract file extension from filename."""
        return '.' + filename.split('.')[-1] if '.' in filename else ''
    
    def _get_canvas_file_type(self, file_ext: str) -> str:
        """Determine canvas display type based on file extension."""
        image_exts = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.bmp', '.ico'}
        text_exts = {'.txt', '.md', '.rst', '.csv', '.json', '.xml', '.yaml', '.yml', 
                    '.py', '.js', '.css', '.ts', '.jsx', '.tsx', '.vue', '.sql'}
        
        if file_ext in image_exts:
            return 'image'
        elif file_ext == '.pdf':
            return 'pdf'
        elif file_ext in {'.html', '.htm'}:
            return 'html'
        elif file_ext in text_exts:
            return 'text'
        else:
            return 'other'