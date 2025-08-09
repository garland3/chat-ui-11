"""
Unified LLM processing engine that handles all three modes cleanly.

This module provides a clean unified interface for processing messages in:
- Plain LLM mode (with/without RAG)
- LLM with tools mode (with/without RAG)  
- Agent mode (delegated to AgentExecutor)
"""

import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from llm_caller import LLMCaller
from tool_executor import ToolExecutor, ExecutionContext
from agent_executor import AgentExecutor, AgentContext
from utils import validate_selected_tools

logger = logging.getLogger(__name__)


@dataclass
class ProcessingResult:
    """Result from message processing."""
    response: str
    model_used: str
    processing_mode: str
    steps_taken: int = 1
    error: Optional[str] = None
    
    @classmethod
    def plain_llm(cls, response: str, model: str) -> 'ProcessingResult':
        return cls(response, model, "plain_llm")
    
    @classmethod  
    def llm_with_tools(cls, response: str, model: str) -> 'ProcessingResult':
        return cls(response, model, "llm_with_tools")
    
    @classmethod
    def agent_mode(cls, response: str, model: str, steps: int) -> 'ProcessingResult':
        return cls(response, model, "agent_mode", steps)
    
    @classmethod
    def error(cls, error_msg: str, model: str = "") -> 'ProcessingResult':
        return cls(f"Error: {error_msg}", model, "error", error=error_msg)


@dataclass
class ProcessingContext:
    """Context for message processing."""
    user_email: str
    model_name: str
    content: str
    messages: List[Dict]
    selected_tools: List[str]
    selected_data_sources: List[str]
    only_rag: bool
    tool_choice_required: bool
    session: Optional[Any] = None
    agent_mode: bool = False
    
    def has_tools(self) -> bool:
        return bool(self.selected_tools)
    
    def has_rag(self) -> bool:
        return bool(self.selected_data_sources)
    
    def is_rag_only(self) -> bool:
        return self.only_rag and self.has_rag()
    
    def is_plain_llm(self) -> bool:
        return not self.has_tools() and not self.has_rag()
    
    def is_llm_with_rag_only(self) -> bool:
        return not self.has_tools() and self.has_rag() and not self.is_rag_only()
    
    def is_llm_with_tools_only(self) -> bool:
        return self.has_tools() and not self.has_rag()
    
    def is_llm_with_rag_and_tools(self) -> bool:
        return self.has_tools() and self.has_rag() and not self.is_rag_only()


