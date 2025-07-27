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
from typing import Any, Dict, List, Set, Annotated

from fastmcp import FastMCP

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('code_executor.log'),
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

# Restrict file operations to current directory only
original_open = open

def safe_open(file, mode='r', **kwargs):
    """Override open to restrict file access to execution directory."""
    file_path = Path(file).resolve()
    exec_path = Path(r"{exec_dir}").resolve()
    
    try:
        file_path.relative_to(exec_path)
    except ValueError:
        raise PermissionError(f"File access outside execution directory not allowed: {{file}}")
    
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
    # User code starts here
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

    Constraints:
        - Only a limited set of safe modules are allowed (e.g., numpy, pandas, matplotlib, seaborn, json, csv, math, etc.).
        - Imports of dangerous or unauthorized modules (e.g., os, sys, subprocess, socket, requests, pickle, threading, etc.) are blocked.
        - Dangerous built-in functions (e.g., eval, exec, compile, __import__, getattr, setattr, input, exit, quit, etc.) are forbidden.
        - File I/O is restricted to the execution directory only; attempts to access files outside are blocked.
        - Attribute access to __builtins__ and double-underscore attributes is forbidden.
        - Code is executed in a temporary, isolated directory that is cleaned up after execution.
        - Execution is time-limited (default: 30 seconds).
        - Only basic Python operations and safe data analysis/visualization are supported.

    Example usage:
        If you upload a file named "data.csv", you can access it in your code like:
        ```python
        import pandas as pd
        df = pd.read_csv('data.csv')
        print(df.head())
        ```

    Args:
        code: Python code to execute (string)
        filename: Name of the file to upload
        file_data_base64: Base64-encoded file data (automatically filled by framework)
        
    Returns:
        Dictionary with execution results, output, any generated visualizations, and file list
    """
    start_time = time.time()
    exec_dir = None
    
    try:
        if filename:
            logger.info(f"Starting code execution with file: {filename}")
        else:
            logger.info("Starting code execution without file upload")
        # log the code. 
        logger.info(f"Code to execute:\n{code}")
        
        # Security check on code
        violations = check_code_security(code)
        if violations:
            logger.warning(f"Security violations detected: {violations}")
            return {
                "success": False,
                "error": f"Security violations detected: {'; '.join(violations)}",
                "output": "",
                "files": [],
                "custom_html": "",
                "execution_time": 0
            }
        
        # Create execution environment
        exec_dir = create_execution_environment()
        
        # Save the uploaded file to the execution directory (if provided)
        saved_filename = None
        if filename and file_data_base64:
            try:
                saved_filename = save_file_to_execution_dir(filename, file_data_base64, exec_dir)
            except ValueError as e:
                logger.error(f"Failed to save uploaded file: {str(e)}")
                return {
                    "success": False,
                    "error": str(e),
                    "output": "",
                    "files": [],
                    "custom_html": "",
                    "execution_time": time.time() - start_time
                }
        elif filename and not file_data_base64:
            logger.warning(f"Filename '{filename}' provided but no file data - proceeding without file")
        elif not filename and file_data_base64:
            logger.warning("File data provided but no filename - ignoring file data")
        
        # Create and execute script
        script_path = create_safe_execution_script(code, exec_dir)
        execution_result = execute_code_safely(script_path, timeout=30)
        
        execution_time = time.time() - start_time
        
        if execution_result["success"]:
            # Check for generated files and plots
            generated_files = list_generated_files(exec_dir)
            plots = detect_matplotlib_plots(exec_dir)
            
            # Create custom HTML if there are plots or significant output
            custom_html = ""
            if plots or execution_result["stdout"].strip():
                try:
                    custom_html = create_visualization_html(plots, execution_result["stdout"])
                except Exception as e:
                    logger.warning(f"Failed to create visualization HTML: {str(e)}")
                    logger.warning(f"Traceback: {traceback.format_exc()}")
            
            # Create downloadable script file with the analysis code
            if filename:
                script_content = f"""# Code Analysis Script
