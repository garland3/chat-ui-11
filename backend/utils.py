import asyncio
import logging
import os
from typing import Any, Dict, List

import requests
from fastapi import Request, WebSocket

from auth import is_user_in_group
from config import config_manager
from mcp_client import MCPToolManager
from auth_utils import create_authorization_manager

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
    """
    Call an LLM using the centralized LLMCaller.
    
    DEPRECATED: This function is now a thin wrapper around LLMCaller.call_plain().
    Direct use of LLMCaller is recommended for new code.
    """
    from llm_caller import LLMCaller
    llm_caller = LLMCaller()
    return await llm_caller.call_plain(model_name, messages)




def create_agent_completion_tool() -> Dict:
    """Create the all_work_done tool for agent mode completion."""
    return {
        "type": "function",
        "function": {
            "name": "all_work_done",
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
    """
    Call LLM with tool-calling support.
    
    IMPORTANT: This function has been refactored to delegate to the new modular architecture.
    It maintains backward compatibility while using the cleaner LLMCaller and ToolExecutor.
    """
    # Import the new components (importing here to avoid circular imports)
    from llm_caller import LLMCaller
    from tool_executor import ToolExecutor, ExecutionContext
    
    # Initialize the new components
    llm_caller = LLMCaller()
    tool_executor = ToolExecutor(mcp_manager)
    
    # Handle simple case: no tools
    if not validated_servers:
        return await llm_caller.call_plain(model_name, messages)

    # Get all available tools from validated servers
    tools_data = mcp_manager.get_tools_for_servers(validated_servers)
    all_tools_schema = tools_data["tools"]
    all_tool_mapping = tools_data["mapping"]
    
    # Filter to only include user's selected tools if provided
    if selected_tools:
        logger.info(f"Filtering tools to selected ones: {selected_tools}")
        tools_schema = []
        tool_mapping = {}
        
        selected_tools_set = set(selected_tools)
        
        for tool_schema in all_tools_schema:
            tool_function_name = tool_schema["function"]["name"]
            if tool_function_name in selected_tools_set:
                tools_schema.append(tool_schema)
                if tool_function_name in all_tool_mapping:
                    tool_mapping[tool_function_name] = all_tool_mapping[tool_function_name]
    else:
        logger.info("No tool filtering - using all available tools from validated servers")
        tools_schema = all_tools_schema
        tool_mapping = all_tool_mapping

    # Add agent completion tool if in agent mode
    if agent_mode:
        agent_tool = create_agent_completion_tool()
        tools_schema.append(agent_tool)
        tool_mapping["all_work_done"] = {
            "server": "agent_completion",
            "tool_name": "all_work_done"
        }

    if not tools_schema:
        return await llm_caller.call_plain(model_name, messages)

    # Determine tool choice
    is_exclusive = any(mcp_manager.is_server_exclusive(s) for s in validated_servers)
    tool_choice = "required" if (tool_choice_required or is_exclusive) else "auto"
    
    # Call LLM with tools using new architecture
    llm_response = await llm_caller.call_with_tools(
        model_name,
        messages,
        tools_schema,
        tool_choice
    )
    
    # Process tool calls if any
    if llm_response.has_tool_calls():
        execution_context = ExecutionContext(
            user_email=user_email,
            session=session,
            agent_mode=agent_mode
        )
        
        tool_results = await tool_executor.execute_tool_calls(
            llm_response.tool_calls,
            tool_mapping,
            execution_context
        )
        
        # Make follow-up LLM call with tool results
        follow_up_messages = messages + [
            {"role": "assistant", "content": llm_response.content, "tool_calls": llm_response.tool_calls}
        ] + [
            {"tool_call_id": result.tool_call_id, "role": "tool", "content": result.content}
            for result in tool_results
        ]
        
        # Log follow-up payload details for debugging
        total_content_length = sum(len(str(msg.get('content', ''))) for msg in follow_up_messages)
        logger.info(f"Follow-up LLM call: {len(follow_up_messages)} messages, total content length: {total_content_length} chars")
        
        follow_up_response = await llm_caller.call_plain(model_name, follow_up_messages)
        return follow_up_response
    
    return llm_response.content

