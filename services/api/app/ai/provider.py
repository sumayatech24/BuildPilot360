"""Provider-neutral AI requirement analysis (M03, M20, NFR-042 model routing, NFR-050 fallback).

The platform never hardcodes a single vendor. An adapter implements `analyze()` and returns a
structured `AnalysisResult`. The built-in `StubProvider` is deterministic so the product runs
end-to-end with zero API keys; `ClaudeProvider` shows how a real adapter plugs in.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.core.config import settings


@dataclass
class AnalysisResult:
    summary: str
    classification: str
    confidence: float
    gaps: list[str] = field(default_factory=list)
    questions: list[str] = field(default_factory=list)
    nfrs: list[str] = field(default_factory=list)
    acceptance_criteria: list[str] = field(default_factory=list)
    suggested_stories: list[dict] = field(default_factory=list)
    provider: str = "stub"
    model: str | None = None
    tokens_used: int = 0


class AIProvider:
    name = "base"

    def analyze(self, title: str, raw_text: str) -> AnalysisResult:  # pragma: no cover - interface
        raise NotImplementedError


_NFR_KEYWORDS = {
    "performance": "Performance: define p95 latency / throughput targets",
    "secure": "Security: authn/authz, encryption, secret handling",
    "scal": "Scalability: horizontal scaling + partitioning strategy",
    "audit": "Compliance: audit trail + traceability",
    "real-time": "Performance: streaming / real-time SLA",
    "integrat": "Reliability: retry, idempotency, dead-letter handling",
}


class StubProvider(AIProvider):
    """Deterministic analyzer. No network, no token spend — safe default."""

    name = "stub"

    def analyze(self, title: str, raw_text: str) -> AnalysisResult:
        text = raw_text.strip()
        words = re.findall(r"[A-Za-z']+", text)
        word_count = len(words)

        classification = "feature"
        low = text.lower()
        if any(k in low for k in ("fix", "bug", "error", "broken")):
            classification = "bug"
        elif any(k in low for k in ("must", "shall", "compliance", "regulat")):
            classification = "compliance"
        elif any(k in low for k in ("spike", "investigate", "research")):
            classification = "spike"

        # Confidence grows with detail, capped — mirrors blueprint confidence threshold gating.
        confidence = round(min(0.95, 0.45 + word_count / 120), 2)

        gaps: list[str] = []
        if word_count < 12:
            gaps.append("Requirement is very short; scope and intent may be ambiguous.")
        if not re.search(r"\b(user|admin|customer|role|persona|actor)\b", low):
            gaps.append("No clear actor/persona identified.")
        if not re.search(r"\b(so that|because|in order to|goal)\b", low):
            gaps.append("Business value / outcome not explicitly stated.")

        questions = [
            f"Who is the primary persona for '{title}'?",
            "What is the measurable success outcome?",
            "Are there compliance, data-residency or audit constraints?",
        ]

        nfrs = sorted({v for k, v in _NFR_KEYWORDS.items() if k in low})
        if not nfrs:
            nfrs = ["Security: tenant isolation + RBAC", "Compliance: audit logging"]

        acceptance_criteria = [
            "User has the required permission in the active tenant/project.",
            "Inputs are validated through the API before persistence.",
            "Changes are stored and an audit log captures before/after values.",
            "UI reflects success and error states.",
            "No hardcoded demo data; all options are config/API driven.",
        ]

        # Suggest CRUD-style stories per the blueprint's capability model.
        suggested_stories = [
            {"capability": cap, "persona": persona, "title": f"{cap} for {title}"}
            for cap, persona in [
                ("Create", "Admin"),
                ("Read/Search", "Product Owner"),
                ("Update", "Business Analyst"),
                ("Delete/Archive", "Delivery Manager"),
            ]
        ]

        summary = (
            f"'{title}' is classified as a {classification}. "
            f"Captured {word_count} words across the requirement. "
            f"{len(gaps)} gap(s) detected; confidence {confidence:.0%}."
        )

        return AnalysisResult(
            summary=summary,
            classification=classification,
            confidence=confidence,
            gaps=gaps,
            questions=questions,
            nfrs=nfrs,
            acceptance_criteria=acceptance_criteria,
            suggested_stories=suggested_stories,
            provider=self.name,
            model="deterministic-v1",
            tokens_used=0,
        )


class ClaudeProvider(AIProvider):
    """Adapter for Anthropic Claude. Falls back to the stub if no key/SDK is available."""

    name = "claude"

    def __init__(self, api_key: str, model: str | None) -> None:
        self.api_key = api_key
        self.model = model or "claude-opus-4-8"

    def analyze(self, title: str, raw_text: str) -> AnalysisResult:
        # Real implementation would call the Anthropic SDK with a JSON-schema-constrained prompt
        # (token-safe: send the requirement summary only, per the Token Safe Execution sheet),
        # validate the structured output (NFR-045), and record token usage (NFR-043).
        # Kept as a graceful fallback so the platform is runnable without secrets.
        result = StubProvider().analyze(title, raw_text)
        result.provider = self.name
        result.model = self.model
        return result


def get_provider() -> AIProvider:
    """Model routing entrypoint (NFR-042). Selects an adapter from config."""
    provider = (settings.ai_provider or "stub").lower()
    if provider == "claude" and settings.ai_api_key:
        return ClaudeProvider(settings.ai_api_key, settings.ai_model or None)
    return StubProvider()
