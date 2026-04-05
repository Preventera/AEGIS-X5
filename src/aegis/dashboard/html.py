"""AEGIS-X5 Dashboard — full multi-view HTML (single file, no React/npm).

Dark theme with gold/cyan/red/violet/emerald accents.
5 views: Overview, Agents, Guard, Predictions, Traces.
"""

DASHBOARD_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AEGIS-X5 Dashboard</title>
<style>
:root {
  --bg: #0a0e17; --surface: #111827; --surface2: #1a2235; --border: #2a3548;
  --text: #e2e8f0; --muted: #64748b; --dim: #475569;
  --gold: #f59e0b; --cyan: #06b6d4; --red: #ef4444; --violet: #8b5cf6;
  --emerald: #10b981; --blue: #3b82f6; --orange: #f97316;
  --font: 'SF Mono','Cascadia Code','JetBrains Mono','Fira Code',monospace;
  --sans: -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
}
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:var(--sans); background:var(--bg); color:var(--text); display:flex; height:100vh; overflow:hidden; }

/* Sidebar */
.sidebar { width:56px; background:var(--surface); border-right:1px solid var(--border); display:flex; flex-direction:column; align-items:center; padding:12px 0; gap:4px; flex-shrink:0; }
.sidebar .logo { font-size:11px; font-weight:800; color:var(--gold); letter-spacing:1px; margin-bottom:16px; writing-mode:vertical-rl; text-orientation:mixed; }
.nav-btn { width:40px; height:40px; border:none; background:transparent; color:var(--muted); cursor:pointer; border-radius:8px; font-size:18px; display:flex; align-items:center; justify-content:center; transition:all .15s; }
.nav-btn:hover { background:var(--surface2); color:var(--text); }
.nav-btn.active { background:var(--gold); color:var(--bg); }
.nav-btn svg { width:20px; height:20px; fill:currentColor; }

/* Main */
.main { flex:1; display:flex; flex-direction:column; overflow:hidden; }
.header { height:48px; background:var(--surface); border-bottom:1px solid var(--border); display:flex; align-items:center; padding:0 20px; gap:16px; flex-shrink:0; }
.header h1 { font-size:14px; font-weight:700; color:var(--gold); }
.header .sep { color:var(--border); }
.header .view-title { font-size:13px; color:var(--text); font-weight:600; }
.header .spacer { flex:1; }
.header .refresh-info { font-size:11px; color:var(--muted); font-family:var(--font); }
.header select { background:var(--surface2); color:var(--text); border:1px solid var(--border); padding:4px 8px; border-radius:4px; font-size:12px; }

.content { flex:1; overflow-y:auto; padding:20px; }
.view { display:none; }
.view.active { display:block; }

/* KPI Cards */
.kpis { display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:12px; margin-bottom:20px; }
.kpi { background:var(--surface); border:1px solid var(--border); border-radius:10px; padding:16px; text-align:center; }
.kpi .val { font-size:1.8rem; font-weight:800; font-family:var(--font); }
.kpi .lbl { font-size:11px; color:var(--muted); margin-top:4px; text-transform:uppercase; letter-spacing:.5px; }
.kpi.gold .val { color:var(--gold); } .kpi.cyan .val { color:var(--cyan); }
.kpi.emerald .val { color:var(--emerald); } .kpi.red .val { color:var(--red); }
.kpi.violet .val { color:var(--violet); } .kpi.blue .val { color:var(--blue); }

/* Tables */
table { width:100%; border-collapse:collapse; background:var(--surface); border-radius:8px; overflow:hidden; }
th { background:var(--surface2); color:var(--muted); font-size:11px; text-transform:uppercase; letter-spacing:.5px; padding:10px 14px; text-align:left; cursor:pointer; user-select:none; }
th:hover { color:var(--text); }
td { padding:9px 14px; border-bottom:1px solid var(--border); font-size:13px; font-family:var(--font); }
tr:hover { background:rgba(245,158,11,.03); }
.badge { display:inline-block; padding:2px 8px; border-radius:10px; font-size:11px; font-weight:600; }
.badge-ok { background:rgba(16,185,129,.15); color:var(--emerald); }
.badge-warn { background:rgba(245,158,11,.15); color:var(--gold); }
.badge-crit { background:rgba(239,68,68,.15); color:var(--red); }
.badge-block { background:rgba(239,68,68,.2); color:var(--red); }

