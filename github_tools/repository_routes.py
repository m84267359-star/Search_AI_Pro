import os
import requests

from flask import Blueprint, request, jsonify
from flask_login import login_required

from .github_client import get_repository_tree
from .repository_analyzer import analyze_repository
from .repository_search import (
    search_repository,
    get_file_content
)

github_bp = Blueprint(
    "github_repository",
    __name__,
    url_prefix="/api/github"
)


def execute(action, *args):

    if os.getenv("GITHUB_ENABLED", "true").lower() != "true":
        return jsonify(error="GitHub integration is disabled"), 503

    try:
        return jsonify(action(*args))

    except ValueError as e:
        return jsonify(error=str(e)), 400

    except RuntimeError as e:
        return jsonify(error=str(e)), 503

    except requests.exceptions.RequestException:
        return jsonify(error="Unable to connect to GitHub"), 502


@github_bp.get("/repository")
@login_required
def repository_details():

    repository = request.args.get("repository", "").strip()

    if not repository:
        return jsonify(error="Repository URL is required"), 400

    return execute(get_repository_tree, repository)


@github_bp.get("/analyze")
@login_required
def repository_analysis():

    repository = request.args.get("repository", "").strip()

    if not repository:
        return jsonify(error="Repository URL is required"), 400

    return execute(analyze_repository, repository)


@github_bp.get("/search")
@login_required
def repository_search():

    repository = request.args.get("repository", "").strip()
    query = request.args.get("query", "").strip()
    mode = request.args.get("mode", "filename")

    if not repository or not query:
        return jsonify(error="Repository and query are required"), 400

    return execute(
        search_repository,
        repository,
        query,
        mode
    )


@github_bp.get("/file")
@login_required
def repository_file():

    repository = request.args.get("repository", "").strip()
    path = request.args.get("path", "").strip()

    if not repository or not path:
        return jsonify(error="Repository and file path are required"), 400

    return execute(
        get_file_content,
        repository,
        path
    )
