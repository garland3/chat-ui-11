#!/usr/bin/env python3
"""
PDF Analyzer MCP Server using FastMCP.
Provides PDF text analysis and report generation through the MCP protocol.
"""

import base64
import io
import re
from collections import Counter
from typing import Any, Dict, Annotated

# This tool requires the PyPDF2 and reportlab libraries.
# Install them using: pip install PyPDF2 reportlab
from PyPDF2 import PdfReader
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch

from fastmcp import FastMCP

mcp = FastMCP("PDF_Analyzer")


def _analyze_pdf_content(instructions: str, filename: str, file_data_base64: str) -> Dict[str, Any]:
    """
    Core PDF analysis logic that can be reused by multiple tools.
    
    Args:
        instructions: Instructions for the tool, not used in this implementation.
        filename: The name of the file, which must have a '.pdf' extension.
        file_data_base64: The Base64-encoded string of the PDF file content.

    Returns:
        A dictionary containing the analysis results or an error message.
    """
    try:
        # print the instructions.
        print(f"Instructions: {instructions}")
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
        # print traceback for debugging
        import traceback
        traceback.print_exc()
        # 6. Return an error message if something goes wrong
        return {"error": f"PDF analysis failed: {str(e)}"}


@mcp.tool
def analyze_pdf(
    instructions: Annotated[str, "Instructions for the tool, not used in this implementation"],
    filename: Annotated[str, "The name of the file, which must have a '.pdf' extension"],
    file_data_base64: Annotated[str, "LLM agent can leave blank. Do NOT fill. This will be filled by the framework."] = ""
) -> Dict[str, Any]:
    """
    Analyzes the text content of a single PDF file.

    It calculates the total word count and determines the top 100 most
    frequently used words. The file content must be provided as a
    Base64 encoded string.

    Args:
        instructions: Instructions for the tool, not used in this implementation.
        filename: The name of the file, which must have a '.pdf' extension.
        file_data_base64: The Base64-encoded string of the PDF file content.

    Returns:
        A dictionary containing the analysis results or an error message.
    """
    return _analyze_pdf_content(instructions, filename, file_data_base64)


@mcp.tool
def generate_report_about_pdf(
    instructions: Annotated[str, "Instructions for the tool, not used in this implementation"],
    filename: Annotated[str, "The name of the file, which must have a '.pdf' extension"],
    file_data_base64: Annotated[str, "LLM agent can leave blank. Do NOT fill. This will be filled by the framework."] = ""
) -> Dict[str, Any]:
    """
    Analyzes a PDF, then generates and returns a new PDF report with the results.

    The report contains the total word count and the top 100 most frequent words.
    This tool returns a new file back to the user.

    Args:
        instructions: Instructions for the tool, not used in this implementation.
        filename: The name of the file to be analyzed.
        file_data_base_64: The Base64-encoded string of the PDF file content.

    Returns:
        A dictionary containing the new report's filename and its Base64-encoded data.
    """
    # --- 1. Perform the same analysis as the first function ---
    analysis_result = _analyze_pdf_content(instructions, filename, file_data_base64)
    if "error" in analysis_result:
        return analysis_result # Return the error if analysis failed

    # --- 2. Generate a PDF report from the analysis results ---
    try:
        buffer = io.BytesIO()
        # Create a canvas to draw on, using the buffer as the "file"
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter

        # Set up starting coordinates
        x = inch
        y = height - inch

        # Write title
        p.setFont("Helvetica-Bold", 16)
        p.drawString(x, y, f"Analysis Report for: {analysis_result['filename']}")
        y -= 0.5 * inch

        # Write summary
        p.setFont("Helvetica", 12)
        p.drawString(x, y, f"Total Word Count: {analysis_result['total_word_count']}")
        y -= 0.3 * inch

        # Write header for top words
        p.setFont("Helvetica-Bold", 12)
        p.drawString(x, y, "Top 100 Most Frequent Words:")
        y -= 0.25 * inch

        # Write the list of top words
        p.setFont("Helvetica", 10)
        col1_x, col2_x, col3_x, col4_x = x, x + 1.75*inch, x + 3.5*inch, x + 5.25*inch
        current_x = col1_x
        
        # Simple column layout
        count = 0
        for word, freq in analysis_result['top_100_words'].items():
            if y < inch: # New page if we run out of space
                p.showPage()
                p.setFont("Helvetica", 10)
                y = height - inch

            p.drawString(current_x, y, f"{word}: {freq}")
            
            # Move to the next column
            if count % 4 == 0: current_x = col2_x
            elif count % 4 == 1: current_x = col3_x
            elif count % 4 == 2: current_x = col4_x
            else: # Move to the next row
                current_x = col1_x
                y -= 0.2 * inch
            count += 1
            
        # Finalize the PDF
        p.save()
        
        # --- 3. Encode the generated PDF for return ---
        report_bytes = buffer.getvalue()
        buffer.close()
        report_base64 = base64.b64encode(report_bytes).decode('utf-8')

        # Create a new filename for the report
        report_filename = f"analysis_report_{filename.replace('.pdf', '.txt')}.pdf"

        # --- 4. Return the new file data ---
        # Create file list for multiple file support
        returned_files = [{
            'filename': report_filename,
            'content_base64': report_base64
        }]
        returned_file_names = [report_filename]
        returned_file_contents = [report_base64]
        
        return {
            "operation": "pdf_analysis_report",
            "original_filename": filename,
            "returned_files": returned_files,
            "returned_file_names": returned_file_names,
            "returned_file_contents": returned_file_contents,
            # Backward compatibility
            "returned_file_name": report_filename,
            "returned_file_base64": report_base64,
            "message": f"Successfully generated analysis report for {filename}."
        }

    except Exception as e:
        # print traceback for debugging
        import traceback
        traceback.print_exc()
        return {"error": f"Failed to generate PDF report: {str(e)}"}


if __name__ == "__main__":
    # This will start the server and listen for MCP requests.
    # To use it, you would run this script and then connect to it
    # with a FastMCP client.
    print("Starting PDF Analyzer MCP server with report generation...")
    mcp.run()
