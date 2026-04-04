"""Example: FastAPI endpoint protected by AEGIS-X5 guard.

Usage::

    pip install aegis-x5 fastapi uvicorn
    uvicorn examples.fastapi_endpoint:app --port 8000
    # Then: curl http://localhost:8000/ask?q=hello
"""

from aegis import Aegis

aegis = Aegis(modules=["observe", "guard"])


def _simulate_llm(query: str) -> str:
    """Simulate an LLM call (replace with real LLM in production)."""
    return f"Response to: {query}"


@aegis.protect("api-guard", level="N3")
@aegis.observe("api-ask")
def process_query(query: str) -> str:
    """Process a user query — observed and guarded by AEGIS."""
    return _simulate_llm(query)


# --- FastAPI app ---

try:
    from fastapi import FastAPI

    app = FastAPI(title="AEGIS-X5 Protected API")

    @app.get("/ask")
    async def ask(q: str = "hello") -> dict:
        """Endpoint protected by AEGIS guard + observe."""
        result = process_query(q)
        return {"query": q, "response": result}

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok", "aegis": "active", "mode": "local" if aegis.is_local else "cloud"}

except ImportError:
    # FastAPI not installed — provide a standalone fallback
    app = None

if __name__ == "__main__":
    if app is not None:
        import uvicorn

        print("Starting AEGIS-protected API on http://localhost:8000")
        uvicorn.run(app, host="0.0.0.0", port=8000)
    else:
        # Demo without FastAPI
        result = process_query("What is AEGIS-X5?")
        print(f"Result: {result}")
        print("\nRun `aegis status` to see the trace.")
