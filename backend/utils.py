import asyncio
import json
import logging
import os
from typing import Any, Dict, List

import requests
from fastapi import Request, WebSocket

from auth import is_user_in_group
from config import config_manager
from mcp_client import MCPToolManager
from auth_utils import create_authorization_manager
from http_client import create_llm_client

logger = logging.getLogger(__name__)


def get_current_user(request: Request) -> str:
    """Return the current user from the request state."""
    return getattr(request.state, "user_email", None)

async def validate_selected_tools(
    selected_tools: List[str],
    user_email: str,
    mcp_manager: MCPToolManager,
) -> List[str]:
    """Validate selected tools and return authorized server names."""
    try:
        auth_manager = create_authorization_manager(is_user_in_group)
        
        # Get authorized servers for the user
        def get_authorized_servers():
            return mcp_manager.get_authorized_servers(user_email, is_user_in_group)
        
        # Validate tool access
        requested_servers, warnings = auth_manager.validate_tool_access(
            user_email, selected_tools, get_authorized_servers
        )
        
        # Log any warnings
        for warning in warnings:
            logger.warning(warning)
        
        if not requested_servers:
            return []
        
        # Handle exclusive servers
        final_servers = auth_manager.handle_exclusive_servers(
            requested_servers, mcp_manager.is_server_exclusive
        )
        
        # Perform final authorization check
        validated_servers = auth_manager.perform_final_authorization_check(
            user_email, final_servers, mcp_manager.get_server_groups
        )
        
        return validated_servers
        
    except Exception as e:
        logger.error(f"Error validating selected tools for user {user_email}: {e}", exc_info=True)
        return []


async def call_llm(model_name: str, messages: List[Dict[str, str]]) -> str:
    """Call an OpenAI-compliant LLM API using requests."""
    llm_config = config_manager.llm_config
    if model_name not in llm_config.models:
        raise ValueError(f"Model {model_name} not found in configuration")

    model_config = llm_config.models[model_name]
    api_url = model_config.model_url
    api_key = os.path.expandvars(model_config.api_key)
    model_id = model_config.model_name

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": model_id, "messages": messages, "max_tokens": 1000, "temperature": 0.7}

    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, lambda: requests.post(api_url, headers=headers, json=payload, timeout=30)
        )
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        logger.error("LLM API error %s: %s", response.status_code, response.text, exc_info=True)
        raise Exception(f"LLM API error: {response.status_code}")
    except requests.RequestException as exc:
        logger.error("Request error calling LLM: %s", exc, exc_info=True)
        raise Exception(f"Failed to call LLM: {exc}")
    except KeyError as exc:
        logger.error("Invalid response format from LLM: %s", exc, exc_info=True)
        raise Exception("Invalid response format from LLM")


async def _save_tool_files_to_session(tool_result: Dict[str, Any], session, tool_name: str) -> None:
    """
    Extract files from tool result and save them to the session for use by other tools.
    
    Args:
        tool_result: Parsed tool result containing file data
        session: ChatSession instance to save files to
        tool_name: Name of the tool that generated the files
    """
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
                session.uploaded_files[filename] = file_info["content_base64"]
                files_saved += 1
                logger.info(f"Saved file {filename} from tool {tool_name} to session {session.session_id}")
    
    # Check for legacy single file format
    elif "returned_file_name" in tool_result and "returned_file_base64" in tool_result:
        if tool_result['returned_file_name'].endswith(('.csv', '.json', '.txt', '.xlsx')):
            filename = tool_result['returned_file_name']
        else:
            filename = f"{tool_name}_{tool_result['returned_file_name']}"
        session.uploaded_files[filename] = tool_result["returned_file_base64"]
        files_saved += 1
        logger.info(f"Saved file {filename} from tool {tool_name} to session {session.session_id}")
    
    if files_saved > 0:
        logger.info(f"Tool {tool_name} generated {files_saved} files now available for other tools in session")


