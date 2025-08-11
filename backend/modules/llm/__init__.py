"""LLM module for the chat backend.

This module provides:
- LLM calling interface for various interaction modes
- Response models and data structures
- CLI tools for testing LLM interactions
"""

from .caller import LLMCaller
from .models import LLMResponse

# Create default instance
llm_caller = LLMCaller()

__all__ = [
    "LLMCaller",
    "LLMResponse",
    "llm_caller",
]