/* Health bar */
.health-bar { width:80px; height:6px; background:var(--surface2); border-radius:3px; overflow:hidden; display:inline-block; vertical-align:middle; margin-right:6px; }
.health-bar .fill { height:100%; border-radius:3px; }

/* Alert list */
.alert-item { background:var(--surface); border:1px solid var(--border); border-radius:8px; padding:12px 16px; margin-bottom:8px; display:flex; align-items:center; gap:12px; }
.alert-dot { width:8px; height:8px; border-radius:50%; flex-shrink:0; }
.alert-dot.crit { background:var(--red); } .alert-dot.warn { background:var(--gold); } .alert-dot.info { background:var(--cyan); }
.alert-msg { font-size:13px; flex:1; } .alert-time { font-size:11px; color:var(--muted); font-family:var(--font); }

/* Filters */
.filters { display:flex; gap:8px; margin-bottom:16px; flex-wrap:wrap; }
.filters input, .filters select { background:var(--surface); border:1px solid var(--border); color:var(--text); padding:6px 12px; border-radius:6px; font-size:12px; font-family:var(--font); }
.filters input { min-width:200px; }

/* Section titles */
.section { font-size:14px; font-weight:700; color:var(--text); margin:20px 0 12px; }
.section:first-child { margin-top:0; }

/* Scrollbar */
::-webkit-scrollbar { width:6px; } ::-webkit-scrollbar-track { background:var(--bg); }
::-webkit-scrollbar-thumb { background:var(--border); border-radius:3px; }
</style>
</head>
<body>

<!-- Sidebar -->
<div class="sidebar">
  <div class="logo">AEGIS</div>
  <button class="nav-btn active" onclick="showView('overview')" title="Overview">&#9632;</button>
  <button class="nav-btn" onclick="showView('agents')" title="Agents">&#9786;</button>
  <button class="nav-btn" onclick="showView('guard')" title="Guard">&#9888;</button>
  <button class="nav-btn" onclick="showView('predictions')" title="Predictions">&#9733;</button>
  <button class="nav-btn" onclick="showView('traces')" title="Traces">&#9776;</button>
</div>

<!-- Main -->
<div class="main">
  <div class="header">
    <h1>AEGIS-X5</h1>
    <span class="sep">|</span>
    <span class="view-title" id="view-title">Overview</span>
    <div class="spacer"></div>
    <select id="ws-filter" onchange="refresh()"><option value="">All Workspaces</option></select>
    <span class="refresh-info" id="refresh-info">...</span>
  </div>

  <div class="content">
    <!-- OVERVIEW -->
    <div class="view active" id="v-overview">
      <div class="kpis" id="overview-kpis"></div>
      <div class="section">Active Alerts</div>
      <div id="overview-alerts"><div style="color:var(--muted);font-size:13px">Loading...</div></div>
      <div class="section">Recent Traces</div>
      <table><thead><tr><th>Name</th><th>Status</th><th>Latency</th><th>Workspace</th><th>Time</th></tr></thead>
      <tbody id="overview-traces"></tbody></table>
    </div>

    <!-- AGENTS -->
    <div class="view" id="v-agents">
      <div class="filters">
        <input type="text" id="agent-search" placeholder="Search agents..." oninput="renderAgents()">
        <select id="agent-status-filter" onchange="renderAgents()">
          <option value="">All Status</option><option value="healthy">Healthy</option>
          <option value="warning">Warning</option><option value="critical">Critical</option>
        </select>
      </div>
      <table><thead><tr>
        <th onclick="sortAgents('name')">Agent</th><th onclick="sortAgents('health')">Health</th>
        <th onclick="sortAgents('traces')">Traces</th><th onclick="sortAgents('latency')">Latency p95</th>
        <th onclick="sortAgents('blocks')">Guard Blocks</th><th onclick="sortAgents('last')">Last Seen</th>
      </tr></thead><tbody id="agents-body"></tbody></table>
    </div>

    <!-- GUARD -->
    <div class="view" id="v-guard">
      <div class="kpis" id="guard-kpis"></div>
      <div class="section">Recent Guard Events</div>
      <table><thead><tr><th>Agent</th><th>Level</th><th>Rule</th><th>Message</th><th>Time</th></tr></thead>
      <tbody id="guard-events"></tbody></table>
    </div>

    <!-- PREDICTIONS -->
    <div class="view" id="v-predictions">
      <div class="kpis" id="pred-kpis"></div>
      <div class="section">Health Score Distribution</div>
      <div id="health-dist" style="display:flex;gap:4px;align-items:end;height:120px;margin-bottom:20px;"></div>
      <div class="section">Recent Anomalies</div>
      <div id="pred-anomalies"></div>
    </div>

    <!-- TRACES -->
    <div class="view" id="v-traces">
      <div class="filters">
        <input type="text" id="trace-search" placeholder="Filter by name..." oninput="renderTraces()">
        <select id="trace-status-filter" onchange="renderTraces()">
          <option value="">All Status</option><option value="ok">OK</option><option value="error">Error</option>
        </select>
      </div>
      <table><thead><tr>
        <th>Name</th><th>Status</th><th>Latency</th><th>Workspace</th><th>Time</th><th>Details</th>
      </tr></thead><tbody id="traces-body"></tbody></table>
    </div>
  </div>
