"""Mini dashboard — single-file FastAPI/Starlette server with embedded HTML.

Runs on port 4005 by default.  No React, no npm — one HTML page with inline JS.
"""

from __future__ import annotations

from typing import Any

from aegis.local.store import LocalStore

# ---------------------------------------------------------------------------
# Try FastAPI first, fall back to raw starlette, then http.server
# ---------------------------------------------------------------------------

_HAS_FASTAPI = False
_HAS_STARLETTE = False

try:
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse, JSONResponse

    _HAS_FASTAPI = True
except ImportError:
    try:
        from starlette.applications import Starlette
        from starlette.responses import HTMLResponse, JSONResponse
        from starlette.routing import Route

        _HAS_STARLETTE = True
    except ImportError:
        pass


# ---------------------------------------------------------------------------
# Dashboard HTML template (dark theme, AEGIS-X5 branded)
# ---------------------------------------------------------------------------

_DASHBOARD_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AEGIS-X5 Dashboard</title>
<style>
  :root {
    --bg: #0d1117; --surface: #161b22; --border: #30363d;
    --text: #e6edf3; --muted: #8b949e; --accent: #58a6ff;
    --green: #3fb950; --red: #f85149; --yellow: #d29922;
    --font: 'SF Mono', 'Cascadia Code', 'Fira Code', monospace;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: var(--font); background: var(--bg); color: var(--text); padding: 24px; }
  h1 { font-size: 1.4rem; color: var(--accent); margin-bottom: 4px; }
  .subtitle { color: var(--muted); font-size: 0.8rem; margin-bottom: 24px; }
  .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-bottom: 24px; }
  .stat-card {
    background: var(--surface); border: 1px solid var(--border); border-radius: 8px;
    padding: 16px; text-align: center;
  }
  .stat-card .value { font-size: 1.8rem; font-weight: 700; color: var(--accent); }
  .stat-card .label { font-size: 0.75rem; color: var(--muted); margin-top: 4px; }
  .stat-card.warn .value { color: var(--yellow); }
  .stat-card.danger .value { color: var(--red); }
  table { width: 100%; border-collapse: collapse; background: var(--surface); border-radius: 8px; overflow: hidden; }
  th { background: var(--border); color: var(--muted); font-size: 0.7rem; text-transform: uppercase;
       padding: 10px 12px; text-align: left; }
  td { padding: 8px 12px; border-bottom: 1px solid var(--border); font-size: 0.8rem; }
  tr:hover { background: rgba(88,166,255,0.05); }
  .status-ok { color: var(--green); }
  .status-error { color: var(--red); }
  .refresh-btn {
    background: var(--surface); border: 1px solid var(--border); color: var(--accent);
    padding: 6px 14px; border-radius: 6px; cursor: pointer; font-family: var(--font);
    font-size: 0.75rem; margin-bottom: 16px;
  }
  .refresh-btn:hover { background: var(--border); }
  .section-title { font-size: 0.95rem; color: var(--text); margin: 0 0 12px 0; }
  #last-update { color: var(--muted); font-size: 0.7rem; margin-left: 12px; }
</style>
</head>
<body>
  <h1>AEGIS-X5</h1>
  <div class="subtitle">Autonomous Agent Governance &mdash; Local Dashboard</div>

  <div class="stats" id="stats">
    <div class="stat-card"><div class="value" id="total-traces">--</div><div class="label">Total Traces</div></div>
    <div class="stat-card"><div class="value" id="avg-latency">--</div><div class="label">Avg Latency (ms)</div></div>
    <div class="stat-card"><div class="value" id="max-latency">--</div><div class="label">Max Latency (ms)</div></div>
    <div class="stat-card" id="guard-card"><div class="value" id="guard-blocks">--</div><div class="label">Guard Blocks</div></div>
  </div>

  <div style="display:flex;align-items:center;margin-bottom:12px;">
    <div class="section-title">Recent Traces</div>
    <button class="refresh-btn" onclick="refresh()" style="margin-left:auto;">Refresh</button>
    <span id="last-update"></span>
  </div>

  <table>
    <thead>
      <tr><th>Name</th><th>Status</th><th>Latency</th><th>Workspace</th><th>Time</th></tr>
    </thead>
    <tbody id="traces-body">
      <tr><td colspan="5" style="text-align:center;color:var(--muted)">Loading...</td></tr>
    </tbody>
  </table>

