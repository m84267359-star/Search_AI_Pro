from pathlib import Path
from datetime import datetime
import shutil
import re

p = Path('app.py')
s = p.read_text(encoding='utf-8-sig')
marker = '# TOKEN_OPTIMIZATION_V2'
if marker in s:
    raise SystemExit('Upgrade already installed.')
from token_manager import classify_task, get_output_limit
assert get_output_limit('Hello') > 0
anchor = 'app = Flask(__name__)'
assert s.count(anchor) == 1, 'Flask anchor not found'
helper = '''# TOKEN_OPTIMIZATION_V2
from token_manager import classify_task, get_output_limit


def get_thinking_config(model, task):
    if model != "gemini-3.1-flash-lite":
        return None
    level = {"greeting": "minimal", "simple": "minimal",
             "medium": "low", "coding": "low",
             "complex": "medium"}.get(task, "minimal")
    print("Thinking level:", level)
    return types.ThinkingConfig(thinking_level=level)


def task_output_limit(prompt, search, document_id):
    task = classify_task(prompt, web_search=search,
                         document=document_id is not None)
    limit = get_output_limit(prompt, web_search=search,
                             document=document_id is not None)
    print("Task type:", task)
    print("Output token limit:", limit)
    return limit


'''
s = s.replace(anchor, helper + anchor, 1)
assert s.count('max_output_tokens=2048,') == 1, 'Fixed token limit not found'
s = s.replace('max_output_tokens=2048,', 'max_output_tokens=task_output_limit(prompt, search, document_id),', 1)
pattern = r'thinking_config\s*=\s*\(\s*types\.ThinkingConfig\(\s*thinking_level\s*=\s*"minimal"\s*\)\s*if model == "gemini-3\.1-flash-lite"\s*else None\s*\)'
replacement = '''thinking_config=get_thinking_config(
                            model, classify_task(prompt, web_search=search,
                                                 document=document_id is not None)
                        )'''
s, count = re.subn(pattern, replacement, s)
assert count == 1, 'Original thinking configuration not found'
compile(s, str(p), 'exec')
backup = p.with_name('app.before-token-upgrade-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.py')
shutil.copy2(p, backup)
p.write_text(s, encoding='utf-8')
print('SUCCESS: Dynamic token optimization integrated')
print('SUCCESS: Thinking optimization integrated')
print('SUCCESS: Python syntax verified')
print('Backup:', backup)