</div>

<script>
// State
let DATA = { overview: {}, agents: [], guard: {}, predictions: {}, traces: [] };
let agentSort = { key: 'name', asc: true };
const views = ['overview','agents','guard','predictions','traces'];
const viewTitles = { overview:'Overview', agents:'Agents', guard:'Guard', predictions:'Predictions', traces:'Traces' };

function showView(name) {
  views.forEach(v => {
    document.getElementById('v-'+v).classList.toggle('active', v===name);
  });
  document.querySelectorAll('.nav-btn').forEach((btn,i) => btn.classList.toggle('active', views[i]===name));
  document.getElementById('view-title').textContent = viewTitles[name];
  refresh();
}

function esc(s) { const d=document.createElement('div'); d.textContent=s; return d.innerHTML; }
function ago(ts) {
  const s=Math.floor(Date.now()/1000-ts);
  if(s<60) return s+'s ago'; if(s<3600) return Math.floor(s/60)+'m ago';
  if(s<86400) return Math.floor(s/3600)+'h ago'; return Math.floor(s/86400)+'d ago';
}
function healthColor(s) { return s>=80?'var(--emerald)':s>=60?'var(--gold)':'var(--red)'; }
function healthLabel(s) { return s>=80?'healthy':s>=60?'warning':'critical'; }
function badgeClass(s) { return s>=80?'badge-ok':s>=60?'badge-warn':'badge-crit'; }

async function fetchJSON(url) {
  const ws = document.getElementById('ws-filter').value;
  const sep = url.includes('?')?'&':'?';
  const full = ws ? url+sep+'workspace='+encodeURIComponent(ws) : url;
  const r = await fetch(full);
  return r.json();
}

async function refresh() {
  try {
    const [ov, ag, gu, pr, tr] = await Promise.all([
      fetchJSON('/api/v1/dashboard/overview'),
      fetchJSON('/api/v1/dashboard/agents'),
      fetchJSON('/api/v1/dashboard/guard'),
      fetchJSON('/api/v1/dashboard/predictions'),
      fetchJSON('/api/v1/dashboard/traces?limit=200'),
    ]);
    DATA = { overview:ov, agents:ag.agents||[], guard:gu, predictions:pr, traces:tr.traces||[] };
    renderAll();
    // Update workspace dropdown
    const sel = document.getElementById('ws-filter');
    const cur = sel.value;
    const wss = [...new Set(DATA.traces.map(t=>t.workspace))].sort();
    sel.innerHTML = '<option value="">All Workspaces</option>' + wss.map(w=>`<option value="${esc(w)}"${w===cur?' selected':''}>${esc(w)}</option>`).join('');
    document.getElementById('refresh-info').textContent = new Date().toLocaleTimeString();
  } catch(e) { console.error('Refresh error:', e); }
}

