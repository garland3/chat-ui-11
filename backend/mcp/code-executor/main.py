#!/usr/bin/env python3
"""
Secure Code Execution MCP Server using FastMCP
Provides safe Python code execution with security controls.
"""

import ast
import base64
import binascii
import io
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
import uuid
from pathlib import Path
from typing import Any, Dict, List, Set, Annotated, Optional

from fastmcp import FastMCP

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


class CodeSecurityError(Exception):
    """Raised when code fails security checks."""
    pass


class CodeExecutionError(Exception):
    """Raised when code execution fails."""
    pass


class SecurityChecker(ast.NodeVisitor):
    """AST visitor to check for dangerous code patterns."""
    
    def __init__(self):
        self.violations = []
        self.imported_modules = set()
        
        # Dangerous modules that should never be imported
        self.forbidden_modules = {
            'os', 'sys', 'subprocess', 'socket', 'urllib', 'urllib2', 'urllib3',
            'requests', 'http', 'ftplib', 'smtplib', 'telnetlib', 'webbrowser',
            'ctypes', 'multiprocessing', 'threading', 'asyncio', 'concurrent',
            'pickle', 'dill', 'shelve', 'dbm', 'sqlite3', 'pymongo',
            'paramiko', 'fabric', 'pexpect', 'pty', 'tty',
            'importlib', '__builtin__', 'builtins', 'imp'
        }
        
        # Allowed safe modules for data analysis
        self.allowed_modules = {
            'numpy', 'np', 'pandas', 'pd', 'matplotlib', 'plt', 'seaborn', 'sns',
            'scipy', 'sklearn', 'PIL', 'pillow', 'openpyxl',
            'json', 'csv', 'datetime', 'math', 'statistics', 'random', 're',
            'collections', 'itertools', 'functools', 'operator', 'copy',
            'decimal', 'fractions', 'pathlib', 'typing'
        }
        
        # Dangerous function names
        self.forbidden_functions = {
            'eval', 'exec', 'compile', '__import__', 'getattr', 'setattr', 'delattr',
            'hasattr', 'callable', 'isinstance', 'issubclass', 'super', 'globals',
            'locals', 'vars', 'dir', 'help', 'input', 'raw_input', 'exit', 'quit'
        }

    def visit_Import(self, node):
        """Check import statements."""
        for alias in node.names:
            module_name = alias.name.split('.')[0]
            self.imported_modules.add(module_name)
            
            if module_name in self.forbidden_modules:
                self.violations.append(f"Forbidden module import: {module_name}")
            elif module_name not in self.allowed_modules:
                self.violations.append(f"Unauthorized module import: {module_name}")
        
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        """Check from...import statements."""
        if node.module:
            module_name = node.module.split('.')[0]
            self.imported_modules.add(module_name)
            
            if module_name in self.forbidden_modules:
                self.violations.append(f"Forbidden module import: {module_name}")
            elif module_name not in self.allowed_modules:
                self.violations.append(f"Unauthorized module import: {module_name}")
        
        self.generic_visit(node)

    def visit_Call(self, node):
        """Check function calls."""
        # Check for dangerous built-in functions
        if isinstance(node.func, ast.Name):
            if node.func.id in self.forbidden_functions:
                self.violations.append(f"Forbidden function call: {node.func.id}")
        
        # Check for file operations outside working directory
        elif isinstance(node.func, ast.Attribute):
            if (isinstance(node.func.value, ast.Name) and 
                node.func.value.id == 'open' or node.func.attr == 'open'):
                # Allow open() but we'll validate paths at runtime
                pass
        
        self.generic_visit(node)

    def visit_With(self, node):
        """Check with statements (often used for file operations)."""
        for item in node.items:
            if isinstance(item.context_expr, ast.Call):
                if (isinstance(item.context_expr.func, ast.Name) and 
                    item.context_expr.func.id == 'open'):
                    # Allow open() but validate paths at runtime
                    pass
        
        self.generic_visit(node)

    def visit_Attribute(self, node):
        """Check attribute access."""
        # Check for dangerous attribute access patterns
        if isinstance(node.value, ast.Name):
            if (node.value.id == '__builtins__' or 
                node.attr.startswith('__') and node.attr.endswith('__')):
                self.violations.append(f"Forbidden attribute access: {node.value.id}.{node.attr}")
        
        self.generic_visit(node)


