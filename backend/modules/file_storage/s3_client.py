"""
S3 Client for file storage operations.

This module provides a client interface to interact with S3 storage,
supporting both real AWS S3 and our mock S3 service for development.
"""

import logging
import re
from typing import Dict, List, Optional, Any
from urllib.parse import quote, unquote
import base64
from datetime import datetime, timezone
import httpx

try:
    import boto3  # type: ignore
    from botocore.client import Config as BotoConfig  # type: ignore
    from botocore.exceptions import ClientError  # type: ignore
except Exception:  # pragma: no cover - boto may not be installed yet during edits
    boto3 = None
    BotoConfig = None
    ClientError = Exception


logger = logging.getLogger(__name__)


class S3StorageClient:
    """Client for interacting with S3 storage (real or mock)."""
    
    def __init__(self, s3_endpoint: str = None, s3_timeout: int = None, s3_use_mock: bool = None):
        """Initialize the S3 client with configuration."""
        # Allow dependency injection for testing
        if s3_endpoint is None or s3_timeout is None or s3_use_mock is None:
            from modules.config import config_manager
            config = config_manager.app_settings
            s3_endpoint = s3_endpoint or config.s3_endpoint
            s3_timeout = s3_timeout or config.s3_timeout
            s3_use_mock = s3_use_mock if s3_use_mock is not None else config.s3_use_mock
        
        self.base_url = s3_endpoint
        self.timeout = s3_timeout
        self.use_mock = s3_use_mock
        self._boto = None
        self._bucket = None
        self._region = None
        self._path_style = True
        self._access_key = None
        self._secret_key = None
        
        logger.info(f"S3Client initialized with endpoint: {self.base_url}")
        if not self.use_mock:
            # Load additional settings only when using real S3/MinIO
            from modules.config import config_manager
            cfg = config_manager.app_settings
            self._bucket = cfg.s3_bucket
            self._region = cfg.s3_region
            self._path_style = bool(cfg.s3_path_style)
            self._access_key = cfg.s3_access_key_id
            self._secret_key = cfg.s3_secret_access_key
            self._init_boto_client()
    
    def _sanitize_log_value(self, s: str, max_length: int = 100) -> str:
        """
        Sanitize a string value for safe logging.
        
        Args:
            s: The string to sanitize
            max_length: Maximum length of the logged string
            
        Returns:
            Sanitized string with newlines removed and length limited
        """
        if not isinstance(s, str):
            s = str(s)
        
        # Remove carriage returns and newlines
        sanitized = s.replace('\r', '').replace('\n', '')
        
        # Truncate if too long
        if len(sanitized) > max_length:
            half_length = max_length // 2
            sanitized = sanitized[:half_length] + '...' + sanitized[-half_length:]
        
        return sanitized
    
    def _get_auth_headers(self, user_email: str) -> Dict[str, str]:
        """Get authorization headers for the request."""
        if self.use_mock:
            # For mock service, use user email as bearer token
            return {"Authorization": f"Bearer {user_email}"}
        else:
            # Not used for real S3 path (boto handles auth)
            return {}
    
    def _validate_and_sanitize_file_key(self, file_key: str) -> str:
        """
        Validate and sanitize file key to prevent SSRF attacks.
        
        Args:
            file_key: The file key to validate
            
        Returns:
            Sanitized file key safe for URL construction
            
        Raises:
            ValueError: If file_key contains invalid characters
        """
        if not file_key or not isinstance(file_key, str):
            raise ValueError("File key must be a non-empty string")
        # Normalize any percent-encoded input once to validate on the real characters
        decoded_key = unquote(file_key)

        # Remove any potentially dangerous characters
        # Allow common email/path characters used in our keys: '@', '+'.
        # Also allow '%' to tolerate pre-encoded inputs reaching this layer.
        # Keep strict allowlist to reduce risk of path or header injection.
        if not re.match(r'^[a-zA-Z0-9._/@+%\-]+$', decoded_key):
            raise ValueError("File key contains invalid characters")

        # Prevent path traversal attempts
        if '..' in decoded_key or decoded_key.startswith('/'):
            raise ValueError("File key contains invalid path sequences")

        # URL encode the file key to safely include it in URLs (keep path separators only)
        return quote(decoded_key, safe='/@+')

    def _init_boto_client(self) -> None:
        if boto3 is None:
            raise RuntimeError("boto3 is required for real S3/MinIO usage")
        session = boto3.session.Session()
        # Path-style addressing is typical for MinIO
        s3cfg = BotoConfig(s3={"addressing_style": "path" if self._path_style else "virtual"})
        self._boto = session.client(
            "s3",
            endpoint_url=self.base_url,
            region_name=self._region,
            aws_access_key_id=self._access_key,
            aws_secret_access_key=self._secret_key,
            config=s3cfg,
        )
        # Ensure bucket exists (idempotent)
        try:
            self._boto.head_bucket(Bucket=self._bucket)
        except ClientError as e:
            code = getattr(e, "response", {}).get("Error", {}).get("Code")
            if code in ("404", "NoSuchBucket"):
                if self._region and self._region != "us-east-1":
                    self._boto.create_bucket(
                        Bucket=self._bucket,
                        CreateBucketConfiguration={"LocationConstraint": self._region},
                    )
                else:
                    self._boto.create_bucket(Bucket=self._bucket)
            else:
                # If different error (e.g., auth), re-raise
                raise
    
    async def upload_file(
        self, 
        user_email: str,
        filename: str,
        content_base64: str,
        content_type: str = "application/octet-stream",
        tags: Optional[Dict[str, str]] = None,
        source_type: str = "user"
    ) -> Dict[str, Any]:
        """
        Upload a file to S3 storage.
        
        Args:
            user_email: Email of the user uploading the file
            filename: Original filename
            content_base64: Base64 encoded file content
            content_type: MIME type of the file
            tags: Additional metadata tags
            source_type: Type of file ("user" or "tool")
            
        Returns:
            Dictionary containing file metadata including the S3 key
        """
        try:
            file_tags = tags or {}
            file_tags["source"] = source_type

            if self.use_mock:
                payload = {
                    "filename": filename,
                    "content_base64": content_base64,
                    "content_type": content_type,
                    "tags": file_tags,
                }
                headers = self._get_auth_headers(user_email)
                headers["Content-Type"] = "application/json"
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/files",
                        json=payload,
                        headers=headers,
                    )
                if response.status_code != 200:
                    error_msg = f"S3 upload failed with status {response.status_code}: {response.text}"
                    logger.error(error_msg)
                    raise Exception(error_msg)
                result = response.json()
                logger.info(f"File uploaded successfully: {self._sanitize_log_value(result['key'])} for user {self._sanitize_log_value(user_email)}")
                return result

            # Real S3/MinIO path
            # Construct key similar to mock: users/{email}/(uploads|generated)/ts_uuid_filename
            now_ts = int(datetime.now(timezone.utc).timestamp())
            safe_filename = re.sub(r"[\\\r\n\t]", "_", filename).replace("/", "_")
            uid = "%08x" % (abs(hash((user_email, filename, now_ts))) & 0xFFFFFFFF)
            subdir = "generated" if source_type == "tool" else "uploads"
            key = f"users/{user_email}/{subdir}/{now_ts}_{uid}_{safe_filename}"
            # Canonicalize to encoded path (same scheme used by getters)
            key = self._validate_and_sanitize_file_key(key)

            body = base64.b64decode(content_base64)
            put_kwargs: Dict[str, Any] = {
                "Bucket": self._bucket,
                "Key": key,
                "Body": body,
                "ContentType": content_type or "application/octet-stream",
                "Metadata": {"filename": filename},
            }
            if file_tags:
                # Convert dict to AWS tagging string: k1=v1&k2=v2
                tag_str = "&".join([f"{quote(str(k), safe='')}={quote(str(v), safe='')}" for k, v in file_tags.items()])
                put_kwargs["Tagging"] = tag_str

            self._boto.put_object(**put_kwargs)
            head = self._boto.head_object(Bucket=self._bucket, Key=key)

            result = {
                "key": key,
                "filename": filename,
                "size": head.get("ContentLength", len(body)),
                "content_type": head.get("ContentType", content_type or "application/octet-stream"),
                "last_modified": head.get("LastModified", datetime.now(timezone.utc)).isoformat(),
                "etag": head.get("ETag", "").strip('"'),
                "tags": file_tags,
                "user_email": user_email,
            }
            logger.info(f"File uploaded successfully: {self._sanitize_log_value(key)} for user {self._sanitize_log_value(user_email)}")
            return result
        except Exception as e:
            logger.error(f"Error uploading file to S3: {str(e)}")
            raise
    
    async def get_file(self, user_email: str, file_key: str) -> Dict[str, Any]:
        """
        Get a file from S3 storage.
        
        Args:
            user_email: Email of the user requesting the file
            file_key: S3 key of the file to retrieve
            
        Returns:
            Dictionary containing file data and metadata
        """
        try:
            # Validate and sanitize file_key to prevent SSRF
            sanitized_file_key = self._validate_and_sanitize_file_key(file_key)

            if self.use_mock:
                headers = self._get_auth_headers(user_email)
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(
                        f"{self.base_url}/files/{sanitized_file_key}",
                        headers=headers,
                    )
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"File retrieved successfully: {self._sanitize_log_value(file_key)} for user {self._sanitize_log_value(user_email)}")
                    return result
                elif response.status_code == 404:
                    logger.warning(f"File not found: {self._sanitize_log_value(file_key)} for user {self._sanitize_log_value(user_email)}")
                    return None
                elif response.status_code == 403:
                    logger.warning(f"Access denied to file: {self._sanitize_log_value(file_key)} for user {self._sanitize_log_value(user_email)}")
                    raise Exception("Access denied to file")
                else:
                    error_msg = f"S3 get failed with status {response.status_code}: {response.text}"
                    logger.error(error_msg)
                    raise Exception(error_msg)

            # Real S3/MinIO path
            head = self._boto.head_object(Bucket=self._bucket, Key=sanitized_file_key)
            obj = self._boto.get_object(Bucket=self._bucket, Key=sanitized_file_key)
            body = obj["Body"].read()
            content_b64 = base64.b64encode(body).decode()
            # Try to use stored filename metadata; fallback to key suffix
            meta = {k.lower(): v for k, v in (head.get("Metadata") or {}).items()}
            filename = meta.get("filename") or sanitized_file_key.split("/")[-1]
            content_type = head.get("ContentType", obj.get("ContentType", "application/octet-stream"))
            result = {
                "key": sanitized_file_key,
                "filename": filename,
                "content_base64": content_b64,
                "content_type": content_type,
                "size": head.get("ContentLength", len(body)),
                "last_modified": head.get("LastModified", datetime.now(timezone.utc)).isoformat(),
                "etag": head.get("ETag", "").strip('"'),
                "tags": {},  # Omitting tag fetch for speed; mock-compatible field present
            }
            logger.info(f"File retrieved successfully: {file_key} for user {user_email}")
            return result
        except ClientError as e:
            code = getattr(e, "response", {}).get("Error", {}).get("Code")
            if code in ("404", "NoSuchKey"):
                logger.warning(f"File not found: {file_key} for user {user_email}")
                return None
            raise
        except Exception as e:
            logger.error(f"Error getting file from S3: {str(e)}")
            raise
    
    async def list_files(
        self, 
        user_email: str,
        file_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List files for a user.
        
        Args:
            user_email: Email of the user
            file_type: Optional filter by file type ("user" or "tool")
            limit: Maximum number of files to return
            
        Returns:
            List of file metadata dictionaries
        """
        try:
            if self.use_mock:
                headers = self._get_auth_headers(user_email)
                params = {"limit": limit}
                if file_type:
                    params["file_type"] = file_type
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(
                        f"{self.base_url}/files",
                        headers=headers,
                        params=params,
                    )
                if response.status_code != 200:
                    error_msg = f"S3 list failed with status {response.status_code}: {response.text}"
                    logger.error(error_msg)
                    raise Exception(error_msg)
                result = response.json()
                logger.info(f"Listed {len(result)} files for user {self._sanitize_log_value(user_email)}")
                return result

            # Real S3/MinIO path
            prefix = f"users/{user_email}/"
            if file_type == "tool":
                prefix += "generated/"
            elif file_type == "user":
                prefix += "uploads/"

            resp = self._boto.list_objects_v2(Bucket=self._bucket, Prefix=prefix, MaxKeys=max(1, min(1000, limit)))
            items = []
            for obj in resp.get("Contents", [])[:limit]:
                items.append({
                    "key": obj["Key"],
                    "filename": obj["Key"].split("/")[-1],
                    "size": obj.get("Size", 0),
                    "content_type": "application/octet-stream",
                    "last_modified": obj.get("LastModified", datetime.now(timezone.utc)).isoformat(),
                    "etag": obj.get("ETag", "").strip('"'),
                    "tags": {},
                    "user_email": user_email,
                })
            # Sort newest first by last_modified
            items.sort(key=lambda x: x["last_modified"], reverse=True)
            logger.info(f"Listed {len(items)} files for user {self._sanitize_log_value(user_email)}")
            return items
        except Exception as e:
            logger.error(f"Error listing files from S3: {str(e)}")
            raise
    
    async def delete_file(self, user_email: str, file_key: str) -> bool:
        """
        Delete a file from S3 storage.
        
        Args:
            user_email: Email of the user deleting the file
            file_key: S3 key of the file to delete
            
        Returns:
            True if deletion was successful
        """
        try:
            sanitized_file_key = self._validate_and_sanitize_file_key(file_key)
            if self.use_mock:
                headers = self._get_auth_headers(user_email)
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.delete(
                        f"{self.base_url}/files/{sanitized_file_key}",
                        headers=headers,
                    )
                if response.status_code == 200:
                    logger.info(f"File deleted successfully: {self._sanitize_log_value(file_key)} for user {self._sanitize_log_value(user_email)}")
                    return True
                elif response.status_code == 404:
                    logger.warning(f"File not found for deletion: {self._sanitize_log_value(file_key)} for user {self._sanitize_log_value(user_email)}")
                    return False
                elif response.status_code == 403:
                    logger.warning(f"Access denied for deletion: {self._sanitize_log_value(file_key)} for user {self._sanitize_log_value(user_email)}")
                    raise Exception("Access denied to delete file")
                else:
                    error_msg = f"S3 delete failed with status {response.status_code}: {response.text}"
                    logger.error(error_msg)
                    raise Exception(error_msg)

            # Real S3/MinIO path
            # Check existence to mirror mock 404 behavior on missing keys
            try:
                self._boto.head_object(Bucket=self._bucket, Key=sanitized_file_key)
            except ClientError as e:
                code = getattr(e, "response", {}).get("Error", {}).get("Code")
                if code in ("404", "NoSuchKey"):
                    logger.warning(f"File not found for deletion: {file_key} for user {user_email}")
                    return False
                raise
            self._boto.delete_object(Bucket=self._bucket, Key=sanitized_file_key)
            logger.info(f"File deleted successfully: {file_key} for user {user_email}")
            return True
        except ClientError as e:
            code = getattr(e, "response", {}).get("Error", {}).get("Code")
            if code in ("404", "NoSuchKey"):
                logger.warning(f"File not found for deletion: {file_key} for user {user_email}")
                return False
            raise
        except Exception as e:
            logger.error(f"Error deleting file from S3: {str(e)}")
            raise
    
    async def get_user_stats(self, user_email: str) -> Dict[str, Any]:
        """
        Get file statistics for a user.
        
        Args:
            user_email: Email of the user
            
        Returns:
            Dictionary containing file statistics
        """
        try:
            if self.use_mock:
                headers = self._get_auth_headers(user_email)
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(
                        f"{self.base_url}/users/{user_email}/files/stats",
                        headers=headers,
                    )
                if response.status_code != 200:
                    error_msg = f"S3 stats failed with status {response.status_code}: {response.text}"
                    logger.error(error_msg)
                    raise Exception(error_msg)
                result = response.json()
                logger.info(f"Got file stats for user {self._sanitize_log_value(user_email)}: {result}")
                return result

            # Real S3/MinIO path: aggregate over list
            files = await self.list_files(user_email=user_email, file_type=None, limit=1000)
            total_size = sum(f.get("size", 0) for f in files)
            upload_count = sum(1 for f in files if "/uploads/" in f.get("key", ""))
            generated_count = sum(1 for f in files if "/generated/" in f.get("key", ""))
            result = {
                "total_files": len(files),
                "total_size": total_size,
                "upload_count": upload_count,
                "generated_count": generated_count,
            }
            logger.info(f"Got file stats for user {self._sanitize_log_value(user_email)}: {result}")
            return result
        except Exception as e:
            logger.error(f"Error getting user stats from S3: {str(e)}")
            raise