function renderAll() { renderOverview(); renderAgents(); renderGuard(); renderPredictions(); renderTraces(); }

// --- OVERVIEW ---
function renderOverview() {
  const o = DATA.overview;
  document.getElementById('overview-kpis').innerHTML = [
    kpi(o.total_traces||0,'Total Traces','cyan'),
    kpi(o.active_agents||0,'Active Agents','gold'),
    kpi((o.avg_health||0).toFixed(0),'Avg Health','emerald'),
    kpi('$'+(o.total_cost||0).toFixed(2),'Cost / Period','violet'),
    kpi(o.guard_blocks||0,'Guard Blocks','red'),
    kpi((o.avg_faithfulness||0).toFixed(2),'Avg Faithfulness','blue'),
  ].join('');

  // Alerts
  const alerts = o.alerts || [];
  const ah = document.getElementById('overview-alerts');
  if (!alerts.length) { ah.innerHTML='<div style="color:var(--muted);font-size:13px;padding:8px">No active alerts</div>'; }
  else { ah.innerHTML = alerts.slice(0,10).map(a =>
    `<div class="alert-item"><div class="alert-dot ${a.severity==='critical'?'crit':a.severity==='warning'?'warn':'info'}"></div><div class="alert-msg">${esc(a.message)}</div><div class="alert-time">${esc(a.agent||'')}</div></div>`
  ).join(''); }

  // Recent traces
  const tbody = document.getElementById('overview-traces');
  const recent = DATA.traces.slice(0,15);
  tbody.innerHTML = recent.map(t => `<tr>
    <td>${esc(t.name)}</td>
    <td><span class="badge ${t.status==='ok'?'badge-ok':'badge-crit'}">${t.status}</span></td>
    <td>${t.duration_ms.toFixed(0)} ms</td><td>${esc(t.workspace)}</td><td>${ago(t.created_at)}</td>
  </tr>`).join('');
}

// --- AGENTS ---
function renderAgents() {
  const search = (document.getElementById('agent-search').value||'').toLowerCase();
  const statusFilter = document.getElementById('agent-status-filter').value;
  let agents = DATA.agents.filter(a => {
    if (search && !a.name.toLowerCase().includes(search)) return false;
    if (statusFilter && healthLabel(a.health_score)!==statusFilter) return false;
    return true;
  });
  // Sort
  agents.sort((a,b) => {
    let va,vb;
    switch(agentSort.key) {
      case 'health': va=a.health_score; vb=b.health_score; break;
      case 'traces': va=a.total_traces; vb=b.total_traces; break;
      case 'latency': va=a.avg_latency_ms; vb=b.avg_latency_ms; break;
      case 'blocks': va=a.guard_blocks; vb=b.guard_blocks; break;
      case 'last': va=a.last_seen||0; vb=b.last_seen||0; break;
      default: va=a.name; vb=b.name;
    }
    if (typeof va==='string') return agentSort.asc?va.localeCompare(vb):vb.localeCompare(va);
    return agentSort.asc?va-vb:vb-va;
  });
  document.getElementById('agents-body').innerHTML = agents.map(a => {
    const hc = healthColor(a.health_score);
    const pct = Math.min(100,Math.max(0,a.health_score));
    return `<tr>
      <td>${esc(a.name)}</td>
      <td><div class="health-bar"><div class="fill" style="width:${pct}%;background:${hc}"></div></div>
          <span style="color:${hc};font-weight:600">${a.health_score.toFixed(0)}</span></td>
      <td>${a.total_traces}</td><td>${a.avg_latency_ms.toFixed(0)} ms</td>
      <td>${a.guard_blocks}</td><td>${a.last_seen?ago(a.last_seen):'—'}</td>
    </tr>`;
  }).join('');
}
function sortAgents(key) { if(agentSort.key===key) agentSort.asc=!agentSort.asc; else { agentSort.key=key; agentSort.asc=true; } renderAgents(); }

