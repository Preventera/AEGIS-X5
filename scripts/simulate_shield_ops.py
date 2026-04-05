"""SHIELD-OPS-X5 Data Simulator — generates realistic traces for dashboard demo.

Populates the local SQLite database with 1000+ traces across all 21 platforms,
simulating realistic latencies, costs, guard events, and anomalies.

Usage::

    python scripts/simulate_shield_ops.py
    aegis dashboard  # open http://localhost:4005
"""

from __future__ import annotations

import math
import random
import sys
import time
from pathlib import Path

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from aegis.core.trace import Span, SpanStatus
from aegis.local.store import LocalStore
from aegis.tenants.shield_ops import ShieldOpsTenant


# ---------------------------------------------------------------------------
# Simulation parameters
# ---------------------------------------------------------------------------

TRACES_PER_PLATFORM_LIVE = 80         # ~80 traces per live platform
TRACES_PER_PLATFORM_PROTOTYPE = 20    # ~20 traces per prototype
SIMULATION_DAYS = 14                  # spread over 14 days
ERROR_RATE = 0.04                     # 4% error rate
GUARD_BLOCK_RATE = 0.03               # 3% guard blocks
HALLUCINATION_RATE = 0.02             # 2% hallucination detections

# Model cost profiles (cost per 1K tokens)
MODEL_PROFILES = {
    "claude-sonnet": {"cost_per_1k": 0.003, "avg_tokens": 1200, "latency_base": 150},
    "claude-opus": {"cost_per_1k": 0.015, "avg_tokens": 2000, "latency_base": 400},
    "gpt-4o": {"cost_per_1k": 0.005, "avg_tokens": 1500, "latency_base": 200},
    "gpt-4o-mini": {"cost_per_1k": 0.00015, "avg_tokens": 800, "latency_base": 80},
    "llama-3.1-70b": {"cost_per_1k": 0.0009, "avg_tokens": 1000, "latency_base": 120},
}

# Platform-specific model assignments
PLATFORM_MODELS = {
    "edgy": ["claude-opus", "claude-sonnet"],
    "literacia": ["claude-opus", "claude-sonnet"],
    "safefleet": ["gpt-4o-mini", "gpt-4o"],
    "visionguard": ["gpt-4o", "claude-sonnet"],
    "chemwatch": ["claude-sonnet", "gpt-4o"],
    "ergosense": ["gpt-4o-mini"],
    "noisemap": ["gpt-4o-mini"],
    "confinedai": ["claude-sonnet", "gpt-4o"],
    "heightsafe": ["claude-sonnet"],
    "lockoutpro": ["gpt-4o-mini", "claude-sonnet"],
    "firewatch": ["claude-sonnet", "gpt-4o"],
    "trainforce": ["gpt-4o-mini", "gpt-4o"],
    "incidentiq": ["claude-opus", "claude-sonnet"],
    "auditshield": ["claude-sonnet"],
    "wellnessai": ["gpt-4o-mini"],
    "enviroguard": ["gpt-4o-mini"],
    "contractorsafe": ["gpt-4o-mini"],
    "ppetracker": ["gpt-4o-mini", "claude-sonnet"],
    "riskmatrix": ["claude-sonnet", "claude-opus"],
    "regwatch": ["claude-sonnet", "gpt-4o", "llama-3.1-70b"],
    "emergencyops": ["claude-opus", "claude-sonnet", "gpt-4o"],
}

# Trace operation types per platform type
OPERATION_TYPES = {
    "default": ["query", "analyze", "summarize", "classify", "generate"],
    "edgy": ["compliance-check", "policy-audit", "risk-assess", "safety-review", "governance-scan"],
    "literacia": ["doc-analyze", "intel-extract", "trend-detect", "source-verify", "brief-generate"],
    "visionguard": ["image-classify", "ppe-detect", "zone-monitor", "anomaly-scan", "alert-generate"],
    "incidentiq": ["incident-classify", "root-cause", "corrective-action", "timeline-build", "report-generate"],
    "regwatch": ["regulation-scan", "compliance-check", "change-detect", "impact-assess", "alert-generate"],
    "emergencyops": ["scenario-assess", "resource-allocate", "comms-generate", "evac-plan", "triage-classify"],
}


# ---------------------------------------------------------------------------
# Simulation logic
# ---------------------------------------------------------------------------

