import json
from datetime import datetime, timezone
from pdf_export import generate_chat_pdf

def generate_repository_pdf(repository, sections):
    if not isinstance(sections, list) or not 1 <= len(sections) <= 3:
        raise ValueError('Generate repository analysis first')
    messages = []
    for section in sections:
        if not isinstance(section, str) or len(section) > 60000:
            raise ValueError('Invalid report section')
        messages.append({'role':'assistant','content':section,'sources':'[]'})
    messages.insert(0, {'role':'assistant','content':'Generated: '+datetime.now(timezone.utc).isoformat(timespec='seconds')+'\n\nUser-provided dashboard snapshot. File classifications are heuristic; AI findings require verification.','sources':'[]'})
    return generate_chat_pdf('Repository Report: '+repository, messages)
