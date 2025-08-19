"""Progress Demo MCP Server using FastMCP.

This server exposes a single long-running tool that reports progress updates
to the client every n seconds until completion. Useful for validating end-to-end
progress handling in the app.
"""

from __future__ import annotations

import asyncio
from typing import Optional

from fastmcp import FastMCP, Context


# Initialize the MCP server
mcp = FastMCP("ProgressDemo")


@mcp.tool
async def long_task(
    task: str = "demo",
    duration_seconds: int = 12,
    interval_seconds: int = 3,
    ctx: Context | None = None,
) -> dict:
    """Run a pseudo long operation and report progress periodically.

    Args:
        task: Arbitrary task label used in progress messages.
        duration_seconds: Total duration for the task (default 12s).
        interval_seconds: How often to emit progress updates (default 3s).
        ctx: FastMCP context (injected) used to emit progress updates.

    Returns:
        dict with a simple results payload.
    """
    total = max(1, int(duration_seconds))
    step = max(1, int(interval_seconds))

    # Initial progress (0%)
    if ctx is not None:
        await ctx.report_progress(progress=0, total=total, message=f"{task}: starting")

    elapsed = 0
    while elapsed < total:
        await asyncio.sleep(step)
        elapsed = min(total, elapsed + step)
        if ctx is not None:
            await ctx.report_progress(
                progress=elapsed,
                total=total,
                message=f"{task}: {elapsed}/{total}s",
            )

    # Final completion (100%)
    if ctx is not None:
        await ctx.report_progress(progress=total, total=total, message=f"{task}: done")

    return {
        "results": {
            "task": task,
            "status": "completed",
            "duration_seconds": total,
            "interval_seconds": step,
        }
    }


@mcp.tool
async def status_updates(
    stages: list[str] | None = None,
    interval_seconds: int = 2,
    ctx: Context | None = None,
) -> dict:
    """Emit text status updates at a fixed interval (indeterminate progress).

    This demo focuses on sending human-readable status messages to the UI
    without a known total. The UI will show an indeterminate bar and the
    latest status message.

    Args:
        stages: Optional list of stage messages to emit sequentially.
        interval_seconds: Delay in seconds between updates.
        ctx: FastMCP context used to report progress messages.

    Returns:
        dict with a simple results payload including the stages traversed.
    """
    steps = stages or [
        "Starting",
        "Validating inputs",
        "Preparing resources",
        "Processing data",
        "Uploading artifacts",
        "Finalizing",
    ]

    # Initial status (no total, indeterminate)
    if ctx is not None:
        await ctx.report_progress(progress=0, message=f"{steps[0]}...")

    for i, stage in enumerate(steps):
        if i > 0:
            await asyncio.sleep(max(1, int(interval_seconds)))
            if ctx is not None:
                # Report only progress counter and message; omit total for indeterminate
                await ctx.report_progress(progress=i, message=f"{stage}...")

    if ctx is not None:
        await ctx.report_progress(progress=len(steps), message="Done.")

    return {
        "results": {
            "status": "completed",
            "stages": steps,
            "updates": len(steps) + 1,
            "interval_seconds": max(1, int(interval_seconds)),
        }
    }


if __name__ == "__main__":
    mcp.run()

