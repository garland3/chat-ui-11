import asyncio
import json
import logging
import os
from typing import Dict, List

import requests
from fastapi import Request, WebSocket

from auth import is_user_in_group
from config_utils import load_llm_config
from mcp_client import MCPToolManager

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
    if not selected_tools:
        return []

    authorized_servers = set(
        mcp_manager.get_authorized_servers(user_email, is_user_in_group)
    )
    logger.info("User %s is authorized for servers: %s", user_email, authorized_servers)

    requested_server_names = set()
    for tool_key in selected_tools:
        parts = tool_key.split("_", 1)
        if len(parts) == 2:
            server_name = parts[0]
            # Allow canvas pseudo-tool for all users
            if server_name == "canvas" or server_name in authorized_servers:
                requested_server_names.add(server_name)
            else:
                logger.warning(
                    "User %s attempted to access unauthorized server: %s",
                    user_email,
                    server_name,
                )

    if not requested_server_names:
        logger.info("No authorized servers requested by user %s", user_email)
        return []

    exclusive_servers = []
    regular_servers = []
    for server_name in requested_server_names:
        if mcp_manager.is_server_exclusive(server_name):
            exclusive_servers.append(server_name)
        else:
            regular_servers.append(server_name)

    if exclusive_servers:
        if len(exclusive_servers) > 1:
            logger.warning("Multiple exclusive servers selected, using only %s", exclusive_servers[0])
        final_servers = {exclusive_servers[0]}
        logger.info("Exclusive mode enabled for server: %s", exclusive_servers[0])
    else:
        final_servers = set(regular_servers)

    validated_servers = []
    for server_name in final_servers:
        required_groups = mcp_manager.get_server_groups(server_name)
        authorized = False
        if not required_groups:
            authorized = True
        else:
            for group in required_groups:
                if is_user_in_group(user_email, group):
                    authorized = True
                    break
        if authorized:
            validated_servers.append(server_name)
        else:
            logger.error(
                "SECURITY VIOLATION: Server %s passed initial auth but failed final validation for user %s",
                server_name,
                user_email,
            )

    logger.info("Final validated servers for user %s: %s", user_email, validated_servers)
    return validated_servers


async def call_llm(model_name: str, messages: List[Dict[str, str]]) -> str:
    """Call an OpenAI-compliant LLM API using requests."""
    llm_config = load_llm_config()
    models = llm_config.get("models", {})
    if model_name not in models:
        raise ValueError(f"Model {model_name} not found in configuration")

    model_config = models[model_name]
    api_url = model_config["model_url"]
    api_key = os.path.expandvars(model_config["api_key"])
    model_id = model_config["model_name"]

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
        logger.error("LLM API error %s: %s", response.status_code, response.text)
        raise Exception(f"LLM API error: {response.status_code}")
    except requests.RequestException as exc:
        logger.error("Request error calling LLM: %s", exc)
        raise Exception(f"Failed to call LLM: {exc}")
    except KeyError as exc:
        logger.error("Invalid response format from LLM: %s", exc)
        raise Exception("Invalid response format from LLM")


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
) -> str:
    """Call LLM with tool-calling support."""
    if not validated_servers:
        return await call_llm(model_name, messages)

    tools_data = mcp_manager.get_tools_for_servers(validated_servers)
    tools_schema = tools_data["tools"]
    tool_mapping = tools_data["mapping"]

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

    llm_config = load_llm_config()
    models = llm_config.get("models", {})
    if model_name not in models:
        raise ValueError(f"Model {model_name} not found in configuration")

    model_config = models[model_name]
    api_url = model_config["model_url"]
    api_key = os.path.expandvars(model_config["api_key"])
    model_id = model_config["model_name"]

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    is_exclusive = any(mcp_manager.is_server_exclusive(s) for s in validated_servers)
    payload = {
        "model": model_id,
        "messages": messages,
        "tools": tools_schema,
        "tool_choice": "required" if is_exclusive else "auto",
        "max_tokens": 1000,
        "temperature": 0.7,
    }

    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, lambda: requests.post(api_url, headers=headers, json=payload, timeout=30)
        )
        if response.status_code != 200:
            logger.error("LLM API error %s: %s", response.status_code, response.text)
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
                        tool_result = await mcp_manager.call_tool(server_name, tool_name, function_args)
                        if hasattr(tool_result, "content"):
                            if hasattr(tool_result.content, "__iter__") and not isinstance(tool_result.content, str):
                                content_text = "\n".join(
                                    [block.text if hasattr(block, "text") else str(block) for block in tool_result.content]
                                )
                            else:
                                content_text = str(tool_result.content)
                        else:
                            content_text = str(tool_result)
                        
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
                    "Follow-up LLM call failed: %s", follow_up_response.status_code
                )
                return message.get(
                    "content", "Tool execution completed but failed to generate response."
                )
        return message.get("content", "")
    except requests.RequestException as exc:
        logger.error("Request error calling LLM with tools: %s", exc)
        raise Exception(f"Failed to call LLM: {exc}")
    except KeyError as exc:
        logger.error("Invalid response format from LLM: %s", exc)
        raise Exception("Invalid response format from LLM")
