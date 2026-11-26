import base64
import re

from pathlib import PurePosixPath
from functools import lru_cache

from .github_client import (
    parse_repository,
    github_request,
    get_repository_tree,
    MAX_FILE_SIZE
)

TEXT_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx",
    ".html", ".css", ".json", ".md", ".txt",
    ".yaml", ".yml", ".toml", ".sql",
    ".java", ".cpp", ".c", ".h", ".go",
    ".rs", ".php", ".rb", ".sh", ".bat",
    ".ps1", ".xml", ".ini", ".cs", ".vue"
}

MAX_SEARCH_FILES = 20
MAX_RESULTS = 100


def is_text_file(path):
    p = PurePosixPath(path.lower())

    if p.name.startswith(".env"):
        return False

    return (
        p.suffix in TEXT_EXTENSIONS
        or p.name in {
            "dockerfile", "makefile",
            "readme", "license", ".gitignore"
        }
    )


@lru_cache(maxsize=64)
def read_blob(owner, repo, sha):

    if not re.fullmatch(r"[a-fA-F0-9]{40,64}", sha):
        raise ValueError("Invalid file hash")

    data = github_request(
        f"/repos/{owner}/{repo}/git/blobs/{sha}"
    )

    if data.get("size", 0) > MAX_FILE_SIZE:
        raise ValueError("File exceeds size limit")

    if data.get("encoding") != "base64":
        raise ValueError("Unsupported file encoding")

    content = base64.b64decode(data["content"])

    if len(content) > MAX_FILE_SIZE:
        raise ValueError("File exceeds size limit")

    if b"\x00" in content:
        raise ValueError("Binary files are not supported")

    return content.decode("utf-8")


def search_repository(repository, query, mode="filename"):

    query = query.strip()

    if not query or len(query) > 200:
        raise ValueError("Enter a valid search query")

    if mode not in {
        "filename", "folder", "extension",
        "code", "function", "class"
    }:
        raise ValueError("Invalid search mode")

    owner, repo = parse_repository(repository)
    data = get_repository_tree(repository)

    results = []
    scanned = 0
    skipped = 0
    limited = False
    keyword = query.casefold()

    if mode == "folder":
        for folder in data["folders"]:
            if keyword in folder.casefold():
                results.append({
                    "path": folder,
                    "type": "folder"
                })

    elif mode in {"filename", "extension"}:

        for file in data["files"]:

            path = file["path"]
            p = PurePosixPath(path)

            if mode == "filename":
                matched = keyword in path.casefold()
            else:
                matched = (
                    p.suffix.casefold().lstrip(".")
                    == keyword.lstrip(".")
                )

            if matched:
                results.append({
                    "path": path,
                    "size": file["size"],
                    "type": "file"
                })

    else:

        for file in data["files"]:

            path = file["path"]

            if not is_text_file(path):
                continue

            if file["size"] > MAX_FILE_SIZE:
                skipped += 1
                continue

            if scanned >= MAX_SEARCH_FILES:
                limited = True
                break

            scanned += 1

            try:
                content = read_blob(
                    owner, repo, file["sha"]
                )
            except (ValueError, UnicodeError):
                skipped += 1
                continue

            for number, line in enumerate(
                content.splitlines(), start=1
            ):

                if keyword not in line.casefold():
                    continue

                if mode == "function":
                    if not re.search(
                        r"\b(def|function|func|fn)\s+",
                        line
                    ):
                        continue

                if mode == "class":
                    if not re.search(
                        r"\bclass\s+", line
                    ):
                        continue

                results.append({
                    "path": path,
                    "line": number,
                    "content": line.strip()[:500],
                    "type": mode
                })

                if len(results) >= MAX_RESULTS:
                    limited = True
                    break

            if len(results) >= MAX_RESULTS:
                break

    return {
        "repository": data["repository"]["full_name"],
        "query": query,
        "mode": mode,
        "total_results": len(results),
        "scanned_files": scanned,
        "skipped_files": skipped,
        "limited": limited or len(results) > MAX_RESULTS,
        "truncated": data["truncated"],
        "results": results[:MAX_RESULTS]
    }


def get_file_content(repository, path):

    owner, repo = parse_repository(repository)
    data = get_repository_tree(repository)

    for file in data["files"]:

        if file["path"] != path:
            continue

        if not is_text_file(path):
            raise ValueError("Unsupported file type")

        if file["size"] > MAX_FILE_SIZE:
            raise ValueError("File is too large")

        content = read_blob(
            owner, repo, file["sha"]
        )

        return {
            "path": path,
            "size": file["size"],
            "extension": PurePosixPath(path).suffix,
            "lines": len(content.splitlines()),
            "content": content
        }

    raise ValueError("File not found")
