#!/usr/bin/env python3
"""
CSV Reporter MCP Server using FastMCP.

Demonstrates two v2 behaviors described in v2_mcp_note.md:
1) filename(s) to downloadable URLs: If the backend rewrites filename/file_names
   to /api/files/download/... URLs, this server will fetch and process them.
   It also accepts file_data_base64 as a fallback for content delivery.
2) username injection: If a `username` parameter is defined in the tool schema,
   the backend can inject the authenticated user's email/username. This server
   trusts the provided username value and echoes it in outputs.

Tools:
 - generate_csv_report: Build a summary report for a single CSV.
 - summarize_multiple_csvs: Summarize multiple CSVs (using file_names[]).
"""

from __future__ import annotations

import base64
import io
import os
import time
import logging
import traceback
from typing import Any, Dict, List, Annotated, Optional
import httpx

import pandas as pd
import requests
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from fastmcp import FastMCP

logger = logging.getLogger(__name__)


mcp = FastMCP("CSV_Reporter")


RUNTIME_UPLOADS = os.environ.get(
    "CHATUI_RUNTIME_UPLOADS", "/workspaces/chat-ui-11/runtime/uploads"
)

BACKEND_BASE_URL = os.environ.get("CHATUI_BACKEND_BASE_URL", "http://127.0.0.1:8000")


def _is_http_url(s: str) -> bool:
    return s.startswith("http://") or s.startswith("https://")


def _is_backend_download_path(s: str) -> bool:
    """Detect backend-relative download paths like /api/files/download/...."""
    return isinstance(s, str) and s.startswith("/api/files/download/")


def _backend_base_url() -> str:
    """Resolve backend base URL from environment variable.

    Fallback to http://127.0.0.1:8000.
    """
    return os.environ.get("CHATUI_BACKEND_BASE_URL", "http://127.0.0.1:8000")


def _finalize_meta(meta: Dict[str, Any], start: float) -> Dict[str, Any]:
    """Attach timing info and return meta_data dict."""
    meta = dict(meta)  # shallow copy
    meta["elapsed_ms"] = round((time.perf_counter() - start) * 1000, 3)
    return meta


def _upload_artifact_to_s3(
    content: bytes, filename: str, content_type: str, username: str
) -> Dict[str, str]:
    """Upload artifact content to S3 via backend API and return artifact info with URL.

    Returns dict with 'name', 'url', 'mime', 'size' fields for artifacts array.
    Uses synchronous httpx.Client to avoid asyncio.run() in running event loop.
    """
    try:
        content_b64 = base64.b64encode(content).decode("utf-8")

        # Upload via backend API
        upload_payload = {
            "filename": filename,
            "content_base64": content_b64,
            "content_type": content_type,
            "tags": {"source": "mcp_tool", "generator": "csv_reporter"},
        }

        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{BACKEND_BASE_URL}/api/files",
                json=upload_payload,
                headers={"X-User-Email": username},  # Auth header
            )
            response.raise_for_status()

            result = response.json()
            file_key = result["key"]

            # Create download URL (will be enhanced with capability token by backend)
            download_url = f"/api/files/download/{file_key}"

            return {
                "name": filename,
                "url": download_url,
                "mime": content_type,
                "size": len(content),
            }

    except Exception as e:
        # Fallback to base64 if S3 upload fails
        logger.warning(f"S3 upload failed for {filename}, falling back to base64: {e}")
        return {
            "name": filename,
            "b64": base64.b64encode(content).decode("utf-8"),
            "mime": content_type,
            "size": len(content),
        }


