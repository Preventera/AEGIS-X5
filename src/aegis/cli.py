"""AEGIS-X5 CLI — developer experience commands.

Commands::

    aegis init       Create aegis.yaml in the current project
    aegis status     Show registered agents and latest traces
    aegis dashboard  Launch the local mini dashboard (port 4005)
    aegis test       Run evaluations on the local golden set
"""

from __future__ import annotations

import argparse
import json
import sys
import textwrap
import time
from datetime import datetime, timezone
from pathlib import Path

_AEGIS_YAML_TEMPLATE = """\
# AEGIS-X5 configuration
# Docs: https://github.com/Preventera/AEGIS-X5

workspace: {workspace}
modules:
  - observe
  - guard
autonomy: monitor

# guard:
#   level: N2
#   validators:
#     - pii
#     - injection

# evaluate:
#   golden_set: tests/golden.yaml
"""


# ---------------------------------------------------------------------------
# aegis init
# ---------------------------------------------------------------------------

def cmd_init(args: argparse.Namespace) -> None:
    """Create aegis.yaml in the current directory."""
    target = Path.cwd() / "aegis.yaml"
    if target.exists() and not args.force:
        print(f"aegis.yaml already exists. Use --force to overwrite.", file=sys.stderr)
        sys.exit(1)

    workspace = args.workspace or Path.cwd().name
    content = _AEGIS_YAML_TEMPLATE.format(workspace=workspace)
    target.write_text(content, encoding="utf-8")
    print(f"Created aegis.yaml (workspace: {workspace})")
    print("Next: from aegis import Aegis; aegis = Aegis()")


# ---------------------------------------------------------------------------
# aegis status
# ---------------------------------------------------------------------------

def cmd_status(args: argparse.Namespace) -> None:
    """Show agents, recent traces, and stats from local store."""
    from aegis.local.store import LocalStore

    store = LocalStore(db_path=args.db)
    stats = store.stats(workspace=args.workspace)
    traces = store.recent_traces(limit=args.limit, workspace=args.workspace)
    workspaces = store.workspaces()

    print("=== AEGIS-X5 Status ===\n")

    # Workspaces
    if workspaces:
        print(f"Workspaces: {', '.join(workspaces)}")
    else:
        print("No traces recorded yet. Instrument your agent with @aegis.observe().")
        return

    # Stats
    print(f"\nTotal traces:   {stats['total_traces']}")
    print(f"Avg latency:    {stats['avg_latency_ms']:.1f} ms")
    print(f"Max latency:    {stats['max_latency_ms']:.1f} ms")
    print(f"Guard blocks:   {stats['guard_blocks']}")

    # Recent traces
    if traces:
        print(f"\n--- Last {min(len(traces), args.limit)} traces ---")
        print(f"{'Name':<30} {'Status':<8} {'Latency':>10} {'Time'}")
        print("-" * 72)
        for t in traces:
            ts = datetime.fromtimestamp(t["created_at"], tz=timezone.utc).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            print(
                f"{t['name']:<30} {t['status']:<8} {t['duration_ms']:>8.1f}ms  {ts}"
            )


# ---------------------------------------------------------------------------
# aegis dashboard
# ---------------------------------------------------------------------------

def cmd_dashboard(args: argparse.Namespace) -> None:
    """Launch the local mini dashboard on port 4005."""
    port = args.port

    try:
        from aegis.dashboard.server import create_app
    except ImportError as exc:
        print(
            "Dashboard requires extra dependencies. Install with:\n"
            "  pip install aegis-x5[dashboard]\n\n"
            f"Missing: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)

    app = create_app(db_path=args.db)
    print(f"\n  AEGIS-X5 Dashboard")
    print(f"  http://localhost:{port}\n")
    print("  Press Ctrl+C to stop.\n")

    try:
        import uvicorn

        uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")
    except ImportError:
        # Fallback: use the built-in ASGI server from starlette or wsgiref
        print("uvicorn not found — install with: pip install uvicorn", file=sys.stderr)
        print("Attempting fallback with built-in server...", file=sys.stderr)
        _run_fallback_server(app, port)


def _run_fallback_server(app: object, port: int) -> None:
    """Minimal fallback if uvicorn is not installed."""
    from http.server import HTTPServer, SimpleHTTPRequestHandler
    from aegis.dashboard.server import render_dashboard_html
    from aegis.local.store import LocalStore

    store = LocalStore()

    class Handler(SimpleHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path == "/" or self.path == "/dashboard":
                html = render_dashboard_html(store)
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(html.encode("utf-8"))
            elif self.path == "/api/traces":
                traces = store.recent_traces(limit=100)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(traces).encode("utf-8"))
            elif self.path == "/api/stats":
                stats = store.stats()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(stats).encode("utf-8"))
            else:
                self.send_error(404)

        def log_message(self, format: str, *log_args: object) -> None:
            pass  # suppress logs

    server = HTTPServer(("0.0.0.0", port), Handler)
    server.serve_forever()


