"""
Server-side usage examples for MCP Enhanced tools.

These examples show proper server-side tool implementation.
Client handles username injection, file resolution, and size-based routing.
"""

import json
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from .decorator import enhanced_tool
from .responses import artifact, create_mcp_response, deferred_artifact
from .utils import list_user_files, secure_output_path


# Example 1: Basic file processing
@enhanced_tool()
def analyze_csv(filename: str, username: str) -> Dict[str, Any]:
    """
    Analyze a CSV file and generate a summary report.

    Server responsibilities:
    - Process the file at the provided path
    - Generate output in secure location
    - Return proper MCP response with artifact path

    Client responsibilities (already handled):
    - Injected username parameter
    - Resolved filename to secure path like /tmp/{username}/input_files/data.csv
    - Will process the returned artifact path for size-based routing
    """
    # filename is already a secure path provided by client
    df = pd.read_csv(filename)

    # Generate summary
    summary = {
        "total_rows": len(df),
        "columns": list(df.columns),
        "numeric_columns": list(df.select_dtypes(include=["number"]).columns),
        "missing_values": df.isnull().sum().to_dict(),
        "data_types": df.dtypes.astype(str).to_dict(),
    }

    # Save summary to secure location
    output_path = secure_output_path(username, "analysis_summary.json")
    with open(output_path, "w") as f:
        json.dump(summary, f, indent=2)

    # Return MCP response - client will handle size-based routing of the path
    return create_mcp_response(
        results={"message": f"Analyzed {len(df)} rows", "columns_found": len(df.columns)},
        artifacts=[
            artifact(
                name="analysis_summary.json",
                path=output_path,
                description=f"Analysis summary for {Path(filename).name}",
                category="report",
                viewer="code",
            )
        ],
    )


# Example 2: Multiple file processing
@enhanced_tool()
def merge_csv_files(filenames: List[str], username: str) -> Dict[str, Any]:
    """
    Merge multiple CSV files into one.

    filenames are already resolved by client to secure paths.
    """
    if not filenames:
        return create_mcp_response(results={"error": "No files provided"})

    dataframes = []
    file_info = []

    for filename in filenames:
        try:
            df = pd.read_csv(filename)
            dataframes.append(df)
            file_info.append(
                {"filename": Path(filename).name, "rows": len(df), "columns": len(df.columns)}
            )
        except Exception as e:
            return create_mcp_response(
                results={"error": f"Failed to read {Path(filename).name}: {str(e)}"}
            )

    # Merge dataframes
    merged_df = pd.concat(dataframes, ignore_index=True)

    # Save to secure location
    output_path = secure_output_path(username, "merged_data.csv")
    merged_df.to_csv(output_path, index=False)

    return create_mcp_response(
        results={
            "message": f"Successfully merged {len(filenames)} files",
            "total_rows": len(merged_df),
            "files_processed": file_info,
        },
        artifacts=[
            artifact(
                name="merged_data.csv",
                path=output_path,
                description=f"Merged data from {len(filenames)} CSV files",
                category="dataset",
                viewer="data",
            )
        ],
    )


# Example 3: Creating multiple outputs
@enhanced_tool()
def generate_report(filename: str, username: str) -> Dict[str, Any]:
    """
    Generate both a JSON summary and HTML report from data.
    """
    df = pd.read_csv(filename)

    # Generate JSON summary
    summary = {
        "dataset_name": Path(filename).name,
        "total_rows": len(df),
        "columns": len(df.columns),
        "summary_stats": df.describe().to_dict(),
    }

    json_path = secure_output_path(username, "data_summary.json")
    with open(json_path, "w") as f:
        json.dump(summary, f, indent=2)

    # Generate HTML report
    html_content = f"""
    <html>
    <head><title>Data Analysis Report</title></head>
    <body>
        <h1>Data Analysis Report</h1>
        <h2>Dataset: {Path(filename).name}</h2>
        <p><strong>Rows:</strong> {len(df)}</p>
        <p><strong>Columns:</strong> {len(df.columns)}</p>
        
        <h3>Column Information</h3>
        <ul>
        {"".join([f"<li>{col}: {df[col].dtype}</li>" for col in df.columns[:10]])}
        </ul>
        
        <h3>Summary Statistics</h3>
        {df.describe().to_html()}
    </body>
    </html>
    """

    html_path = secure_output_path(username, "data_report.html")
    with open(html_path, "w") as f:
        f.write(html_content)

    return create_mcp_response(
        results={"message": "Generated summary and report", "rows_analyzed": len(df)},
        artifacts=[
            artifact(
                name="data_summary.json",
                path=json_path,
                description="Machine-readable data summary",
                category="report",
                viewer="code",
            ),
            artifact(
                name="data_report.html",
                path=html_path,
                description="Human-readable analysis report",
                category="report",
                viewer="html",
                auto_open=True,
            ),
        ],
    )