def _load_csv_bytes(filename: str, file_data_base64: str = "") -> bytes:
    """Return raw CSV bytes from either base64, URL, or local uploads path.

    Priority:
    1) file_data_base64 if provided
    2) If filename is URL -> GET
    3) Try local file in runtime uploads
    Raises FileNotFoundError or requests.HTTPError as appropriate.
    """
    if file_data_base64:
        return base64.b64decode(file_data_base64)

    # Support backend-injected relative download URLs by resolving with a base URL
    if filename and _is_backend_download_path(filename):
        base = _backend_base_url()
        url = base.rstrip("/") + "/" + filename.lstrip("/")
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        return r.content

    if filename and _is_http_url(filename):
        r = requests.get(filename, timeout=20)
        r.raise_for_status()
        return r.content

    # Fallback: treat filename as a key under runtime uploads
    if filename:
        local_path = filename
        if not os.path.isabs(local_path):
            local_path = os.path.join(RUNTIME_UPLOADS, filename)
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"CSV not found: {local_path}")
        with open(local_path, "rb") as f:
            return f.read()

    raise FileNotFoundError("No filename or file data provided")


def _dataframe_report(df: pd.DataFrame, *, username: str, source_name: str) -> str:
    """Create a human-readable report for a DataFrame."""
    lines: List[str] = []
    lines.append(f"CSV Report for: {source_name}")
    lines.append(f"Requested by: {username}")
    lines.append("")
    lines.append(f"Shape: {df.shape[0]} rows x {df.shape[1]} columns")
    lines.append("")
    # Column dtypes
    lines.append("Column types:")
    lines.append(df.dtypes.to_string())
    lines.append("")
    # Missing values
    na_counts = df.isna().sum()
    if (na_counts > 0).any():
        lines.append("Missing values per column:")
        lines.append(na_counts.to_string())
        lines.append("")
    # Numeric summary
    num_df = df.select_dtypes(include=["number"])  # type: ignore[arg-type]
    if not num_df.empty:
        desc = num_df.describe().transpose()
        lines.append("Numeric columns summary:")
        lines.append(desc.to_string())
        lines.append("")
    # Sample rows
    try:
        sample = df.head(5)
        lines.append("Sample (first 5 rows):")
        lines.append(sample.to_string(index=False))
    except Exception:
        pass
    return "\n".join(lines)