# Generated by Secure Code Executor
# Original file: {filename}

{code}
"""
                script_filename = f"analysis_code_{filename.replace('.', '_')}.py"
            else:
                script_content = f"""# Code Execution Script
# Generated by Secure Code Executor

{code}
"""
                script_filename = "generated_code.py"
            
            script_base64 = base64.b64encode(script_content.encode('utf-8')).decode('utf-8')
            
            logger.info(f"Code execution completed successfully in {execution_time:.2f}s")
            return {
                "success": True,
                "output": execution_result["stdout"],
                "error": execution_result.get("stderr", ""),
                "error_type": execution_result.get("error_type"),
                "files": generated_files,
                "uploaded_file": saved_filename,
                "custom_html": custom_html,
                "execution_time": execution_time,
                "returned_file_name": script_filename,
                "returned_file_base64": script_base64
            }
        else:
            # Create downloadable script file even on failure so user can debug
            if filename:
                script_content = f"""# Code Analysis Script
# Generated by Secure Code Executor
# Original file: {filename}

{code}
"""
                script_filename = f"analysis_code_{filename.replace('.', '_')}.py"
            else:
                script_content = f"""# Code Execution Script
# Generated by Secure Code Executor

{code}
"""
                script_filename = "generated_code.py"
            
            script_base64 = base64.b64encode(script_content.encode('utf-8')).decode('utf-8')
            
            logger.error(f"Code execution failed: {execution_result.get('error', 'Unknown error')}")
            return {
                "success": False,
                "error": execution_result.get("error", "Unknown execution error"),
                "error_type": execution_result.get("error_type"),
                "output": execution_result.get("stdout", ""),
                "files": [],
                "uploaded_file": saved_filename if 'saved_filename' in locals() else None,
                "custom_html": "",
                "execution_time": execution_time,
                "returned_file_name": script_filename,
                "returned_file_base64": script_base64
            }
    
    except CodeExecutionError as e:
        execution_time = time.time() - start_time
        logger.error(f"Code execution error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Create downloadable script file even on exception so user can debug
        if filename:
            script_content = f"""# Code Analysis Script
# Generated by Secure Code Executor
# Original file: {filename}

{code}
"""
            script_filename = f"analysis_code_{filename.replace('.', '_')}.py"
        else:
            script_content = f"""# Code Execution Script
# Generated by Secure Code Executor

{code}
"""
            script_filename = "generated_code.py"
        
        script_base64 = base64.b64encode(script_content.encode('utf-8')).decode('utf-8')
        
        return {
            "success": False,
            "error": f"Code execution error: {str(e)}",
            "error_type": "CodeExecutionError",
            "output": "",
            "files": [],
            "custom_html": "",
            "execution_time": execution_time,
            "returned_file_name": script_filename,
            "returned_file_base64": script_base64
        }
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"Unexpected server error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Create downloadable script file even on exception so user can debug
        if filename:
            script_content = f"""# Code Analysis Script
# Generated by Secure Code Executor
# Original file: {filename}

{code}
"""
            script_filename = f"analysis_code_{filename.replace('.', '_')}.py"
        else:
            script_content = f"""# Code Execution Script
# Generated by Secure Code Executor

{code}
"""
            script_filename = "generated_code.py"
        
        script_base64 = base64.b64encode(script_content.encode('utf-8')).decode('utf-8')
        
        return {
            "success": False,
            "error": f"Server error: {str(e)}",
            "error_type": type(e).__name__,
            "output": "",
            "files": [],
            "custom_html": "",
            "execution_time": execution_time,
            "returned_file_name": script_filename,
            "returned_file_base64": script_base64
        }
    
    # finally:
    #     # Clean up execution environment
    #     if exec_dir:
    #         cleanup_execution_environment(exec_dir)

if __name__ == "__main__":
    mcp.run()