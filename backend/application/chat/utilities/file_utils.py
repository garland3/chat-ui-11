"""
File management utilities - pure functions for session file operations.

This module provides stateless utility functions for handling files within
chat sessions, including user uploads and tool-generated artifacts.
"""

import logging
from typing import Any, Dict, List, Optional, Callable, Awaitable

logger = logging.getLogger(__name__)

# Type hint for update callback
UpdateCallback = Callable[[Dict[str, Any]], Awaitable[None]]


async def handle_session_files(
    session_context: Dict[str, Any],
    user_email: Optional[str],
    files_map: Optional[Dict[str, str]],
    file_manager,
    update_callback: Optional[UpdateCallback] = None
) -> Dict[str, Any]:
    """
    Handle user file ingestion and return updated session context.
    
    Pure function that processes files and returns new context without mutations.
    """
    if not files_map or not file_manager or not user_email:
        return session_context

    # Work with a copy to avoid mutations
    updated_context = dict(session_context)
    session_files_ctx = updated_context.setdefault("files", {})
    
    try:
        uploaded_refs: Dict[str, Dict[str, Any]] = {}
        for filename, b64 in files_map.items():
            try:
                meta = await file_manager.upload_file(
                    user_email=user_email,
                    filename=filename,
                    content_base64=b64,
                    source_type="user",
                    tags={"source": "user"}
                )
                # Store minimal reference in session context
                session_files_ctx[filename] = {
                    "key": meta.get("key"),
                    "content_type": meta.get("content_type"),
                    "size": meta.get("size"),
                    "source": "user",
                    "last_modified": meta.get("last_modified"),
                }
                uploaded_refs[filename] = meta
            except Exception as e:
                logger.error(f"Failed uploading user file {filename}: {e}")

        # Emit files update if successful uploads
        if uploaded_refs and update_callback:
            organized = file_manager.organize_files_metadata(uploaded_refs)
            await update_callback({
                "type": "intermediate_update",
                "update_type": "files_update",
                "data": organized
            })

    except Exception as e:
        logger.error(f"Error ingesting user files: {e}", exc_info=True)

    return updated_context


async def process_tool_artifacts(
    session_context: Dict[str, Any],
    tool_result,
    file_manager,
    update_callback: Optional[UpdateCallback] = None
) -> Dict[str, Any]:
    """
    Process artifacts produced by a tool and return updated session context.
    
    Pure function that handles tool files without side effects on input context.
    """
    if not tool_result.returned_file_names or not file_manager:
        return session_context

    user_email = session_context.get("user_email")
    if not user_email:
        return session_context

    # Work with a copy to avoid mutations
    updated_context = dict(session_context)
    
    # Process tool files
    updated_context = await ingest_tool_files(
        session_context=updated_context,
        tool_result=tool_result,
        user_email=user_email,
        file_manager=file_manager,
        update_callback=update_callback
    )

    # Handle canvas file notifications
    await notify_canvas_files(
        session_context=updated_context,
        file_names=tool_result.returned_file_names,
        file_manager=file_manager,
        update_callback=update_callback
    )

    return updated_context


async def ingest_tool_files(
    session_context: Dict[str, Any],
    tool_result,
    user_email: str,
    file_manager,
    update_callback: Optional[UpdateCallback] = None
) -> Dict[str, Any]:
    """
    Persist tool-produced files into storage and update session context.
    
    Pure function that returns updated context without mutations.
    """
    if not tool_result.returned_file_names:
        return session_context

    # Work with a copy
    updated_context = dict(session_context)
    
    # Safety: avoid huge ingestions
    MAX_FILES = 10
    names = tool_result.returned_file_names[:MAX_FILES]
    contents = tool_result.returned_file_contents[:MAX_FILES] if tool_result.returned_file_contents else []
    
    if contents and len(contents) != len(names):
        logger.warning(
            "ToolResult file arrays length mismatch (names=%d, contents=%d) for tool_call_id=%s", 
            len(names), len(contents), tool_result.tool_call_id
        )
    
    pair_count = min(len(names), len(contents)) if contents else 0
    session_files_ctx = updated_context.setdefault("files", {})
    uploaded_refs: Dict[str, Dict[str, Any]] = {}
    
    for idx, fname in enumerate(names):
        try:
            if idx < pair_count:
                b64 = contents[idx]
                meta = await file_manager.upload_file(
                    user_email=user_email,
                    filename=fname,
                    content_base64=b64,
                    source_type="tool",
                    tags={"source": "tool"}
                )
                session_files_ctx[fname] = {
                    "key": meta.get("key"),
                    "content_type": meta.get("content_type"),
                    "size": meta.get("size"),
                    "source": "tool",
                    "last_modified": meta.get("last_modified"),
                    "tool_call_id": tool_result.tool_call_id
                }
                uploaded_refs[fname] = meta
            else:
                # Name without content – record reference placeholder only if not existing
                if fname not in session_files_ctx:
                    session_files_ctx[fname] = {"source": "tool", "incomplete": True}
        except Exception as e:
            logger.error(f"Failed uploading tool-produced file {fname}: {e}")

    # Emit files update if successful uploads
    if uploaded_refs and update_callback:
        try:
            organized = file_manager.organize_files_metadata(uploaded_refs)
            await update_callback({
                "type": "intermediate_update",
                "update_type": "files_update",
                "data": organized
            })
        except Exception as e:
            logger.error(f"Failed emitting tool files update: {e}")

    return updated_context