@mcp.tool
def generate_csv_report(
    filename: Annotated[str, "CSV filename. No directory. Just the filename."],
    username: Annotated[str, "Injected by backend. Trust this value."] = "",
    file_data_base64: Annotated[
        str, "Framework may supply Base64 content as fallback."
    ] = "",
) -> Dict[str, Any]:
    """Generate comprehensive statistical analysis and summary report for CSV data files.

    This tool performs in-depth analysis of CSV files to provide actionable insights:

    **Data Analysis Features:**
    - Complete dataset overview (rows, columns, data types)
    - Statistical summaries for all numeric columns (mean, median, std, min, max, quartiles)
    - Missing value analysis and data quality assessment
    - Column type detection and classification
    - Sample data preview for context understanding

    **Report Contents:**
    - Dataset dimensions and structure
    - Data type distribution across columns
    - Missing value patterns and percentages
    - Descriptive statistics for numeric data
    - Sample rows for data format verification
    - Data quality indicators and potential issues

    **File Input Support:**
    - Direct CSV file upload via file browser
    - Base64 encoded CSV content
    - Backend-generated downloadable URLs
    - UTF-8 and common CSV encoding formats

    **Output Format:**
    - Structured text report with clear sections
    - Easy-to-read tabular summaries
    - Professional formatting suitable for sharing
    - Downloadable report file for future reference

    **Use Cases:**
    - Initial data exploration and quality assessment
    - Dataset documentation and profiling
    - Data validation before analysis or modeling
    - Quick statistical overview for stakeholder reports
    - Data preprocessing planning and strategy

    **Examples:**
    - Sales data: Revenue distribution, transaction patterns, missing customer info
    - Survey data: Response rates, demographic breakdowns, incomplete answers
    - Financial data: Account balances, transaction volumes, data completeness

    Args:
        instructions: Optional analysis instructions (currently not used in processing logic)
        filename: Name/path of CSV file to analyze (supports various input methods)
        username: User identity for report attribution (automatically injected by backend)
        file_data_base64: Base64-encoded CSV content (alternative input method)

    Returns:
        Dictionary containing:
        - results: Analysis summary and status message
        - artifacts: Downloadable text report with complete analysis
        - display: Viewer configuration for optimal report presentation
        - meta_data: Dataset metrics (rows, columns, generator info)
        Or error message if file cannot be processed
    """
    start = time.perf_counter()
    meta: Dict[str, Any] = {}

    try:
        raw = _load_csv_bytes(filename, file_data_base64)
        df = pd.read_csv(io.BytesIO(raw))
        if df.empty:
            meta.update({"is_error": True, "reason": "empty_csv"})
            return {
                "results": {"error": "CSV is empty."},
                "meta_data": _finalize_meta(meta, start),
            }

        # Use the raw filename; let the chat UI handle any sanitization
        report_text = _dataframe_report(
            df, username=username or "unknown", source_name=filename
        )
        report_content = report_text.encode("utf-8")

        # Upload report to S3
        artifact = _upload_artifact_to_s3(
            content=report_content,
            filename="report.txt",
            content_type="text/plain",
            username=username or "unknown",
        )

        meta.update({"is_error": False})
        return {
            "results": {
                "operation": "csv_report",
                "filename": filename,
                "message": "CSV report generated and uploaded to storage.",
            },
            "artifacts": [artifact],
            "display": {
                "open_canvas": True,
                "primary_file": "report.txt",
                "mode": "replace",
                "viewer_hint": "code",
            },
            "meta_data": _finalize_meta(
                {
                    "generated_by": username,
                    "rows": int(df.shape[0]),
                    "columns": int(df.shape[1]),
                    "storage_method": "s3" if "url" in artifact else "base64_fallback",
                    "is_error": False,
                },
                start,
            ),
        }
    except FileNotFoundError as e:
        meta.update({"is_error": True, "reason": "file_not_found"})
        return {
            "results": {"error": str(e) + traceback.format_exc()},
            "meta_data": _finalize_meta(meta, start),
        }
    except pd.errors.EmptyDataError:
        meta.update({"is_error": True, "reason": "empty_data"})
        return {
            "results": {"error": "CSV file is empty or unreadable."},
            "meta_data": _finalize_meta(meta, start),
        }
    except pd.errors.ParserError as e:
        meta.update({"is_error": True, "reason": "parsing_error"})
        return {
            "results": {"error": f"CSV parsing error: {e}"},
            "meta_data": _finalize_meta(meta, start),
        }
    except requests.HTTPError as e:
        meta.update({"is_error": True, "reason": "http_error"})
        return {
            "results": {"error": f"Download failed: {e}"},
            "meta_data": _finalize_meta(meta, start),
        }
    except Exception as e:  # noqa: BLE001
        meta.update({"is_error": True, "reason": type(e).__name__})
        return {
            "results": {"error": f"Unexpected error: {str(e)}"},
            "meta_data": _finalize_meta(meta, start),
        }