# ---------------------------------------------------------------------------
# aegis test
# ---------------------------------------------------------------------------

def cmd_test(args: argparse.Namespace) -> None:
    """Run evaluations on the local golden set."""
    golden_path = Path(args.golden_set)
    if not golden_path.exists():
        print(f"Golden set not found: {golden_path}", file=sys.stderr)
        print("Create a golden set file or specify path with --golden-set", file=sys.stderr)
        sys.exit(1)

    try:
        import yaml

        with open(golden_path, encoding="utf-8") as f:
            cases = yaml.safe_load(f) or []
    except ImportError:
        print("PyYAML required for golden set loading. pip install pyyaml", file=sys.stderr)
        sys.exit(1)

    if not isinstance(cases, list):
        cases = cases.get("cases", cases.get("tests", []))

    print(f"Running {len(cases)} evaluation cases from {golden_path}...\n")

    passed = 0
    failed = 0
    for i, case in enumerate(cases, 1):
        name = case.get("name", f"case-{i}")
        expected = case.get("expected", "")
        actual = case.get("actual", case.get("output", ""))

        # Simple string match evaluation
        if str(expected).strip() == str(actual).strip():
            print(f"  PASS  {name}")
            passed += 1
        else:
            print(f"  FAIL  {name}")
            print(f"        expected: {expected!r}")
            print(f"        actual:   {actual!r}")
            failed += 1

    print(f"\n{passed} passed, {failed} failed out of {passed + failed} cases")
    if failed:
        sys.exit(1)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    """CLI entry point — ``aegis`` command."""
    parser = argparse.ArgumentParser(
        prog="aegis",
        description="AEGIS-X5 — Autonomous Agent Governance CLI",
    )
    parser.add_argument("--version", action="version", version=f"aegis-x5 {_get_version()}")
    sub = parser.add_subparsers(dest="command")

    # aegis init
    p_init = sub.add_parser("init", help="Create aegis.yaml in current project")
    p_init.add_argument("--workspace", "-w", default=None, help="Workspace name")
    p_init.add_argument("--force", "-f", action="store_true", help="Overwrite existing config")
    p_init.set_defaults(func=cmd_init)

    # aegis status
    p_status = sub.add_parser("status", help="Show agents and recent traces")
    p_status.add_argument("--workspace", "-w", default=None, help="Filter by workspace")
    p_status.add_argument("--limit", "-n", type=int, default=20, help="Number of traces")
    p_status.add_argument("--db", default=None, help="Path to local SQLite DB")
    p_status.set_defaults(func=cmd_status)

    # aegis dashboard
    p_dash = sub.add_parser("dashboard", help="Launch local mini dashboard")
    p_dash.add_argument("--port", "-p", type=int, default=4005, help="Port (default: 4005)")
    p_dash.add_argument("--db", default=None, help="Path to local SQLite DB")
    p_dash.set_defaults(func=cmd_dashboard)

    # aegis test
    p_test = sub.add_parser("test", help="Run evaluations on golden set")
    p_test.add_argument(
        "--golden-set", "-g", default="tests/golden.yaml", help="Path to golden set"
    )
    p_test.set_defaults(func=cmd_test)

    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        sys.exit(0)

    args.func(args)


def _get_version() -> str:
    try:
        from aegis import __version__

        return __version__
    except Exception:
        return "0.3.0"


if __name__ == "__main__":
    main()