def _filter_large_base64_from_tool_result(content_text: str) -> str:
    """
    Filter out large base64 content from tool results to prevent LLM context overflow.
    
    Specifically targets the returned_file_contents and returned_file_base64 fields
    that contain large base64 encoded files that can crash the LLM.
    """
    try:
        # Try to parse as JSON to filter base64 fields
        import json
        import re
        
        logger.info(f"Filtering tool result content: {len(content_text)} chars")
        
        # Check if this looks like JSON
        if content_text.strip().startswith('{'):
            try:
                data = json.loads(content_text)
                if isinstance(data, dict):
                    logger.info(f"Parsed JSON data with keys: {list(data.keys())}")
                    # Filter out large base64 content fields
                    filtered_data = data.copy()
                    
                    # Remove or truncate large base64 fields
                    large_base64_fields = [
                        'returned_file_contents', 'returned_file_base64', 
                        'content_base64', 'file_data_base64'
                    ]
                    
                    for field in large_base64_fields:
                        if field in filtered_data:
                            if isinstance(filtered_data[field], list):
                                # For arrays of base64 content, replace with placeholders
                                filtered_data[field] = [
                                    f"<file_content_removed_{i}_size_{len(content)}_bytes>" 
                                    if len(content) > 10000 else content
                                    for i, content in enumerate(filtered_data[field])
                                ]
                            elif isinstance(filtered_data[field], str) and len(filtered_data[field]) > 10000:
                                # For single large base64 strings, replace with placeholder
                                filtered_data[field] = f"<file_content_removed_size_{len(filtered_data[field])}_bytes>"
                    
                    # Remove HTML content entirely from LLM context (it's only for UI)
                    ui_only_fields = ['custom_html', 'html_content', 'plot_html']
                    for field in ui_only_fields:
                        if field in filtered_data:
                            content_size = len(str(filtered_data[field])) if filtered_data[field] else 0
                            if content_size > 0:
                                logger.info(f"Removing UI-only field '{field}' ({content_size} bytes) from LLM context")
                                del filtered_data[field]
                                
                    # Remove or summarize other non-essential large fields for LLM context
                    if 'files' in filtered_data and isinstance(filtered_data['files'], list):
                        # Replace with just filenames for LLM context
                        filtered_data['files'] = [f"Generated file: {f}" for f in filtered_data['files']]
                    
                    # Also filter returned_files array
                    if 'returned_files' in filtered_data and isinstance(filtered_data['returned_files'], list):
                        for file_info in filtered_data['returned_files']:
                            if isinstance(file_info, dict) and 'content_base64' in file_info:
                                content_size = len(file_info['content_base64'])
                                if content_size > 10000:  # 10KB threshold
                                    file_info['content_base64'] = f"<file_content_removed_size_{content_size}_bytes>"
                    
                    # Convert back to JSON string
                    filtered_json = json.dumps(filtered_data, indent=2)
                    logger.info(f"Filtered JSON result: {len(filtered_json)} chars (was {len(content_text)} chars)")
                    return filtered_json
                    
            except json.JSONDecodeError:
                # Not JSON, fall through to text processing
                pass
        
        # Fallback: Use regex to find and replace large base64-like strings
        # Base64 pattern: long strings of alphanumeric characters, +, /, and = at the end
        base64_pattern = r'\b[A-Za-z0-9+/]{1000,}={0,2}\b'
        
        def replace_large_base64(match):
            content = match.group(0)
            return f"<large_base64_content_removed_size_{len(content)}_bytes>"
        
        # Replace large base64 strings with placeholders
        filtered_content = re.sub(base64_pattern, replace_large_base64, content_text)
        
        if len(filtered_content) != len(content_text):
            logger.info(f"Regex filtered large base64 content from tool result: {len(content_text)} -> {len(filtered_content)} chars")
        else:
            logger.info(f"No large base64 content found to filter (content: {len(content_text)} chars)")
        
        return filtered_content
        
    except Exception as e:
        logger.warning(f"Error filtering base64 content from tool result: {e}")
        return content_text


