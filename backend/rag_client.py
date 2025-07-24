"""RAG Client for integrating with RAG mock endpoint."""

import logging
import os
from typing import Dict, List, Optional
import httpx
from fastapi import HTTPException

logger = logging.getLogger(__name__)


class RAGClient:
    """Client for communicating with RAG mock API."""
    
    def __init__(self):
        self.base_url = os.getenv("RAG_MOCK_URL", "http://localhost:8001")
        self.timeout = 30.0
        
    async def discover_data_sources(self, user_name: str) -> List[str]:
        """Discover data sources accessible by a user."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/v1/discover/datasources/{user_name}"
                )
                response.raise_for_status()
                data = response.json()
                return data.get("accessible_data_sources", [])
        except httpx.RequestError as exc:
            logger.error(f"Request error while discovering data sources for {user_name}: {exc}")
            import traceback
            print(traceback.format_exc())
            # Return empty list instead of raising error for graceful degradation
            return []
        except httpx.HTTPStatusError as exc:
            logger.error(f"HTTP error {exc.response.status_code} while discovering data sources for {user_name}: {exc}")
            if exc.response.status_code == 404:
                # User not found
                return []
            # Return empty list for other errors to avoid breaking the app
            return []
        except Exception as exc:
            logger.error(f"Unexpected error while discovering data sources for {user_name}: {exc}")
            return []
    
    async def query_rag(self, user_name: str, data_source: str, messages: List[Dict]) -> str:
        """Query RAG endpoint for a response."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                payload = {
                    "messages": messages,
                    "user_name": user_name,
                    "data_source": data_source,
                    "model": "gpt-4-rag-mock",
                    "stream": False
                }
                
                response = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    json=payload
                )
                response.raise_for_status()
                data = response.json()
                
                # Extract the assistant message from the response
                if "choices" in data and len(data["choices"]) > 0:
                    choice = data["choices"][0]
                    if "message" in choice and "content" in choice["message"]:
                        return choice["message"]["content"]
                
                return "No response from RAG system."
                
        except httpx.RequestError as exc:
            logger.error(f"Request error while querying RAG for {user_name}: {exc}")
            raise HTTPException(status_code=503, detail="RAG service unavailable")
        except httpx.HTTPStatusError as exc:
            logger.error(f"HTTP error {exc.response.status_code} while querying RAG for {user_name}: {exc}")
            if exc.response.status_code == 403:
                raise HTTPException(status_code=403, detail="Access denied to data source")
            elif exc.response.status_code == 404:
                raise HTTPException(status_code=404, detail="Data source not found")
            else:
                raise HTTPException(status_code=503, detail="RAG service error")
        except Exception as exc:
            logger.error(f"Unexpected error while querying RAG for {user_name}: {exc}")
            raise HTTPException(status_code=500, detail="Internal server error")


# Global RAG client instance
rag_client = RAGClient()