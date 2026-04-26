import csv
import io
import os
import sys
import re
from datetime import datetime
from urllib.parse import urlparse
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import github
    from github import Github, GithubException
    PYGITHUB_AVAILABLE = True
except ImportError:
    PYGITHUB_AVAILABLE = False

# ─────────────────────────────────────────────────────────────────────────────
# App setup
# ─────────────────────────────────────────────────────────────────────────────
app = FastAPI(title="Git Integration API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        # Vite dev server — covers ports 5173-5180 in case of port conflicts
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:5174", "http://127.0.0.1:5174",
        "http://localhost:5175", "http://127.0.0.1:5175",
        "http://localhost:5176", "http://127.0.0.1:5176",
        "http://localhost:5177", "http://127.0.0.1:5177",
        "http://localhost:5178", "http://127.0.0.1:5178",
        # CRA / other React setups
        "http://localhost:3000", "http://127.0.0.1:3000",
        "http://localhost:3001", "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────────────────────
# Request / Response Models
# ─────────────────────────────────────────────────────────────────────────────
class DetectRequest(BaseModel):
    repo_url: str
    token: str

class CommitsRequest(BaseModel):
    repo_url: str
    token: str
    platform: str                    # "github" | "gitea"
    gitea_base_url: Optional[str] = None
    since: Optional[str] = None      # YYYY-MM-DD
    until: Optional[str] = None
    author: Optional[str] = None
    branch: Optional[str] = None
    page: int = 1
    per_page: int = 30               # commits per page (max 100)
    search: Optional[str] = None     # text filter on commit message

class CommitDetailRequest(BaseModel):
    repo_url: str
    token: str
    platform: str
    gitea_base_url: Optional[str] = None
    sha: str

class ExportRequest(BaseModel):
    repo_url: str
    token: str
    platform: str
    gitea_base_url: Optional[str] = None
    since: Optional[str] = None
    until: Optional[str] = None
    author: Optional[str] = None
    branch: Optional[str] = None
    search: Optional[str] = None

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def parse_repo_url(repo_url: str):
    ssh_match = re.match(r"git@([^:]+):(.+?)/(.+?)(\.git)?$", repo_url.strip())
    if ssh_match:
        return {
            "host": ssh_match.group(1),
            "owner": ssh_match.group(2),
            "repo": ssh_match.group(3).replace(".git", "")
        }
    parsed = urlparse(repo_url.strip())
    if parsed.scheme in ("http", "https"):
        parts = parsed.path.strip("/").replace(".git", "").split("/")
        if len(parts) >= 2:
            return {
                "host": parsed.hostname,
                "owner": parts[-2],
                "repo": parts[-1]
            }
    raise ValueError(f"Invalid Git repository URL: {repo_url}")


def detect_platform(repo_url: str) -> dict:
    info = parse_repo_url(repo_url)
    host = (info.get("host") or "").lower()
    if "github.com" in host:
        return {**info, "platform": "github", "base_url": None}
    parsed = urlparse(repo_url.strip())
    base_url = f"{parsed.scheme}://{parsed.hostname}"
    if parsed.port:
        base_url += f":{parsed.port}"
    return {**info, "platform": "gitea", "base_url": base_url}


def parse_diff_to_lines(patch: str):
    if not patch:
        return []
    lines = []
    old_line = 0
    new_line = 0
    for raw in patch.split("\n"):
        if raw.startswith("@@"):
            m = re.match(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", raw)
            if m:
                old_line = int(m.group(1)) - 1
                new_line = int(m.group(2)) - 1
            lines.append({"type": "hunk", "content": raw, "old_line": None, "new_line": None})
        elif raw.startswith("+"):
            new_line += 1
            lines.append({"type": "addition", "content": raw[1:], "old_line": None, "new_line": new_line})
        elif raw.startswith("-"):
            old_line += 1
            lines.append({"type": "deletion", "content": raw[1:], "old_line": old_line, "new_line": None})
        else:
            old_line += 1
            new_line += 1
            lines.append({"type": "context", "content": raw[1:] if raw.startswith(" ") else raw, "old_line": old_line, "new_line": new_line})
    return lines


def apply_search_filter(commits: list, search: Optional[str]) -> list:
    """Client-side text search across message, author, sha."""
    if not search:
        return commits
    q = search.lower()
    return [
        c for c in commits
        if q in c["message"].lower()
        or q in c["author"].lower()
        or q in c["sha"].lower()
    ]


def build_stats(commits: list) -> dict:
    total_additions = sum(c["additions"] for c in commits)
    total_deletions = sum(c["deletions"] for c in commits)
    contributors: dict = {}
    for c in commits:
        a = c["author"]
        if a not in contributors:
            contributors[a] = {"commits": 0, "additions": 0, "deletions": 0, "email": c["email"]}
        contributors[a]["commits"] += 1
        contributors[a]["additions"] += c["additions"]
        contributors[a]["deletions"] += c["deletions"]
    return {
        "total_commits": len(commits),
        "total_additions": total_additions,
        "total_deletions": total_deletions,
        "contributors": contributors,
    }


# ─────────────────────────────────────────────────────────────────────────────
# GitHub helpers (PyGithub)
# ─────────────────────────────────────────────────────────────────────────────
def gh_connect(token: str, repo_url: str):
    info = parse_repo_url(repo_url)
    g = Github(auth=github.Auth.Token(token))
    repo = g.get_repo(f"{info['owner']}/{info['repo']}")
    return g, repo, info


def gh_fetch_commits(token: str, repo_url: str, since=None, until=None, author=None, branch=None):
    g, repo, info = gh_connect(token, repo_url)
    params = {}
    if since:
        params["since"] = datetime.fromisoformat(since)
    if until:
        params["until"] = datetime.fromisoformat(until)
    if author:
        params["author"] = author
    if branch:
        params["sha"] = branch

    # Fetch up to 500 commits (rate-limit friendly — still capped)
    commits_raw = repo.get_commits(**params)
    commits = []
    for c in commits_raw[:500]:
        try:
            stats = c.stats
            additions = stats.additions
            deletions = stats.deletions
        except Exception:
            additions = deletions = 0
        try:
            files_count = len(list(c.files))
        except Exception:
            files_count = 0

        commits.append({
            "sha": c.sha,
            "short_sha": c.sha[:8],
            "author": c.commit.author.name or "Unknown",
            "email": c.commit.author.email or "",
            "message": c.commit.message.strip(),
            "timestamp": c.commit.author.date.isoformat(),
            "additions": additions,
            "deletions": deletions,
            "files_changed": files_count,
        })

    # Include rate-limit info
    try:
        rate = g.get_rate_limit()
        rate_remaining = rate.core.remaining
        rate_reset = rate.core.reset.isoformat() if hasattr(rate.core.reset, "isoformat") else str(rate.core.reset)
    except Exception:
        rate_remaining = None
        rate_reset = None

    return commits, rate_remaining, rate_reset


def gh_fetch_commit_detail(token: str, repo_url: str, sha: str):
    g, repo, info = gh_connect(token, repo_url)
    c = repo.get_commit(sha)
    files = []
    for f in c.files:
        files.append({
            "filename": f.filename,
            "status": f.status,
            "additions": f.additions,
            "deletions": f.deletions,
            "patch": f.patch or "",
            "diff_lines": parse_diff_to_lines(f.patch or ""),
        })
    return {
        "sha": c.sha,
        "short_sha": c.sha[:8],
        "author": c.commit.author.name,
        "email": c.commit.author.email,
        "message": c.commit.message.strip(),
        "timestamp": c.commit.author.date.isoformat(),
        "additions": c.stats.additions,
        "deletions": c.stats.deletions,
        "url": c.html_url,
        "files": files,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Gitea helpers (httpx REST)
# ─────────────────────────────────────────────────────────────────────────────
async def gitea_get(base_url: str, token: str, path: str, params: dict = None):
    headers = {"Authorization": f"token {token}", "Accept": "application/json"}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(f"{base_url}/api/v1{path}", headers=headers, params=params or {})
        if r.status_code == 404:
            raise HTTPException(status_code=404, detail="Gitea resource not found")
        if r.status_code == 401:
            raise HTTPException(status_code=401, detail="Gitea authentication failed — check your token")
        if r.status_code == 429:
            raise HTTPException(status_code=429, detail="Rate limit exceeded — please wait before retrying")
        r.raise_for_status()
        return r.json()


async def gitea_fetch_commits(base_url: str, token: str, owner: str, repo: str,
                               since=None, until=None, branch=None, page=1, per_page=50):
    params = {"limit": per_page, "page": page}
    if since:
        params["since"] = since + "T00:00:00Z"
    if until:
        params["until"] = until + "T23:59:59Z"
    if branch:
        params["sha"] = branch

    data = await gitea_get(base_url, token, f"/repos/{owner}/{repo}/commits", params)
    commits = []
    for c in data:
        commit_obj = c.get("commit", {})
        author_obj = commit_obj.get("author", {})
        stats = c.get("stats", {})
        commits.append({
            "sha": c.get("sha", ""),
            "short_sha": c.get("sha", "")[:8],
            "author": author_obj.get("name", "Unknown"),
            "email": author_obj.get("email", ""),
            "message": commit_obj.get("message", "").strip(),
            "timestamp": author_obj.get("date", ""),
            "additions": stats.get("additions", 0),
            "deletions": stats.get("deletions", 0),
            "files_changed": len(c.get("files", [])),
        })
    return commits


async def gitea_fetch_commit_detail(base_url: str, token: str, owner: str, repo: str, sha: str):
    c = await gitea_get(base_url, token, f"/repos/{owner}/{repo}/git/commits/{sha}")
    try:
        full = await gitea_get(base_url, token, f"/repos/{owner}/{repo}/commits/{sha}")
    except Exception:
        full = {}

    files_raw = c.get("files", [])
    files = []
    for f in files_raw:
        patch = f.get("patch", "") or ""
        files.append({
            "filename": f.get("filename", ""),
            "status": f.get("status", "modified"),
            "additions": f.get("additions", 0),
            "deletions": f.get("deletions", 0),
            "patch": patch,
            "diff_lines": parse_diff_to_lines(patch),
        })

    commit_obj = c.get("commit", c)
    author_obj = commit_obj.get("author", {}) if isinstance(commit_obj, dict) else {}
    stats = full.get("stats", {}) if isinstance(full, dict) else {}

    return {
        "sha": sha,
        "short_sha": sha[:8],
        "author": author_obj.get("name", "Unknown"),
        "email": author_obj.get("email", ""),
        "message": (commit_obj.get("message", "") if isinstance(commit_obj, dict) else "").strip(),
        "timestamp": author_obj.get("date", ""),
        "additions": stats.get("additions", 0),
        "deletions": stats.get("deletions", 0),
        "url": None,
        "files": files,
    }


# ─────────────────────────────────────────────────────────────────────────────
# API Routes
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {"status": "ok", "message": "Git Integration API v2 running"}


@app.post("/api/detect")
async def detect_repo(req: DetectRequest):
    """Detect platform and validate token access."""
    try:
        info = detect_platform(req.repo_url)
        platform = info["platform"]
        owner = info["owner"]
        repo_name = info["repo"]

        if platform == "github":
            if not PYGITHUB_AVAILABLE:
                raise HTTPException(status_code=500, detail="PyGithub not installed")
            try:
                g, repo, _ = gh_connect(req.token, req.repo_url)
                perms = repo.permissions
                rate = g.get_rate_limit()
                remaining = rate.core.remaining if hasattr(rate, "core") else None
                return {
                    "platform": "github",
                    "owner": owner,
                    "repo": repo_name,
                    "full_name": repo.full_name,
                    "description": repo.description or "",
                    "default_branch": repo.default_branch,
                    "stars": repo.stargazers_count,
                    "language": repo.language or "",
                    "private": repo.private,
                    "permissions": {
                        "read": perms.pull,
                        "write": perms.push,
                        "admin": perms.admin,
                    },
                    "rate_limit_remaining": remaining,
                }
            except GithubException as e:
                if e.status == 401:
                    raise HTTPException(status_code=401, detail="Invalid GitHub token — please check your credentials")
                if e.status == 403:
                    raise HTTPException(status_code=403, detail="GitHub rate limit exceeded or insufficient permissions")
                if e.status == 404:
                    raise HTTPException(status_code=404, detail="Repository not found — check the URL and your token scope")
                raise HTTPException(status_code=e.status, detail=str(e.data.get("message", str(e))))

        else:  # gitea
            base_url = info["base_url"]
            try:
                data = await gitea_get(base_url, req.token, f"/repos/{owner}/{repo_name}")
                return {
                    "platform": "gitea",
                    "owner": owner,
                    "repo": repo_name,
                    "full_name": data.get("full_name", f"{owner}/{repo_name}"),
                    "description": data.get("description", ""),
                    "default_branch": data.get("default_branch", "main"),
                    "stars": data.get("stars_count", 0),
                    "language": data.get("language", ""),
                    "private": data.get("private", False),
                    "base_url": base_url,
                    "permissions": {
                        "read": True,
                        "write": data.get("permissions", {}).get("push", False),
                        "admin": data.get("permissions", {}).get("admin", False),
                    },
                }
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Gitea connection failed: {str(e)}")

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/commits")
async def get_commits(req: CommitsRequest):
    """Fetch paginated commits list with optional filters and search."""
    try:
        info = parse_repo_url(req.repo_url)
        owner = info["owner"]
        repo_name = info["repo"]
        per_page = min(req.per_page, 100)

        if req.platform == "github":
            all_commits, rate_remaining, rate_reset = gh_fetch_commits(
                req.token, req.repo_url,
                since=req.since, until=req.until,
                author=req.author, branch=req.branch
            )
        else:
            base_url = req.gitea_base_url or detect_platform(req.repo_url)["base_url"]
            all_commits = await gitea_fetch_commits(
                base_url, req.token, owner, repo_name,
                since=req.since, until=req.until, branch=req.branch,
                page=req.page, per_page=per_page
            )
            rate_remaining = None
            rate_reset = None

        # Apply search filter
        filtered = apply_search_filter(all_commits, req.search)

        # Paginate (for GitHub, we already have all the data; apply client-side pagination)
        total = len(filtered)
        start = (req.page - 1) * per_page
        end = start + per_page
        page_commits = filtered[start:end]

        stats = build_stats(filtered)   # stats over all filtered results

        return {
            "commits": page_commits,
            "pagination": {
                "page": req.page,
                "per_page": per_page,
                "total": total,
                "total_pages": max(1, -(-total // per_page)),  # ceiling division
                "has_next": end < total,
                "has_prev": req.page > 1,
            },
            "stats": stats,
            "rate_limit_remaining": rate_remaining,
            "rate_reset": rate_reset,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/commit/detail")
async def get_commit_detail(req: CommitDetailRequest):
    """Fetch a single commit's full file diffs."""
    try:
        info = parse_repo_url(req.repo_url)
        owner = info["owner"]
        repo_name = info["repo"]

        if req.platform == "github":
            detail = gh_fetch_commit_detail(req.token, req.repo_url, req.sha)
        else:
            base_url = req.gitea_base_url or detect_platform(req.repo_url)["base_url"]
            detail = await gitea_fetch_commit_detail(base_url, req.token, owner, repo_name, req.sha)

        return detail

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/export/csv")
async def export_commits_csv(req: ExportRequest):
    """Export all matching commits as a CSV file download."""
    try:
        info = parse_repo_url(req.repo_url)
        owner = info["owner"]
        repo_name = info["repo"]

        if req.platform == "github":
            all_commits, _, _ = gh_fetch_commits(
                req.token, req.repo_url,
                since=req.since, until=req.until,
                author=req.author, branch=req.branch
            )
        else:
            base_url = req.gitea_base_url or detect_platform(req.repo_url)["base_url"]
            all_commits = await gitea_fetch_commits(
                base_url, req.token, owner, repo_name,
                since=req.since, until=req.until, branch=req.branch,
                page=1, per_page=100
            )

        filtered = apply_search_filter(all_commits, req.search)

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            "sha", "short_sha", "author", "email", "timestamp",
            "message", "additions", "deletions", "files_changed"
        ])
        writer.writeheader()
        for c in filtered:
            writer.writerow({
                "sha": c["sha"],
                "short_sha": c["short_sha"],
                "author": c["author"],
                "email": c["email"],
                "timestamp": c["timestamp"],
                "message": c["message"].replace("\n", " "),
                "additions": c["additions"],
                "deletions": c["deletions"],
                "files_changed": c["files_changed"],
            })

        output.seek(0)
        filename = f"{owner}_{repo_name}_commits.csv"
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