def _inject_file_data(function_args: Dict, session) -> Dict:
    """Inject file data into tool arguments if tool expects it and files are available"""
    logger.info(f"_inject_file_data called with args: {list(function_args.keys())}")
    
    if not session:
        logger.warning("No session provided to _inject_file_data")
        return function_args
        
    if not hasattr(session, 'uploaded_files'):
        logger.warning("Session has no uploaded_files attribute")
        return function_args
        
    if not session.uploaded_files:
        logger.warning("Session uploaded_files is empty")
        return function_args
    
    logger.info(f"Session has {len(session.uploaded_files)} files: {list(session.uploaded_files.keys())}")
    
    # Create a copy to avoid modifying the original
    enhanced_args = function_args.copy()
    
    # Check if tool has filename parameter - if so, it might need file injection
    if 'filename' in function_args:
        filename = function_args.get('filename')
        logger.info(f"Tool has filename parameter: {filename}")
        
        if filename and filename in session.uploaded_files:
            # Add file_data_base64 parameter even if LLM didn't include it
            file_data = session.uploaded_files[filename]
            enhanced_args['file_data_base64'] = file_data
            logger.info(f"Successfully injected file data for '{filename}' into tool call (data length: {len(file_data) if file_data else 0})")
        else:
            logger.warning(f"File '{filename}' not found in uploaded files. Available: {list(session.uploaded_files.keys())}")
    else:
        logger.info(f"Tool does not have filename parameter. Args: {list(function_args.keys())}")
    
    return enhanced_args


def create_agent_completion_tool() -> Dict:
    """Create the all_work_is_done tool for agent mode completion."""
    return {
        "type": "function",
        "function": {
            "name": "all_work_is_done",
            "description": """IMPORTANT: Call this function when you have completely finished all the work requested by the user. 

This function signals that you have successfully completed the entire task or question asked by the user. Only call this when:
1. You have fully addressed the user's request
2. All necessary steps have been completed
3. You have provided a comprehensive final answer or solution
4. No further work or analysis is needed

Do not call this function if you need to continue thinking, gather more information, or perform additional steps.""",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "string",
                        "description": "A brief summary of what was accomplished"
                    }
                },
                "required": ["summary"]
            }
        }
    }

