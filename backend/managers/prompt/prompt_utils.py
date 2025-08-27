"""Utilities for prompt handling and extraction logic."""

from typing import Any, Dict, Optional


def extract_special_system_prompt(
    selected_prompt_map: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """
    Best-effort extraction of a special system prompt from frontend-provided fields.

    Extracts a prompt from selected_prompt_map under common keys
    (accepts either a string or a non-empty list[str], uses first string).

    Returns the extracted prompt text or None if nothing usable was found.
    """
    # Try selected_prompt_map
    spm = selected_prompt_map
    if isinstance(spm, dict):
        for key in ("system", "system_prompt", "prompt", "custom"):
            val = spm.get(key)
            if isinstance(val, str) and val.strip():
                return val
            if isinstance(val, list) and val:
                # Use first stringy item
                first = val[0]
                if isinstance(first, str) and first.strip():
                    return first

    return None
