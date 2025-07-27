import asyncio
import json
import logging
import os
from typing import Dict, List

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
    
    logger.info(f"Session has {len(session.uploaded_files)} uploaded files: {list(session.uploaded_files.keys())}")
    
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
                    
                    logger.info(f"🔧 TOOL MAPPING: {function_name} -> server: {server_name}, tool: {tool_name}")
                    
                    # Send tool call notification to UI
                    if session:
                        await session.send_update_to_ui("tool_call", {
                            "tool_name": tool_name,
                            "server_name": server_name,
                            "function_name": function_name,
                            "parameters": function_args,
                            "tool_call_id": tool_call["id"]
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
                        
                        # Send tool result notification to UI
                        if session:
                            await session.send_update_to_ui("tool_result", {
                                "tool_name": tool_name,
                                "server_name": server_name,
                                "function_name": function_name,
                                "tool_call_id": tool_call["id"],
                                "result": content_text,
                                "success": True
                            })
                        
                        tool_results.append(
                            {"tool_call_id": tool_call["id"], "role": "tool", "content": content_text}
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
                                "error": str(exc)
                            })
                        
                        tool_results.append(
                            {
                                "tool_call_id": tool_call["id"],
                                "role": "tool",
                                "content": json.dumps({"error": error_message}),
                            }
                        )
                else:
                    # Tool not found in mapping
                    logger.error(f"🔧 TOOL NOT FOUND: {function_name} not in tool mapping. Available tools: {list(tool_mapping.keys())}")
                    error_message = f"Unknown tool: {function_name}. Available tools: {', '.join(tool_mapping.keys())}"
                    
                    # Send tool error notification to UI
                    if session:
                        await session.send_update_to_ui("tool_result", {
                            "tool_name": function_name,
                            "server_name": "unknown",
                            "function_name": function_name,
                            "tool_call_id": tool_call["id"],
                            "result": error_message,
                            "success": False,
                            "error": f"Tool {function_name} not found"
                        })
                    
                    tool_results.append(
                        {
                            "tool_call_id": tool_call["id"],
                            "role": "tool",
                            "content": json.dumps({"error": error_message}),
                        }
                    )
            if tool_results:
                follow_up_messages = messages + [message] + tool_results
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
