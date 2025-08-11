import React, { useEffect, useState, useCallback, useRef } from 'react';

const DEFAULT_POLL_INTERVAL = 5000; // 5s refresh

export default function LogViewer() {
  const [entries, setEntries] = useState([]);
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(100);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [levelFilter, setLevelFilter] = useState('');
  const [moduleFilter, setModuleFilter] = useState('');
  const [hideViewerRequests, setHideViewerRequests] = useState(true);
  const [autoScrollEnabled, setAutoScrollEnabled] = useState(true); // State for auto-scroll
  const [pollIntervalInput, setPollIntervalInput] = useState(String(DEFAULT_POLL_INTERVAL / 1000)); // Input for poll interval in seconds
  const [pollInterval, setPollInterval] = useState(DEFAULT_POLL_INTERVAL); // Actual poll interval in ms

  const tableContainerRef = useRef(null);
  const isScrolledToBottom = useRef(true); // Track if user has scrolled up
  const intervalIdRef = useRef(null); // Ref to store interval ID

  const fetchLogs = useCallback(() => {
    setLoading(true);
    const params = new URLSearchParams();
    if (levelFilter) params.append('level_filter', levelFilter);
    if (moduleFilter) params.append('module_filter', moduleFilter);
    fetch(`/admin/logs/viewer?${params.toString()}`, {
      headers: {
        'X-User-Email': 'test@test.com'
      }
    })
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(data => {
        setEntries(data.entries || []);
        setError(null);
        // After updating entries, scroll to bottom if auto-scroll is enabled and user hasn't scrolled up
        requestAnimationFrame(() => {
          if (tableContainerRef.current && autoScrollEnabled && isScrolledToBottom.current) {
            tableContainerRef.current.scrollTop = tableContainerRef.current.scrollHeight;
          }
        });
      })
      .catch(err => setError(err))
      .finally(() => setLoading(false));
  }, [levelFilter, moduleFilter, autoScrollEnabled]); // Added autoScrollEnabled to dependencies

  useEffect(() => {
    // Clear existing interval before setting a new one
    if (intervalIdRef.current) {
      clearInterval(intervalIdRef.current);
    }
    // Fetch logs immediately and then set interval
    fetchLogs();
    intervalIdRef.current = setInterval(fetchLogs, pollInterval);

    // Cleanup interval on component unmount or when pollInterval changes
    return () => clearInterval(intervalIdRef.current);
  }, [fetchLogs, pollInterval]); // Depend on pollInterval

  // Handle scroll event to determine if user has manually scrolled up
  const handleScroll = useCallback(() => {
    if (tableContainerRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = tableContainerRef.current;
      isScrolledToBottom.current = scrollTop + clientHeight >= scrollHeight - 10; // Allow a small buffer
    }
  }, []);

  useEffect(() => {
    const container = tableContainerRef.current;
    if (container) {
      container.addEventListener('scroll', handleScroll);
    }
    return () => {
      if (container) {
        container.removeEventListener('scroll', handleScroll);
      }
    };
  }, [handleScroll]);

  const handlePollIntervalChange = (e) => {
    setPollIntervalInput(e.target.value);
    const intervalInSeconds = parseInt(e.target.value, 10);
    if (!isNaN(intervalInSeconds) && intervalInSeconds > 0) {
      setPollInterval(intervalInSeconds * 1000);
    } else {
      // Reset to default or handle invalid input appropriately
      setPollInterval(DEFAULT_POLL_INTERVAL);
    }
  };

  const levels = Array.from(new Set(entries.map(e => e.level))).sort();
  const modules = Array.from(new Set(entries.map(e => e.module))).sort();

  // Optionally hide the self-referential fetch request log lines to reduce noise
  const filtered = hideViewerRequests
    ? entries.filter(e => !(
        (e.message && e.message.includes('GET /admin/logs/viewer')) ||
        (e.path && e.path.includes('/admin/logs/viewer'))
      ))
    : entries;

  const paginated = filtered.slice().reverse().slice(page * pageSize, (page + 1) * pageSize);
  const totalPages = Math.ceil(filtered.length / pageSize) || 1;

  const changePage = (delta) => {
    setPage(p => Math.min(Math.max(0, p + delta), totalPages - 1));
  };

  return (
    <div className="p-4 space-y-4 h-full flex flex-col">
      <div className="flex items-end gap-4 flex-wrap">
        <div>
          <label className="block text-xs font-semibold mb-1">Level</label>
          <select value={levelFilter} onChange={e => setLevelFilter(e.target.value)} className="bg-gray-200 dark:bg-gray-700 p-2 rounded text-sm">
            <option value="">All</option>
            {levels.map(l => <option key={l}>{l}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-xs font-semibold mb-1">Module</label>
            <select value={moduleFilter} onChange={e => setModuleFilter(e.target.value)} className="bg-gray-200 dark:bg-gray-700 p-2 rounded text-sm max-w-52">
              <option value="">All</option>
              {modules.map(m => <option key={m}>{m}</option>)}
            </select>
        </div>
        <button onClick={fetchLogs} className="bg-cyan-500 hover:bg-cyan-600 text-white px-4 py-2 rounded text-sm font-semibold">Refresh</button>
        {loading && <span className="text-sm text-gray-500">Loading...</span>}
        <button onClick={() => window.location.href='/admin/logs/download'} className="bg-gray-300 dark:bg-gray-700 hover:bg-gray-400 dark:hover:bg-gray-600 text-gray-800 dark:text-gray-100 px-3 py-2 rounded text-sm font-medium">Download</button>
        {error && <span className="text-sm text-red-500">{error.message}</span>}
        <label className="flex items-center gap-2 text-xs font-medium select-none cursor-pointer ml-2">
          <input type="checkbox" className="accent-cyan-600" checked={hideViewerRequests} onChange={e => { setPage(0); setHideViewerRequests(e.target.checked); }} />
          Hide GET /admin/logs/viewer
        </label>
        {/* Auto-scroll toggle */}
        <label className="flex items-center gap-2 text-xs font-medium select-none cursor-pointer ml-2">
          <input type="checkbox" className="accent-cyan-600" checked={autoScrollEnabled} onChange={e => setAutoScrollEnabled(e.target.checked)} />
          Auto-scroll
        </label>
        {/* Poll interval input */}
        <div className="flex items-center gap-2">
          <label className="block text-xs font-semibold">Update Frequency (s)</label>
          <input
            type="number"
            value={pollIntervalInput}
            onChange={handlePollIntervalChange}
            min="1"
            className="bg-gray-200 dark:bg-gray-700 p-1 rounded text-sm w-16 text-center"
          />
        </div>
      </div>
      <div className="flex items-center gap-3 text-xs">
        <div className="flex items-center gap-2">
          <button onClick={() => changePage(-1)} disabled={page===0} className="px-2 py-1 bg-gray-200 dark:bg-gray-700 rounded disabled:opacity-40">Prev</button>
          <span>Page {page+1} / {totalPages}</span>
          <button onClick={() => changePage(1)} disabled={page>=totalPages-1} className="px-2 py-1 bg-gray-200 dark:bg-gray-700 rounded disabled:opacity-40">Next</button>
        </div>
        <div>
          <label className="mr-2">Page Size</label>
          <select value={pageSize} onChange={e => {setPageSize(parseInt(e.target.value,10)); setPage(0);}} className="bg-gray-200 dark:bg-gray-700 p-1 rounded">
            {[50,100,250,500].map(s => <option key={s}>{s}</option>)}
          </select>
        </div>
  <span className="text-gray-500">Total entries: {entries.length}{hideViewerRequests && filtered.length !== entries.length && ` (showing ${filtered.length})`}</span>
      </div>
      <div ref={tableContainerRef} className="flex-1 overflow-auto border border-gray-300 dark:border-gray-700 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100" onScroll={handleScroll}> {/* Added onScroll handler */}
        <table className="w-full text-sm">
          <thead className="bg-gray-100 dark:bg-gray-800 sticky top-0">
            <tr>
              <th className="text-left p-2 font-semibold">Module</th>
              <th className="text-left p-2 font-semibold">Function</th>
              <th className="text-left p-2 font-semibold">Message</th>
              <th className="text-left p-2 font-semibold">Timestamp</th>
              <th className="text-left p-2 font-semibold">Level</th>
              <th className="text-left p-2 font-semibold">Logger</th>
            </tr>
          </thead>
          <tbody>
            {paginated.map((e, idx) => (
              <tr key={idx} className="border-t border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
                <td className="p-2 font-mono text-[11px] text-gray-800 dark:text-gray-200">{e.module}</td>
                <td className="p-2 font-mono text-[11px] text-gray-700 dark:text-gray-300">{e.function}</td>
                <td className="p-2 text-[12px] whitespace-pre-wrap break-words leading-snug text-gray-900 dark:text-gray-100 max-w-[480px]">{e.message}</td>
                <td className="p-2 font-mono text-[11px] text-gray-600 dark:text-gray-400 whitespace-nowrap">{e.timestamp?.replace('T',' ').replace('Z','')}</td>
                <td className="p-2 font-semibold text-[11px]">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold tracking-wide ${e.level === 'ERROR' ? 'bg-red-600/20 text-red-700 dark:bg-red-500/30 dark:text-red-200' : e.level === 'WARNING' ? 'bg-yellow-500/20 text-yellow-700 dark:bg-yellow-500/30 dark:text-yellow-100' : 'bg-cyan-500/20 text-cyan-700 dark:bg-cyan-500/30 dark:text-cyan-100'}`}>{e.level}</span>
                </td>
                <td className="p-2 font-mono text-[11px] text-gray-700 dark:text-gray-300">{e.logger}</td>
              </tr>
            ))}
            {!filtered.length && !loading && (
              <tr><td colSpan={6} className="p-4 text-center text-gray-500">No log entries</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
