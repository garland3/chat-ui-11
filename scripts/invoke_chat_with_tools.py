#!/usr/bin/env python3
"""
Invoke ChatService.handle_chat_message directly for debugging a specific tool flow.

Default prompt: "get the csv file then use teh rport tool"
Default tools: [
  'order_database_get_signal_data_csv',
  'csv_reporter_generate_csv_report'
]

This script initializes MCP servers, discovers tools/prompts, and then
invokes the chat service with a simple console update callback so you can
step through the flow in a debugger.
"""

import asyncio
import os

# Silence LiteLLM DEBUG noise for this script run before any backend imports
os.environ.setdefault("DEBUG_MODE", "false")
os.environ.setdefault("LITELLM_LOG", "ERROR")
import json
import logging
import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

# Ensure the backend package is on the import path
REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_PATH = REPO_ROOT / "backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

# Import after adjusting sys.path
from infrastructure.app_factory import app_factory  # type: ignore  # noqa: E402

logger = logging.getLogger("invoke_chat_with_tools")


def _quiet_litellm_logs():
    """Aggressively silence LiteLLM library logs for this script.

    We both set logger levels, stop propagation, clear existing handlers,
    and attach a NullHandler. We also add a root filter to drop any records
    from LiteLLM/litellm if they sneak through.
    """
    class _DropLiteLLMFilter(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:  # type: ignore[override]
            name = record.name or ""
            return not (name.startswith("LiteLLM") or name.startswith("litellm"))

    root = logging.getLogger()
    # Add drop filter only once
    already_added = any(isinstance(f, _DropLiteLLMFilter) for f in getattr(root, "filters", []))
    if not already_added:
        root.addFilter(_DropLiteLLMFilter())

    for name in ("LiteLLM", "litellm"):
        lg = logging.getLogger(name)
        lg.setLevel(logging.ERROR)
        lg.propagate = False
        # Replace any existing handlers with a NullHandler to absorb output
        for h in list(lg.handlers):
            lg.removeHandler(h)
        lg.addHandler(logging.NullHandler())


async def console_update_callback(message: Dict[str, Any]) -> None:
    """Minimal update callback that prints message summaries to stdout."""
    try:
        mtype = message.get("type")
        summary = {
            "type": mtype,
            "keys": list(message.keys()),
        }
        # Truncate potentially large content fields for readability
        if "content" in message and isinstance(message["content"], str):
            c = message["content"]
            summary["content_preview"] = (c[:120] + "...") if len(c) > 120 else c
        if "data" in message and isinstance(message["data"], dict):
            data_keys = list(message["data"].keys())
            summary["data_keys"] = data_keys
        print("[UI_UPDATE]", json.dumps(summary))
    except Exception as e:
        logger.debug("Error in console_update_callback: %s", e)


async def run(
    prompt: str,
    tools: List[str],
    user: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.7,
) -> None:
    """Run a single handle_chat_message invocation with the given settings."""
    # Initialize logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")
    # Force LiteLLM logger to quiet level even if library toggles it
    _quiet_litellm_logs()

    # Initialize MCP tool manager similar to FastAPI lifespan
    mcp_manager = app_factory.get_mcp_manager()
    logger.info("Initializing MCP clients...")
    await mcp_manager.initialize_clients()
    logger.info("Discovering tools...")
    await mcp_manager.discover_tools()
    logger.info("Discovering prompts...")
    await mcp_manager.discover_prompts()
    
    # Ensure env still reflects quiet setting during runtime
    os.environ.setdefault("LITELLM_LOG", "ERROR")

    try:
        # Resolve a model from config if not provided
        cfg = app_factory.get_config_manager()
        chosen_model = model
        try:
            # Prefer an explicit default if defined
            if not chosen_model and hasattr(cfg.llm_config, "default_model"):
                chosen_model = getattr(cfg.llm_config, "default_model")
            # Fallback to the first configured model
            if not chosen_model and getattr(cfg.llm_config, "models", None):
                chosen_model = cfg.llm_config.models[0]
        except Exception:
            pass
        chosen_model = chosen_model or "openai/gpt-4o-mini"

        # Create chat service
        chat_service = app_factory.create_chat_service(connection=None)

        # Build invocation args mirroring backend/main.py
        session_id = uuid4()
        selected_tools = tools
        selected_prompts = None
        selected_data_sources = None
        only_rag = False
        tool_choice_required = False
        user_email = user or os.environ.get("CHAT_DEBUG_USER", "test@test.com")
        agent_mode = True
        agent_max_steps = 10
        files = None

        logger.info("Invoking chat_service.handle_chat_message...")
        result = await chat_service.handle_chat_message(
            session_id=session_id,
            content=prompt,
            model=chosen_model,
            selected_tools=selected_tools,
            selected_prompts=selected_prompts,
            selected_data_sources=selected_data_sources,
            only_rag=only_rag,
            tool_choice_required=tool_choice_required,
            user_email=user_email,
            agent_mode=agent_mode,
            agent_max_steps=agent_max_steps,
            temperature=temperature,
            update_callback=console_update_callback,
            files=files,
        )

        print("\n=== Final Response ===")
        try:
            print(json.dumps(result, indent=2))
        except Exception:
            print(result)
    finally:
        # Cleanup MCP clients
        try:
            await mcp_manager.cleanup()
        except Exception:
            pass


def parse_args():
    parser = ArgumentParser(description="Invoke ChatService.handle_chat_message with selected tools for debugging.")
    parser.add_argument(
        "--prompt",
        type=str,
        default="get the csv file then use teh rport tool",
        help="User prompt to send to the chat service.",
    )
    parser.add_argument(
        "--tools",
        type=str,
        default="order_database_get_signal_data_csv,csv_reporter_generate_csv_report",
        help="Comma-separated list of selected tools to run.",
    )
    parser.add_argument("--user", type=str, default="test@test.com", help="User email.")
    parser.add_argument("--model", type=str, default="openrouter-gpt-oss", help="LLM model id to use.")
    parser.add_argument("--temperature", type=float, default=0.7, help="Sampling temperature.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    tools_list = [t.strip() for t in args.tools.split(",") if t.strip()]
    asyncio.run(
        run(
            prompt=args.prompt,
            tools=tools_list,
            user=args.user,
            model=args.model,
            temperature=args.temperature,
        )
    )