class LLMProcessor:
    """Unified processor that handles all three modes cleanly."""
    
    def __init__(self, session):
        self.session = session
        self.llm_caller = LLMCaller()
        self.tool_executor = ToolExecutor(session.mcp_manager)
        self.agent_executor = AgentExecutor(self.llm_caller, self.tool_executor)
    
    async def process_message(self, context: ProcessingContext) -> ProcessingResult:
        """Main entry point - routes to appropriate mode."""
        try:
            if context.agent_mode:
                return await self._execute_agent_mode(context)
            elif context.is_rag_only():
                return await self._execute_rag_only_mode(context)
            elif context.is_plain_llm():
                return await self._execute_plain_mode(context)
            elif context.is_llm_with_rag_only():
                return await self._execute_llm_with_rag_mode(context)
            elif context.is_llm_with_tools_only():
                return await self._execute_llm_with_tools_mode(context)
            elif context.is_llm_with_rag_and_tools():
                return await self._execute_llm_with_rag_and_tools_mode(context)
            else:
                # Fallback to plain LLM
                logger.warning(f"Unhandled processing mode for user {context.user_email}, falling back to plain LLM")
                return await self._execute_plain_mode(context)
                
        except Exception as exc:
            logger.error(f"Error in message processing for {context.user_email}: {exc}", exc_info=True)
            return ProcessingResult.error(str(exc), context.model_name)
    
    async def _execute_agent_mode(self, context: ProcessingContext) -> ProcessingResult:
        """Execute agent mode with recursive logic."""
        logger.info(f"Starting agent mode for user {context.user_email}")
        
        # Validate tools for agent mode
        validated_servers = await validate_selected_tools(
            context.selected_tools, 
            context.user_email, 
            self.session.mcp_manager
        )
        
        # Get tools data
        tools_data = self.session.mcp_manager.get_tools_for_servers(validated_servers)
        
        # Filter to selected tools if specified
        if context.selected_tools:
            tools_schema = []
            tool_mapping = {}
            selected_tools_set = set(context.selected_tools)
            
            for tool_schema in tools_data["tools"]:
                tool_function_name = tool_schema["function"]["name"]
                if tool_function_name in selected_tools_set:
                    tools_schema.append(tool_schema)
                    if tool_function_name in tools_data["mapping"]:
                        tool_mapping[tool_function_name] = tools_data["mapping"][tool_function_name]
        else:
            tools_schema = tools_data["tools"]
            tool_mapping = tools_data["mapping"]
        
        # Create agent context
        from config import config_manager
        app_settings = config_manager.app_settings
        
        agent_context = AgentContext(
            user_email=context.user_email,
            model_name=context.model_name,
            max_steps=app_settings.agent_max_steps,
            tools_schema=tools_schema,
            tool_mapping=tool_mapping,
            session=context.session,
            messages=context.messages.copy()
        )
        
        # Execute using loop-based approach
        agent_result = await self.agent_executor.execute_agent_loop(
            context.content,
            agent_context
        )
        
        return ProcessingResult.agent_mode(
            agent_result.final_response,
            context.model_name,
            agent_result.steps_taken
        )
    
    async def _execute_rag_only_mode(self, context: ProcessingContext) -> ProcessingResult:
        """Handle RAG-only queries by querying the first selected data source."""
        logger.info(f"Using RAG-only mode for user {context.user_email} with data sources: {context.selected_data_sources}")
        
        response = await self.llm_caller.call_with_rag(
            context.model_name,
            context.messages,
            context.selected_data_sources,
            context.user_email
        )
        
        return ProcessingResult.plain_llm(response, context.model_name)
    
    async def _execute_plain_mode(self, context: ProcessingContext) -> ProcessingResult:
        """Execute plain LLM call without tools or RAG."""
        logger.info(f"Using plain LLM mode for user {context.user_email}")
        
        response = await self.llm_caller.call_plain(context.model_name, context.messages)
        return ProcessingResult.plain_llm(response, context.model_name)
    
    async def _execute_llm_with_rag_mode(self, context: ProcessingContext) -> ProcessingResult:
        """Execute LLM with RAG integration but no tools."""
        logger.info(f"Using LLM with RAG mode for user {context.user_email}")
        
        response = await self.llm_caller.call_with_rag(
            context.model_name,
            context.messages,
            context.selected_data_sources,
            context.user_email
        )
        
        return ProcessingResult.plain_llm(response, context.model_name)
    
    async def _execute_llm_with_tools_mode(self, context: ProcessingContext) -> ProcessingResult:
        """Execute LLM with tools but no RAG."""
        logger.info(f"Using LLM with tools mode for user {context.user_email}")
        
        # Validate tools
        validated_servers = await validate_selected_tools(
            context.selected_tools, 
            context.user_email, 
            self.session.mcp_manager
        )
        
        if not validated_servers:
            logger.warning(f"No validated servers for user {context.user_email}, falling back to plain LLM")
            return await self._execute_plain_mode(context)
        
        # Get tools data
        tools_data = self.session.mcp_manager.get_tools_for_servers(validated_servers)
        
        # Filter to selected tools if specified
        if context.selected_tools:
            tools_schema = []
            tool_mapping = {}
            selected_tools_set = set(context.selected_tools)
            
            for tool_schema in tools_data["tools"]:
                tool_function_name = tool_schema["function"]["name"]
                if tool_function_name in selected_tools_set:
                    tools_schema.append(tool_schema)
                    if tool_function_name in tools_data["mapping"]:
                        tool_mapping[tool_function_name] = tools_data["mapping"][tool_function_name]
        else:
            tools_schema = tools_data["tools"]
            tool_mapping = tools_data["mapping"]
        
        if not tools_schema:
            logger.warning(f"No tools available after filtering for user {context.user_email}, falling back to plain LLM")
            return await self._execute_plain_mode(context)
        
        # Determine tool choice
        is_exclusive = any(self.session.mcp_manager.is_server_exclusive(s) for s in validated_servers)
        tool_choice = "required" if (context.tool_choice_required or is_exclusive) else "auto"
        
        # Call LLM with tools
        llm_response = await self.llm_caller.call_with_tools(
            context.model_name,
            context.messages,
            tools_schema,
            tool_choice
        )
        
        # Process tool calls if any
        if llm_response.has_tool_calls():
            execution_context = ExecutionContext(
                user_email=context.user_email,
                session=context.session,
                agent_mode=False
            )
            
            tool_results = await self.tool_executor.execute_tool_calls(
                llm_response.tool_calls,
                tool_mapping,
                execution_context
            )
            
            # Make follow-up LLM call with tool results
            follow_up_messages = context.messages + [
                {"role": "assistant", "content": llm_response.content, "tool_calls": llm_response.tool_calls}
            ] + [
                {"tool_call_id": result.tool_call_id, "role": "tool", "content": result.content}
                for result in tool_results
            ]
            
            follow_up_response = await self.llm_caller.call_plain(context.model_name, follow_up_messages)
            return ProcessingResult.llm_with_tools(follow_up_response, context.model_name)
        
        return ProcessingResult.llm_with_tools(llm_response.content, context.model_name)
    
    async def _execute_llm_with_rag_and_tools_mode(self, context: ProcessingContext) -> ProcessingResult:
        """Execute LLM with both RAG and tools integration."""
        logger.info(f"Using LLM with RAG and tools mode for user {context.user_email}")
        
        # Validate tools
        validated_servers = await validate_selected_tools(
            context.selected_tools, 
            context.user_email, 
            self.session.mcp_manager
        )
        
        if not validated_servers:
            logger.warning(f"No validated servers for user {context.user_email}, falling back to RAG only")
            return await self._execute_llm_with_rag_mode(context)
        
        # Get tools data
        tools_data = self.session.mcp_manager.get_tools_for_servers(validated_servers)
        
        # Filter to selected tools if specified
        if context.selected_tools:
            tools_schema = []
            tool_mapping = {}
            selected_tools_set = set(context.selected_tools)
            
            for tool_schema in tools_data["tools"]:
                tool_function_name = tool_schema["function"]["name"]
                if tool_function_name in selected_tools_set:
                    tools_schema.append(tool_schema)
                    if tool_function_name in tools_data["mapping"]:
                        tool_mapping[tool_function_name] = tools_data["mapping"][tool_function_name]
        else:
            tools_schema = tools_data["tools"]
            tool_mapping = tools_data["mapping"]
        
        if not tools_schema:
            logger.warning(f"No tools available after filtering for user {context.user_email}, falling back to RAG only")
            return await self._execute_llm_with_rag_mode(context)
        
        # Determine tool choice
        is_exclusive = any(self.session.mcp_manager.is_server_exclusive(s) for s in validated_servers)
        tool_choice = "required" if (context.tool_choice_required or is_exclusive) else "auto"
        
        # Call LLM with RAG and tools
        llm_response = await self.llm_caller.call_with_rag_and_tools(
            context.model_name,
            context.messages,
            context.selected_data_sources,
            tools_schema,
            context.user_email,
            tool_choice
        )
        
        # Process tool calls if any
        if llm_response.has_tool_calls():
            execution_context = ExecutionContext(
                user_email=context.user_email,
                session=context.session,
                agent_mode=False
            )
            
            tool_results = await self.tool_executor.execute_tool_calls(
                llm_response.tool_calls,
                tool_mapping,
                execution_context
            )
            
            # Make follow-up LLM call with tool results (using RAG-enhanced messages)
            # Re-enhance messages with RAG for follow-up call
            rag_enhanced_messages = await self._enhance_messages_with_rag(
                context.messages, 
                context.selected_data_sources, 
                context.user_email
            )
            
            follow_up_messages = rag_enhanced_messages + [
                {"role": "assistant", "content": llm_response.content, "tool_calls": llm_response.tool_calls}
            ] + [
                {"tool_call_id": result.tool_call_id, "role": "tool", "content": result.content}
                for result in tool_results
            ]
            
            follow_up_response = await self.llm_caller.call_plain(context.model_name, follow_up_messages)
            return ProcessingResult.llm_with_tools(follow_up_response, context.model_name)
        
        return ProcessingResult.llm_with_tools(llm_response.content, context.model_name)
    
    async def _enhance_messages_with_rag(self, messages: List[Dict], data_sources: List[str], user_email: str) -> List[Dict]:
        """Enhance messages with RAG context."""
        if not data_sources:
            return messages
        
        try:
            import rag_client
            data_source = data_sources[0]
            
            rag_response = await rag_client.rag_client.query_rag(
                user_email,
                data_source,
                messages
            )
            
            enhanced_messages = messages.copy()
            rag_context_message = {
                "role": "system", 
                "content": f"Retrieved context from {data_source}:\n\n{rag_response.content}\n\nUse this context to inform your response."
            }
            enhanced_messages.insert(-1, rag_context_message)
            
            return enhanced_messages
            
        except Exception as exc:
            logger.error(f"Error enhancing messages with RAG: {exc}")
            return messages