async def notify_canvas_files(
    session_context: Dict[str, Any],
    file_names: List[str],
    file_manager,
    update_callback: Optional[UpdateCallback] = None
) -> None:
    """
    Send canvas files notification for tool-produced files.
    
    Pure function with no side effects on session context.
    """
    if not update_callback or not file_names or not file_manager:
        return

    try:
        uploaded_refs = {}
        files_ctx = session_context.get("files", {})
        
        for fname in file_names:
            ref = files_ctx.get(fname)
            if ref and ref.get("key"):
                uploaded_refs[fname] = {
                    "key": ref.get("key"),
                    "size": ref.get("size", 0),
                    "content_type": ref.get("content_type", "application/octet-stream"),
                    "last_modified": ref.get("last_modified"),
                    "tags": {"source": ref.get("source", "tool")}
                }

        if uploaded_refs:
            canvas_files = []
            for fname, meta in uploaded_refs.items():
                if file_manager.should_display_in_canvas(fname):
                    file_ext = file_manager.get_file_extension(fname).lower()
                    canvas_files.append({
                        "filename": fname,
                        "type": file_manager.get_canvas_file_type(file_ext),
                        "s3_key": meta.get("key"),
                        "size": meta.get("size", 0),
                    })
            
            if canvas_files:
                await update_callback({
                    "type": "intermediate_update",
                    "update_type": "canvas_files",
                    "data": {"files": canvas_files}
                })
    except Exception as emit_err:
        logger.warning(f"Non-fatal: failed to emit canvas_files update: {emit_err}")


async def emit_files_update_from_context(
    session_context: Dict[str, Any],
    file_manager,
    update_callback: Optional[UpdateCallback] = None
) -> None:
    """
    Emit a files_update event based on session context files.
    
    Pure function with no side effects.
    """
    if not file_manager or not update_callback:
        return

    try:
        # Build temp structure expected by organizer
        file_refs: Dict[str, Dict[str, Any]] = {}
        for fname, ref in session_context.get("files", {}).items():
            # Expand to shape similar to S3 metadata for organizer
            file_refs[fname] = {
                "key": ref.get("key"),
                "size": ref.get("size", 0),
                "content_type": ref.get("content_type", "application/octet-stream"),
                "last_modified": ref.get("last_modified"),
                "tags": {"source": ref.get("source", "user")}
            }
        
        organized = file_manager.organize_files_metadata(file_refs)
        await update_callback({
            "type": "intermediate_update",
            "update_type": "files_update",
            "data": organized
        })
    except Exception as e:
        logger.error(f"Failed emitting files update: {e}")


def build_files_manifest(session_context: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """
    Build ephemeral files manifest for LLM context.
    
    Pure function that creates manifest from session context.
    """
    files_ctx = session_context.get("files", {})
    if not files_ctx:
        return None

    file_list = "\n".join(f"- {name}" for name in sorted(files_ctx.keys()))
    return {
        "role": "system",
        "content": (
            "Available session files:\n"
            f"{file_list}\n\n"
            "(You can ask to open or analyze any of these by name. "
            "Large contents are not fully in this prompt unless user or tools provided excerpts.)"
        )
    }