#!/usr/bin/env python3
"""
CSV/XLSX Analyzer MCP Server using FastMCP.
Detects numerical columns, generates basic statistical plots, and returns as Base64.
"""

import base64
import io
from typing import Any, Dict, Annotated

import pandas as pd
import matplotlib.pyplot as plt
from fastmcp import FastMCP

# Initialize the MCP server
mcp = FastMCP("CSV_XLSX_Analyzer")

@mcp.tool
def analyze_spreadsheet(
    instructions: Annotated[str, "Instructions for the tool, not used in this implementation"],
    filename: Annotated[str, "The name of the file (.csv or .xlsx)"],
    file_data_base64: Annotated[str, "LLM agent can leave blank. Do NOT fill. Framework will fill this."] = ""
) -> Dict[str, Any]:
    """
    Analyzes a spreadsheet (CSV or XLSX), detects numerical columns, and generates a plot.

    Args:
        instructions: Instructions for the tool (not used).
        filename: File name (must end in .csv or .xlsx).
        file_data_base64: Base64-encoded spreadsheet content.

    Returns:
        A dictionary with the operation result and a Base64-encoded PNG plot.
    """
    try:
        # Validate file extension
        ext = filename.lower().split('.')[-1]
        if ext not in ['csv', 'xlsx']:
            return {"error": "Invalid file type. Only .csv or .xlsx allowed."}

        # Decode file data
        decoded_bytes = base64.b64decode(file_data_base64)
        buffer = io.BytesIO(decoded_bytes)

        # Load dataframe
        if ext == 'csv':
            df = pd.read_csv(buffer)
        else:
            df = pd.read_excel(buffer)

        if df.empty:
            return {"error": "File is empty or has no readable content."}

        # Detect numerical columns
        num_cols = df.select_dtypes(include=['number']).columns.tolist()
        if not num_cols:
            return {"error": "No numerical columns found for plotting."}

        # Generate plot
        plt.figure(figsize=(8, 6))
        df[num_cols].hist(bins=20, figsize=(10, 8), grid=False)
        plt.tight_layout()

        # Save to buffer as PNG
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png')
        plt.close()
        img_buffer.seek(0)

        # Encode to Base64
        img_base64 = base64.b64encode(img_buffer.read()).decode('utf-8')
        img_buffer.close()

        # Create file list for multiple file support
        returned_files = [{
            'filename': "analysis_plot.png",
            'content_base64': img_base64
        }]
        returned_file_names = ["analysis_plot.png"]
        returned_file_contents = [img_base64]
        
        return {
            "operation": "spreadsheet_analysis",
            "filename": filename,
            "numerical_columns": num_cols,
            "returned_files": returned_files,
            "returned_file_names": returned_file_names,
            "returned_file_contents": returned_file_contents,
            # Backward compatibility
            "returned_file_name": "analysis_plot.png",
            "returned_file_base64": img_base64,
            "message": f"Detected numerical columns: {', '.join(num_cols)}. Histogram plot generated."
        }

    except Exception as e:
        # print traceback for debugging
        import traceback
        traceback.print_exc()
        return {"error": f"Spreadsheet analysis failed: {str(e)}"}

if __name__ == "__main__":
    print("Starting CSV/XLSX Analyzer MCP server...")
    mcp.run()
