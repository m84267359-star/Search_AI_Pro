"""Generate a sampled repository architecture report using the existing chat engine."""
import re
from .repository_chat import ask_repository


def analyze_architecture(repository):
    question = (
        'Explain the architecture of this repository using the available source evidence. '
        'Identify frontend, backend, database, external APIs, entry points and data flow '
        'only where supported. Include technology stack and source file references. '
        'Provide exactly one fenced mermaid code block using flowchart TD. '
        'Use simple node IDs and quoted labels, with arrows for supported connections. '
        'Do not use click directives, links, HTML, initialization directives or styling. '
        'Explain missing evidence separately. Do not invent dependencies.'
    )
    result = ask_repository(repository, question)
    answer = result['answer']
    match = re.search(r'```mermaid\s*\n(.*?)```', answer, re.S | re.I)
    diagram = match.group(1).strip() if match else ''
    if diagram and (not re.match(r'^flowchart\s+(TD|TB|LR|RL|BT)\b', diagram) or re.search(r'(?im)^\s*click\b|%%|<|https?://', diagram) or len(diagram) > 8000):
        diagram = ''
    return {**result, 'diagram': diagram, 'report': answer, 'diagram_available': bool(diagram)}
