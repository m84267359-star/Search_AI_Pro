from pathlib import PurePosixPath
from collections import Counter, defaultdict

from .github_client import get_repository_tree


GENERATED_FOLDERS = {
    "__pycache__", ".venv", "venv",
    "node_modules", ".pytest_cache",
    ".mypy_cache", ".ruff_cache"
}

SOURCE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx",
    ".html", ".css", ".java", ".cpp",
    ".c", ".h", ".go", ".rs", ".php",
    ".rb", ".sql", ".cs", ".sh", ".bat",
    ".ps1", ".vue", ".ipynb"
}

CONFIG_EXTENSIONS = {
    ".json", ".yaml", ".yml", ".toml",
    ".ini", ".cfg", ".xml", ".lock"
}

ASSET_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".svg",
    ".webp", ".ico", ".gif", ".woff",
    ".woff2", ".ttf"
}

DOCUMENT_EXTENSIONS = {
    ".md", ".rst", ".txt", ".pdf"
}


def classify_file(path):
    p = PurePosixPath(path.lower())

    name = p.name
    suffix = p.suffix
    folders = set(p.parts[:-1])

    if folders & GENERATED_FOLDERS:
        return "unnecessary", "Generated cache or dependency folder"

    if suffix in {".pyc", ".pyo", ".tmp", ".log"}:
        return "unnecessary", "Generated or temporary file"

    if name in {".ds_store", "thumbs.db"}:
        return "unnecessary", "Operating system metadata"

    if (
        suffix in {".bak", ".backup", ".old"}
        or "backup" in folders
        or "backups" in folders
        or "_backup" in name
        or ".backup" in name
    ):
        return "review", "Possible backup file"

    if name == ".env":
        return "review", "Possible sensitive configuration"

    if name in {
        "dockerfile", "makefile", "license",
        "readme", ".gitignore", ".dockerignore",
        ".gitattributes", "procfile"
    }:
        return "useful", "Project configuration or documentation"

    if suffix in SOURCE_EXTENSIONS:
        return "useful", "Application source code"

    if suffix in CONFIG_EXTENSIONS:
        return "useful", "Project configuration or structured data"

    if suffix in ASSET_EXTENSIONS:
        return "useful", "Project asset"

    if suffix in DOCUMENT_EXTENSIONS:
        return "useful", "Project documentation or text data"

    return "review", "Requires manual inspection"


def percentage(value, total):
    return round(value * 100 / total, 2) if total else 0


def analyze_repository(repository):
    data = get_repository_tree(repository)

    files = data["files"]
    total_files = len(files)
    total_bytes = sum(f["size"] for f in files)

    counts = Counter()
    sizes = Counter()
    extensions = Counter()

    hashes = defaultdict(list)
    classified = []

    for file in files:
        path = file["path"]
        size = file["size"]

        category, reason = classify_file(path)

        counts[category] += 1
        sizes[category] += size

        extension = PurePosixPath(path).suffix.lower()
        extensions[extension or "No extension"] += 1

        sha = file.get("sha")

        if sha and size > 0:
            hashes[sha].append(path)

        classified.append({
            **file,
            "category": category,
            "reason": reason
        })

    duplicates = [
        {
            "sha": sha,
            "files": paths,
            "count": len(paths)
        }
        for sha, paths in hashes.items()
        if len(paths) > 1
    ]

    categories = {}

    for category in ["useful", "review", "unnecessary"]:
        categories[category] = {
            "files": counts[category],
            "bytes": sizes[category],
            "file_percentage": percentage(
                counts[category], total_files
            ),
            "size_percentage": percentage(
                sizes[category], total_bytes
            )
        }

    return {
        "repository": data["repository"],
        "total_files": total_files,
        "total_folders": data["total_folders"],
        "total_bytes": total_bytes,
        "truncated": data["truncated"],
        "categories": categories,
        "extensions": dict(extensions.most_common()),
        "duplicate_groups": duplicates,
        "duplicate_group_count": len(duplicates),
        "files": classified,
        "largest_files": sorted(
            classified,
            key=lambda f: f["size"],
            reverse=True
        )[:10]
    }
