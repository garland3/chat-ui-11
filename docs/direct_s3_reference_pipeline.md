# Direct S3 Reference Pipeline Implementation

## Overview

The Direct S3 Reference Pipeline eliminates the inefficient double-upload problem in the MCP v2 artifact system:

1. **Before**: MCP Tools → Upload files to S3 → Return url in artifacts → Backend ingest_v2_artifacts() → Downloads from S3 → Re-uploads to S3 via file manager
2. **After**: MCP Tools → Upload files to S3 → Return url in artifacts → Backend ingest_v2_artifacts() → Directly references S3 URLs without re-uploading

## Implementation Status

✅ **Phase 1: Update Backend Artifact Processing** - COMPLETED
- File: `backend/application/chat/utilities/file_utils.py`
- Function: `ingest_v2_artifacts()` updated to handle direct S3 references

✅ **Phase 2: Update File Manager Integration** - COMPLETED
- File: `backend/modules/file_storage/manager.py`
- Added: `validate_s3_file_access()` method for S3 URL validation

✅ **Phase 3: Canvas/UI Compatibility** - COMPLETED
- No changes needed - canvas already supports `/api/files/download/{file_key}` URLs

✅ **Phase 4: Session Context Updates** - COMPLETED
- File: `backend/application/chat/utilities/tool_utils.py`
- Function: `inject_context_into_args()` already handles URL conversion

✅ **Phase 5: Security & Validation** - COMPLETED
- Access Control: `validate_user_file_access()` checks ownership before adding to context
- Capability Tokens: Stripped from URLs and re-generated when needed

## Key Components

### 1. URL Parsing Helper
```python
def extract_file_key_from_s3_url(url: str) -> Optional[str]:
    """Extract S3 file key from download URL format /api/files/download/{key}"""
    match = re.match(r'^/api/files/download/([^?]+)', url)
    return match.group(1) if match else None
```

### 2. Enhanced Artifact Processing
```python
async def ingest_v2_artifacts(...):
    for artifact in artifacts:
        if artifact.get("url"):
            # Validate S3 URL belongs to user
            file_key = extract_file_key_from_s3_url(artifact["url"])
            if file_key and await validate_user_file_access(user_email, file_key, file_manager):
                s3_refs_to_add.append({
                    "name": artifact["name"], 
                    "key": file_key,
                    "content_type": artifact.get("mime", "application/octet-stream"),
                    "size": artifact.get("size", 0),
                    "source": "mcp_s3_direct"
                })
```

### 3. File Validation
```python
async def validate_user_file_access(user_email: str, file_key: str, file_manager) -> bool:
    """Verify user owns the S3 file referenced by key."""
    try:
        file_info = await file_manager.s3_client.get_file(user_email, file_key)
        return file_info is not None
    except:
        return False
```

## Benefits

✅ **Performance**: Eliminates double S3 upload
✅ **Storage**: No duplicate files in S3
✅ **Bandwidth**: Reduces backend → S3 traffic
✅ **Latency**: Faster tool responses (no re-upload wait)
✅ **Security**: Maintains user file isolation
✅ **Compatibility**: Supports both URL and base64 artifacts

## Backward Compatibility

✅ Existing tools with b64 artifacts continue to work
✅ Canvas/UI sees no difference in file access
✅ File manager APIs remain unchanged
✅ Session context structure stays consistent

## Testing

Tests have been added to verify the implementation:
- `backend/tests/test_direct_s3_reference_pipeline.py`

## Troubleshooting

If you encounter issues with tools not properly handling S3 URLs:

1. **Check the artifact format**: Ensure tools return artifacts with proper "url" field
2. **Verify file access validation**: Make sure the user has access to the S3 file
3. **Check session context**: Ensure files are properly stored in the session context
4. **Verify URL injection**: Confirm that filename parameters are being converted to URLs

## Example Artifact Format

```json
{
  "name": "signal_data.csv",
  "url": "/api/files/download/users/test@example.com/generated/1234567890_abc123_signal_data.csv",
  "mime": "text/csv",
  "size": 1024
}
