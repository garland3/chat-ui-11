#!/usr/bin/env python3
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from collections import deque
import json
from pathlib import Path
from typing import List
import html

app = FastAPI()
# Updated LOG_PATH as requested
LOG_PATH = Path("backend/logs/app.jsonl")
MAX_LINES = 2000

def read_last_lines(n: int) -> List[dict]:
    """
    Reads the last 'n' lines from the log file efficiently
    using a deque, which avoids loading the entire file into memory.
    """
    if not LOG_PATH.exists():
        raise FileNotFoundError(f"{LOG_PATH} not found")
    
    with LOG_PATH.open("r", encoding="utf-8") as f:
        lines_deque = deque(f, maxlen=n)
    
    out = []
    for line in lines_deque:
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            out.append({"raw": line.strip(), "_parse_error": True, "message": "Failed to parse JSON line"})
    return out

def render_row(entry: dict) -> str:
    """Renders a single log entry as an HTML table row."""
    if entry.get("_parse_error"):
        return f"""<tr class="log-entry" data-level="ERROR">
            <td colspan="7" class="mono error-row">
                <strong>Parse Error:</strong> {html.escape(entry.get("raw", ""))}
            </td>
        </tr>"""

    ts = html.escape(entry.get("timestamp", ""))
    level = html.escape(entry.get("level", "UNKNOWN")).upper()
    logger = html.escape(entry.get("logger", ""))
    msg = html.escape(entry.get("message", ""))
    trace = html.escape(entry.get("trace_id", ""))
    span = html.escape(entry.get("span_id", ""))
    
    extras = {k: v for k, v in entry.items() if k.startswith("extra_")}
    extras_html = ""
    if extras:
        extras_html = '<div class="extras-wrapper"><dl class="extras-list">'
        for k, v in extras.items():
            key = html.escape(k[len('extra_'):])
            value = html.escape(str(v))
            extras_html += f"<dt>{key}</dt><dd>{value}</dd>"
        extras_html += '</dl></div>'

    copy_icon = """<svg onclick="copyToClipboard(this.previousSibling.textContent, this)" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="copy-icon"><path fill-rule="evenodd" d="M4 2a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V2Zm2-1a1 1 0 0 0-1 1v8a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1V2a1 1 0 0 0-1-1H6ZM2 5a1 1 0 0 0-1 1v8a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1v-1h1v1a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h1V5H2Z" clip-rule="evenodd"></path></svg>"""

    return f"""
    <tr class="log-entry" data-level="{level}" data-logger="{logger}">
      <td class="col-ts mono">{ts}</td>
      <td class="col-level"><span class="level-badge level-{level}">{level}</span></td>
      <td class="col-logger">{logger}</td>
      <td class="col-msg">{msg}</td>
      <td class="col-trace mono"><span>{trace}</span>{copy_icon if trace else ''}</td>
      <td class="col-span mono"><span>{span}</span>{copy_icon if span else ''}</td>
      <td class="col-extras">{extras_html}</td>
    </tr>
    """