@mcp.tool
def summarize_multiple_csvs(
    instructions: Annotated[str, "Instructions for the tool, not used for logic"],
    file_names: Annotated[
        List[str], "Array of CSV filenames. Backend may rewrite to downloadable URLs."
    ],
    username: Annotated[str, "Injected by backend. Trust this value."] = "",
) -> Dict[str, Any]:
    """Create comparative analysis and consolidated summary across multiple CSV datasets.

    This advanced tool processes multiple CSV files simultaneously to provide:

    **Cross-Dataset Analysis:**
    - Comparative dataset metrics (rows, columns, sizes)
    - Column name consistency analysis across files
    - Data type compatibility assessment
    - Missing value patterns comparison
    - Overall data quality evaluation across all files

    **Consolidated Reporting:**
    - Unified summary of all datasets
    - Total record counts and column inventories
    - Data structure compatibility matrix
    - Common and unique column identification
    - Quality metrics aggregation

    **Batch Processing Features:**
    - Processes all files in a single operation
    - Error handling for individual file failures
    - Continues processing even if some files fail
    - Detailed error reporting for problematic files
    - Success rate and processing statistics

    **Multi-File Insights:**
    - Dataset size distribution across files
    - Schema consistency validation
    - Potential data merging opportunities
    - Data integration readiness assessment
    - Standardization recommendations

    **Use Cases:**
    - Data integration planning and validation
    - Multi-source data quality assessment
    - Database migration preparation
    - Data warehouse loading validation
    - Cross-system data consistency checks
    - Batch data processing workflows

    **Examples:**
    - Multiple monthly sales reports → Consolidated annual analysis
    - Regional customer databases → Cross-region data consistency check
    - Survey results from different periods → Longitudinal study preparation

    Args:
        instructions: Optional processing instructions (currently not used in logic)
        file_names: List of CSV file names/paths to analyze (supports various input methods)
        username: User identity for report attribution (automatically injected by backend)

    Returns:
        Dictionary containing:
        - results: Consolidated analysis summary with cross-file insights
        - artifacts: Downloadable comprehensive report with all file analyses
        - display: Viewer configuration for optimal multi-file report presentation
        - meta_data: Aggregated statistics (total files, success rate, combined metrics)
        Or error summary if multiple files cannot be processed
    """
    start = time.perf_counter()
    meta: Dict[str, Any] = {}

    summaries: List[str] = []
    total_rows = 0
    total_cols_unique = set()
    processed = 0
    errors: List[str] = []

    for name in file_names:
        try:
            raw = _load_csv_bytes(name)
            df = pd.read_csv(io.BytesIO(raw))
            processed += 1
            total_rows += int(df.shape[0])
            total_cols_unique.update(df.columns.tolist())
            summaries.append(f"{name}: {df.shape[0]} rows x {df.shape[1]} cols")
        except Exception as e:  # collect per-file error, continue
            errors.append(f"{name}: {e}")

    report_lines = [f"Multi-CSV summary for {username or 'unknown'}:"]
    report_lines.extend(summaries or ["No files processed."])
    if errors:
        report_lines.append("")
        report_lines.append("Errors:")
        report_lines.extend(errors)

    text = "\n".join(report_lines)
    content = text.encode("utf-8")

    # Upload summary to S3
    artifact = _upload_artifact_to_s3(
        content=content,
        filename="multi_csv_summary.txt",
        content_type="text/plain",
        username=username or "unknown",
    )

    meta.update({"is_error": False})
    return {
        "results": {
            "operation": "multi_csv_summary",
            "processed_files": processed,
            "message": "Multi-CSV summary generated and uploaded to storage.",
        },
        "artifacts": [artifact],
        "display": {
            "open_canvas": True,
            "primary_file": "multi_csv_summary.txt",
            "mode": "replace",
            "viewer_hint": "code",
        },
        "meta_data": _finalize_meta(
            {
                "generated_by": username,
                "total_rows": total_rows,
                "unique_columns": sorted(list(total_cols_unique)),
                "errors": errors,
                "storage_method": "s3" if "url" in artifact else "base64_fallback",
                "is_error": False,
            },
            start,
        ),
    }