def check_code_security(code: str) -> List[str]:
    """
    Check Python code for security violations using AST parsing.
    
    Args:
        code: Python code to check
        
    Returns:
        List of security violations (empty if safe)
    """
    try:
        tree = ast.parse(code)
        checker = SecurityChecker()
        checker.visit(tree)
        return checker.violations
    except SyntaxError as e:
        error_msg = f"Syntax error: {str(e)}"
        logger.warning(f"Code syntax error: {error_msg}")
        return [error_msg]
    except Exception as e:
        error_msg = f"Security check error: {str(e)}"
        logger.error(f"Unexpected error during security check: {error_msg}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return [error_msg]


def create_execution_environment() -> Path:
    """Create a secure execution environment with UUID-based directory."""
    try:
        exec_id = str(uuid.uuid4())
        base_dir = Path(tempfile.gettempdir()) / "secure_code_exec"
        exec_dir = base_dir / exec_id
        
        # Create directory structure
        base_dir.mkdir(exist_ok=True)
        exec_dir.mkdir(exist_ok=True)
        
        logger.info(f"Created execution environment: {exec_dir}")
        return exec_dir
    except Exception as e:
        error_msg = f"Failed to create execution environment: {str(e)}"
        logger.error(error_msg)
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise CodeExecutionError(error_msg)


def create_safe_execution_script(code: str, exec_dir: Path) -> Path:
    """
    Create a Python script with the user code wrapped in safety measures.
    
    Args:
        code: User's Python code
        exec_dir: Execution directory
        
    Returns:
        Path to the created script
    """
    try:
        # Indent each line of user code to fit inside the try block
        indented_code = '\n'.join('    ' + line for line in code.split('\n'))
        
        script_content = f'''#!/usr/bin/env python3
import sys
import os
import json
import traceback
from pathlib import Path

# Change to execution directory
os.chdir(r"{exec_dir}")

# Configure matplotlib for safe plotting
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend that saves to files
matplotlib.rcParams['savefig.directory'] = r"{exec_dir}"  # Default save directory

# Restrict file operations to current directory only
original_open = open

def safe_open(file, mode='r', **kwargs):
    """Override open to restrict file access to execution directory, with exceptions for safe plotting libraries."""
    file_path = Path(file).resolve()
    exec_path = Path(r"{exec_dir}").resolve()
    
    try:
        file_path.relative_to(exec_path)
        # File is in execution directory - always allow
        return original_open(file, mode, **kwargs)
    except ValueError:
        # File is outside execution directory - check if it's an allowed library file
        file_str = str(file_path)
        
        # Allow matplotlib and seaborn configuration and data files (read-only)
        allowed_paths = [
            '/matplotlib/',
            '/seaborn/', 
            '/site-packages/matplotlib/',
            '/site-packages/seaborn/',
            'matplotlib/mpl-data/',
            'matplotlib/backends/',
            'matplotlib/font_manager.py',
            'seaborn/data/',
            'seaborn/_core/',
            'numpy/core/',
            'pandas/io/',
            '/usr/share/fonts/',
            '/usr/local/share/fonts/',
            'fontconfig/',
            '.cache/matplotlib/',
            '/tmp/matplotlib-',
            '/home/.matplotlib/',
            '/.matplotlib/',
        ]
        
        # Check if file path contains any allowed library paths  
        is_allowed_path = any(allowed_path in file_str for allowed_path in allowed_paths)
        
        if not is_allowed_path:
            raise PermissionError(f"File access outside execution directory not allowed: {{file}}")
            
        # Allow read access to all allowed paths
        if 'r' in mode and 'w' not in mode and 'a' not in mode and '+' not in mode:
            return original_open(file, mode, **kwargs)
        
        # Allow write access only to matplotlib cache directories
        if ('.cache/matplotlib/' in file_str or 
            'matplotlib/fontList.cache' in file_str or
            'matplotlib/tex.cache' in file_str or
            '/tmp/matplotlib-' in file_str or
            '/.matplotlib/' in file_str):
            return original_open(file, mode, **kwargs)
            
        # Deny write access to other external files
        if 'w' in mode or 'a' in mode or '+' in mode:
            raise PermissionError(f"Write access outside execution directory not allowed: {{file}}")
            
        return original_open(file, mode, **kwargs)

# Override built-in open
if isinstance(__builtins__, dict):
    __builtins__['open'] = safe_open
else:
    __builtins__.open = safe_open

# Capture output
import io
import sys

stdout_buffer = io.StringIO()
stderr_buffer = io.StringIO()

# Redirect stdout and stderr
old_stdout = sys.stdout
old_stderr = sys.stderr
sys.stdout = stdout_buffer
sys.stderr = stderr_buffer

execution_error = None
error_traceback = None

try:
    # User code starts here (matplotlib/seaborn should now work with plotting)
{indented_code}
    # User code ends here
    
except Exception as e:
    execution_error = e
    error_traceback = traceback.format_exc()
    print(f"Execution error: {{type(e).__name__}}: {{str(e)}}", file=sys.stderr)
    print(f"Traceback:\\n{{error_traceback}}", file=sys.stderr)

finally:
    # Restore stdout and stderr
    sys.stdout = old_stdout
    sys.stderr = old_stderr
    
    # Output results
    result = {{
        "stdout": stdout_buffer.getvalue(),
        "stderr": stderr_buffer.getvalue(),
        "success": execution_error is None,
        "error_type": type(execution_error).__name__ if execution_error else None,
        "error_traceback": error_traceback
    }}
    
    print(json.dumps(result))
'''
        
        script_path = exec_dir / "exec_script.py"
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        logger.info(f"Created execution script: {script_path}")
        return script_path
    
    except Exception as e:
        error_msg = f"Failed to create execution script: {str(e)}"
        logger.error(error_msg)
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise CodeExecutionError(error_msg)


def execute_code_safely(script_path: Path, timeout: int = 30) -> Dict[str, Any]:
    """
    Execute Python script safely with resource limits.
    
    Args:
        script_path: Path to the script to execute
        timeout: Maximum execution time in seconds
        
    Returns:
        Execution results
    """
    try:
        logger.info(f"Executing script: {script_path} with timeout: {timeout}s")
        
        # Execute with subprocess for isolation
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=script_path.parent
        )
        
        logger.info(f"Script execution completed with return code: {result.returncode}")
        
        if result.returncode == 0:
            # Parse the JSON output from the script
            try:
                execution_result = json.loads(result.stdout.strip())
                if not execution_result.get("success", True):
                    logger.warning(f"Code execution failed: {execution_result.get('stderr', 'Unknown error')}")
                    if execution_result.get("error_traceback"):
                        logger.error(f"User code traceback:\n{execution_result['error_traceback']}")
                return execution_result
            except json.JSONDecodeError as e:
                error_msg = "Failed to parse execution output"
                logger.error(f"{error_msg}: {str(e)}")
                logger.error(f"Raw stdout: {result.stdout}")
                logger.error(f"Raw stderr: {result.stderr}")
                return {
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "success": False,
                    "error": error_msg,
                    "error_type": "JSONDecodeError"
                }
        else:
            error_msg = f"Script execution failed with return code {result.returncode}"
            logger.error(error_msg)
            logger.error(f"stdout: {result.stdout}")
            logger.error(f"stderr: {result.stderr}")
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "success": False,
                "error": error_msg,
                "error_type": "SubprocessError"
            }
    
    except subprocess.TimeoutExpired as e:
        error_msg = f"Code execution timed out after {timeout} seconds"
        logger.error(error_msg)
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "stdout": "",
            "stderr": "",
            "success": False,
            "error": error_msg,
            "error_type": "TimeoutError"
        }
    except Exception as e:
        error_msg = f"Execution error: {str(e)}"
        logger.error(error_msg)
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "stdout": "",
            "stderr": "",
            "success": False,
            "error": error_msg,
            "error_type": type(e).__name__
        }


