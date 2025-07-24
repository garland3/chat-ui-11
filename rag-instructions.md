# RAG (Retrieval Augmented Generation) Implementation Instructions

## Overview
Integrate Retrieval Augmented Generation as a core feature of the application. The RAG system should provide contextual information retrieval to enhance chat responses.

## Frontend Requirements

### Left Panel - Data Sources
- Create a collapsible panel on the left side of the main interface
- Display available data sources that the user can access
- Allow users to select one or more data sources for their queries
- Panel should be toggleable (expand/collapse functionality)

### RAG Panel Controls
At the top of the RAG panel, include:
- **"Only RAG" checkbox**: Checked by default
  - When checked: Skip tool calling and other processing steps in the `async def run(self) -> None:` function
  - When checked: Return RAG endpoint response directly to user without additional processing
  - When unchecked: Allow normal tool calling and processing pipeline, after retrieving the information from the RAG system. 

## Backend Integration

### Data Source Discovery
- Use `rag-mock/main-rag-mock.py` to mock the actual RAG endpoint
- In production, this will be replaced with real API calls
- The discovery endpoint must check the user's username
- Only return data sources that the user is authorized to access

### Response Handling
- RAG system should return a complete response ready for user consumption
- No additional processing required when "Only RAG" mode is enabled
- When "Only RAG" is disabled, integrate RAG results into the normal processing pipeline

## Testing Implementation
- Use FastAPI TestClient for testing mode
- This approach skips actual HTTP calls during development/testing
- Ensures reliable testing without external dependencies

## Technical Notes
- The RAG endpoint mock provides data source discovery functionality
- User authorization is handled at the data source level
- Response format should be consistent whether using RAG-only or integrated mode