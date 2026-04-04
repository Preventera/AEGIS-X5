"""Example: CrewAI multi-agent team with AEGIS-X5 guard on each agent.

Usage::

    pip install aegis-x5 crewai
    python examples/crewai_team.py
"""

from aegis import Aegis

aegis = Aegis(modules=["observe", "guard"])


@aegis.protect("researcher-guard", level="N2")
@aegis.observe("researcher-agent")
def researcher(topic: str) -> str:
    """Research agent — gathers information on a topic."""
    # In production: crewai Agent with role="Researcher"
    return f"Research findings on '{topic}': AI governance is critical for safe deployment."


@aegis.protect("writer-guard", level="N2")
@aegis.observe("writer-agent")
def writer(research: str) -> str:
    """Writer agent — drafts content from research."""
    # In production: crewai Agent with role="Writer"
    return f"Draft report: {research[:60]}... [Full report follows]"


@aegis.protect("reviewer-guard", level="N3")
@aegis.observe("reviewer-agent")
def reviewer(draft: str) -> str:
    """Reviewer agent — validates the draft for quality and safety."""
    # In production: crewai Agent with role="Reviewer"
    return f"APPROVED: {draft[:50]}..."


@aegis.observe("crew-pipeline")
def run_crew(topic: str) -> str:
    """Orchestrate the crew: research -> write -> review."""
    research = researcher(topic)
    draft = writer(research)
    final = reviewer(draft)
    return final


if __name__ == "__main__":
    result = run_crew("AI agent governance best practices")
    print(f"\nFinal output: {result}")
    print("\nRun `aegis status` to see all agent traces.")