// --- GUARD ---
function renderGuard() {
  const g = DATA.guard;
  document.getElementById('guard-kpis').innerHTML = [
    kpi(g.total_blocks||0,'Total Blocks','red'),
    kpi(g.pii_blocks||0,'PII Detected','orange'),
    kpi(g.injection_blocks||0,'Injections','violet'),
    kpi(g.hallucination_blocks||0,'Hallucinations','cyan'),
  ].join('');
  const events = g.events || [];
  document.getElementById('guard-events').innerHTML = events.slice(0,30).map(e => `<tr>
    <td>${esc(e.agent||e.name||'')}</td>
    <td><span class="badge badge-block">${esc(e.level||'N4')}</span></td>
    <td>${esc(e.rule||'')}</td><td style="max-width:400px;overflow:hidden;text-overflow:ellipsis">${esc(e.message||e.error||'')}</td>
    <td>${e.time?ago(e.time):'—'}</td>
  </tr>`).join('');
}

// --- PREDICTIONS ---
function renderPredictions() {
  const p = DATA.predictions;
  document.getElementById('pred-kpis').innerHTML = [
    kpi((p.avg_health||0).toFixed(0),'Avg Health Score','emerald'),
    kpi(p.drift_alerts||0,'Drift Alerts','gold'),
    kpi(p.anomaly_count||0,'Anomalies','red'),
    kpi(p.predictions_count||0,'Active Predictions','violet'),
  ].join('');

  // Health distribution histogram
  const dist = p.health_distribution || {};
  const hd = document.getElementById('health-dist');
  const maxV = Math.max(1, ...Object.values(dist));
  hd.innerHTML = Object.entries(dist).map(([range,count]) => {
    const h = Math.max(4, (count/maxV)*100);
    const color = range.includes('80')?'var(--emerald)':range.includes('60')?'var(--gold)':'var(--red)';
    return `<div style="flex:1;text-align:center"><div style="background:${color};height:${h}px;border-radius:3px 3px 0 0;margin:0 2px"></div><div style="font-size:10px;color:var(--muted);margin-top:4px">${range}</div><div style="font-size:12px;font-weight:600;color:var(--text)">${count}</div></div>`;
  }).join('');

  // Anomalies
  const anomalies = p.anomalies || [];
  document.getElementById('pred-anomalies').innerHTML = anomalies.length
    ? anomalies.slice(0,10).map(a => `<div class="alert-item"><div class="alert-dot crit"></div><div class="alert-msg">${esc(a.message||a.metric+': '+a.direction)}</div><div class="alert-time">${esc(a.agent||'')}</div></div>`).join('')
    : '<div style="color:var(--muted);font-size:13px;padding:8px">No anomalies detected</div>';
}

// --- TRACES ---
function renderTraces() {
  const search = (document.getElementById('trace-search').value||'').toLowerCase();
  const statusFilter = document.getElementById('trace-status-filter').value;
  let traces = DATA.traces.filter(t => {
    if (search && !t.name.toLowerCase().includes(search)) return false;
    if (statusFilter && t.status!==statusFilter) return false;
    return true;
  });
  document.getElementById('traces-body').innerHTML = traces.slice(0,200).map(t => {
    const attrs = typeof t.attributes==='string'?JSON.parse(t.attributes||'{}'):t.attributes||{};
    const details = Object.entries(attrs).slice(0,6).map(([k,v])=>`${k}=${v}`).join(', ');
    return `<tr>
      <td>${esc(t.name)}</td>
      <td><span class="badge ${t.status==='ok'?'badge-ok':'badge-crit'}">${t.status}</span></td>
      <td>${t.duration_ms.toFixed(0)} ms</td><td>${esc(t.workspace)}</td><td>${ago(t.created_at)}</td>
      <td style="font-size:11px;color:var(--muted);max-width:300px;overflow:hidden;text-overflow:ellipsis">${esc(details)}</td>
    </tr>`;
  }).join('');
}

function kpi(val,label,color) {
  return `<div class="kpi ${color}"><div class="val">${val}</div><div class="lbl">${label}</div></div>`;
}

// Init
refresh();
setInterval(refresh, 5000);
</script>
</body>
</html>
"""
