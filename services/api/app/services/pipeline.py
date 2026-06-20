"""Orchestration pipeline (M03/M04/M10): requirement -> stories -> prioritize -> code+tests -> PR.

Token-safe: each step sends a compact context (not the whole project) and runs a single,
budgeted LLM call via app.ai.llm. Code generation runs as a background task and writes its
result to a GitHub branch + PR when a repo and token are configured; otherwise the generated
files are stored on the run for in-app review.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from sqlmodel import Session, select

from app.ai import llm
from app.core.crypto import decrypt
from app.core.db import engine
from app.integrations.github import GitHubClient, parse_repo
from app.models import GenerationRun, ProviderCredential, Project, Requirement, Story


def _uuid_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")


# --------------------------------------------------------------------------- story generation
def generate_stories(session: Session, tenant_id: str, req: Requirement, actor_id: str) -> list[Story]:
    system = ("You are a senior product analyst. Break a requirement into clear, testable "
              "user stories. Return JSON: {\"stories\":[{\"title\",\"persona\",\"story\","
              "\"acceptance_criteria\":[],\"estimate\":int,\"dependencies\":[]}]}.")
    user = f"requirement: {req.title}\n\n{req.raw_text}"
    result = llm.complete_json(session, tenant_id, purpose="story_generation",
                               system=system, user=user, max_tokens=4000, effort="low")
    stories_data = result.data.get("stories", []) if isinstance(result.data, dict) else []
    created: list[Story] = []
    for s in stories_data:
        story = Story(
            tenant_id=tenant_id, project_id=req.project_id, requirement_id=req.id,
            title=str(s.get("title", req.title))[:300],
            persona=s.get("persona"),
            story_text=s.get("story"),
            acceptance_criteria_json=json.dumps(s.get("acceptance_criteria", [])),
            estimate=s.get("estimate") if isinstance(s.get("estimate"), int) else None,
            dependencies=json.dumps(s.get("dependencies", [])),
            priority=req.priority, status_code="STORY_DRAFT",
            created_by=actor_id, updated_by=actor_id,
        )
        session.add(story)
        session.flush()
        created.append(story)
    req.status = "analyzed"
    session.add(req)
    return created


# --------------------------------------------------------------------------- prioritization
def prioritize_stories(session: Session, tenant_id: str, project_id: str) -> list[Story]:
    stories = session.exec(
        select(Story).where(Story.tenant_id == tenant_id, Story.project_id == project_id,
                            Story.is_deleted == False)  # noqa: E712
    ).all()
    if not stories:
        return []
    compact = [{"id": s.id, "title": s.title, "estimate": s.estimate or 3,
                "deps": json.loads(s.dependencies or "[]")} for s in stories]
    system = ("You are a delivery lead. Prioritize stories by MVP value vs effort/dependency "
              "(RICE/MoSCoW). Return JSON: {\"ranking\":[{\"id\",\"rank\":int,\"mvp\":bool,"
              "\"score\":number,\"rationale\"}]}.")
    user = "stories: " + json.dumps(compact)
    result = llm.complete_json(session, tenant_id, purpose="prioritization",
                               system=system, user=user, max_tokens=3000, effort="low")
    ranking = {r["id"]: r for r in result.data.get("ranking", [])} if isinstance(result.data, dict) else {}
    by_id = {s.id: s for s in stories}
    for sid, r in ranking.items():
        s = by_id.get(sid)
        if not s:
            continue
        s.rank = int(r.get("rank", 0))
        s.mvp = bool(r.get("mvp", False))
        s.priority_score = float(r.get("score", 0) or 0)
        s.priority_rationale = r.get("rationale")
        session.add(s)
    return sorted(stories, key=lambda x: x.rank or 9999)


# --------------------------------------------------------------------------- code generation
def execute_generation_run(run_id: str) -> None:
    """Background entrypoint — opens its own DB session."""
    with Session(engine) as session:
        run = session.get(GenerationRun, run_id)
        if not run:
            return
        try:
            run.status = "running"
            session.add(run)
            session.commit()

            story = session.get(Story, run.story_id) if run.story_id else None
            project = session.get(Project, run.project_id)
            result = _generate_code(session, run.tenant_id, project, story)
            run.input_tokens, run.output_tokens = result.input_tokens, result.output_tokens
            run.provider, run.model = result.provider, result.model

            files = _collect_files(result.data)
            run.files_json = json.dumps(files)
            run.rationale = (result.data or {}).get("reasoning") if isinstance(result.data, dict) else None

            pr_url, branch, log = _publish(session, run, project, story, files)
            run.pr_url, run.branch, run.log = pr_url, branch, log
            run.status = "succeeded"
        except llm.BudgetExceeded as e:
            run.status = "failed"
            run.log = f"Blocked by token budget: {e}"
        except Exception as e:  # noqa: BLE001
            run.status = "failed"
            run.log = f"{type(e).__name__}: {e}"[:2000]
        session.add(run)
        session.commit()


def _generate_code(session: Session, tenant_id: str, project: Project | None, story: Story | None):
    stack = (project.tech_stack if project else None) or "Python + pytest"
    ac = json.loads(story.acceptance_criteria_json) if story else []
    system = ("You are a senior engineer. Implement the user story for the given stack. "
              "Return JSON: {\"files\":[{\"path\",\"language\",\"content\"}],"
              "\"tests\":[{\"path\",\"language\",\"content\"}],"
              "\"perf_test\":{\"path\",\"language\",\"content\"},\"reasoning\"}. "
              "Keep code minimal, runnable, and idiomatic.")
    user = (f"tech_stack: {stack}\n"
            f"title: {story.title if story else 'feature'}\n"
            f"story: {story.story_text if story else ''}\n"
            f"acceptance_criteria: {json.dumps(ac)}")
    return llm.complete_json(session, tenant_id, purpose="code_generation",
                             system=system, user=user, max_tokens=8000, effort="medium")


def _collect_files(data: object) -> list[dict]:
    files: list[dict] = []
    if not isinstance(data, dict):
        return files
    for key in ("files", "tests"):
        for f in data.get(key, []) or []:
            if f.get("path") and f.get("content") is not None:
                files.append({"path": f["path"], "language": f.get("language", ""),
                              "content": f["content"], "kind": key})
    perf = data.get("perf_test")
    if isinstance(perf, dict) and perf.get("path"):
        files.append({"path": perf["path"], "language": perf.get("language", ""),
                      "content": perf.get("content", ""), "kind": "perf"})
    return files


def _publish(session: Session, run: GenerationRun, project: Project | None,
             story: Story | None, files: list[dict]) -> tuple[str | None, str | None, str]:
    """Push to a GitHub branch + PR when configured; else leave files for in-app review."""
    if not project or not project.repo_url:
        return None, None, f"Generated {len(files)} file(s). No repo configured — review in-app."
    gh_cred = session.exec(
        select(ProviderCredential).where(
            ProviderCredential.tenant_id == run.tenant_id,
            ProviderCredential.provider == "github",
            ProviderCredential.is_active == True,  # noqa: E712
        )
    ).first()
    if not gh_cred:
        return None, None, f"Generated {len(files)} file(s). Add a GitHub token in Settings to open a PR."
    token = decrypt(gh_cred.secret_encrypted)
    if not token:
        return None, None, "GitHub token could not be read."

    owner, repo = parse_repo(project.repo_url)
    gh = GitHubClient(token)
    base = project.default_branch or "main"
    slug = re.sub(r"[^a-z0-9]+", "-", (story.title if story else "feature").lower()).strip("-")[:40]
    branch = f"ai/{slug}-{_uuid_now()}"
    gh.create_branch(owner, repo, base, branch)
    for f in files:
        gh.put_file(owner, repo, branch, f["path"], f["content"],
                    f"AI: add {f['path']} for {story.title if story else 'feature'}")
    body = (f"Generated by BuildPilot360 for story **{story.title if story else ''}**.\n\n"
            f"{run.rationale or ''}\n\nFiles: {', '.join(f['path'] for f in files)}\n\n"
            f"Model: {run.model} · tokens in/out: {run.input_tokens}/{run.output_tokens}")
    pr_url = gh.open_pr(owner, repo, base, branch,
                        f"AI: {story.title if story else 'feature'}", body)
    return pr_url, branch, f"Opened PR with {len(files)} file(s)."
