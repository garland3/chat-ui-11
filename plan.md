# Refactoring Plan: Clean Agent Mode with Recursive Function Calling

## Current Architecture Understanding

```
WebSocket → ChatSession → MessageProcessor → call_llm_with_tools
                    ↓           ↓                    ↓
                File Mgmt   RAG Client        MCPToolManager
```

## Current Issues Identified

1. **`call_llm_with_tools` (utils.py:362-714)**: 353-line function handling multiple concerns
2. **`handle_chat_message` (message_processor.py:167-358)**: 191-line function with complex branching
3. **`handle_agent_mode_message` (message_processor.py:40-115)**: Loop-based with "continue reasoning" prompting
4. **Mixed concerns**: UI updates, tool execution, file handling, and LLM calling all in one place

## Refined Refactoring Strategy

### 1. Core Processing Modes Support

Create a unified `LLMProcessor` that handles all three modes cleanly:

```python
# New unified processor
class LLMProcessor:
    def __init__(self, session: ChatSession):
        self.session = session
        self.llm_caller = LLMCaller()
        self.tool_executor = ToolExecutor(session.mcp_manager)
        self.rag_integrator = RAGIntegrator()
    
    async def process_message(self, message: Dict) -> ProcessingResult:
        """Main entry point - routes to appropriate mode"""
        if message.get("agent_mode"):
            return await self._execute_agent_mode(message)
        elif self.session.selected_tools:
            return await self._execute_tool_mode(message) 
        else:
            return await self._execute_plain_mode(message)
```

### 2. Clean Agent Mode with Pure Recursion

```python
class AgentExecutor:
    async def execute_recursively(
        self, 
        message_content: str,
        context: AgentContext,
        depth: int = 0
    ) -> AgentResult:
        # Base cases
        if depth >= context.max_steps:
            return AgentResult.max_steps()
        
        # Execute one step  
        step_result = await self._execute_single_step(message_content, context)
        
        # Check completion
        if step_result.used_completion_tool():
            return AgentResult.completed(step_result, depth + 1)
        
        # Recurse with LLM's response as next input
        return await self.execute_recursively(
            step_result.content,  # No artificial prompting!
            context,
            depth + 1
        )
    
    async def _execute_single_step(self, content: str, context: AgentContext) -> StepResult:
        """Execute one complete LLM+tools step"""
        # Build messages for this step
        messages = context.build_messages_for_step(content)
        
        # Call LLM with tools (including completion tool)
        response = await context.llm_caller.call_with_tools(
            messages, 
            context.tools + [self._get_completion_tool()],
            agent_mode=True
        )
        
        return StepResult(response, context)
```

### 3. Modular Tool Execution

Extract from the massive `call_llm_with_tools`:

```python
class ToolExecutor:
    def __init__(self, mcp_manager: MCPToolManager):
        self.mcp_manager = mcp_manager
        self.file_manager = FileManager()
        
    async def execute_tool_calls(self, tool_calls: List[Dict], context: ExecutionContext) -> List[ToolResult]:
        """Execute all tool calls and return results"""
        results = []
        for tool_call in tool_calls:
            result = await self._execute_single_tool(tool_call, context)
            results.append(result)
        return results
    
    async def _execute_single_tool(self, tool_call: Dict, context: ExecutionContext) -> ToolResult:
        """Execute one tool call with proper error handling"""
        # Handle special tools (completion, canvas)
        if tool_call.function.name == "all_work_is_done":
            return await self._handle_completion_tool(tool_call, context)
        
        # Handle regular MCP tools
        return await self._handle_mcp_tool(tool_call, context)
```

### 4. Clean LLM Calling Interface

```python
class LLMCaller:
    async def call_plain(self, messages: List[Dict]) -> str:
        """Plain LLM call - no tools"""
        
    async def call_with_rag(self, messages: List[Dict], data_sources: List[str]) -> str:
        """LLM call with RAG integration"""
        
    async def call_with_tools(self, messages: List[Dict], tools: List[Dict], **opts) -> LLMResponse:
        """LLM call with tool support"""
        
    async def call_with_rag_and_tools(self, messages: List[Dict], data_sources: List[str], tools: List[Dict]) -> LLMResponse:
        """Full integration: RAG + Tools"""
```

### 5. Simplified MessageProcessor

