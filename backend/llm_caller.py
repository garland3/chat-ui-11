"""
DEPRECATED: Legacy LLM caller module for backward compatibility.

This module is deprecated. Use modules.llm instead:
    from modules.llm import llm_caller, LLMCaller, LLMResponse

This file exists only to maintain backward compatibility during the migration.
"""

import warnings
from modules.llm import *

warnings.warn(
    "llm_caller.py is deprecated. Use 'from modules.llm import ...' instead.",
    DeprecationWarning,
    stacklevel=2
)