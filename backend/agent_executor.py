"""
Agent execution engine with pure recursive logic.

This module provides a clean recursive implementation of agent mode that eliminates
the need for "continue reasoning" prompts and loop-based execution. Instead, it uses
natural recursion where the LLM's response becomes the input for the next step.
"""

import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

from llm_caller import LLMCaller, LLMResponse
from tool_executor import ToolExecutor, ExecutionContext

logger = logging.getLogger(__name__)


class AgentCompletionReason(Enum):
    """Reasons why agent execution completed."""
    COMPLETION_TOOL_USED = "completion_tool_used"
    MAX_STEPS_REACHED = "max_steps_reached"
    ERROR_OCCURRED = "error_occurred"
    EMPTY_RESPONSE = "empty_response"


@dataclass
class AgentResult:
    """Result from agent execution."""
    final_response: str
    steps_taken: int
    completion_reason: AgentCompletionReason
    error: Optional[str] = None
    
    @classmethod
    def completed(cls, response: str, steps: int) -> 'AgentResult':
        return cls(response, steps, AgentCompletionReason.COMPLETION_TOOL_USED)
    
    @classmethod
    def max_steps(cls, response: str, steps: int) -> 'AgentResult':
        return cls(
            f"{response}\n\n[Agent completed after reaching maximum {steps} steps]", 
            steps, 
            AgentCompletionReason.MAX_STEPS_REACHED
        )
    
    @classmethod
    def error(cls, error_msg: str, steps: int) -> 'AgentResult':
        return cls(
            f"Agent encountered an error: {error_msg}", 
            steps, 
            AgentCompletionReason.ERROR_OCCURRED, 
            error_msg
        )
    
    @classmethod
    def empty_response(cls, steps: int) -> 'AgentResult':
        return cls(
            "Agent returned empty response", 
            steps, 
            AgentCompletionReason.EMPTY_RESPONSE
        )


@dataclass
class AgentContext:
    """Context for agent execution."""
    user_email: str
    model_name: str
    max_steps: int
    tools_schema: List[Dict]
    tool_mapping: Dict[str, Dict]
    session: Optional[Any] = None
    messages: Optional[List[Dict]] = None
    
    def __post_init__(self):
        if self.messages is None:
            self.messages = []
    
    def build_messages_for_step(self, content: str) -> List[Dict]:
        """Build messages for a single agent step."""
        # Start with base conversation messages
        step_messages = self.messages.copy()
        
        # Add the current input as user message
        user_message = {"role": "user", "content": content}
        step_messages.append(user_message)
        
        return step_messages
    
    def to_execution_context(self) -> ExecutionContext:
        """Convert to ToolExecutor execution context."""
        return ExecutionContext(
            user_email=self.user_email,
            session=self.session,
            agent_mode=True
        )