def _generate_trace(
    platform_code: str,
    model: str,
    operation: str,
    base_time: float,
    day_offset: float,
) -> Span:
    """Generate a single realistic trace span."""
    profile = MODEL_PROFILES[model]

    # Latency with realistic variation + occasional spikes
    base_latency = profile["latency_base"]
    latency_ms = base_latency * random.lognormvariate(0, 0.3)
    # 5% chance of latency spike
    if random.random() < 0.05:
        latency_ms *= random.uniform(3, 8)
    latency_s = latency_ms / 1000.0

    # Tokens with variation
    tokens = int(profile["avg_tokens"] * random.lognormvariate(0, 0.25))
    input_tokens = int(tokens * random.uniform(0.3, 0.5))
    output_tokens = tokens - input_tokens

    # Cost
    cost = tokens * profile["cost_per_1k"] / 1000.0

    # Status determination
    is_error = random.random() < ERROR_RATE
    is_guard_block = random.random() < GUARD_BLOCK_RATE
    is_hallucination = random.random() < HALLUCINATION_RATE

    status = SpanStatus.OK
    error_msg = None
    guard_status = "PASS"

    if is_error:
        status = SpanStatus.ERROR
        error_msg = random.choice([
            "LLM timeout exceeded",
            "Rate limit reached",
            "Context window overflow",
            "API connection error",
            "Token limit exceeded",
        ])
    elif is_guard_block:
        status = SpanStatus.ERROR
        guard_status = "BLOCK"
        error_msg = random.choice([
            "Guard N4: Safety assertion violation detected",
            "Guard N4: Hazard minimization blocked",
            "Guard N3: Missing PPE recommendation",
            "Guard N3: CNESST reference required",
            "Guard N4: Dangerous procedure bypass detected",
        ])
    elif is_hallucination:
        guard_status = "WARN"

    # Faithfulness score (slightly degrading over time for drift simulation)
    base_faith = 0.96
    drift_factor = day_offset / SIMULATION_DAYS * 0.03  # 3% drift over 14 days
    faithfulness = max(0.85, base_faith - drift_factor + random.gauss(0, 0.015))

    # Timestamps
    timestamp = base_time + day_offset * 86400 + random.uniform(0, 86400)
    start_time = timestamp
    end_time = timestamp + latency_s

    span = Span(
        name=f"{platform_code}:{operation}",
        workspace="shield-ops-x5",
        tenant_id="shield-ops",
        status=status,
        start_time=start_time,
        end_time=end_time,
        error=error_msg,
    )

    span.set_attribute("aegis.module", "observe")
    span.set_attribute("platform", platform_code)
    span.set_attribute("model", model)
    span.set_attribute("operation", operation)
    span.set_attribute("tokens", tokens)
    span.set_attribute("input_tokens", input_tokens)
    span.set_attribute("output_tokens", output_tokens)
    span.set_attribute("cost", round(cost, 6))
    span.set_attribute("aegis.guard.status", guard_status)
    span.set_attribute("faithfulness", round(faithfulness, 4))

    return span


def simulate(
    db_path: str | None = None,
    quiet: bool = False,
) -> dict[str, int]:
    """Run the full simulation. Returns stats dict.

    Parameters
    ----------
    db_path : str | None
        SQLite database path. Defaults to ~/.aegis/local.db.
    quiet : bool
        Suppress output.
    """
    store = LocalStore(db_path=db_path)
    tenant = ShieldOpsTenant()

    if not quiet:
        print("SHIELD-OPS-X5 Simulator")
        print(f"  Platforms: {tenant.total_platforms}")
        print(f"  Agents:    {tenant.total_agents}")
        print()

    base_time = time.time() - SIMULATION_DAYS * 86400  # start 14 days ago
    total_traces = 0
    total_errors = 0
    total_blocks = 0

    for platform in tenant.platforms:
        count = TRACES_PER_PLATFORM_LIVE if platform.is_live else TRACES_PER_PLATFORM_PROTOTYPE
        models = PLATFORM_MODELS.get(platform.code, ["gpt-4o-mini"])
        ops = OPERATION_TYPES.get(platform.code, OPERATION_TYPES["default"])

        if not quiet:
            print(f"  Generating {count} traces for {platform.code}...", end="", flush=True)

        for _ in range(count):
            model = random.choice(models)
            operation = random.choice(ops)
            day_offset = random.uniform(0, SIMULATION_DAYS)

            span = _generate_trace(platform.code, model, operation, base_time, day_offset)
            store.store_span(span)
            total_traces += 1

            if span.status == SpanStatus.ERROR:
                total_errors += 1
            if span.attributes.get("aegis.guard.status") == "BLOCK":
                total_blocks += 1

        if not quiet:
            print(f" done")

    stats = {
        "total_traces": total_traces,
        "total_errors": total_errors,
        "total_blocks": total_blocks,
        "platforms": tenant.total_platforms,
    }

    if not quiet:
        print()
        print(f"Simulation complete:")
        print(f"  Total traces:  {stats['total_traces']}")
        print(f"  Errors:        {stats['total_errors']}")
        print(f"  Guard blocks:  {stats['total_blocks']}")
        print(f"  Database:      {store._db_path}")
        print()
        print("Run `aegis dashboard` to view the data.")

    return stats


if __name__ == "__main__":
    simulate()
