"""Example: LangChain RAG pipeline with AEGIS-X5 observe + evaluate.

Usage::

    pip install aegis-x5 langchain langchain-openai
    python examples/langchain_rag.py
"""

from aegis import Aegis

aegis = Aegis(modules=["observe", "evaluate"])


@aegis.observe("rag-retrieve")
def retrieve(query: str) -> list[str]:
    """Simulate document retrieval."""
    docs = [
        "AEGIS-X5 provides observe, guard, and evaluate modules.",
        "The platform supports multi-tenant agent governance.",
        "Guard levels range from N1 (info) to N4 (critical block).",
    ]
    return [d for d in docs if any(w in d.lower() for w in query.lower().split())]


@aegis.observe("rag-generate")
def generate(query: str, context: list[str]) -> str:
    """Simulate LLM generation with retrieved context."""
    # In production, replace with: llm.invoke(prompt)
    return f"Based on {len(context)} documents: {context[0][:80]}..."


@aegis.observe("rag-pipeline")
def rag_pipeline(query: str) -> str:
    """Full RAG pipeline: retrieve + generate, fully traced."""
    docs = retrieve(query)
    if not docs:
        return "No relevant documents found."
    return generate(query, docs)


if __name__ == "__main__":
    result = rag_pipeline("What guard levels does AEGIS support?")
    print(f"\nAnswer: {result}")
    print("\nRun `aegis status` to see the traces.")
