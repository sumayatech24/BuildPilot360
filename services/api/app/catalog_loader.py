"""Load the committed blueprint.json into the catalog_items table (idempotent)."""
from __future__ import annotations

import json
from pathlib import Path

from sqlmodel import Session, delete, select

from app.models import CatalogItem

DATA_FILE = Path(__file__).resolve().parent / "data" / "blueprint.json"


def _first(row: dict, *keys: str) -> str | None:
    for k in keys:
        if k in row and row[k]:
            return row[k]
    return None


# Maps a JSON category -> function extracting (item_id, module_id, title, domain, phase, priority, status)
def _map(category: str, row: dict) -> dict:
    return {
        "module": dict(
            item_id=_first(row, "Module ID"), module_id=_first(row, "Module ID"),
            title=_first(row, "Module"), domain=_first(row, "Domain"),
            priority=_first(row, "MVP Priority"), phase=_first(row, "MVP Priority"),
        ),
        "feature": dict(
            item_id=_first(row, "Feature ID"), module_id=_first(row, "Module ID"),
            title=_first(row, "Feature Title"), domain=_first(row, "Domain"),
            phase=_first(row, "Phase"), priority=_first(row, "Priority"),
            status=_first(row, "Status"),
        ),
        "user_story": dict(
            item_id=_first(row, "Story ID"), module_id=_first(row, "Linked Feature ID"),
            title=_first(row, "User Story"), priority=_first(row, "Priority"),
        ),
        "nfr": dict(
            item_id=_first(row, "NFR ID"), title=_first(row, "Requirement"),
            domain=_first(row, "Category"),
        ),
        "api_integration": dict(
            item_id=_first(row, "Integration ID"), title=_first(row, "Provider"),
            domain=_first(row, "Category"), priority=_first(row, "Implementation Priority"),
        ),
        "screen": dict(
            item_id=_first(row, "Screen ID"), title=_first(row, "Screen Name"),
            domain=_first(row, "App"), priority=_first(row, "Priority"),
        ),
        "roadmap": dict(
            title=_first(row, "Milestone"), phase=_first(row, "Phase"),
        ),
        "database_table": dict(
            title=_first(row, "Table Name"), domain=_first(row, "Domain"),
        ),
        "ai_prompt": dict(title=_first(row, "Prompt Name", "Capability", "Module")),
        "build_prompt": dict(title=_first(row, "Prompt Name")),
        "token_safe": dict(title=_first(row, "Feature"), domain=_first(row, "Config Area"),
                           priority=_first(row, "Priority")),
        "verification_gate": dict(title=_first(row, "Verification Gate")),
        "milestone_type": dict(title=_first(row, "Milestone Type")),
        "gcp_matrix": dict(title=_first(row, "Provider/Tool"), domain=_first(row, "Area"),
                           priority=_first(row, "Priority")),
        "workflow_config": dict(title=_first(row, "Capability", "Feature", "Config Area", "Module")),
        "story_lifecycle": dict(title=_first(row, "Lifecycle Stage"),
                                item_id=_first(row, "Status Code")),
    }.get(category, dict(title=_first(row, "Title", "Name")))


# JSON key -> catalog category
SHEET_TO_CATEGORY = {
    "modules": "module",
    "features": "feature",
    "user_stories": "user_story",
    "nfrs": "nfr",
    "api_integrations": "api_integration",
    "screens": "screen",
    "roadmap": "roadmap",
    "database_schema": "database_table",
    "ai_prompts": "ai_prompt",
    "build_prompts": "build_prompt",
    "token_safe": "token_safe",
    "verification_matrix": "verification_gate",
    "milestone_planner": "milestone_type",
    "gcp_data_matrix": "gcp_matrix",
    "workflow_config": "workflow_config",
    "story_lifecycle": "story_lifecycle",
}


def load_catalog(session: Session, *, replace: bool = True) -> dict[str, int]:
    if not DATA_FILE.exists():
        print(f"[catalog] {DATA_FILE} missing — run scripts/ingest_blueprint.py first.")
        return {}

    blueprint = json.loads(DATA_FILE.read_text(encoding="utf-8"))

    existing = session.exec(select(CatalogItem.id)).first()
    if existing and not replace:
        return {"skipped": 1}
    if existing and replace:
        session.exec(delete(CatalogItem))
        session.flush()

    counts: dict[str, int] = {}
    for sheet_key, category in SHEET_TO_CATEGORY.items():
        rows = blueprint.get(sheet_key, [])
        for row in rows:
            mapped = _map(category, row)
            session.add(CatalogItem(
                category=category,
                item_id=mapped.get("item_id"),
                module_id=mapped.get("module_id"),
                title=(mapped.get("title") or "")[:500] or None,
                domain=mapped.get("domain"),
                phase=mapped.get("phase"),
                priority=mapped.get("priority"),
                status=mapped.get("status"),
                data_json=json.dumps(row, ensure_ascii=False),
            ))
        counts[category] = len(rows)
    session.flush()
    return counts
