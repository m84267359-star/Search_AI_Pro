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

# GITHUB_AI_UI_V1
@github_bp.post("/ai-analyze")
@login_required
def repository_ai_analysis():
    from .ai_analyzer import analyze_repository_ai
    data = request.get_json(silent=True)
    repository = data.get("repository") if isinstance(data, dict) else None
    if not isinstance(repository, str) or not repository.strip() or len(repository) > 300:
        return jsonify(error="Valid repository URL is required"), 400
    return execute(analyze_repository_ai, repository.strip())

# GITHUB_CHAT_UI_V1
@github_bp.post('/ask')
@login_required
def repository_ask():
    from .repository_chat import ask_repository
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error='JSON object required'), 400
    repository = data.get('repository')
    question = data.get('question')
    repository, question = data.get('repository'), data.get('question')
    if not isinstance(repository, str) or not 1 <= len(repository.strip()) <= 300:
        return jsonify(error='Valid repository URL required'), 400
    if not isinstance(question, str) or not 1 <= len(question.strip()) <= 2000:
        return jsonify(error='Question must contain 1-2000 characters'), 400
    return execute(ask_repository, repository.strip(), question.strip())

# ARCHITECTURE_UI_V1
@github_bp.post('/architecture')
@login_required
def repository_architecture():
    from .architecture_analyzer import analyze_architecture
    data = request.get_json(silent=True)
    repository = data.get('repository') if isinstance(data, dict) else None
    if not isinstance(repository, str) or not 1 <= len(repository.strip()) <= 300:
        return jsonify(error='Valid repository URL required'), 400
    return execute(analyze_architecture, repository.strip())

# REPOSITORY_PDF_V1
@github_bp.post('/report.pdf')
@login_required
def repository_pdf():
    from flask import send_file
    from io import BytesIO
    from .github_client import parse_repository
    from .repository_pdf import generate_repository_pdf
    if os.getenv('GITHUB_ENABLED','true').lower() != 'true':
        return jsonify(error='GitHub integration is disabled'), 503
    if request.content_length is None or request.content_length > 250000:
        return jsonify(error='Invalid report size'), 413
    data = request.get_json(silent=True)
    try:
        if not isinstance(data, dict) or not isinstance(data.get('repository'), str):
            raise ValueError('Repository required')
        owner, repo = parse_repository(data['repository'])
        pdf = generate_repository_pdf(owner+'/'+repo, data.get('sections'))
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    return send_file(BytesIO(pdf), mimetype='application/pdf', as_attachment=True, download_name='repository-report.pdf')