@app.get("/", response_class=HTMLResponse)
async def ui():
    try:
        entries = read_last_lines(250)
    except FileNotFoundError as e:
        return HTMLResponse(f"<h2>Error:</h2><pre>{e}</pre>", status_code=404)
    
    rows_html = "".join(render_row(e) for e in entries)
    
    html_content = f"""
    <!doctype html>
    <html lang="en">
    <head>
      <title>Log Viewer</title>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width,initial-scale=1">
      <style>
        :root {{
          /* A more professional, business-like color scheme */
          --bg: #111827;      /* Gray 900 */
          --card: #1F2937;    /* Gray 800 */
          --border: #374151;  /* Gray 700 */
          --text: #F9FAFB;    /* Gray 50 */
          --muted: #9CA3AF;   /* Gray 400 */
          --accent: #3B82F6;  /* Blue 500 */
          --accent-hover: #60A5FA; /* Blue 400 */
          --green: #22C55E; --yellow: #F59E0B; --red: #EF4444;
          --radius: 6px;
        }}
        * {{ box-sizing: border-box; }}
        body {{ margin: 0; background: var(--bg); font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; color: var(--text); -webkit-font-smoothing: antialiased; }}
        .wrapper {{ max-width: 96%; margin: 16px auto; }}
        
        /* Toolbar */
        .toolbar {{ display: flex; gap: 16px; align-items: center; background: var(--card); padding: 12px 16px; border-radius: var(--radius); flex-wrap: wrap; border: 1px solid var(--border); }}
        .title {{ margin: 0; font-size: 1.1rem; font-weight: 600; }}
        .controls, .filters {{ display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }}
        button {{ padding: 8px 16px; border: none; border-radius: var(--radius); cursor: pointer; background: var(--accent); color: #fff; font-weight: 500; transition: background .2s; }}
        button:hover {{ background: var(--accent-hover); }}
        select, input[type="checkbox"] {{ vertical-align: middle; }}
        select {{ padding: 4px 8px; border: 1px solid var(--border); border-radius: var(--radius); background: var(--card); color: var(--text); }}
        label {{ display: flex; align-items: center; gap: 6px; font-size: 0.9rem; user-select: none; }}
        .filters label {{ background: #374151; padding: 6px 12px; border-radius: var(--radius); cursor: pointer; transition: background .2s; }}
        .filters label:hover {{ background: #4B5563; }}
        .filters input:checked + span {{ font-weight: 600; color: var(--text); }}
        .status {{ margin-left: auto; font-size: 0.8rem; display: flex; gap: 12px; align-items: center; color: var(--muted); }}
        
        /* Log Container & Table */
        #log-container {{ height: calc(100vh - 150px); overflow: auto; margin-top: 16px; background: var(--card); border-radius: var(--radius); border: 1px solid var(--border); }}
        table {{ width: 100%; border-collapse: collapse; font-size: 0.8rem; min-width: 1400px; }}
        th, td {{ padding: 8px 12px; border-bottom: 1px solid var(--border); vertical-align: middle; text-align: left; }}
        th {{ position: sticky; top: 0; background: rgba(31, 41, 55, 0.85); backdrop-filter: blur(8px); font-weight: 600; color: var(--muted); text-transform: uppercase; font-size: 0.7rem; letter-spacing: 0.5px; }}
        tr.log-entry:hover {{ background: rgba(59, 130, 246, 0.08); }}

        /* Column Styles */
        .mono {{ font-family: "Fira Code", "JetBrains Mono", ui-monospace, monospace; }}
        .col-ts {{ width: 180px; color: var(--muted); }}
        .col-level {{ width: 100px; }}
        .col-logger {{ width: 150px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: var(--muted); }}
        .col-msg {{ width: auto; line-height: 1.5; }}
        .col-trace, .col-span {{ width: 110px; }}
        .col-trace span, .col-span span {{ display: inline-block; max-width: 80px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; vertical-align: middle; }}
        .col-extras {{ width: 350px; }} /* Increased width for extras */

        /* Log Levels & Extras */
        .level-badge {{ padding: 3px 8px; border-radius: var(--radius); font-weight: 700; font-size: 0.7rem; text-align: center; }}
        .level-INFO {{ background-color: #166534; color: #DCFCE7; }}
        .level-WARN {{ background-color: #92400E; color: #FEF3C7; }}
        .level-ERROR, .level-CRITICAL {{ background-color: #991B1B; color: #FEE2E2; }}
        .level-DEBUG {{ background-color: #4B5563; color: #E5E7EB; }}
        .error-row {{ color: var(--red); padding: 12px; }}

        /* New: Scrollable container for extras to prevent tall rows */
        .extras-wrapper {{ max-height: 90px; overflow-y: auto; padding-right: 8px; }}
        .extras-list {{ margin: 0; padding: 0; font-size: 0.75rem; line-height: 1.4; }}
        .extras-list dt {{ font-weight: 600; color: var(--accent); }}
        .extras-list dd {{ margin-left: 8px; color: var(--muted); word-break: break-all; }}

        /* Interactive Elements */
        .copy-icon {{ width: 14px; height: 14px; cursor: pointer; display: inline-block; margin-left: 6px; vertical-align: middle; color: #6B7280; }}
        .copy-icon:hover {{ color: var(--text); }}
        .copy-icon.copied {{ color: var(--green); }}
        #newIndicator {{ position: absolute; top: 12px; right: 12px; background: var(--accent); color: #fff; padding: 8px 14px; border-radius: var(--radius); font-size: 0.8rem; font-weight: 600; display: none; }}
      </style>
    </head>
    <body>
      <div class="wrapper">
        <div class="toolbar">
          <h2 class="title">Application Logs</h2>
          <div class="controls">
            <button onclick="refresh()">Refresh</button>
            <label>Lines
              <select id="lines" onchange="refresh()">
                <option value="100">100</option><option value="250" selected>250</option>
                <option value="500">500</option><option value="1000">1000</option>
              </select>
            </label>
            <label><input type="checkbox" id="autoScroll" checked> Auto-scroll</label>
          </div>
          <div class="filters">
             <label><input type="checkbox" class="filter-cb" value="DEBUG" onchange="applyFilters()" checked><span>DEBUG</span></label>
             <label><input type="checkbox" class="filter-cb" value="INFO" onchange="applyFilters()" checked><span>INFO</span></label>
             <label><input type="checkbox" class="filter-cb" value="WARN" onchange="applyFilters()" checked><span>WARN</span></label>
             <label><input type="checkbox" class="filter-cb" value="ERROR" onchange="applyFilters()" checked><span>ERROR</span></label>
             <label><input type="checkbox" class="filter-cb" value="CRITICAL" onchange="applyFilters()" checked><span>CRITICAL</span></label>
             <label>Logger
               <select id="loggerFilter" onchange="applyFilters()">
                 <option value="">All Loggers</option>
               </select>
             </label>
          </div>
          <div class="status">
            <div id="updated">Updated: --</div>
            <div id="count">Lines: 0</div>
          </div>
        </div>

        <div id="log-container">
          <div id="newIndicator">New logs available</div>
          <table>
            <thead>
              <tr>
                <th class="col-ts">Timestamp</th><th class="col-level">Level</th>
                <th class="col-logger">Logger</th><th class="col-msg">Message</th>
                <th class="col-trace">TraceID</th><th class="col-span">SpanID</th>
                <th class="col-extras">Extras</th>
              </tr>
            </thead>
            <tbody id="log-body">{rows_html}</tbody>
          </table>
        </div>
      </div>
      <script>
        let lastHTML = document.getElementById("log-body").innerHTML;

        function populateLoggerFilter() {{
            const rows = document.querySelectorAll('#log-body tr.log-entry');
            const loggers = new Set();
            rows.forEach(row => {{
                const logger = row.dataset.logger;
                if (logger && logger.trim()) {{
                    loggers.add(logger);
                }}
            }});
            
            const select = document.getElementById("loggerFilter");
            const currentValue = select.value;
            
            // Clear existing options except "All Loggers"
            select.innerHTML = '<option value="">All Loggers</option>';
            
            // Add sorted logger options
            Array.from(loggers).sort().forEach(logger => {{
                const option = document.createElement('option');
                option.value = logger;
                option.textContent = logger;
                select.appendChild(option);
            }});
            
            // Restore previous selection if it still exists
            if (currentValue && Array.from(loggers).includes(currentValue)) {{
                select.value = currentValue;
            }}
        }}

        function applyFilters() {{
            const levelFilters = Array.from(document.querySelectorAll('.filter-cb:checked')).map(cb => cb.value);
            const loggerFilter = document.getElementById("loggerFilter").value;
            const rows = document.querySelectorAll('#log-body tr.log-entry');
            let visibleCount = 0;
            
            rows.forEach(row => {{
                const level = row.dataset.level;
                const logger = row.dataset.logger;
                
                const levelMatch = levelFilters.includes(level);
                const loggerMatch = !loggerFilter || logger === loggerFilter;
                
                if (levelMatch && loggerMatch) {{
                    row.style.display = '';
                    visibleCount++;
                }} else {{
                    row.style.display = 'none';
                }}
            }});
            document.getElementById("count").textContent = "Lines: " + visibleCount;
        }}

        function refresh() {{
          const lines = document.getElementById("lines").value;
          fetch(`/api/logs?lines=${{encodeURIComponent(lines)}}`)
            .then(r => r.json())
            .then(data => {{
              const body = document.getElementById("log-body");
              if (data.rows !== lastHTML) {{
                const container = document.getElementById("log-container");
                const isScrolledToBottom = container.scrollHeight - container.clientHeight <= container.scrollTop + 1;
                
                body.innerHTML = data.rows;
                populateLoggerFilter(); // Populate logger dropdown with new data
                applyFilters(); // Apply filters to the new content
                
                document.getElementById("updated").textContent = "Updated: " + new Date().toLocaleTimeString();
                
                if (document.getElementById("autoScroll").checked && isScrolledToBottom) {{
                  container.scrollTo({{ top: container.scrollHeight, behavior: "smooth" }});
                  document.getElementById("newIndicator").style.display = "none";
                }} else if (!isScrolledToBottom) {{
                  const indicator = document.getElementById("newIndicator");
                  indicator.style.display = "block";
                  setTimeout(() => {{ indicator.style.display="none"; }}, 3000);
                }}
                lastHTML = data.rows;
              }}
            }})
            .catch(e => console.error("Failed to refresh logs:", e));
        }}
        
        function copyToClipboard(text, iconElement) {{
            navigator.clipboard.writeText(text).then(() => {{
                iconElement.classList.add('copied');
                setTimeout(() => iconElement.classList.remove('copied'), 1500);
            }});
        }}

        window.onload = () => {{
            populateLoggerFilter();
            applyFilters();
            const container = document.getElementById("log-container");
            container.scrollTop = container.scrollHeight;
        }};

        setInterval(refresh, 5000);
      </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/api/logs")
async def api_logs(lines: int = 250):
    if not 0 < lines <= MAX_LINES:
        raise HTTPException(400, f"Lines must be between 1 and {MAX_LINES}")
    try:
        entries = read_last_lines(lines)
    except FileNotFoundError:
        raise HTTPException(404, "Log file not found")
    
    rows_html = "".join(render_row(e) for e in entries)
    return JSONResponse(content={"rows": rows_html})