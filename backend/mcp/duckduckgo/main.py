#!/usr/bin/env python3
"""
MCP Server for Web Search using DuckDuckGo.
Provides a tool to search DuckDuckGo, fetch the content of a result,
and return it.
"""

import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from typing import Any, Dict, Union

from fastmcp import FastMCP

# Initialize the MCP server
mcp = FastMCP("WebSearcher")


def get_page_content(url: str) -> str:
    """
    Fetches and parses the text content of a given URL.

    Args:
        url: The URL of the webpage to parse.

    Returns:
        The cleaned text content of the page, or an error message.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

        soup = BeautifulSoup(response.text, 'html.parser')

        # Remove script and style elements
        for script_or_style in soup(["script", "style"]):
            script_or_style.decompose()

        # Get text and clean it up
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        cleaned_text = '\n'.join(chunk for chunk in chunks if chunk)

        return cleaned_text

    except requests.RequestException as e:
        return f"Error fetching URL {url}: {e}"
    except Exception as e:
        return f"An error occurred during page parsing: {e}"


@mcp.tool
def search_and_fetch(query: str) -> Dict[str, Any]:
    """
    Searches DuckDuckGo for a query, fetches the first result, and returns its content.

    Args:
        query: The search term.

    Returns:
        A dictionary containing the search result's title, URL, and parsed content.
    """
    try:
        with DDGS() as ddgs:
            # Perform the search and get the first result
            results = list(ddgs.text(query, max_results=1))

        if not results:
            return {"error": "No results found for your query."}

        # Extract information from the first result
        first_result = results[0]
        result_title = first_result.get('title')
        result_url = first_result.get('href')

        if not result_url:
            return {"error": "Could not extract URL from search result."}

        # Fetch and parse the content of the page
        content = get_page_content(result_url)

        if content.startswith("Error"):
             return {
                "operation": "search_and_fetch",
                "query": query,
                "error": content,
                "source_title": result_title,
                "source_url": result_url,
            }

        return {
            "operation": "search_and_fetch",
            "query": query,
            "result_title": result_title,
            "result_url": result_url,
            "content": content
        }

    except Exception as e:
        return {"error": f"An unexpected error occurred: {str(e)}"}


if __name__ == "__main__":
    # To run this server, you need to install the required libraries:
    # pip install fastmcp duckduckgo-search requests beautifulsoup4
    mcp.run()
