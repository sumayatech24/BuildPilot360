"""Cost-guarded, provider-neutral LLM gateway (M20).

- Uses the official Anthropic SDK for live calls (model is config/Settings driven).
- Hard guardrails to protect the user's quota: capped max_tokens, single-shot, a per-tenant
  monthly token budget that BLOCKS calls, and usage recorded on every call (NFR-043).
- When no provider key is configured (or provider == 'mock'), a deterministic MockProvider is
  used so the platform runs end-to-end with zero token spend (clearly flagged as simulation).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlmodel import Session, select

from app.core.config import settings
from app.core.crypto import decrypt
from app.models import LlmUsage, ProviderCredential


class BudgetExceeded(Exception):
    pass


@dataclass
class LlmResult:
    data: object
    text: str
    input_tokens: int
    output_tokens: int
    provider: str
    model: str
    simulated: bool


# --------------------------------------------------------------------------- providers
class BaseProvider:
    name = "base"

    def complete(self, system: str, user: str, max_tokens: int, effort: str) -> tuple[str, int, int]:
        raise NotImplementedError


class MockProvider(BaseProvider):
    """Deterministic, no network, no token spend. Returns purpose-shaped JSON."""

    name = "mock"

    def complete(self, system: str, user: str, max_tokens: int, effort: str) -> tuple[str, int, int]:
        purpose = _purpose_hint(system)
        title = _extract_title(user)
        if purpose == "story_generation":
            payload = {"stories": [
                {"title": f"{cap} {title}", "persona": persona,
                 "story": f"As a {persona}, I want to {cap.lower()} {title}.",
                 "acceptance_criteria": [
                     "Permission enforced", "Inputs validated", "Audited", "UI states shown"],
                 "estimate": est, "dependencies": []}
                for cap, persona, est in [
                    ("Create", "Admin", 3), ("View/search", "Product Owner", 2),
                    ("Update", "Business Analyst", 3), ("Delete/archive", "Delivery Manager", 2)]
            ]}
        elif purpose == "prioritization":
            ids = re.findall(r'"id"\s*:\s*"([^"]+)"', user)
            payload = {"ranking": [
                {"id": sid, "rank": i + 1, "mvp": i < max(1, len(ids) // 2),
                 "score": round(100 - i * 7, 1),
                 "rationale": "High business value, low dependency." if i < 2 else "Deferrable."}
                for i, sid in enumerate(ids)]}
        elif purpose == "code_generation":
            slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_") or "feature"
            payload = {
                "files": [
                    {"path": f"src/{slug}.py", "language": "python",
                     "content": f'"""{title}."""\n\n\ndef {slug}():\n    """TODO: implement {title}."""\n    return True\n'},
                ],
                "tests": [
                    {"path": f"tests/test_{slug}.py", "language": "python",
                     "content": f"from src.{slug} import {slug}\n\n\ndef test_{slug}():\n    assert {slug}() is True\n"},
                ],
                "perf_test": {"path": f"perf/{slug}_load.js", "language": "javascript",
                              "content": "import http from 'k6/http';\nexport default function () { http.get('http://localhost:8000/health'); }\n"},
                "reasoning": f"Scaffolded {title} with a unit test and a k6 load test (simulation).",
            }
        else:
            payload = {"result": "ok"}
        text = json.dumps(payload)
        # Rough token estimate for the simulated usage meter.
        return text, len(user) // 4, len(text) // 4


class AnthropicProvider(BaseProvider):
    name = "anthropic"

    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def complete(self, system: str, user: str, max_tokens: int, effort: str) -> tuple[str, int, int]:
        import anthropic  # imported lazily so the package isn't required for mock/dev

        client = anthropic.Anthropic(api_key=self.api_key)
        # Cost-safe: thinking off, final-answer-only, capped tokens, single request.
        sys_prompt = (system + "\n\nRespond with ONLY valid JSON — no preamble, no markdown "
                      "fences, no commentary or reasoning outside the JSON.")
        kwargs: dict = {
            "model": self.model,
            "max_tokens": max_tokens,
            "system": sys_prompt,
            "messages": [{"role": "user", "content": user}],
        }
        if effort in ("low", "medium", "high"):
            kwargs["output_config"] = {"effort": effort}
        resp = client.messages.create(**kwargs)
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        usage = resp.usage
        return text, int(getattr(usage, "input_tokens", 0)), int(getattr(usage, "output_tokens", 0))


# --------------------------------------------------------------------------- selection
def get_active_credential(session: Session, tenant_id: str, provider: str) -> ProviderCredential | None:
    return session.exec(
        select(ProviderCredential).where(
            ProviderCredential.tenant_id == tenant_id,
            ProviderCredential.provider == provider,
            ProviderCredential.is_active == True,  # noqa: E712
            ProviderCredential.is_deleted == False,  # noqa: E712
        )
    ).first()


def _select_provider(session: Session, tenant_id: str) -> BaseProvider:
    cred = get_active_credential(session, tenant_id, "anthropic")
    if cred:
        cfg = json.loads(cred.config_json or "{}")
        model = cfg.get("model") or settings.llm_default_model
        api_key = decrypt(cred.secret_encrypted)
        if api_key:
            return AnthropicProvider(api_key, model)
    return MockProvider()


# --------------------------------------------------------------------------- budget + usage
def _period() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _usage_row(session: Session, tenant_id: str) -> LlmUsage:
    row = session.exec(
        select(LlmUsage).where(LlmUsage.tenant_id == tenant_id, LlmUsage.period == _period())
    ).first()
    if not row:
        row = LlmUsage(tenant_id=tenant_id, period=_period())
        session.add(row)
        session.flush()
    return row


def check_budget(session: Session, tenant_id: str) -> None:
    row = _usage_row(session, tenant_id)
    if row.input_tokens + row.output_tokens >= settings.monthly_token_budget:
        raise BudgetExceeded(
            f"Monthly LLM token budget ({settings.monthly_token_budget:,}) reached. "
            "Raise MONTHLY_TOKEN_BUDGET or wait for next period."
        )


def _record(session: Session, tenant_id: str, in_tok: int, out_tok: int) -> None:
    row = _usage_row(session, tenant_id)
    row.input_tokens += in_tok
    row.output_tokens += out_tok
    row.calls += 1
    session.add(row)
    session.flush()


# --------------------------------------------------------------------------- entrypoint
def _extract_json(text: str):
    cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(cleaned)
    except Exception:  # noqa: BLE001
        m = re.search(r"(\{.*\}|\[.*\])", cleaned, re.DOTALL)
        if m:
            return json.loads(m.group(1))
        raise


def complete_json(
    session: Session,
    tenant_id: str,
    *,
    purpose: str,
    system: str,
    user: str,
    max_tokens: int | None = None,
    effort: str | None = None,
) -> LlmResult:
    """Run a single, budgeted, JSON-returning LLM call (or the mock)."""
    check_budget(session, tenant_id)
    provider = _select_provider(session, tenant_id)
    cap = min(max_tokens or settings.llm_max_output_tokens, settings.llm_max_output_tokens)
    eff = effort or settings.llm_effort
    tagged_system = f"[purpose:{purpose}]\n{system}"
    text, in_tok, out_tok = provider.complete(tagged_system, user, cap, eff)
    _record(session, tenant_id, in_tok, out_tok)
    data = _extract_json(text)
    model = getattr(provider, "model", provider.name)
    return LlmResult(data=data, text=text, input_tokens=in_tok, output_tokens=out_tok,
                     provider=provider.name, model=model, simulated=provider.name == "mock")


def _purpose_hint(system: str) -> str:
    m = re.search(r"\[purpose:([a-z_]+)\]", system)
    return m.group(1) if m else ""


def _extract_title(user: str) -> str:
    m = re.search(r"(?:title|requirement)\s*[:=]\s*(.+)", user, re.IGNORECASE)
    if m:
        return m.group(1).strip().strip('"').split("\n")[0][:80]
    return user.strip().split("\n")[0][:80] or "feature"
