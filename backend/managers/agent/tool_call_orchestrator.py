"""Tool call orchestrator for managing LLM tool execution workflows."""

import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional
from uuid import UUID

from managers.session.session_models import Session
from managers.tools.tool_caller import ToolCaller
from managers.tools.tool_models import ToolCall, ToolResult
from managers.llm.llm_manager import LLMManager
from managers.ui_callback.tool_notifications import (
    notify_tool_start,
    notify_tool_complete,
    notify_tool_error,
)
from managers.auth.auth_manager import is_user_in_group

logger = logging.getLogger(__name__)


class ToolCallOrchestrator:
    """Orchestrates the complete tool execution workflow with LLM integration."""

    def __init__(self, tool_caller: ToolCaller, llm_manager: LLMManager):
        """Initialize the orchestrator with required managers."""
        self.tool_caller = tool_caller
        self.llm_manager = llm_manager
        logger.info("ToolCallOrchestrator initialized")

    async def orchestrate_tool_workflow(
        self,
        session: Session,
        session_id: UUID,
        model: str,
        temperature: float,
        selected_tool_map: Dict[str, List[str]],
        user_email: Optional[str] = None,
        update_callback: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None,
    ) -> tuple[str, List[ToolResult]]:
        """
        Execute the complete tool workflow: authorization -> LLM call -> tool execution -> final LLM call.

        Args:
            session: The chat session
            session_id: Session ID for callbacks
            model: LLM model to use
            temperature: LLM temperature setting
            selected_tool_map: Selected tools for the user
            user_email: User email for authorization
            update_callback: Callback for UI updates

        Returns:
            Tuple of (final_response, tool_results)
        """
        # Get authorized and filtered tools using dependency injection
        filtered_tools = self.tool_caller.get_authorized_tools_for_user(
            username=user_email or "",
            selected_tool_map=selected_tool_map,
            is_user_in_group=is_user_in_group,
        )
        logger.info(
            f"User {user_email} is authorized for tools (schemas count): {len(filtered_tools)}"
        )

        logger.info(f"Using {len(filtered_tools)} tools for LLM call")

        # Call LLM with tools
        llm_response_data = await self.llm_manager.call_with_tools(
            model, session.history, filtered_tools, "auto", temperature
        )

        llm_content = llm_response_data.get("content", "")
        tool_calls = llm_response_data.get("tool_calls", [])

        # Execute tool calls if any
        tool_results = await self._execute_tool_calls(
            tool_calls, session, session_id, update_callback
        )

        # Determine final response
        final_response = llm_content
        if tool_results:
            # If there were tool results, make a final call to get response
            N_chars_per_message = 100
            # print the message to the llm, for each message truncate. put in logging.info.
            truncated_messages = [
                message.content[:N_chars_per_message]
                for message in session.history.messages
            ]
            logging.info(f"Truncated messages for LLM call: {truncated_messages}")
            final_llm_response = await self.llm_manager.call_plain(
                model, session.history, temperature
            )
            final_response = final_llm_response

        return final_response, tool_results

    async def _execute_tool_calls(
        self,
        tool_calls: List[Dict[str, Any]],
        session: Session,
        session_id: UUID,
        update_callback: Optional[Callable[[Dict[str, Any]], Awaitable[None]]],
    ) -> List[ToolResult]:
        """
        Execute a list of tool calls with notifications and session updates.

        Args:
            tool_calls: List of tool call data from LLM
            session: The chat session
            session_id: Session ID for callbacks
            update_callback: Callback for UI updates

        Returns:
            List of tool results
        """
        tool_results = []

        if not tool_calls:
            return tool_results

        # logger.info(f"Executing {len(tool_calls)} tool calls")

        for tool_call_data in tool_calls:
            tool_call = ToolCall(
                id=tool_call_data["id"],
                name=tool_call_data["name"],
                arguments=tool_call_data["arguments"],
            )
            logging.info(
                f"Executing tool call: {tool_call.name} with args {tool_call.arguments}"
            )

            # Send tool_start notification
            await notify_tool_start(tool_call, session_id, update_callback)

            # Execute the tool
            try:
                result = await self.tool_caller.execute_tool(tool_call)
                tool_results.append(result)

                # Send tool_complete notification
                await notify_tool_complete(
                    tool_call, result, session_id, update_callback
                )

            except Exception as tool_error:
                logger.error(f"Error executing tool {tool_call.name}: {tool_error}")

                # Create failed result
                failed_result = ToolResult(
                    tool_call_id=tool_call.id,
                    success=False,
                    content="",
                    error=str(tool_error),
                )
                tool_results.append(failed_result)

                # Send tool_error notification
                await notify_tool_error(
                    tool_call, str(tool_error), session_id, update_callback
                )

            # Add tool result to session history (for both success and failure)
            session.add_tool_message(
                tool_call.name, tool_results[-1].content, tool_call.id
            )

        return tool_results