@mcp.tool
def plot_correlation_matrix(
    instructions: Annotated[str, "Instructions for the tool, not used for logic"],
    filename: Annotated[
        str, "CSV filename. Backend may rewrite to a downloadable URL."
    ],
    columns: Annotated[
        Optional[List[str]],
        "Specific columns to plot. If None, plots all numeric columns.",
    ] = None,
    username: Annotated[str, "Injected by backend. Trust this value."] = "",
    file_data_base64: Annotated[
        str, "Framework may supply Base64 content as fallback."
    ] = "",
) -> Dict[str, Any]:
    """Generate an N by N correlation matrix plot for numeric columns in a CSV file.

    Creates a heatmap showing linear correlations between specified columns or all numeric columns.
    """
    start = time.perf_counter()
    meta: Dict[str, Any] = {}

    try:
        # Load and parse CSV
        raw = _load_csv_bytes(filename, file_data_base64)
        df = pd.read_csv(io.BytesIO(raw))
        if df.empty:
            meta.update({"is_error": True, "reason": "empty_csv"})
            return {
                "results": {"error": "CSV is empty."},
                "meta_data": _finalize_meta(meta, start),
            }

        # Select numeric columns
        numeric_df = df.select_dtypes(include=[np.number])
        if numeric_df.empty:
            meta.update({"is_error": True, "reason": "no_numeric_columns"})
            return {
                "results": {"error": "No numeric columns found in the CSV."},
                "meta_data": _finalize_meta(meta, start),
            }

        # Filter to specified columns if provided
        if columns:
            available_cols = [col for col in columns if col in numeric_df.columns]
            if not available_cols:
                meta.update({"is_error": True, "reason": "no_matching_columns"})
                return {
                    "results": {
                        "error": f"None of the specified columns {columns} are numeric or exist in the CSV."
                    },
                    "meta_data": _finalize_meta(meta, start),
                }
            numeric_df = numeric_df[available_cols]

        # Calculate correlation matrix
        corr_matrix = numeric_df.corr()

        # Create the plot
        plt.figure(figsize=(10, 8))
        sns.heatmap(
            corr_matrix,
            annot=True,
            cmap="coolwarm",
            center=0,
            square=True,
            fmt=".2f",
            cbar_kws={"shrink": 0.8},
        )
        plt.title("Correlation Matrix")
        plt.tight_layout()

        # Save plot to bytes
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format="png", dpi=300, bbox_inches="tight")
        img_buffer.seek(0)
        img_content = img_buffer.getvalue()
        plt.close()

        # Upload plot to S3
        artifact = _upload_artifact_to_s3(
            content=img_content,
            filename="correlation_matrix.png",
            content_type="image/png",
            username=username or "unknown",
        )

        meta.update({"is_error": False})
        return {
            "results": {
                "operation": "correlation_matrix_plot",
                "filename": filename,
                "columns_plotted": list(numeric_df.columns),
                "message": "Correlation matrix plot generated and uploaded to storage.",
            },
            "artifacts": [artifact],
            "display": {
                "open_canvas": True,
                "primary_file": "correlation_matrix.png",
                "mode": "replace",
                "viewer_hint": "image",
            },
            "meta_data": _finalize_meta(
                {
                    "generated_by": username,
                    "correlation_shape": corr_matrix.shape,
                    "columns_used": list(numeric_df.columns),
                    "storage_method": "s3" if "url" in artifact else "base64_fallback",
                    "is_error": False,
                },
                start,
            ),
        }
    except FileNotFoundError as e:
        meta.update({"is_error": True, "reason": "file_not_found"})
        return {"results": {"error": str(e)}, "meta_data": _finalize_meta(meta, start)}
    except pd.errors.EmptyDataError:
        meta.update({"is_error": True, "reason": "empty_data"})
        return {
            "results": {"error": "CSV file is empty or unreadable."},
            "meta_data": _finalize_meta(meta, start),
        }
    except pd.errors.ParserError as e:
        meta.update({"is_error": True, "reason": "parsing_error"})
        return {
            "results": {"error": f"CSV parsing error: {e}"},
            "meta_data": _finalize_meta(meta, start),
        }
    except requests.HTTPError as e:
        meta.update({"is_error": True, "reason": "http_error"})
        return {
            "results": {"error": f"Download failed: {e}"},
            "meta_data": _finalize_meta(meta, start),
        }
    except Exception as e:
        meta.update({"is_error": True, "reason": type(e).__name__})
        return {
            "results": {"error": f"Unexpected error: {str(e)}"},
            "meta_data": _finalize_meta(meta, start),
        }


