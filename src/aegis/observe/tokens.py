"""Token extraction — multi-format parser for LLM responses."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TokenUsage:
    """Normalised token counts extracted from any LLM response."""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

    def __post_init__(self) -> None:
        if self.total_tokens == 0 and (self.input_tokens or self.output_tokens):
            object.__setattr__(self, "total_tokens", self.input_tokens + self.output_tokens)


# ---------------------------------------------------------------------------
# Extraction strategies (no SDK imports — pure dict parsing)
# ---------------------------------------------------------------------------


def _extract_openai(data: dict[str, Any]) -> TokenUsage | None:
    """OpenAI-style: response.usage.{prompt_tokens, completion_tokens, total_tokens}."""
    usage = data.get("usage")
    if not isinstance(usage, dict):
        return None
    prompt = usage.get("prompt_tokens")
    completion = usage.get("completion_tokens")
    if prompt is None and completion is None:
        return None
    return TokenUsage(
        input_tokens=prompt or 0,
        output_tokens=completion or 0,
        total_tokens=usage.get("total_tokens", 0),
    )


def _extract_anthropic(data: dict[str, Any]) -> TokenUsage | None:
    """Anthropic-style: response.usage.{input_tokens, output_tokens}."""
    usage = data.get("usage")
    if not isinstance(usage, dict):
        return None
    inp = usage.get("input_tokens")
    out = usage.get("output_tokens")
    if inp is None and out is None:
        return None
    return TokenUsage(
        input_tokens=inp or 0,
        output_tokens=out or 0,
    )


def _extract_generic(data: dict[str, Any]) -> TokenUsage | None:
    """Flat dict with input_tokens / output_tokens / total_tokens at top level."""
    inp = data.get("input_tokens")
    out = data.get("output_tokens")
    total = data.get("total_tokens")
    if inp is None and out is None and total is None:
        return None
    return TokenUsage(
        input_tokens=inp or 0,
        output_tokens=out or 0,
        total_tokens=total or 0,
    )


_EXTRACTORS = [_extract_openai, _extract_anthropic, _extract_generic]


def extract_tokens(response: Any) -> TokenUsage:
    """Extract token usage from an LLM response (dict or object with __dict__).

    Tries OpenAI, Anthropic, then generic flat-dict formats.
    Returns a zero-valued :class:`TokenUsage` if nothing matches.
    """
    if not isinstance(response, dict):
        if hasattr(response, "model_dump"):
            data = response.model_dump()
        elif hasattr(response, "__dict__"):
            data = response.__dict__
        else:
            return TokenUsage()
        # Also convert nested objects
        for key in ("usage",):
            val = data.get(key)
            if val is not None and not isinstance(val, dict):
                if hasattr(val, "model_dump"):
                    data[key] = val.model_dump()
                elif hasattr(val, "__dict__"):
                    data[key] = val.__dict__
    else:
        data = response

    for extractor in _EXTRACTORS:
        result = extractor(data)
        if result is not None:
            return result
    return TokenUsage()