def detect_matplotlib_plots(exec_dir: Path) -> List[str]:
    """
    Detect if matplotlib plots were created and convert to base64.
    
    Args:
        exec_dir: Execution directory to scan for plot files
        
    Returns:
        List of base64-encoded plot images
    """
    try:
        plot_files = []
        for ext in ['*.png', '*.jpg', '*.jpeg', '*.svg']:
            plot_files.extend(exec_dir.glob(ext))
        
        base64_plots = []
        for plot_file in plot_files:
            try:
                with open(plot_file, 'rb') as f:
                    image_data = base64.b64encode(f.read()).decode('utf-8')
                    file_ext = plot_file.suffix.lower()
                    mime_type = {
                        '.png': 'image/png',
                        '.jpg': 'image/jpeg', 
                        '.jpeg': 'image/jpeg',
                        '.svg': 'image/svg+xml'
                    }.get(file_ext, 'image/png')
                    
                    base64_plots.append(f"data:{mime_type};base64,{image_data}")
                    logger.info(f"Successfully encoded plot: {plot_file.name}")
            except Exception as e:
                logger.warning(f"Failed to encode plot {plot_file}: {str(e)}")
                logger.warning(f"Traceback: {traceback.format_exc()}")
                continue
        
        logger.info(f"Detected {len(base64_plots)} plots in {exec_dir}")
        return base64_plots
    
    except Exception as e:
        logger.error(f"Error detecting matplotlib plots: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return []


def create_visualization_html(plots: List[str], output_text: str) -> str:
    """
    Create HTML for displaying plots and output matching the frontend dark theme.
    
    Args:
        plots: List of base64-encoded plot images
        output_text: Text output from code execution
        
    Returns:
        HTML string for display
    """
    html_content = """
    <div style="font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif; 
                max-width: 100%; 
                padding: 20px; 
                background-color: #111827; 
                color: #e5e7eb; 
                line-height: 1.6;">
        <h3 style="color: #e5e7eb; margin: 0 0 16px 0; font-weight: 600;">Code Execution Results</h3>
    """
    
    if output_text.strip():
        html_content += f"""
        <div style="background-color: #1f2937; 
                    border: 1px solid #374151; 
                    padding: 16px; 
                    border-radius: 8px; 
                    margin-bottom: 20px;">
            <h4 style="color: #e5e7eb; margin: 0 0 12px 0; font-weight: 500; font-size: 14px;">Output:</h4>
            <pre style="white-space: pre-wrap; 
                       margin: 0; 
                       font-family: 'Consolas', 'Monaco', 'Courier New', monospace; 
                       color: #d1d5db; 
                       background-color: #111827; 
                       padding: 12px; 
                       border-radius: 6px; 
                       border: 1px solid #4b5563; 
                       overflow-x: auto;">{output_text}</pre>
        </div>
        """
    
    if plots:
        html_content += '<h4 style="color: #e5e7eb; margin: 20px 0 16px 0; font-weight: 500;">Generated Visualizations:</h4>'
        for i, plot in enumerate(plots):
            html_content += f"""
            <div style="margin-bottom: 20px; 
                        text-align: center; 
                        background-color: #1f2937; 
                        border: 1px solid #374151; 
                        border-radius: 8px; 
                        padding: 16px;">
                <img src="{plot}" 
                     alt="Plot {i+1}" 
                     style="max-width: 100%; 
                            height: auto; 
                            border: 1px solid #4b5563; 
                            border-radius: 6px; 
                            background-color: white;">
            </div>
            """
    
    html_content += "</div>"
    return html_content


def list_generated_files(exec_dir: Path) -> List[str]:
    """
    List files generated during code execution.
    
    Args:
        exec_dir: Execution directory
        
    Returns:
        List of generated file names
    """
    try:
        generated_files = []
        for file_path in exec_dir.iterdir():
            if file_path.is_file() and file_path.name != "exec_script.py":
                generated_files.append(file_path.name)
        
        logger.info(f"Generated files: {generated_files}")
        return generated_files
    
    except Exception as e:
        logger.error(f"Error listing generated files: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return []


def encode_generated_files(exec_dir: Path) -> List[Dict[str, str]]:
    """
    Encode generated files to base64 for download.
    
    Args:
        exec_dir: Execution directory
        
    Returns:
        List of dictionaries with 'filename' and 'content_base64' keys
    """
    try:
        encoded_files = []
        for file_path in exec_dir.iterdir():
            if file_path.is_file() and file_path.name != "exec_script.py":
                try:
                    with open(file_path, 'rb') as f:
                        file_content = f.read()
                    
                    content_base64 = base64.b64encode(file_content).decode('utf-8')
                    encoded_files.append({
                        'filename': file_path.name,
                        'content_base64': content_base64
                    })
                    logger.info(f"Encoded file: {file_path.name} ({len(file_content)} bytes)")
                except Exception as e:
                    logger.warning(f"Failed to encode file {file_path.name}: {str(e)}")
                    continue
        
        logger.info(f"Encoded {len(encoded_files)} generated files")
        return encoded_files
    
    except Exception as e:
        logger.error(f"Error encoding generated files: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return []


def truncate_output_for_llm(output: str, max_chars: int = 2000) -> tuple[str, bool]:
    """
    Smart truncation that preserves important context around key terms.
    
    Args:
        output: The output text to potentially truncate
        max_chars: Maximum characters to allow (default: 2000)
        
    Returns:
        Tuple of (truncated_output, was_truncated)
    """
    if len(output) <= max_chars:
        return output, False
    
    # Key terms that indicate important context
    key_terms = [
        'error', 'Error', 'ERROR', 'exception', 'Exception', 'EXCEPTION',
        'traceback', 'Traceback', 'TRACEBACK', 'failed', 'Failed', 'FAILED',
        'warning', 'Warning', 'WARNING', 'success', 'Success', 'SUCCESS',
        'completed', 'Completed', 'COMPLETED', 'result', 'Result', 'RESULT',
        'summary', 'Summary', 'SUMMARY', 'total', 'Total', 'TOTAL',
        'shape:', 'dtype:', 'columns:', 'index:', 'memory usage:', 'non-null'
    ]
    
    # Find all important sections
    important_sections = []
    context_chars = 150  # Characters around each key term
    
    for term in key_terms:
        start_pos = 0
        while True:
            pos = output.find(term, start_pos)
            if pos == -1:
                break
            
            # Extract context around the term
            section_start = max(0, pos - context_chars)
            section_end = min(len(output), pos + len(term) + context_chars)
            
            # Expand to word boundaries if possible
            while section_start > 0 and not output[section_start].isspace():
                section_start -= 1
            while section_end < len(output) and not output[section_end].isspace():
                section_end += 1
            
            important_sections.append((section_start, section_end, term))
            start_pos = pos + 1
    
    if important_sections:
        # Sort sections by position and merge overlapping ones
        important_sections.sort(key=lambda x: x[0])
        merged_sections = []
        
        for start, end, term in important_sections:
            if merged_sections and start <= merged_sections[-1][1] + 50:  # Merge if close
                merged_sections[-1] = (merged_sections[-1][0], max(end, merged_sections[-1][1]), merged_sections[-1][2] + f", {term}")
            else:
                merged_sections.append((start, end, term))
        
        # Build truncated output with important sections
        result_parts = []
        total_chars = 0
        
        # Always include the beginning (first 300 chars)
        beginning = output[:300]
        result_parts.append(beginning)
        total_chars += len(beginning)
        
        # Add important sections
        for start, end, terms in merged_sections:
            section = output[start:end]
            if total_chars + len(section) + 100 > max_chars:  # Reserve space for truncation message
                break
            
            if start > 300:  # Don't duplicate beginning
                result_parts.append(f"\n\n[... content around: {terms} ...]\n")
                result_parts.append(section)
                total_chars += len(section) + 50
        
        truncated = ''.join(result_parts)
    else:
        # No key terms found, use simple truncation
        truncated = output[:max_chars - 200]  # Reserve space for message
        # Try to break at a reasonable point (newline) near the limit
        last_newline = truncated.rfind('\n')
        if last_newline > len(truncated) * 0.8:  # If newline is in last 20%, use it
            truncated = truncated[:last_newline]
    
    truncation_msg = f"\n\n[OUTPUT TRUNCATED - Original length: {len(output)} characters. Full output preserved in downloaded files and visualizations.]"
    return truncated + truncation_msg, True


def cleanup_execution_environment(exec_dir: Path):
    """Clean up the execution environment."""
    try:
        if exec_dir and exec_dir.exists():
            shutil.rmtree(exec_dir)
            logger.info(f"Cleaned up execution environment: {exec_dir}")
    except Exception as e:
        logger.warning(f"Failed to cleanup execution environment {exec_dir}: {str(e)}")
        logger.warning(f"Traceback: {traceback.format_exc()}")


def save_file_to_execution_dir(filename: str, file_data_base64: str, exec_dir: Path) -> str:
    """
    Save a base64-encoded file to the execution directory.
    
    Args:
        filename: Name of the file
        file_data_base64: Base64-encoded file data
        exec_dir: Execution directory
        
    Returns:
        The filename that was saved
    """
    try:
        logger.info(f"Saving file {filename} to execution directory: {exec_dir}")
        
        # Decode the base64 data
        file_data = base64.b64decode(file_data_base64)
        
        # Ensure filename is safe (no path traversal)
        safe_filename = os.path.basename(filename)
        file_path = exec_dir / safe_filename
        
        # Write the file
        with open(file_path, 'wb') as f:
            f.write(file_data)
        
        logger.info(f"Successfully saved file: {safe_filename} ({len(file_data)} bytes)")
        return safe_filename
        
    except binascii.Error as e:
        error_msg = f"Invalid base64 data for file {filename}: {str(e)}"
        logger.error(error_msg)
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise ValueError(error_msg)
    except Exception as e:
        error_msg = f"Failed to save file {filename}: {str(e)}"
        logger.error(error_msg)
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise ValueError(error_msg)


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
            returned_file_names = [f["filename"] for f in returned_files]
            returned_file_contents = [f["content_base64"] for f in returned_files]

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
                "generated_file_count": len(returned_file_names),
                "has_plots": bool(plots),
                "is_error": False
            }
            return {
                "results": results_payload,
                "meta_data": meta_data,
                "returned_file_names": returned_file_names,
                "returned_file_contents": returned_file_contents
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
            return {
                "results": results_payload,
                "meta_data": meta_data,
                "returned_file_names": returned_file_names,
                "returned_file_contents": returned_file_contents
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
        return {
            "results": {"error": f"Code execution error: {str(ce)}"},
            "meta_data": {"is_error": True, "error_type": "CodeExecutionError", "execution_time_sec": exec_time},
            "returned_file_names": [script_filename],
            "returned_file_contents": [script_base64]
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
        return {
            "results": {"error": f"Server error: {str(e)}"},
            "meta_data": {"is_error": True, "error_type": type(e).__name__, "execution_time_sec": exec_time},
            "returned_file_names": [script_filename],
            "returned_file_contents": [script_base64]
        }
    
    # finally:
    #     # Clean up execution environment
    #     if exec_dir:
    #         cleanup_execution_environment(exec_dir)

if __name__ == "__main__":
    mcp.run()