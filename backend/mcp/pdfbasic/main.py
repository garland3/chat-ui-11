#!/usr/bin/env python3
"""
PDF Analyzer MCP Server using FastMCP.
Provides PDF text analysis through the MCP protocol.
"""

import base64
import io
import re
from collections import Counter
from typing import Any, Dict

# This tool requires the PyPDF2 library.
# Install it using: pip install PyPDF2
from PyPDF2 import PdfReader

from fastmcp import FastMCP

# Initialize the MCP server
mcp = FastMCP("PDF_Analyzer")


@mcp.tool
def analyze_pdf(filename: str, file_data_base64: str) -> Dict[str, Any]:
    """
    Analyzes the text content of a single PDF file.

    It calculates the total word count and determines the top 100 most
    frequently used words. The file content must be provided as a
    Base64 encoded string.

    Args:
        filename: The name of the file, which must have a '.pdf' extension.
        file_data_base64: The Base64-encoded string of the PDF file content.

    Returns:
        A dictionary containing the analysis results or an error message.
    """
    try:
        # 1. Validate that the filename is for a PDF
        if not filename.lower().endswith('.pdf'):
            return {"error": "Invalid file type. This tool only accepts PDF files."}

        # 2. Decode the Base64 data and read the PDF content
        decoded_bytes = base64.b64decode(file_data_base64)
        pdf_stream = io.BytesIO(decoded_bytes)
        reader = PdfReader(pdf_stream)

        full_text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                full_text += page_text + "\n"

        if not full_text.strip():
            return {
                "operation": "pdf_analysis",
                "filename": filename,
                "status": "Success",
                "message": "PDF contained no extractable text.",
                "total_word_count": 0,
                "top_100_words": {}
            }

        # 3. Process the text to get a word list and count
        # This regex finds all word-like sequences, ignoring case
        words = re.findall(r'\b\w+\b', full_text.lower())
        total_word_count = len(words)

        # 4. Count word frequencies and get the top 100
        word_counts = Counter(words)
        # Convert list of (word, count) tuples to a dictionary
        top_100_words_dict = dict(word_counts.most_common(100))

        # 5. Return the successful result
        return {
            "operation": "pdf_analysis",
            "filename": filename,
            "total_word_count": total_word_count,
            "top_100_words": top_100_words_dict
        }

    except Exception as e:
        return {"error": f"PDF analysis failed: {str(e)}"}


if __name__ == "__main__":
    # This will start the server and listen for MCP requests.
    # To use it, you would run this script and then connect to it
    # with a FastMCP client.
    print("Starting PDF Analyzer MCP server...")
    mcp.run()