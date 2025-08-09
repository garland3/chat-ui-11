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
        # Start with base conversation messages but use agent-specific system prompt
        step_messages = self.messages.copy()
        
        # Replace system prompt with agent-specific prompt if this is the first step
        if step_messages and step_messages[0]["role"] == "system":
            agent_system_prompt = self._load_agent_system_prompt()
            if agent_system_prompt:
                step_messages[0] = {"role": "system", "content": agent_system_prompt}
        
        # Add the current input as user message
        user_message = {"role": "user", "content": content}
        step_messages.append(user_message)
        
        return step_messages
    
    def _load_agent_system_prompt(self) -> str:
        """Load agent-specific system prompt from file."""
        try:
            import os
            
            # Get the directory where this script is located
            current_dir = os.path.dirname(os.path.abspath(__file__))
            prompt_file_path = os.path.join(current_dir, 'prompts', 'agent_system_prompt.md')
            
            # Read the agent system prompt template
            with open(prompt_file_path, 'r', encoding='utf-8') as f:
                prompt_template = f.read()
            
            # Format the template with user email
            try:
                return prompt_template.format(user_email=self.user_email)
            except KeyError:
                # If formatting fails, return the template as-is
                return prompt_template
            
        except Exception as exc:
            logger.warning(f"Failed to load agent system prompt from file: {exc}")
            # Return None to use the default system prompt
            return None
    
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
        """Create the all_work_done tool schema for agent completion."""
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
                    "properties": {}
                }
            }
        }
    
    async def execute_agent_loop(
        self, 
        message_content: str,
        context: AgentContext,
        depth: int = 0
    ) -> AgentResult:
        """
        Enhanced loop-based agent execution with real-time updates and better error handling.
        
        Args:
            message_content: The content to process (user message or LLM response)
            context: Agent execution context
            depth: Starting depth (for compatibility, usually 0)
            
        Returns:
            AgentResult with final response and metadata
        """
        logger.info(f"Starting agent loop for user {context.user_email}")
        logger.info(f"Initial prompt: {message_content[:100]}...")
        logger.info(f"Available tools: {len(context.tools_schema)} tools")
        
        # Send initial update
        if context.session:
            await self._send_agent_update(context.session, {
                "type": "agent_start",
                "message": f"Starting agent execution with {len(context.tools_schema)} tools",
                "max_steps": context.max_steps,
                "user": context.user_email
            })
        
        current_content = message_content
        current_step = depth
        all_responses = []
        
        while current_step < context.max_steps:
            turn_number = current_step + 1
            logger.info(f"Agent step {turn_number}/{context.max_steps} starting for user {context.user_email}")
            
            # Send turn start update
            if context.session:
                await self._send_agent_update(context.session, {
                    "type": "agent_turn_start", 
                    "turn": turn_number,
                    "max_steps": context.max_steps,
                    "user": context.user_email
                })
            
            try:
                # Execute one complete step (LLM call + tool execution)
                step_result = await self._execute_single_step(current_content, context, current_step)
                
                # Track this step's results
                all_responses.append({
                    "turn": turn_number,
                    "type": "agent_step",
                    "content": current_content[:200],
                    "response": step_result.response[:200] if step_result.response else None,
                    "used_completion": step_result.used_completion_tool
                })
                
                # Check if step returned empty response
                if not step_result.response or not step_result.response.strip():
                    logger.warning(f"Agent step {turn_number} returned empty response")
                    if context.session:
                        await self._send_agent_update(context.session, {
                            "type": "agent_warning",
                            "message": f"Step {turn_number} returned empty response",
                            "turn": turn_number,
                            "user": context.user_email
                        })
                    return AgentResult.empty_response(turn_number)
                
                # Check if completion tool was used
                if step_result.used_completion_tool:
                    logger.info(f"Agent used completion tool after {turn_number} steps")
                    if context.session:
                        await self._send_agent_update(context.session, {
                            "type": "agent_completion",
                            "message": "Agent marked task as complete",
                            "turn": turn_number,
                            "final_response": step_result.response,
                            "total_steps": turn_number,
                            "user": context.user_email
                        })
                    
                    # Generate comprehensive final response
                    final_response = await self._generate_final_summary(
                        message_content, step_result.response, all_responses, context
                    )
                    
                    return AgentResult.completed(final_response, turn_number)
                
                # Send step completion update
                if context.session:
                    await self._send_agent_update(context.session, {
                        "type": "agent_step_complete",
                        "turn": turn_number,
                        "response_preview": step_result.response[:100] + "..." if len(step_result.response) > 100 else step_result.response,
                        "user": context.user_email
                    })
                
                # Continue loop with step result as next input
                current_content = step_result.response
                current_step += 1
                
            except Exception as exc:
                logger.error(f"Error in agent step {turn_number}: {exc}", exc_info=True)
                
                # Send error update to UI
                if context.session:
                    await self._send_agent_update(context.session, {
                        "type": "agent_error",
                        "message": f"Error in step {turn_number}: {str(exc)}",
                        "turn": turn_number,
                        "error": str(exc),
                        "user": context.user_email
                    })
                
                return AgentResult.error(str(exc), turn_number)
        
        # Max steps reached
        logger.info(f"Agent reached max steps ({context.max_steps})")
        if context.session:
            await self._send_agent_update(context.session, {
                "type": "agent_max_steps",
                "message": f"Reached maximum {context.max_steps} steps",
                "max_steps": context.max_steps,
                "final_content": current_content,
                "user": context.user_email
            })
        
        # Generate summary even if max steps reached
        final_response = await self._generate_final_summary(
            message_content, current_content, all_responses, context
        )
        
        return AgentResult.max_steps(final_response, current_step)
    
    async def _execute_single_step(self, content: str, context: AgentContext, depth: int) -> 'StepResult':
        """Execute one complete LLM+tools step."""
        
        # Build messages for this step
        messages = context.build_messages_for_step(content)
        
        # Add completion tool to available tools
        tools_with_completion = context.tools_schema + [self._create_completion_tool_schema()]
        
        # Add completion tool to mapping
        tool_mapping_with_completion = context.tool_mapping.copy()
        tool_mapping_with_completion["all_work_done"] = {
            "server": "agent_completion",
            "tool_name": "all_work_done"
        }
        
        logger.info(f"Agent step {depth + 1}: Calling LLM with {len(messages)} messages and {len(tools_with_completion)} tools")
        
        # Send LLM call update
        if context.session:
            await self._send_agent_update(context.session, {
                "type": "agent_llm_call",
                "step": depth + 1,
                "message_count": len(messages),
                "tool_count": len(tools_with_completion),
                "user": context.user_email
            })
        
        # Call LLM with tools (including completion tool)
        llm_response = await self.llm_caller.call_with_tools(
            context.model_name,
            messages,
            tools_with_completion,
            tool_choice="required"  # Require LLM to use tools
        )
        
        # Process tool calls if any
        used_completion_tool = False
        final_response = llm_response.content or ""
        
        if llm_response.has_tool_calls():
            logger.info(f"Agent step {depth + 1}: Processing {len(llm_response.tool_calls)} tool calls")
            
            # Send tool calls start update
            if context.session:
                await self._send_agent_update(context.session, {
                    "type": "agent_tool_calls_start",
                    "step": depth + 1,
                    "tool_count": len(llm_response.tool_calls),
                    "user": context.user_email
                })
            
            # Log detailed information about each tool call
            for i, tool_call in enumerate(llm_response.tool_calls):
                function_name = tool_call["function"]["name"]
                try:
                    import json
                    function_args = json.loads(tool_call["function"]["arguments"])
                    logger.info(f"Agent step {depth + 1}: Tool call {i + 1}/{len(llm_response.tool_calls)}: {function_name}")
                    logger.info(f"Agent step {depth + 1}: Tool arguments: {function_args}")
                    
                    # Send individual tool call update
                    if context.session:
                        await self._send_agent_update(context.session, {
                            "type": "agent_tool_call",
                            "step": depth + 1,
                            "tool_index": i + 1,
                            "total_tools": len(llm_response.tool_calls),
                            "function_name": function_name,
                            "arguments": function_args,
                            "user": context.user_email
                        })
                        
                except Exception as e:
                    logger.warning(f"Agent step {depth + 1}: Could not parse tool arguments for {function_name}: {e}")
                    if context.session:
                        await self._send_agent_update(context.session, {
                            "type": "agent_tool_call_error",
                            "step": depth + 1,
                            "function_name": function_name,
                            "error": f"Could not parse arguments: {e}",
                            "user": context.user_email
                        })
            
            # Execute all tool calls
            execution_context = context.to_execution_context()
            tool_results = await self.tool_executor.execute_tool_calls(
                llm_response.tool_calls,
                tool_mapping_with_completion,
                execution_context
            )
            
            # Send tool results update
            if context.session:
                await self._send_agent_update(context.session, {
                    "type": "agent_tool_results",
                    "step": depth + 1,
                    "results_count": len(tool_results),
                    "results_preview": [result.content[:100] + "..." if len(result.content) > 100 
                                      else result.content for result in tool_results[:3]],
                    "user": context.user_email
                })
            
            # Check if completion tool was used - look at original tool calls for function name
            for i, (tool_call, tool_result) in enumerate(zip(llm_response.tool_calls, tool_results)):
                if tool_call["function"]["name"] == "all_work_done":
                    used_completion_tool = True
                    # For completion tool, make follow-up call to get final response
                    follow_up_messages = messages + [
                        {"role": "assistant", "content": llm_response.content, "tool_calls": llm_response.tool_calls}
                    ] + [
                        {"tool_call_id": result.tool_call_id, "role": "tool", "content": result.content}
                        for result in tool_results
                    ]
                    
                    logger.info(f"Agent step {depth + 1}: Completion tool used, making follow-up call for final response")
                    
                    # Send completion detected update
                    if context.session:
                        await self._send_agent_update(context.session, {
                            "type": "agent_completion_detected",
                            "step": depth + 1,
                            "message": "Agent marked task as complete, generating final response",
                            "user": context.user_email
                        })
                    
                    # Make follow-up call to get final response (no tools required)
                    follow_up_response = await self.llm_caller.call_with_tools(
                        context.model_name,
                        follow_up_messages,
                        [],  # No tools for final response
                        tool_choice="none"
                    )
                    
                    final_response = follow_up_response.content or tool_result.content
                    break
            
            # If no completion tool was used, use the tool results as the response for next iteration
            if not used_completion_tool:
                # Combine tool results into response for next step
                tool_summaries = []
                for tool_result in tool_results:
                    tool_summaries.append(f"Tool result: {tool_result.content}")
                final_response = "\n".join(tool_summaries)
        
        logger.info(f"Agent step {depth + 1}: Completed, used_completion_tool={used_completion_tool}")
        
        return StepResult(
            response=final_response,
            used_completion_tool=used_completion_tool,
            step_number=depth + 1
        )
    
    async def _send_agent_step_update(self, session, current_step: int, max_steps: int, status: str) -> None:
        """Send agent step progress update to frontend (legacy method)."""
        payload = {
            "type": "agent_step_update",
            "current_step": current_step,
            "max_steps": max_steps,
            "status": status,
            "user": session.user_email
        }
        await session.send_json(payload)
    
    async def _send_agent_update(self, session, update_data: dict) -> None:
        """Send enhanced agent update to frontend."""
        try:
            # Use the existing send_update_to_ui method to ensure proper UI updates
            await session.send_update_to_ui("agent_update", update_data)
            logger.debug(f"Sent agent update: {update_data['type']}")
        except Exception as exc:
            logger.error(f"Failed to send agent update: {exc}")
    
    async def _generate_final_summary(self, original_prompt: str, final_response: str, all_responses: list, context: AgentContext) -> str:
        """Generate a comprehensive final summary of the agent's work."""
        try:
            # Create summary of agent actions
            summary_parts = []
            tool_count = 0
            
            for response in all_responses:
                if response.get("type") == "agent_step":
                    summary_parts.append(f"Step {response['turn']}: {response.get('content', '')[:100]}...")
                    tool_count += 1
            
            summary = "\n".join(summary_parts) if summary_parts else "No detailed steps recorded."
            
            # Load the agent summary prompt from file
            summary_prompt = self._load_agent_summary_prompt(
                original_prompt=original_prompt,
                step_count=len(all_responses),
                summary=summary,
                final_response=final_response
            )

            # Use the LLM to generate a comprehensive summary
            summary_messages = [{"role": "user", "content": summary_prompt}]
            
            try:
                summary_response = await self.llm_caller.call_with_tools(
                    context.model_name,
                    summary_messages,
                    [],  # No tools for summary generation
                    tool_choice="none"
                )
                
                if summary_response and summary_response.content:
                    return summary_response.content.strip()
                    
            except Exception as summary_exc:
                logger.warning(f"Failed to generate LLM summary: {summary_exc}")
            
            # Fallback to simple summary if LLM call fails
            return f"""Task Summary:

Original Request: {original_prompt}

Agent completed {len(all_responses)} steps and finished with: {final_response}

The agent successfully processed your request using available tools and provided the above response."""
            
        except Exception as exc:
            logger.error(f"Error generating final summary: {exc}")
            return final_response  # Return the raw final response as fallback
    
    def _load_agent_summary_prompt(self, original_prompt: str, step_count: int, summary: str, final_response: str) -> str:
        """Load and format the agent summary prompt from file."""
        try:
            import os
            
            # Get the directory where this script is located
            current_dir = os.path.dirname(os.path.abspath(__file__))
            prompt_file_path = os.path.join(current_dir, 'prompts', 'agent_summary_prompt.md')
            
            # Read the prompt template
            with open(prompt_file_path, 'r', encoding='utf-8') as f:
                prompt_template = f.read()
            
            # Format the template with the provided values
            formatted_prompt = prompt_template.format(
                original_prompt=original_prompt,
                step_count=step_count,
                summary=summary,
                final_response=final_response
            )
            
            return formatted_prompt
            
        except Exception as exc:
            logger.warning(f"Failed to load agent summary prompt from file: {exc}")
            # Fallback to hardcoded prompt
            return f"""The user requested: "{original_prompt}"

The agent completed {step_count} steps and performed the following actions:
{summary}

The agent's final response was: "{final_response}"

Please provide a comprehensive summary for the user that includes:
1. What was requested and what was accomplished
2. Key results and findings from the agent's work
3. The overall outcome and whether the task was completed successfully
4. Any important details or next steps

Make this response informative and well-organized."""


@dataclass
class StepResult:
    """Result from a single agent step."""
    response: str
    used_completion_tool: bool
    step_number: int