class AgentExecutor:
    """Handles recursive agent execution without loops or artificial prompting."""
    
    def __init__(self, llm_caller: LLMCaller, tool_executor: ToolExecutor):
        self.llm_caller = llm_caller
        self.tool_executor = tool_executor
    
    def _create_completion_tool_schema(self) -> Dict:
        """Create the all_work_is_done tool schema for agent completion."""
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
    
    async def execute_recursively(
        self, 
        message_content: str,
        context: AgentContext,
        depth: int = 0
    ) -> AgentResult:
        """
        Pure recursive agent execution - no loops, no prompting hacks.
        
        Args:
            message_content: The content to process (user message or LLM response)
            context: Agent execution context
            depth: Current recursion depth
            
        Returns:
            AgentResult with final response and metadata
        """
        logger.info(f"Agent step {depth + 1}/{context.max_steps} starting for user {context.user_email}")
        
        # Base case: max depth reached
        if depth >= context.max_steps:
            logger.info(f"Agent reached max steps ({context.max_steps})")
            return AgentResult.max_steps(message_content, depth)
        
        # Send step update to frontend if session available
        if context.session:
            await self._send_agent_step_update(context.session, depth + 1, context.max_steps, "processing")
        
        try:
            # Execute one complete step (LLM call + tool execution)
            step_result = await self._execute_single_step(message_content, context, depth)
            
            # # Check if step returned empty response
            # if not step_result.response or not step_result.response.strip():
            #     logger.warning(f"Agent step {depth + 1} returned empty response")
            #     return AgentResult.empty_response(depth + 1)
            
            # Base case: completion tool was used
            if step_result.used_completion_tool:
                logger.info(f"Agent used completion tool after {depth + 1} steps")
                return AgentResult.completed(step_result.response, depth + 1)
            
            # Recursive case: continue with LLM response as next input
            # This is the key improvement - no artificial "continue reasoning" prompts!
            return await self.execute_recursively(
                step_result.response,  # LLM's actual response becomes next input
                context,
                depth + 1
            )
            
        except Exception as exc:
            logger.error(f"Error in agent step {depth + 1}: {exc}", exc_info=True)
            return AgentResult.error(str(exc), depth + 1)
    
    async def _execute_single_step(self, content: str, context: AgentContext, depth: int) -> 'StepResult':
        """Execute one complete LLM+tools step."""
        
        # Build messages for this step
        messages = context.build_messages_for_step(content)
        
        # Add completion tool to available tools
        tools_with_completion = context.tools_schema + [self._create_completion_tool_schema()]
        
        # Add completion tool to mapping
        tool_mapping_with_completion = context.tool_mapping.copy()
        tool_mapping_with_completion["all_work_is_done"] = {
            "server": "agent_completion",
            "tool_name": "all_work_is_done"
        }
        
        logger.info(f"Agent step {depth + 1}: Calling LLM with {len(messages)} messages and {len(tools_with_completion)} tools")
        
        # Call LLM with tools (including completion tool)
        llm_response = await self.llm_caller.call_with_tools(
            context.model_name,
            messages,
            tools_with_completion,
            tool_choice="auto"  # Let LLM decide whether to use tools
        )
        
        # Process tool calls if any
        used_completion_tool = False
        final_response = llm_response.content or ""
        
        if llm_response.has_tool_calls():
            logger.info(f"Agent step {depth + 1}: Processing {len(llm_response.tool_calls)} tool calls")
            
            # Execute all tool calls
            execution_context = context.to_execution_context()
            tool_results = await self.tool_executor.execute_tool_calls(
                llm_response.tool_calls,
                tool_mapping_with_completion,
                execution_context
            )
            
            # Check if completion tool was used
            for tool_result in tool_results:
                if "Agent completion acknowledged:" in tool_result.content:
                    used_completion_tool = True
                    final_response = tool_result.content
                    break
            
            # If no completion tool, prepare follow-up LLM call with tool results
            if not used_completion_tool:
                # Build follow-up messages with tool results
                follow_up_messages = messages + [
                    {"role": "assistant", "content": llm_response.content, "tool_calls": llm_response.tool_calls}
                ] + [
                    {"tool_call_id": result.tool_call_id, "role": "tool", "content": result.content}
                    for result in tool_results
                ]
                
                logger.info(f"Agent step {depth + 1}: Follow-up LLM call with {len(follow_up_messages)} messages")
                
                # Make follow-up call to get LLM's response to tool results
                follow_up_response = await self.llm_caller.call_with_tools(
                    context.model_name,
                    follow_up_messages,
                    tools_with_completion,
                    tool_choice="auto"
                )
                
                final_response = follow_up_response.content or ""
                
                # Check if completion tool was used in follow-up
                if follow_up_response.has_tool_calls():
                    follow_up_tool_results = await self.tool_executor.execute_tool_calls(
                        follow_up_response.tool_calls,
                        tool_mapping_with_completion,
                        execution_context
                    )
                    
                    for tool_result in follow_up_tool_results:
                        if "Agent completion acknowledged:" in tool_result.content:
                            used_completion_tool = True
                            final_response = tool_result.content
                            break
        
        logger.info(f"Agent step {depth + 1}: Completed, used_completion_tool={used_completion_tool}")
        
        return StepResult(
            response=final_response,
            used_completion_tool=used_completion_tool,
            step_number=depth + 1
        )
    
    async def _send_agent_step_update(self, session, current_step: int, max_steps: int, status: str) -> None:
        """Send agent step progress update to frontend."""
        payload = {
            "type": "agent_step_update",
            "current_step": current_step,
            "max_steps": max_steps,
            "status": status,
            "user": session.user_email
        }
        await session.send_json(payload)


@dataclass
class StepResult:
    """Result from a single agent step."""
    response: str
    used_completion_tool: bool
    step_number: int