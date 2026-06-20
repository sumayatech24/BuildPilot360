"""GitHub REST integration (M11): create a branch, commit files, open a PR.

Uses httpx against api.github.com with a token from the tenant's 'github' ProviderCredential.
Token never leaves the server. repo_url accepts 'owner/repo' or a full GitHub URL.
"""
from __future__ import annotations

import base64
import re

import httpx

API = "https://api.github.com"


def parse_repo(repo_url: str) -> tuple[str, str]:
    s = repo_url.strip().removesuffix(".git")
    m = re.search(r"github\.com[/:]([^/]+)/([^/]+)", s)
    if m:
        return m.group(1), m.group(2)
    parts = s.split("/")
    if len(parts) >= 2:
        return parts[-2], parts[-1]
    raise ValueError(f"Cannot parse repo from '{repo_url}'")


class GitHubClient:
    def __init__(self, token: str) -> None:
        self._h = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def _get(self, url: str) -> dict:
        r = httpx.get(url, headers=self._h, timeout=30)
        r.raise_for_status()
        return r.json()

    def _post(self, url: str, body: dict) -> dict:
        r = httpx.post(url, headers=self._h, json=body, timeout=30)
        r.raise_for_status()
        return r.json()

    def _put(self, url: str, body: dict) -> dict:
        r = httpx.put(url, headers=self._h, json=body, timeout=30)
        r.raise_for_status()
        return r.json()

    def create_branch(self, owner: str, repo: str, base: str, new_branch: str) -> None:
        ref = self._get(f"{API}/repos/{owner}/{repo}/git/ref/heads/{base}")
        sha = ref["object"]["sha"]
        self._post(f"{API}/repos/{owner}/{repo}/git/refs",
                   {"ref": f"refs/heads/{new_branch}", "sha": sha})

    def put_file(self, owner: str, repo: str, branch: str, path: str,
                 content: str, message: str) -> None:
        url = f"{API}/repos/{owner}/{repo}/contents/{path}"
        existing_sha = None
        try:
            cur = httpx.get(url, headers=self._h, params={"ref": branch}, timeout=30)
            if cur.status_code == 200:
                existing_sha = cur.json().get("sha")
        except httpx.HTTPError:
            pass
        body = {
            "message": message,
            "content": base64.b64encode(content.encode()).decode(),
            "branch": branch,
        }
        if existing_sha:
            body["sha"] = existing_sha
        self._put(url, body)

    def open_pr(self, owner: str, repo: str, base: str, head: str,
                title: str, body: str) -> str:
        pr = self._post(f"{API}/repos/{owner}/{repo}/pulls",
                        {"title": title, "head": head, "base": base, "body": body})
        return pr.get("html_url", "")
