#!/usr/bin/env python3
"""
Secure Code Execution MCP Server using FastMCP
Provides safe Python code execution with security controls.
"""

import base64
import logging
import time
import traceback
from pathlib import Path
from typing import Any, Dict, List, Annotated, Optional

from fastmcp import FastMCP

# Import from modular components
from .security_checker import check_code_security
from .execution_environment import CodeExecutionError, create_execution_environment, save_file_to_execution_dir
from .script_generation import create_safe_execution_script
from .execution_engine import execute_code_safely
from .result_processing import (
    detect_matplotlib_plots,
    create_visualization_html,
    list_generated_files,
    encode_generated_files,
    truncate_output_for_llm
)

# Configure logging to use main app log with prefix
main_log_path = 'logs/app.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - CODE_EXECUTOR - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(main_log_path),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize the MCP server
mcp = FastMCP("SecureCodeExecutor")


# Security checking functionality moved to security_checker.py


# Execution environment functionality moved to execution_environment.py


# Script generation functionality moved to script_generation.py


# Execution engine functionality moved to execution_engine.py


# Result processing functionality moved to result_processing.py


# Cleanup functionality moved to execution_environment.py


# File saving functionality moved to execution_environment.py


@mcp.tool
def execute_python_code_with_file(
    code: Annotated[str, "Python code to execute"],
    filename: Annotated[str, "Name of the file to make available to the code (optional - leave empty if not uploading a file)"] = "",
    file_data_base64: Annotated[str, "LLM agent can leave blank. Do NOT fill. This will be filled by the framework."] = ""
) -> Dict[str, Any]:
    """
    Safely execute Python code in an isolated environment with optional file upload.

    This function allows you to execute Python code either standalone or with access 
    to an uploaded file (e.g., CSV, JSON, TXT, etc.). If a file is provided, it will 
    be available in the execution directory and can be accessed by filename in your code.

    IMPORTANT - Output Truncation:
        - Console output (print statements, etc.) is limited to 2000 characters in LLM context.
        - If output exceeds this limit, it will be truncated with a warning message.
        - Full output is always available in generated downloadable files.
        - Large data should be saved to files rather than printed to console.
        - Use plt.savefig() for plots - they will be displayed separately from text output.

    Constraints:
        - Only a limited set of safe modules are allowed (e.g., numpy, pandas, matplotlib, seaborn, json, csv, math, etc.).
        - Imports of dangerous or unauthorized modules (e.g., os, sys, subprocess, socket, requests, pickle, threading, etc.) are blocked.
        - Dangerous built-in functions (e.g., eval, exec, compile, __import__, getattr, setattr, input, exit, quit, etc.) are forbidden.
        - File I/O is restricted to the execution directory, with read-only access to matplotlib/seaborn config files for plotting.
        - Matplotlib and seaborn plotting is fully supported - you MUST use plt.savefig() to create plot files (plt.show() will not work).
        - Attribute access to __builtins__ and double-underscore attributes is forbidden.
        - Code is executed in a temporary, isolated directory that is cleaned up after execution.
        - Execution is time-limited (default: 30 seconds).
        - Supports data analysis, visualization, and basic Python operations in a secure sandbox.

    Example usage:
        If you upload a file named "data.csv", you can access it in your code like:
        ```python
        import pandas as pd
        import matplotlib.pyplot as plt
        
        df = pd.read_csv('data.csv')
        print(df.head())  # This will be truncated if very large
        
        # For large datasets, save to file instead of printing
        df.describe().to_csv('summary.csv')  # Better approach for large output
        print(f"Dataset has {len(df)} rows")  # Concise summary instead
        
        # Create plots - MUST use plt.savefig() to generate plot files
        plt.figure(figsize=(10, 6))
        plt.plot(df['column_name'])
        plt.title('My Plot')
        plt.savefig('my_plot.png')  # REQUIRED - plt.show() won't work in this environment
        plt.close()  # Good practice to close figures
        ```

    Args:
        code: Python code to execute (string)
        filename: Name of the file to upload
        file_data_base64: Base64-encoded file data (automatically filled by framework)
        
        Returns (MCP Contract):
                {
                    "results": <primary result payload or {"error": msg}>,
                    "meta_data": {<small supplemental info incl. timings / flags>},
                    "returned_file_names": [...optional...],
                    "returned_file_contents": [...base64 contents matching names order...]
                }
    """
    start_time = time.time()
    exec_dir: Optional[Path] = None
    try:
        # Log basic invocation context (do not log full base64 file data)
        logger.info(
            "Code executor start: filename=%s has_file_data=%s code_chars=%d",
            filename or None,
            bool(file_data_base64),
            len(code)
        )

        # 1. Security check
        violations = check_code_security(code)
        if violations:
            return {
                "results": {"error": "Security violations detected", "violations": violations},
                "meta_data": {"is_error": True, "execution_time_sec": 0}
            }

        # 2. Environment setup
        exec_dir = create_execution_environment()

        # 3. Optional uploaded file
        saved_filename = None
        if filename and file_data_base64:
            try:
                saved_filename = save_file_to_execution_dir(filename, file_data_base64, exec_dir)
            except ValueError as ve:
                return {
                    "results": {"error": str(ve)},
                    "meta_data": {"is_error": True, "execution_time_sec": round(time.time() - start_time, 4)}
                }
        elif filename and not file_data_base64:
            logger.warning("Filename provided without file data; proceeding without file")
        elif file_data_base64 and not filename:
            logger.warning("File data provided without filename; ignoring data")

        # 4. Create script & execute
        script_path = create_safe_execution_script(code, exec_dir)
        execution_result = execute_code_safely(script_path, timeout=30)
        execution_time = time.time() - start_time

        # Helper to build script artifact (always produced)
        if filename:
            script_content = f"""# Code Analysis Script\n# Generated by Secure Code Executor\n# Original file: {filename}\n\n{code}\n"""
            script_filename = f"analysis_code_{filename.replace('.', '_')}.py"
        else:
            script_content = f"""# Code Execution Script\n# Generated by Secure Code Executor\n\n{code}\n"""
            script_filename = "generated_code.py"
        script_base64 = base64.b64encode(script_content.encode("utf-8")).decode("utf-8")

        if execution_result.get("success"):
            # Gather artifacts
            generated_files = list_generated_files(exec_dir)
            encoded_generated_files = encode_generated_files(exec_dir)
            plots = detect_matplotlib_plots(exec_dir)

            raw_output = execution_result.get("stdout", "")
            truncated_output, _ = truncate_output_for_llm(raw_output)

            # Visualization HTML (optional)
            returned_files: List[Dict[str, str]] = [{"filename": script_filename, "content_base64": script_base64}]
            html_filename = None
            if plots or raw_output.strip():
                try:
                    visualization_html = create_visualization_html(plots, raw_output)
                    html_filename = f"execution_results_{int(time.time())}.html"
                    html_content_b64 = base64.b64encode(visualization_html.encode("utf-8")).decode("utf-8")
                    returned_files.append({
                        "filename": html_filename,
                        "content_base64": html_content_b64
                    })
                except Exception as html_err:  # noqa: BLE001
                    logger.warning(f"Failed to generate visualization HTML: {html_err}")
            # Add other generated files
            returned_files.extend(encoded_generated_files)

            # Convert to v2 artifacts format
            artifacts = []
            for file_info in returned_files:
                filename = file_info["filename"]
                content_b64 = file_info["content_base64"]
                
                # Determine MIME type based on file extension
                if filename.endswith('.html'):
                    mime_type = "text/html"
                    viewer = "html"
                elif filename.endswith('.py'):
                    mime_type = "text/x-python"
                    viewer = "code"
                elif filename.endswith('.png'):
                    mime_type = "image/png"
                    viewer = "image"
                elif filename.endswith('.jpg') or filename.endswith('.jpeg'):
                    mime_type = "image/jpeg"
                    viewer = "image"
                elif filename.endswith('.txt'):
                    mime_type = "text/plain"
                    viewer = "code"
                else:
                    mime_type = "application/octet-stream"
                    viewer = "auto"
                
                # Calculate size from base64
                try:
                    size = len(base64.b64decode(content_b64))
                except:
                    size = 0
                
                artifacts.append({
                    "name": filename,
                    "b64": content_b64,
                    "mime": mime_type,
                    "size": size,
                    "description": f"Generated from code execution: {filename}",
                    "viewer": viewer
                })

            results_payload: Dict[str, Any] = {
                "summary": "Execution completed successfully",
                "stdout": truncated_output,
            }
            if execution_result.get("stderr"):
                stderr_val = execution_result.get("stderr", "")
                if len(stderr_val) > 800:
                    results_payload["stderr"] = stderr_val[:800] + "... [truncated]"
                    results_payload["stderr_truncated"] = True
                else:
                    results_payload["stderr"] = stderr_val
            if saved_filename:
                results_payload["uploaded_file"] = saved_filename

            meta_data = {
                "execution_time_sec": round(execution_time, 4),
                "generated_file_count": len(artifacts),
                "has_plots": bool(plots),
                "is_error": False
            }
            
            # Determine primary file for display (prefer HTML visualization)
            primary_file = None
            if html_filename:
                primary_file = html_filename
            elif artifacts:
                primary_file = artifacts[0]["name"]
            
            return {
                "results": results_payload,
                "meta_data": meta_data,
                "artifacts": artifacts,
                "display": {
                    "open_canvas": True,
                    "primary_file": primary_file,
                    "mode": "replace",
                    "viewer_hint": "html" if html_filename else "auto"
                }
            }
        else:
            # Failure path
            returned_files = [{"filename": script_filename, "content_base64": script_base64}]
            returned_file_names = [script_filename]
            returned_file_contents = [script_base64]
            raw_output = execution_result.get("stdout", "")
            truncated_output, _ = truncate_output_for_llm(raw_output)
            error_msg = execution_result.get("error", "Unknown execution error")
            results_payload = {
                "error": error_msg,
                "stdout": truncated_output
            }
            if execution_result.get("stderr"):
                stderr_val = execution_result.get("stderr", "")
                if len(stderr_val) > 800:
                    results_payload["stderr"] = stderr_val[:800] + "... [truncated]"
                    results_payload["stderr_truncated"] = True
                else:
                    results_payload["stderr"] = stderr_val
            meta_data = {
                "is_error": True,
                "error_type": execution_result.get("error_type"),
                "execution_time_sec": round(execution_time, 4)
            }
            # Convert failure to v2 format
            artifacts = [{
                "name": script_filename,
                "b64": script_base64,
                "mime": "text/x-python",
                "size": len(script_content.encode("utf-8")),
                "description": f"Failed execution script: {script_filename}",
                "viewer": "code"
            }]
            
            return {
                "results": results_payload,
                "meta_data": meta_data,
                "artifacts": artifacts,
                "display": {
                    "open_canvas": False,  # Don't auto-open on failure
                    "primary_file": script_filename,
                    "mode": "replace",
                    "viewer_hint": "code"
                }
            }
    except CodeExecutionError as ce:  # Specific controlled errors
        exec_time = round(time.time() - start_time, 4)
        logger.error(f"Code execution error: {ce}")
        # Provide minimal artifact (script)
        if filename:
            script_content = f"""# Code Analysis Script\n# Generated by Secure Code Executor\n# Original file: {filename}\n\n{code}\n"""
            script_filename = f"analysis_code_{filename.replace('.', '_')}.py"
        else:
            script_content = f"""# Code Execution Script\n# Generated by Secure Code Executor\n\n{code}\n"""
            script_filename = "generated_code.py"
        script_base64 = base64.b64encode(script_content.encode("utf-8")).decode("utf-8")
        # Convert exception to v2 format
        artifacts = [{
            "name": script_filename,
            "b64": script_base64,
            "mime": "text/x-python",
            "size": len(script_content.encode("utf-8")),
            "description": f"Script that caused execution error: {script_filename}",
            "viewer": "code"
        }]
        
        return {
            "results": {"error": f"Code execution error: {str(ce)}"},
            "meta_data": {"is_error": True, "error_type": "CodeExecutionError", "execution_time_sec": exec_time},
            "artifacts": artifacts,
            "display": {
                "open_canvas": False,  # Don't auto-open on error
                "primary_file": script_filename,
                "mode": "replace",
                "viewer_hint": "code"
            }
        }
    except Exception as e:  # Catch-all
        exec_time = round(time.time() - start_time, 4)
        logger.error(f"Unexpected server error: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        if filename:
            script_content = f"""# Code Analysis Script\n# Generated by Secure Code Executor\n# Original file: {filename}\n\n{code}\n"""
            script_filename = f"analysis_code_{filename.replace('.', '_')}.py"
        else:
            script_content = f"""# Code Execution Script\n# Generated by Secure Code Executor\n\n{code}\n"""
            script_filename = "generated_code.py"
        script_base64 = base64.b64encode(script_content.encode("utf-8")).decode("utf-8")
        # Convert general exception to v2 format
        artifacts = [{
            "name": script_filename,
            "b64": script_base64,
            "mime": "text/x-python",
            "size": len(script_content.encode("utf-8")),
            "description": f"Script that caused server error: {script_filename}",
            "viewer": "code"
        }]
        
        return {
            "results": {"error": f"Server error: {str(e)}"},
            "meta_data": {"is_error": True, "error_type": type(e).__name__, "execution_time_sec": exec_time},
            "artifacts": artifacts,
            "display": {
                "open_canvas": False,  # Don't auto-open on error
                "primary_file": script_filename,
                "mode": "replace",
                "viewer_hint": "code"
            }
        }
    
    # finally:
    #     # Clean up execution environment
    #     if exec_dir:
    #         cleanup_execution_environment(exec_dir)

if __name__ == "__main__":
    mcp.run()
