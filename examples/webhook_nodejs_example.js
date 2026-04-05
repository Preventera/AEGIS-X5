/**
 * Example: Node.js agent sending traces to AEGIS-X5 via webhook.
 *
 * Start the AEGIS API first:
 *   make up
 *   # or: python -m aegis.cli dashboard
 *
 * Then run this script:
 *   node examples/webhook_nodejs_example.js
 */

const AEGIS_URL = process.env.AEGIS_URL || "http://localhost:4000";

async function sendTrace(agent, input, output, model, tokens) {
  const response = await fetch(`${AEGIS_URL}/webhook/trace`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      agent,
      input,
      output,
      model,
      tokens,
      latency_ms: Math.random() * 500 + 50,
      metadata: {
        language: "javascript",
        runtime: "node",
        version: process.version,
      },
    }),
  });

  const data = await response.json();
  console.log(`Trace sent: ${data.span_id} (${agent})`);
  return data;
}

async function validateOutput(output) {
  const response = await fetch(`${AEGIS_URL}/webhook/validate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ output }),
  });

  const data = await response.json();
  console.log(`Validation: ${data.passed ? "PASS" : "BLOCK"}`);
  return data;
}

async function main() {
  console.log("AEGIS-X5 Webhook Example (Node.js)\n");

  // Send traces from a simulated Node.js agent
  await sendTrace(
    "node-safety-agent",
    "What PPE is needed for welding?",
    "Welding requires a welding mask, safety glasses, leather gloves, and a fire-resistant apron.",
    "gpt-4o-mini",
    450
  );

  await sendTrace(
    "node-compliance-agent",
    "Is this chemical storage compliant?",
    "The storage follows WHMIS/SIMDUT requirements with proper labeling and SDS available.",
    "gpt-4o",
    680
  );

  // Validate an output through guard pipeline
  await validateOutput(
    "There is no risk when handling this chemical without gloves."
  );

  console.log("\nDone. Check `aegis dashboard` for traces.");
}

main().catch(console.error);
