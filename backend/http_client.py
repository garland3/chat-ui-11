"""
Unified HTTP client utility with standardized error handling and logging.

This module provides a reusable HTTP client that:
- Eliminates duplicate error handling patterns across the codebase
- Provides consistent logging with tracebacks for all errors
- Supports both async and sync operations
- Handles common HTTP patterns (JSON requests, timeouts, retries)
"""

import logging
from typing import Any, Dict, Optional, Union
import httpx
from fastapi import HTTPException

logger = logging.getLogger(__name__)


class HTTPClientError(Exception):
    """Base exception for HTTP client errors."""
    pass


class HTTPTimeoutError(HTTPClientError):
    """Raised when HTTP requests timeout."""
    pass


class HTTPStatusError(HTTPClientError):
    """Raised when HTTP requests return error status codes."""
    def __init__(self, message: str, status_code: int, response_text: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text


class UnifiedHTTPClient:
    """
    Unified HTTP client with standardized error handling and logging.
    
    This client provides consistent error handling and logging across all HTTP operations
    in the application, eliminating the duplicate patterns found in rag_client.py.
    """
    
    def __init__(self, base_url: str = "", timeout: float = 30.0):
        """
        Initialize the HTTP client.
        
        Args:
            base_url: Base URL for requests (optional)
            timeout: Default timeout for requests in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
    
    def _build_url(self, endpoint: str) -> str:
        """Build full URL from endpoint."""
        if endpoint.startswith('http'):
            return endpoint
        return f"{self.base_url}/{endpoint.lstrip('/')}"
    
    def _handle_request_error(self, error: Exception, operation: str, url: str) -> HTTPException:
        """
        Handle and log request errors with proper tracebacks.
        
        Args:
            error: The original exception
            operation: Description of the operation (for logging)
            url: The URL that was being accessed
            
        Returns:
            HTTPException: Appropriate FastAPI exception
        """
        if isinstance(error, httpx.TimeoutException):
            logger.error(f"Timeout during {operation} to {url}: {error}", exc_info=True)
            return HTTPException(status_code=504, detail=f"Request timeout during {operation}")
        
        elif isinstance(error, httpx.RequestError):
            logger.error(f"Request error during {operation} to {url}: {error}", exc_info=True)
            return HTTPException(status_code=503, detail=f"Service unavailable during {operation}")
        
        elif isinstance(error, httpx.HTTPStatusError):
            logger.error(
                f"HTTP {error.response.status_code} error during {operation} to {url}: {error}",
                exc_info=True
            )
            
            # Map common HTTP status codes to appropriate FastAPI exceptions
            status_code = error.response.status_code
            if status_code == 403:
                return HTTPException(status_code=403, detail=f"Access denied during {operation}")
            elif status_code == 404:
                return HTTPException(status_code=404, detail=f"Resource not found during {operation}")
            elif status_code >= 500:
                return HTTPException(status_code=503, detail=f"Service error during {operation}")
            else:
                return HTTPException(status_code=status_code, detail=f"HTTP error during {operation}")
        
        else:
            logger.error(f"Unexpected error during {operation} to {url}: {error}", exc_info=True)
            return HTTPException(status_code=500, detail=f"Internal error during {operation}")
    
    async def get(
        self, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Perform async GET request with error handling.
        
        Args:
            endpoint: API endpoint or full URL
            params: Query parameters
            headers: Request headers
            timeout: Request timeout (overrides default)
            
        Returns:
            Response JSON data
            
        Raises:
            HTTPException: On any request error
        """
        url = self._build_url(endpoint)
        request_timeout = timeout or self.timeout
        
        try:
            async with httpx.AsyncClient(timeout=request_timeout) as client:
                logger.debug(f"GET request to {url} with params: {params}")
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                logger.info(f"Successful GET request to {url}")
                return data
                
        except Exception as e:
            raise self._handle_request_error(e, "GET request", url)
    
    async def post(
        self, 
        endpoint: str, 
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Perform async POST request with error handling.
        
        Args:
            endpoint: API endpoint or full URL
            json_data: JSON payload
            data: Form data payload
            headers: Request headers
            timeout: Request timeout (overrides default)
            
        Returns:
            Response JSON data
            
        Raises:
            HTTPException: On any request error
        """
        url = self._build_url(endpoint)
        request_timeout = timeout or self.timeout
        
        try:
            async with httpx.AsyncClient(timeout=request_timeout) as client:
                logger.debug(f"POST request to {url} with JSON data keys: {list(json_data.keys()) if json_data else 'None'}")
                response = await client.post(url, json=json_data, data=data, headers=headers)
                response.raise_for_status()
                
                response_data = response.json()
                logger.info(f"Successful POST request to {url}")
                return response_data
                
        except Exception as e:
            raise self._handle_request_error(e, "POST request", url)
    
    def get_sync(
        self, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Perform synchronous GET request with error handling.
        
        Args:
            endpoint: API endpoint or full URL
            params: Query parameters
            headers: Request headers
            timeout: Request timeout (overrides default)
            
        Returns:
            Response JSON data
            
        Raises:
            HTTPClientError: On any request error
        """
        url = self._build_url(endpoint)
        request_timeout = timeout or self.timeout
        
        try:
            with httpx.Client(timeout=request_timeout) as client:
                logger.debug(f"Sync GET request to {url} with params: {params}")
                response = client.get(url, params=params, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                logger.info(f"Successful sync GET request to {url}")
                return data
                
        except httpx.TimeoutException as e:
            logger.error(f"Timeout during sync GET to {url}: {e}", exc_info=True)
            raise HTTPTimeoutError(f"Request timeout to {url}")
        
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP {e.response.status_code} error during sync GET to {url}: {e}", exc_info=True)
            raise HTTPStatusError(
                f"HTTP {e.response.status_code} error",
                e.response.status_code,
                e.response.text
            )
        
        except Exception as e:
            logger.error(f"Unexpected error during sync GET to {url}: {e}", exc_info=True)
            raise HTTPClientError(f"Request failed to {url}: {e}")
    
    def post_sync(
        self, 
        endpoint: str, 
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Perform synchronous POST request with error handling.
        
        Args:
            endpoint: API endpoint or full URL
            json_data: JSON payload
            data: Form data payload
            headers: Request headers
            timeout: Request timeout (overrides default)
            
        Returns:
            Response JSON data
            
        Raises:
            HTTPClientError: On any request error
        """
        url = self._build_url(endpoint)
        request_timeout = timeout or self.timeout
        
        try:
            with httpx.Client(timeout=request_timeout) as client:
                logger.debug(f"Sync POST request to {url} with JSON data keys: {list(json_data.keys()) if json_data else 'None'}")
                response = client.post(url, json=json_data, data=data, headers=headers)
                response.raise_for_status()
                
                response_data = response.json()
                logger.info(f"Successful sync POST request to {url}")
                return response_data
                
        except httpx.TimeoutException as e:
            logger.error(f"Timeout during sync POST to {url}: {e}", exc_info=True)
            raise HTTPTimeoutError(f"Request timeout to {url}")
        
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP {e.response.status_code} error during sync POST to {url}: {e}", exc_info=True)
            raise HTTPStatusError(
                f"HTTP {e.response.status_code} error",
                e.response.status_code,
                e.response.text
            )
        
        except Exception as e:
            logger.error(f"Unexpected error during sync POST to {url}: {e}", exc_info=True)
            raise HTTPClientError(f"Request failed to {url}: {e}")


# Convenience functions for common patterns
def create_rag_client(base_url: str, timeout: float = 30.0) -> UnifiedHTTPClient:
    """Create HTTP client configured for RAG service."""
    return UnifiedHTTPClient(base_url=base_url, timeout=timeout)


def create_llm_client(timeout: float = 30.0) -> UnifiedHTTPClient:
    """Create HTTP client configured for LLM API calls."""
    return UnifiedHTTPClient(timeout=timeout)