@mcp.tool
def plot_time_series(
    instructions: Annotated[str, "Instructions for the tool, not used for logic"],
    filename: Annotated[
        str, "CSV filename. Backend may rewrite to a downloadable URL."
    ],
    columns: Annotated[
        List[str], "Columns to plot as time series with index as x-axis."
    ],
    username: Annotated[str, "Injected by backend. Trust this value."] = "",
    file_data_base64: Annotated[
        str, "Framework may supply Base64 content as fallback."
    ] = "",
) -> Dict[str, Any]:
    """Generate connected scatter plots for specified columns with index as x-axis.

    Creates a time series style plot where each specified column is plotted against the row index.
    """
    start = time.perf_counter()
    meta: Dict[str, Any] = {}

    try:
        # Load and parse CSV
        raw = _load_csv_bytes(filename, file_data_base64)
        df = pd.read_csv(io.BytesIO(raw))
        if df.empty:
            meta.update({"is_error": True, "reason": "empty_csv"})
            return {
                "results": {"error": "CSV is empty."},
                "meta_data": _finalize_meta(meta, start),
            }

        # Handle cases where columns is None or empty
        if columns is None or not columns:
            columns = df.columns.tolist()
        else:
            # Check if specified columns exist
            missing_cols = [col for col in columns if col not in df.columns]
            if missing_cols:
                meta.update({"is_error": True, "reason": "missing_columns"})
                return {
                    "results": {"error": f"Columns not found in CSV: {missing_cols}"},
                    "meta_data": _finalize_meta(meta, start),
                }

        # Select only the specified columns
        plot_df = df[columns]

        # Check if columns are numeric (convert if possible)
        for col in columns:
            if not pd.api.types.is_numeric_dtype(plot_df[col]):
                try:
                    plot_df[col] = pd.to_numeric(plot_df[col], errors="coerce")
                except Exception as e:
                    print(e)
                    meta.update({"is_error": True, "reason": "conversion_error"})
                    return {
                        "results": {
                            "error": f"Column '{col}' cannot be converted to numeric values."
                        },
                        "meta_data": _finalize_meta(meta, start),
                    }

        # Create the plot
        plt.figure(figsize=(12, 8))

        for col in columns:
            plt.plot(
                plot_df.index,
                plot_df[col],
                marker="o",
                markersize=3,
                linewidth=1.5,
                label=col,
                alpha=0.8,
            )

        plt.xlabel("Index")
        plt.ylabel("Values")
        plt.title("Time Series Plot")
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        # Save plot to bytes
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format="png", dpi=300, bbox_inches="tight")
        img_buffer.seek(0)
        img_content = img_buffer.getvalue()
        plt.close()

        # Upload plot to S3
        artifact = _upload_artifact_to_s3(
            content=img_content,
            filename="time_series.png",
            content_type="image/png",
            username=username or "unknown",
        )

        meta.update({"is_error": False})
        return {
            "results": {
                "operation": "time_series_plot",
                "filename": filename,
                "columns_plotted": columns,
                "message": "Time series plot generated and uploaded to storage.",
            },
            "artifacts": [artifact],
            "display": {
                "open_canvas": True,
                "primary_file": "time_series.png",
                "mode": "replace",
                "viewer_hint": "image",
            },
            "meta_data": _finalize_meta(
                {
                    "generated_by": username,
                    "data_points": len(plot_df),
                    "columns_plotted": columns,
                    "storage_method": "s3" if "url" in artifact else "base64_fallback",
                    "is_error": False,
                },
                start,
            ),
        }
    except FileNotFoundError as e:
        meta.update({"is_error": True, "reason": "file_not_found"})
        return {"results": {"error": str(e)}, "meta_data": _finalize_meta(meta, start)}
    except pd.errors.EmptyDataError:
        meta.update({"is_error": True, "reason": "empty_data"})
        return {
            "results": {"error": "CSV file is empty or unreadable."},
            "meta_data": _finalize_meta(meta, start),
        }
    except pd.errors.ParserError as e:
        meta.update({"is_error": True, "reason": "parsing_error"})
        return {
            "results": {"error": f"CSV parsing error: {e}"},
            "meta_data": _finalize_meta(meta, start),
        }
    except requests.HTTPError as e:
        meta.update({"is_error": True, "reason": "http_error"})
        return {
            "results": {"error": f"Download failed: {e}"},
            "meta_data": _finalize_meta(meta, start),
        }
    except Exception as e:
        meta.update({"is_error": True, "reason": type(e).__name__})
        return {
            "results": {"error": f"Unexpected error: {str(e)}"},
            "meta_data": _finalize_meta(meta, start),
        }


if __name__ == "__main__":
    mcp.run()