async def call_llm_with_tools(
    model_name: str,
    messages: List[Dict[str, str]],
    validated_servers: List[str],
    user_email: str,
    websocket: WebSocket,
    mcp_manager: MCPToolManager,
    session=None,  # Optional session for UI updates
    agent_mode: bool = False,  # New parameter for agent mode
    tool_choice_required: bool = False,  # New parameter for tool choice preference
    selected_tools: List[str] = None,  # New parameter for selected tools
) -> str:
    """Call LLM with tool-calling support."""
    if not validated_servers:
        return await call_llm(model_name, messages)

    # Get all available tools from validated servers
    tools_data = mcp_manager.get_tools_for_servers(validated_servers)
    all_tools_schema = tools_data["tools"]
    all_tool_mapping = tools_data["mapping"]
    
    # Filter to only include user's selected tools if provided
    if selected_tools:
        logger.info(f"Filtering tools to selected ones: {selected_tools}")
        tools_schema = []
        tool_mapping = {}
        
        # Convert selected tools to a set for faster lookup
        selected_tools_set = set(selected_tools)
        
        # Filter tools schema and mapping to only include selected tools
        for tool_schema in all_tools_schema:
            tool_function_name = tool_schema["function"]["name"]
            if tool_function_name in selected_tools_set:
                tools_schema.append(tool_schema)
                if tool_function_name in all_tool_mapping:
                    tool_mapping[tool_function_name] = all_tool_mapping[tool_function_name]
                    logger.info(f"Including selected tool: {tool_function_name}")
        
        logger.info(f"Filtered tools: {[t['function']['name'] for t in tools_schema]}")
    else:
        # Use all available tools if no specific selection
        logger.info("No tool filtering - using all available tools from validated servers")
        tools_schema = all_tools_schema
        tool_mapping = all_tool_mapping
    # LOG IF REQUIRED is on. tool_choice_required
    logger.info(f"Tool choice required: {tool_choice_required}, Agent mode: {agent_mode}")


    # Add agent completion tool if in agent mode
    if agent_mode:
        agent_tool = create_agent_completion_tool()
        tools_schema.append(agent_tool)
        tool_mapping["all_work_is_done"] = {
            "server": "agent_completion",
            "tool_name": "all_work_is_done"
        }

    if not tools_schema:
        return await call_llm(model_name, messages)

    llm_config = config_manager.llm_config
    if model_name not in llm_config.models:
        raise ValueError(f"Model {model_name} not found in configuration")

    model_config = llm_config.models[model_name]
    api_url = model_config.model_url
    api_key = os.path.expandvars(model_config.api_key)
    model_id = model_config.model_name

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    # Use user's tool choice preference, but fallback to exclusive server logic if not explicitly set
    is_exclusive = any(mcp_manager.is_server_exclusive(s) for s in validated_servers)
    tool_choice = "required" if (tool_choice_required or is_exclusive) else "auto"
    payload = {
        "model": model_id,
        "messages": messages,
        "tools": tools_schema,
        "tool_choice": tool_choice,
        "max_tokens": 1000,
        "temperature": 0.7,
    }

    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, lambda: requests.post(api_url, headers=headers, json=payload, timeout=30)
        )
        if response.status_code != 200:
            logger.error("LLM API error %s: %s", response.status_code, response.text, exc_info=True)
            raise Exception(f"LLM API error: {response.status_code}")

        result = response.json()
        choice = result["choices"][0]
        message = choice["message"]

        if message.get("tool_calls"):
            tool_results = []
            for tool_call in message["tool_calls"]:
                function_name = tool_call["function"]["name"]
                function_args = json.loads(tool_call["function"]["arguments"])
                
                # Handle agent completion tool specially
                if function_name == "all_work_is_done":
                    logger.info("Agent completion tool called by user %s", user_email)
                    summary = function_args.get("summary", "Work completed")
                    
                    # Enhanced logging for agent mode
                    if agent_mode:
                        logger.info("AGENT MODE: Work completion tool called")
                        logger.info(f"AGENT MODE: Completion summary: {summary}")
                    
                    # Send tool call notification to UI for completion
                    if session:
                        await session.send_update_to_ui("tool_call", {
                            "tool_name": "all_work_is_done",
                            "server_name": "agent_completion",
                            "function_name": "all_work_is_done",
                            "parameters": function_args,
                            "tool_call_id": tool_call["id"],
                            "agent_mode": agent_mode
                        })
                    
                    # Send tool result notification to UI for completion
                    if session:
                        await session.send_update_to_ui("tool_result", {
                            "tool_name": "all_work_is_done",
                            "server_name": "agent_completion",
                            "function_name": "all_work_is_done",
                            "tool_call_id": tool_call["id"],
                            "result": f"Agent completion acknowledged: {summary}",
                            "success": True,
                            "agent_mode": agent_mode
                        })
                    
                    tool_results.append({
                        "tool_call_id": tool_call["id"],
                        "role": "tool",
                        "content": f"Agent completion acknowledged: {summary}"
                    })
                    continue
                
                # Handle canvas tool specially
                if function_name == "canvas_canvas":
                    logger.info("Canvas tool called by user %s", user_email)
                    content = function_args.get("content", "")
                    
                    # Send canvas content to UI
                    if session:
                        await session.send_update_to_ui("canvas_content", {
                            "content": content,
                            "tool_call_id": tool_call["id"]
                        })
                    
                    tool_results.append({
                        "tool_call_id": tool_call["id"],
                        "role": "tool",
                        "content": f"Content displayed in canvas successfully."
                    })
                    continue
                
                if function_name in tool_mapping:
                    mapping = tool_mapping[function_name]
                    server_name = mapping["server"]
                    tool_name = mapping["tool_name"]
                    
                    logger.info(f"TOOL MAPPING: {function_name} -> server: {server_name}, tool: {tool_name}")
                    
                    # Enhanced logging for agent mode
                    if agent_mode:
                        logger.info(f"AGENT MODE: Executing tool {tool_name} on server {server_name}")
                        logger.info(f"AGENT MODE: Tool parameters: {function_args}")
                    
                    # Send tool call notification to UI
                    if session:
                        await session.send_update_to_ui("tool_call", {
                            "tool_name": tool_name,
                            "server_name": server_name,
                            "function_name": function_name,
                            "parameters": function_args,
                            "tool_call_id": tool_call["id"],
                            "agent_mode": agent_mode  # Add agent mode flag to UI update
                        })
                    
                    try:
                        logger.info(
                            "Executing tool %s on server %s for user %s",
                            tool_name,
                            server_name,
                            user_email,
                        )
                        logger.info(f"Original tool arguments: {function_args}")
                        
                        # Inject file data if tool expects it and session has uploaded files
                        enhanced_args = _inject_file_data(function_args, session)
                        logger.info(f"Enhanced tool arguments: {list(enhanced_args.keys())}")
                        
                        tool_result = await mcp_manager.call_tool(server_name, tool_name, enhanced_args)
                        
                        # Enhanced logging for agent mode
                        if agent_mode:
                            logger.info(f"AGENT MODE: Tool {tool_name} executed successfully")
                            logger.info(f"AGENT MODE: Tool result preview: {str(tool_result)[:200]}...")
                        
                        
                        # Parse the tool result to extract custom_html if present
                        custom_html_content = None
                        parsed_result = None
                        
                        # Extract text content from CallToolResult
                        if hasattr(tool_result, "content") and tool_result.content:
                            # Get the first text content item
                            text_content_item = tool_result.content[0]
                            if hasattr(text_content_item, "text"):
                                try:
                                    # Try to parse as JSON to see if it contains custom_html
                                    parsed_result = json.loads(text_content_item.text)
                                    if isinstance(parsed_result, dict) and "custom_html" in parsed_result:
                                        custom_html_content = parsed_result["custom_html"]
                                        logger.info(f"Tool {tool_name} returned custom HTML content for UI modification")
                                except json.JSONDecodeError:
                                    # Not JSON, treat as regular text
                                    pass
                        
                        # Check if tool_result is a dict with custom_html field (fallback)
                        if custom_html_content is None and isinstance(tool_result, dict) and "custom_html" in tool_result:
                            custom_html_content = tool_result["custom_html"]
                            logger.info(f"Tool {tool_name} returned custom HTML content for UI modification")
                        
                        if hasattr(tool_result, "content"):
                            if hasattr(tool_result.content, "__iter__") and not isinstance(tool_result.content, str):
                                content_text = "\n".join(
                                    [block.text if hasattr(block, "text") else str(block) for block in tool_result.content]
                                )
                            else:
                                content_text = str(tool_result.content)
                        else:
                            content_text = str(tool_result)
                        
                        # Send custom UI update if custom_html is present
                        if session and custom_html_content:
                            await session.send_update_to_ui("custom_ui", {
                                "type": "html_injection",
                                "content": custom_html_content,
                                "tool_name": tool_name,
                                "server_name": server_name,
                                "tool_call_id": tool_call["id"]
                            })
                        
                        # Extract and save files from tool result to session
                        # Try to get the result as a dict from various sources
                        result_dict = None
                        if parsed_result and isinstance(parsed_result, dict):
                            result_dict = parsed_result
                        elif isinstance(tool_result, dict):
                            result_dict = tool_result
                        
                        if session and result_dict:
                            logger.info(f"About to save tool files to session for tool {tool_name}")
                            await _save_tool_files_to_session(result_dict, session, tool_name)
                            logger.info(f"Session now has {len(session.uploaded_files)} files: {list(session.uploaded_files.keys())}")
                            
                            # Log file sizes for debugging large file issues
                            for filename, base64_data in session.uploaded_files.items():
                                file_size = len(base64_data) if base64_data else 0
                                logger.info(f"File {filename}: {file_size} bytes (base64)")
                                if file_size > 100000:  # Log warning for files over 100KB
                                    logger.warning(f"Large file {filename} ({file_size} bytes) may cause LLM context issues")
                        
                        # Send tool result notification to UI (with unfiltered content for downloads)
                        if session:
                            await session.send_update_to_ui("tool_result", {
                                "tool_name": tool_name,
                                "server_name": server_name,
                                "function_name": function_name,
                                "tool_call_id": tool_call["id"],
                                "result": content_text,  # Send unfiltered content to UI for downloads
                                "success": True,
                                "agent_mode": agent_mode  # Add agent mode flag to UI update
                            })
                        
                        # Filter out large base64 content from tool results for LLM context only
                        logger.info(f"About to filter content for LLM: {len(content_text)} chars")
                        filtered_content_for_llm = _filter_large_base64_from_tool_result(content_text)
                        logger.info(f"Filtered content for LLM: {len(filtered_content_for_llm)} chars")
                        
                        tool_results.append(
                            {"tool_call_id": tool_call["id"], "role": "tool", "content": filtered_content_for_llm}
                        )
                    except Exception as exc:
                        logger.error("Error executing tool %s: %s", tool_name, exc)
                        error_message = f"Tool execution failed: {exc}"
                        
                        # Send tool error notification to UI
                        if session:
                            await session.send_update_to_ui("tool_result", {
                                "tool_name": tool_name,
                                "server_name": server_name,
                                "function_name": function_name,
                                "tool_call_id": tool_call["id"],
                                "result": error_message,
                                "success": False,
                                "error": str(exc),
                                "agent_mode": agent_mode  # Add agent mode flag to UI update
                            })
                        
                        error_content = json.dumps({"error": error_message})
                        tool_results.append(
                            {
                                "tool_call_id": tool_call["id"],
                                "role": "tool",
                                "content": error_content,
                            }
                        )
                else:
                    # Tool not found in mapping
                    logger.error(f"TOOL NOT FOUND: {function_name} not in tool mapping. Available tools: {list(tool_mapping.keys())}")
                    error_message = f"Unknown tool: {function_name}. Available tools: {', '.join(tool_mapping.keys())}"
                    
                    # Enhanced logging for agent mode
                    if agent_mode:
                        logger.error(f"AGENT MODE: Tool {function_name} not found in mapping")
                    
                    # Send tool error notification to UI
                    if session:
                        await session.send_update_to_ui("tool_result", {
                            "tool_name": function_name,
                            "server_name": "unknown",
                            "function_name": function_name,
                            "tool_call_id": tool_call["id"],
                            "result": error_message,
                            "success": False,
                            "error": f"Tool {function_name} not found",
                            "agent_mode": agent_mode  # Add agent mode flag to UI update
                        })
                    
                    error_content = json.dumps({"error": error_message})
                    tool_results.append(
                        {
                            "tool_call_id": tool_call["id"],
                            "role": "tool",
                            "content": error_content,
                        }
                    )
            if tool_results:
                follow_up_messages = messages + [message] + tool_results
                
                # Log follow-up payload details for debugging
                total_content_length = sum(len(str(msg.get('content', ''))) for msg in follow_up_messages)
                logger.info(f"Follow-up LLM call: {len(follow_up_messages)} messages, total content length: {total_content_length} chars")
                
                # Check if any message content is extremely large
                for i, msg in enumerate(follow_up_messages):
                    content_length = len(str(msg.get('content', '')))
                    if content_length > 50000:  # Warn about messages over 50KB
                        logger.warning(f"Message {i} has large content: {content_length} chars, role: {msg.get('role', 'unknown')}")
                
                follow_up_payload = {
                    "model": model_id,
                    "messages": follow_up_messages,
                    "max_tokens": 1000,
                    "temperature": 0.7,
                }
                follow_up_response = await loop.run_in_executor(
                    None,
                    lambda: requests.post(api_url, headers=headers, json=follow_up_payload, timeout=30),
                )
                if follow_up_response.status_code == 200:
                    follow_up_result = follow_up_response.json()
                    return follow_up_result["choices"][0]["message"]["content"]
                logger.error(
                    "Follow-up LLM call failed: %s", follow_up_response.status_code, exc_info=True
                )
                return message.get(
                    "content", "Tool execution completed but failed to generate response."
                )
        return message.get("content", "")
    except requests.RequestException as exc:
        logger.error("Request error calling LLM with tools: %s", exc, exc_info=True)
        raise Exception(f"Failed to call LLM: {exc}")
    except KeyError as exc:
        logger.error("Invalid response format from LLM: %s", exc, exc_info=True)
        raise Exception("Invalid response format from LLM")