```python
class MessageProcessor:
    def __init__(self, session: ChatSession):
        self.session = session
        self.processor = LLMProcessor(session)
        self.agent_executor = AgentExecutor(session)
    
    async def handle_chat_message(self, message: Dict, agent_mode: bool = False) -> Optional[str]:
        """Simplified routing - under 50 lines"""
        
        # Prepare context
        context = self._build_processing_context(message)
        
        # Route to appropriate processor
        if agent_mode:
            result = await self.agent_executor.execute_recursively(
                message["content"], 
                context.to_agent_context()
            )
            return result.final_response if agent_mode else await self._send_response(result)
        else:
            result = await self.processor.process_message(context)
            return await self._send_response(result)
    
    async def handle_agent_mode_message(self, message: Dict) -> None:
        """Just delegate to recursive executor - under 10 lines"""
        context = self._build_processing_context(message).to_agent_context()
        result = await self.agent_executor.execute_recursively(message["content"], context)
        await self._send_agent_final_response(result)
```

### 6. Support for All Three Modes

**Mode 1: Plain LLM (with/without RAG)**
```python
# No tools selected
result = await llm_caller.call_plain(messages)
# OR with RAG
result = await llm_caller.call_with_rag(messages, data_sources)
```

**Mode 2: LLM with Tools (with/without RAG)**  
```python
# Tools selected, normal mode
result = await llm_caller.call_with_tools(messages, tools)
# OR with RAG
result = await llm_caller.call_with_rag_and_tools(messages, data_sources, tools)
```

**Mode 3: Agent Mode**
```python
# agent_mode=True, recursive execution
result = await agent_executor.execute_recursively(content, agent_context)
```

### 7. New Architecture

```
AgentExecutor (new)
├── execute_recursively()      # Pure recursive logic
├── execute_single_step()      # One LLM call + tools
└── AgentContext/AgentResult   # Clean data structures

LLMCaller (extracted from utils.py)  
├── call_plain()               # Simple LLM calls
├── call_with_rag()            # RAG integration
├── call_with_tools()          # Tool-enabled calls  
├── call_with_rag_and_tools()  # Full integration
└── build_llm_payload()        # Request construction

ToolExecutor (extracted from utils.py)
├── execute_tool_calls()       # Execute all tool calls
├── execute_single_tool()      # Single tool execution
├── handle_special_tools()     # Canvas, completion tools
└── process_tool_results()     # Result processing

MessageProcessor (refactored)
├── handle_chat_message()      # Simplified routing (under 50 lines)
├── handle_agent_mode_message() # Delegates to AgentExecutor (under 10 lines)
└── build_processing_context() # Context preparation

ContentEnhancer (extracted)
├── build_content_with_files()       
├── apply_custom_prompts()
└── enhance_context()
```

### 8. Key Improvements

1. **Agent mode is truly recursive** - no "continue reasoning" hacks
2. **Each function under 50 lines** - focused responsibilities  
3. **Clear separation**: WebSocket ↔ Session ↔ Processor ↔ LLM/Tools
4. **All three modes supported** cleanly with shared components
5. **MCP integration preserved** - `MCPToolManager` usage unchanged
6. **Session management unchanged** - file handling, callbacks preserved
7. **Easier testing** - each component independently testable

### 9. Eliminate "Continue Reasoning" Hack

Instead of:
```python
# Current problematic approach
current_message = {
    "content": f"Continue reasoning from your previous response. Previous response: {response}",
    # ... 
}
```

Use:
```python
# Clean recursive approach  
return await execute_recursively(
    response.content,  # LLM's actual response becomes next input
    context,
    depth + 1
)
```

### 10. Migration Strategy

1. **Phase 1**: Extract `LLMCaller` and `ToolExecutor` from `utils.py`
2. **Phase 2**: Create `AgentExecutor` with recursive logic
3. **Phase 3**: Refactor `MessageProcessor` to use new components
4. **Phase 4**: Update `call_llm_with_tools` to delegate to new architecture
5. **Phase 5**: Clean up old code and add comprehensive tests

## Benefits of This Refactoring

1. **Agent mode becomes truly recursive** - no loops or artificial prompting
2. **Functions become focused** - each under 50 lines
3. **Easier testing** - each component can be tested independently  
4. **Better error handling** - localized error handling per component
5. **Clearer data flow** - explicit inputs/outputs for each function
6. **Maintainable** - changes to one concern don't affect others

This refactoring transforms the current 500+ line monolithic functions into a clean, modular architecture where agent mode uses natural recursion instead of artificial looping with "continue reasoning" prompts, while maintaining backward compatibility and properly supporting all three processing modes (plain LLM, LLM with tools, agent mode).