<script>
async function refresh() {
  try {
    const [statsRes, tracesRes] = await Promise.all([
      fetch('/api/stats'), fetch('/api/traces')
    ]);
    const stats = await statsRes.json();
    const traces = await tracesRes.json();

    document.getElementById('total-traces').textContent = stats.total_traces;
    document.getElementById('avg-latency').textContent = stats.avg_latency_ms.toFixed(1);
    document.getElementById('max-latency').textContent = stats.max_latency_ms.toFixed(1);
    document.getElementById('guard-blocks').textContent = stats.guard_blocks;

    const gc = document.getElementById('guard-card');
    gc.className = stats.guard_blocks > 0 ? 'stat-card danger' : 'stat-card';

    const tbody = document.getElementById('traces-body');
    if (traces.length === 0) {
      tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--muted)">No traces yet</td></tr>';
    } else {
      tbody.innerHTML = traces.map(t => {
        const cls = t.status === 'ok' ? 'status-ok' : 'status-error';
        const icon = t.status === 'ok' ? '\\u2713' : '\\u2717';
        const ts = new Date(t.created_at * 1000).toLocaleString();
        return `<tr>
          <td>${esc(t.name)}</td>
          <td class="${cls}">${icon} ${t.status}</td>
          <td>${t.duration_ms.toFixed(1)} ms</td>
          <td>${esc(t.workspace)}</td>
          <td>${ts}</td>
        </tr>`;
      }).join('');
    }

    document.getElementById('last-update').textContent = 'Updated ' + new Date().toLocaleTimeString();
  } catch(e) {
    console.error('Refresh failed:', e);
  }
}

function esc(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }

refresh();
setInterval(refresh, 5000);
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Render HTML with pre-baked data (for fallback server)
# ---------------------------------------------------------------------------

def render_dashboard_html(store: LocalStore | None = None) -> str:
    """Return the dashboard HTML string."""
    return _DASHBOARD_HTML


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app(db_path: str | None = None) -> Any:
    """Create and return a FastAPI/Starlette app serving the dashboard."""
    store = LocalStore(db_path=db_path)

    if _HAS_FASTAPI:
        app = FastAPI(title="AEGIS-X5 Dashboard", docs_url=None, redoc_url=None)

        @app.get("/", response_class=HTMLResponse)
        async def index() -> str:
            return _DASHBOARD_HTML

        @app.get("/dashboard", response_class=HTMLResponse)
        async def dashboard() -> str:
            return _DASHBOARD_HTML

        @app.get("/api/stats")
        async def api_stats(workspace: str | None = None) -> dict:
            return store.stats(workspace=workspace)

        @app.get("/api/traces")
        async def api_traces(limit: int = 100, workspace: str | None = None) -> list:
            return store.recent_traces(limit=limit, workspace=workspace)

        return app

    if _HAS_STARLETTE:

        async def index(request: Any) -> Any:
            return HTMLResponse(_DASHBOARD_HTML)

        async def api_stats(request: Any) -> Any:
            ws = request.query_params.get("workspace")
            return JSONResponse(store.stats(workspace=ws))

        async def api_traces(request: Any) -> Any:
            ws = request.query_params.get("workspace")
            limit = int(request.query_params.get("limit", 100))
            return JSONResponse(store.recent_traces(limit=limit, workspace=ws))

        app = Starlette(
            routes=[
                Route("/", index),
                Route("/dashboard", index),
                Route("/api/stats", api_stats),
                Route("/api/traces", api_traces),
            ]
        )
        return app

    # No ASGI framework available — return a marker so the CLI fallback kicks in
    return None