# Example 4: Deferred artifacts for drafts
@enhanced_tool()
def create_draft_analysis(filename: str, username: str) -> Dict[str, Any]:
    """
    Create a draft analysis that needs user input to complete.
    """
    df = pd.read_csv(filename)

    # Create initial analysis file
    draft_content = f"""# Data Analysis Draft
    
Dataset: {Path(filename).name}
Rows: {len(df)}
Columns: {len(df.columns)}

## Column Analysis
{df.dtypes.to_string()}

## Summary Statistics  
{df.describe().to_string()}

## TODO: Complete Analysis
- [ ] Add interpretation of key findings
- [ ] Identify data quality issues
- [ ] Suggest next steps
- [ ] Add visualizations

## Notes
[Add your observations here]
"""

    draft_path = secure_output_path(username, "analysis_draft.md")
    with open(draft_path, "w") as f:
        f.write(draft_content)

    # Also save the raw data for reference
    data_path = secure_output_path(username, "source_data.csv")
    df.to_csv(data_path, index=False)

    return create_mcp_response(
        results={"message": "Created analysis draft", "requires_completion": True},
        artifacts=[
            artifact(
                name="source_data.csv",
                path=data_path,
                description="Source data for reference",
                category="dataset",
            )
        ],
        deferred_artifacts=[
            deferred_artifact(
                name="analysis_draft.md",
                path=draft_path,
                description="Draft analysis requiring user input",
                reason="needs_editing",
                next_actions=[
                    "Complete the TODO sections",
                    "Add your interpretations",
                    "Review and finalize findings",
                ],
                category="draft",
            )
        ],
    )


# Example 5: Tool that scans its own output
@enhanced_tool()
def batch_process_data(filename: str, username: str) -> Dict[str, Any]:
    """
    Process data and create multiple output files, then report on all generated files.
    """
    df = pd.read_csv(filename)

    # Create multiple outputs
    outputs_created = []

    # 1. Summary statistics
    summary_path = secure_output_path(username, "summary_stats.csv")
    df.describe().to_csv(summary_path)
    outputs_created.append(summary_path)

    # 2. Data types info
    dtypes_path = secure_output_path(username, "data_types.json")
    with open(dtypes_path, "w") as f:
        json.dump(df.dtypes.astype(str).to_dict(), f)
    outputs_created.append(dtypes_path)

    # 3. Missing values report
    if df.isnull().sum().sum() > 0:
        missing_path = secure_output_path(username, "missing_values.csv")
        df.isnull().sum().to_csv(missing_path)
        outputs_created.append(missing_path)

    # Scan for any other files we might have created
    all_files = list_user_files(username)

    return create_mcp_response(
        results={
            "message": f"Processed data and created {len(outputs_created)} files",
            "files_created": [Path(p).name for p in outputs_created],
            "all_user_files": [Path(p).name for p in all_files],
        },
        artifacts=[
            artifact(
                name=Path(path).name,
                path=path,
                description=f"Generated output: {Path(path).name}",
                category="report",
            )
            for path in outputs_created
        ],
    )


# Test runner for examples
def run_server_examples():
    """
    Run examples with mock data to demonstrate server-side functionality.

    Note: In real usage, the client would handle username injection
    and file path resolution before calling these tools.
    """
    print("Running MCP Enhanced server-side examples...")

    # Create test data
    test_data = {
        "id": range(1, 101),
        "name": [f"Item_{i}" for i in range(1, 101)],
        "value": [i * 10 for i in range(1, 101)],
        "category": ["A"] * 50 + ["B"] * 30 + ["C"] * 20,
    }

    df = pd.DataFrame(test_data)

    # Simulate client providing resolved file paths
    mock_username = "test_user"
    mock_input_file = f"/tmp/{mock_username}/input_files/test_data.csv"

    # Ensure directories exist
    Path(mock_input_file).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(mock_input_file, index=False)

    print("\n1. Analyzing CSV file...")
    result1 = analyze_csv(mock_input_file, mock_username)
    print(f"   Result: {result1['results']['message']}")
    if "artifacts" in result1:
        print(f"   Generated: {result1['artifacts'][0]['name']}")

    print("\n2. Generating report...")
    result2 = generate_report(mock_input_file, mock_username)
    print(f"   Result: {result2['results']['message']}")
    print(f"   Artifacts: {len(result2.get('artifacts', []))}")

    print("\n3. Creating draft analysis...")
    result3 = create_draft_analysis(mock_input_file, mock_username)
    print(f"   Result: {result3['results']['message']}")
    if "deferred_artifacts" in result3:
        print(f"   Deferred: {result3['deferred_artifacts'][0]['name']}")

    print("\nServer-side examples completed!")
    print("Note: Client would handle size-based routing of artifact paths.")


if __name__ == "__main__":
    run_server_examples()
