"""Example: SHIELD-OPS-X5 integration with AEGIS-X5.

Demonstrates how SHIELD-OPS-X5 uses AEGIS-X5 as its governance backend
with 21 AgenticX5 platforms and 500+ agents.

Usage::

    pip install aegis-x5
    python examples/shield_ops_integration.py
    aegis dashboard  # see the results
"""

from __future__ import annotations

import random
import time

from aegis import Aegis
from aegis.predict.health_score import HealthScore
from aegis.tenants.shield_ops import ShieldOpsTenant


def main() -> None:
    # --- Load tenant configuration ---
    tenant = ShieldOpsTenant()
    print(f"SHIELD-OPS-X5 loaded: {tenant.total_platforms} platforms, {tenant.total_agents} agents")
    print()

    # --- Initialize AEGIS with HSE template ---
    aegis = Aegis(workspace="shield-ops-x5", verbose=True)

    # --- Register and demonstrate each live platform ---
    health = HealthScore()

    for platform in tenant.live_platforms[:5]:  # demo first 5 live platforms
        print(f"--- {platform.name} ({platform.code}) ---")
        print(f"    Agents: {platform.agent_count} | Guard: {platform.guard_level}")
        print(f"    Modules: {', '.join(platform.modules)}")

        # Simulate an agent call with observe + protect
        @aegis.observe(f"{platform.code}-agent")
        @aegis.protect(f"{platform.code}-guard", level=platform.guard_level)
        def agent_call(prompt: str) -> str:
            time.sleep(random.uniform(0.05, 0.2))
            return f"[{platform.code}] Response to: {prompt}"

        # Execute a traced call
        result = agent_call(f"Safety check for {platform.name}")
        print(f"    Result: {result[:60]}...")

        # Compute health score
        snap = health.compute(platform.code, {
            "latency_p95": random.uniform(100, 500),
            "error_rate": random.uniform(0.0, 0.05),
            "faithfulness": random.uniform(0.92, 0.99),
            "guard_blocks": random.randint(0, 3),
            "cost_per_day": random.uniform(5, 30),
        })
        print(f"    Health: {snap.score:.0f}/100 ({snap.status.value})")
        print()

    # --- Summary ---
    print("=" * 60)
    summary = tenant.summary()
    print(f"Workspace:  {summary['workspace']}")
    print(f"Template:   {summary['template']}")
    print(f"Platforms:  {summary['total_platforms']} ({summary['live']} live, {summary['prototype']} prototype)")
    print(f"Agents:     {summary['total_agents']}")
    print()

    # --- Coverage matrix ---
    matrix = tenant.coverage_matrix()
    modules = ["observe", "guard", "evaluate", "collect", "remember", "predict", "loops"]
    header = f"{'Platform':<16}" + "".join(f"{m[:5]:>7}" for m in modules)
    print(header)
    print("-" * len(header))
    for code, coverage in matrix.items():
        row = f"{code:<16}" + "".join(
            f"{'  yes':>7}" if coverage[m] else f"{'   —':>7}" for m in modules
        )
        print(row)

    print()
    print("Run `aegis status` or `aegis dashboard` to see full metrics.")


if __name__ == "__main__":
    main()
