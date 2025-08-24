"""
File management utilities - pure functions for session file operations.

This module provides stateless utility functions for handling files within
chat sessions, including user uploads and tool-generated artifacts.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Callable, Awaitable

logger = logging.getLogger(__name__)

# Type hint for update callback
UpdateCallback = Callable[[Dict[str, Any]], Awaitable[None]]


def extract_file_key_from_s3_url(url: str) -> Optional[str]:
    """Extract S3 file key from download URL format
/api/files/download/{key}"""
    if not isinstance(url, str):
        return None
    match = re.match(r'^/api/files/download/([^?]+)', url)
    return match.group(1) if match else None


async def validate_user_file_access(user_email: str, file_key: str,
file_manager) -> bool:
    """Verify user owns the S3 file referenced by key."""
    try:
        # It's expected that `get_file` is a method on the s3_client,
        # not directly on the file_manager. If this needs adjustment,
        # the calling code should be file_manager.s3_client.get_file(...).
        # This function assumes the file_manager has an s3_client attribute.
        if hasattr(file_manager, 's3_client') and hasattr(file_manager.s3_client, 'get_file'):
            file_info = await file_manager.s3_client.get_file(user_email, file_key)
            return file_info is not None
        else:
            logger.error("file_manager.s3_client.get_file method not found.")
            return False
    except Exception as e:
        logger.error(f"Error validating user file access for key {file_key}: {e}")
        return False


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
            logger.info(
                "Emitting files_update for user uploads: total=%d, names=%s",
                len(organized.get('files', [])),
                list(uploaded_refs.keys()),
            )
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
    Process v2 MCP artifacts produced by a tool and return updated session context.
    
    Pure function that handles tool files without side effects on input context.
    """
    if not tool_result.artifacts or not file_manager:
        return session_context

    user_email = session_context.get("user_email")
    if not user_email:
        return session_context

    # Work with a copy to avoid mutations
    updated_context = dict(session_context)
    
    # Process v2 artifacts
    updated_context = await ingest_v2_artifacts(
        session_context=updated_context,
        tool_result=tool_result,
        user_email=user_email,
        file_manager=file_manager,
        update_callback=update_callback
    )

    # Handle canvas file notifications with v2 display config
    await notify_canvas_files_v2(
        session_context=updated_context,
        tool_result=tool_result,
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
    # add a log message. 
    logger.info(f"ingest_tool_files called with tool_result: {tool_result} and user_email: {user_email}")
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
            logger.debug(
                "Emitting files_update for tool uploads: total=%d, names=%s",
                len(organized.get('files', [])),
                list(uploaded_refs.keys()),
            )
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
        logger.debug(
            "Emitting files_update from context: total=%d",
            len(organized.get('files', [])),
        )
        await update_callback({
            "type": "intermediate_update",
            "update_type": "files_update",
            "data": organized
        })
    except Exception as e:
        logger.error(f"Failed emitting files update: {e}")


async def ingest_v2_artifacts(
    session_context: Dict[str, Any],
    tool_result,
    user_email: str,
    file_manager,
    update_callback: Optional[UpdateCallback] = None
) -> Dict[str, Any]:
    """
    Persist v2 MCP artifacts into storage and update session context.
    
    Handles both direct S3 URL references and base64-encoded content.
    """
    if not tool_result.artifacts:
        return session_context

    updated_context = dict(session_context)
    MAX_ARTIFACTS = 10
    artifacts = tool_result.artifacts[:MAX_ARTIFACTS]
    
    s3_refs_to_add = []
    b64_uploads = []
    
    for artifact in artifacts:
        name = artifact.get("name")
        if not name:
            logger.warning("Skipping artifact with missing name.")
            continue

        url = artifact.get("url")
        b64_content = artifact.get("b64")

        if url:
            file_key = extract_file_key_from_s3_url(url)
            if file_key and await validate_user_file_access(user_email, file_key, file_manager):
                s3_refs_to_add.append({
                    "name": name,
                    "key": file_key,
                    "content_type": artifact.get("mime", "application/octet-stream"),
                    "size": artifact.get("size", 0),
                    "source": "mcp_s3_direct"
                })
            else:
                logger.warning(f"Invalid or inaccessible S3 URL for artifact: {name} ({url})")
        elif b64_content:
            b64_uploads.append({
                "filename": name,
                "content": b64_content,
                "mime_type": artifact.get("mime")
            })

    try:
        uploaded_refs = {}
        current_files = updated_context.setdefault("files", {})

        # Process direct S3 references
        for ref in s3_refs_to_add:
            current_files[ref["name"]] = {
                "key": ref["key"],
                "content_type": ref["content_type"],
                "size": ref["size"],
                "source": ref["source"],
            }
            # Add to uploaded_refs for the final notification
            uploaded_refs[ref["name"]] = {
                "key": ref["key"],
                "content_type": ref["content_type"],
                "size": ref["size"],
                "source": ref["source"],
                "tags": {"source": ref["source"]},
            }

        # Process base64 uploads
        if b64_uploads:
            b64_uploaded_refs = await file_manager.upload_files_from_base64(
                b64_uploads, user_email
            )
            current_files.update(b64_uploaded_refs)
            uploaded_refs.update(b64_uploaded_refs)

        # Emit a single files_update event for all processed artifacts
        if uploaded_refs:
            organized = file_manager.organize_files_metadata(uploaded_refs)
            if update_callback:
                logger.debug(
                    "Emitting files_update for v2 artifacts: total=%d, names=%s",
                    len(organized.get('files', [])),
                    list(uploaded_refs.keys()),
                )
                await update_callback({
                    "type": "intermediate_update",
                    "update_type": "files_update",
                    "data": organized
                })
            
    except Exception as e:
        logger.error(f"Error ingesting v2 artifacts: {e}", exc_info=True)
    
    return updated_context


async def notify_canvas_files_v2(
    session_context: Dict[str, Any],
    tool_result,
    file_manager,
    update_callback: Optional[UpdateCallback] = None
) -> None:
    """
    Send v2 canvas files notification with display configuration.
    
    Pure function with no side effects on session context.
    """
    if not update_callback or not tool_result.artifacts:
        return
        
    try:
        # Get uploaded file references from session context
        uploaded_refs = session_context.get("files", {})
        artifact_names = [artifact.get("name") for artifact in tool_result.artifacts if artifact.get("name")]
        
        if uploaded_refs and artifact_names:
            canvas_files = []
            for fname in artifact_names:
                meta = uploaded_refs.get(fname)
                if meta and file_manager.should_display_in_canvas(fname):
                    # Get MIME type from artifact if available
                    artifact = next((a for a in tool_result.artifacts if a.get("name") == fname), {})
                    mime_type = artifact.get("mime")
                    
                    file_ext = file_manager.get_file_extension(fname).lower()
                    canvas_files.append({
                        "filename": fname,
                        "type": file_manager.get_canvas_file_type(file_ext),
                        "s3_key": meta.get("key"),
                        "size": meta.get("size", 0),
                        "mime_type": mime_type
                    })
            
            if canvas_files:
                # Reorder files to put primary_file first if provided
                primary = None
                if tool_result.display_config and isinstance(tool_result.display_config, dict):
                    primary = tool_result.display_config.get("primary_file")
                if primary:
                    # stable reorder
                    canvas_files = sorted(
                        canvas_files,
                        key=lambda f: 0 if f.get("filename") == primary else 1
                    )

                # Build canvas update with v2 display configuration
                logger.info(
                    "Emitting canvas_files event: count=%d, files=%s, display=%s",
                    len(canvas_files),
                    [f.get("filename") for f in canvas_files],
                    tool_result.display_config,
                )
                canvas_update = {
                    "type": "intermediate_update",
                    "update_type": "canvas_files",
                    "data": {"files": canvas_files}
                }
                
                # Add v2 display configuration if present
                if tool_result.display_config:
                    canvas_update["data"]["display"] = tool_result.display_config
                    
                await update_callback(canvas_update)
            else:
                logger.info(
                    "No canvas-displayable artifacts found. artifact_names=%s",
                    artifact_names,
                )
                
    except Exception as emit_err:
        logger.warning(f"Non-fatal: failed to emit v2 canvas_files update: {emit_err}")


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
