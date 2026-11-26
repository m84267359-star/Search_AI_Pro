import os
import re
import requests

from urllib.parse import urlsplit, quote
from dotenv import load_dotenv

load_dotenv()

API_URL = "https://api.github.com"

TIMEOUT = int(os.getenv("GITHUB_REQUEST_TIMEOUT", "20"))
MAX_FILES = int(os.getenv("GITHUB_MAX_FILES", "5000"))
MAX_FILE_SIZE = int(os.getenv("GITHUB_MAX_FILE_SIZE", "200000"))


def parse_repository(repository):
    repository = repository.strip().rstrip("/")

    if "://" in repository:
        parsed = urlsplit(repository)

        if parsed.scheme != "https" or parsed.netloc.lower() != "github.com":
            raise ValueError("Enter a valid GitHub repository URL")

        repository = parsed.path.strip("/")

    repository = repository.removesuffix(".git")

    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("Use owner/repository format")

    owner, repo = repository.split("/")

    if owner in (".", "..") or repo in (".", ".."):
        raise ValueError("Invalid repository name")

    return owner, repo


def github_request(endpoint, params=None):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "Search-AI-Pro"
    }

    token = os.getenv("GITHUB_TOKEN", "").strip()

    if token:
        headers["Authorization"] = f"Bearer {token}"

    response = requests.get(
        API_URL + endpoint,
        headers=headers,
        params=params,
        timeout=TIMEOUT,
        allow_redirects=False
    )

    if response.status_code == 404:
        raise ValueError("Repository or file not found")

    if response.status_code in (403, 429):
        raise RuntimeError(
            "GitHub access denied or API rate limit reached"
        )

    if response.status_code != 200:
        raise RuntimeError(
            f"GitHub API returned {response.status_code}"
        )

    return response.json()


def get_repository(repository):
    owner, repo = parse_repository(repository)

    data = github_request(f"/repos/{owner}/{repo}")

    return {
        "owner": owner,
        "name": repo,
        "full_name": data["full_name"],
        "description": data.get("description"),
        "language": data.get("language"),
        "stars": data.get("stargazers_count", 0),
        "forks": data.get("forks_count", 0),
        "size_kb": data.get("size", 0),
        "default_branch": data["default_branch"],
        "url": data["html_url"],
        "updated_at": data.get("updated_at")
    }


def get_repository_tree(repository):
    info = get_repository(repository)

    owner = info["owner"]
    repo = info["name"]
    branch = quote(info["default_branch"], safe="")

    data = github_request(
        f"/repos/{owner}/{repo}/git/trees/{branch}",
        params={"recursive": "1"}
    )

    files = []
    folders = []

    for item in data.get("tree", []):
        if item["type"] == "blob":
            files.append({
                "path": item["path"],
                "size": item.get("size", 0),
                "sha": item["sha"],
                "mode": item.get("mode")
            })

        elif item["type"] == "tree":
            folders.append(item["path"])

    truncated = bool(data.get("truncated")) or len(files) > MAX_FILES

    files = files[:MAX_FILES]

    return {
        "repository": info,
        "files": files,
        "folders": folders,
        "total_files": len(files),
        "total_folders": len(folders),
        "total_bytes": sum(f["size"] for f in files),
        "truncated": truncated
    }


def get_languages(repository):
    owner, repo = parse_repository(repository)

    return github_request(
        f"/repos/{owner}/{repo}/languages"
    )
