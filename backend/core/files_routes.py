"""
Files API routes for S3 file management.

Provides REST API endpoints for file operations including upload, download,
list, delete, and user statistics. Integrates with S3 storage backend.
"""

import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from s3_client import s3_client
from utils import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["files"])


class FileUploadRequest(BaseModel):
    filename: str
    content_base64: str
    content_type: Optional[str] = "application/octet-stream"
    tags: Optional[Dict[str, str]] = {}


class FileResponse(BaseModel):
    key: str
    filename: str
    size: int
    content_type: str
    last_modified: str
    etag: str
    tags: Dict[str, str]
    user_email: str


class FileContentResponse(BaseModel):
    key: str
    filename: str
    content_base64: str
    content_type: str
    size: int
    last_modified: str
    etag: str
    tags: Dict[str, str]


@router.post("/files", response_model=FileResponse)
async def upload_file(
    request: FileUploadRequest,
    current_user: str = Depends(get_current_user)
) -> FileResponse:
    """Upload a file to S3 storage."""
    try:
        result = await s3_client.upload_file(
            user_email=current_user,
            filename=request.filename,
            content_base64=request.content_base64,
            content_type=request.content_type,
            tags=request.tags,
            source_type=request.tags.get("source", "user") if request.tags else "user"
        )
        
        return FileResponse(**result)
        
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/files/{file_key}", response_model=FileContentResponse)
async def get_file(
    file_key: str,
    current_user: str = Depends(get_current_user)
) -> FileContentResponse:
    """Get a file from S3 storage."""
    try:
        result = await s3_client.get_file(current_user, file_key)
        
        if not result:
            raise HTTPException(status_code=404, detail="File not found")
            
        return FileContentResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting file: {str(e)}")
        if "Access denied" in str(e):
            raise HTTPException(status_code=403, detail="Access denied")
        raise HTTPException(status_code=500, detail=f"Failed to get file: {str(e)}")


@router.get("/files", response_model=List[FileResponse])
async def list_files(
    current_user: str = Depends(get_current_user),
    file_type: Optional[str] = None,
    limit: int = 100
) -> List[FileResponse]:
    """List files for the current user."""
    try:
        result = await s3_client.list_files(
            user_email=current_user,
            file_type=file_type,
            limit=limit
        )
        
        return [FileResponse(**file_data) for file_data in result]
        
    except Exception as e:
        logger.error(f"Error listing files: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")


@router.delete("/files/{file_key}")
async def delete_file(
    file_key: str,
    current_user: str = Depends(get_current_user)
) -> Dict[str, str]:
    """Delete a file from S3 storage."""
    try:
        success = await s3_client.delete_file(current_user, file_key)
        
        if not success:
            raise HTTPException(status_code=404, detail="File not found")
            
        return {"message": "File deleted successfully", "key": file_key}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting file: {str(e)}")
        if "Access denied" in str(e):
            raise HTTPException(status_code=403, detail="Access denied")
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")


@router.get("/users/{user_email}/files/stats")
async def get_user_file_stats(
    user_email: str,
    current_user: str = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get file statistics for a user."""
    # Users can only see their own stats
    if current_user != user_email:
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        result = await s3_client.get_user_stats(current_user)
        return result
        
    except Exception as e:
        logger.error(f"Error getting user stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@router.get("/files/health")
async def files_health_check():
    """Health check for files service."""
    return {
        "status": "healthy",
        "service": "files-api",
        "s3_config": {
            "endpoint": s3_client.base_url,
            "use_mock": s3_client.use_mock
        }
    }