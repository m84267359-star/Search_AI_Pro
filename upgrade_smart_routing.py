from pathlib import Path
from datetime import datetime
import re
import shutil

p = Path('app.py')
s = p.read_text(encoding='utf-8-sig')

def replace(old, new):
    global s
    if s.count(old) != 1:
        raise RuntimeError('Expected exactly one match: ' + old[:100])
    s = s.replace(old, new, 1)

pattern = r'(?m)^MODELS\s*=\s*\{[^}]*\}'
s, n = re.subn(pattern, 'from model_router import (MODELS, ECONOMY_MODEL, get_model_candidates,\n                          can_fallback, mark_unavailable)', s)
assert n == 1, 'Model list not found or already upgraded'
replace('    model = settings["model"]\n\n    if model not in MODELS:\n        model = DEFAULT_MODEL', '    selected_model = settings["model"]\n\n    if selected_model not in MODELS:\n        selected_model = DEFAULT_MODEL\n\n    candidates = get_model_candidates(selected_model)\n    if not candidates:\n        return fail("All automatic models are cooling down. Try again later or select a model manually.", 503)')
replace('    print(f"Selected model: {model}")', '    print(f"Selected mode: {selected_model}")')
replace('    def generate():\n        answer = ""', '    def generate():\n        model = candidates[0]\n        answer = ""')
start = s.index('            config = types.GenerateContentConfig(')
end = s.index('            estimated_cost = price(', start)
block = s[start:end].rstrip('\n')
assert 'for chunk in stream:' in block and 'yield emit("delta"' in block
# Keep the existing streaming and usage logic, but retry only provider failures before text.
wrapped = '''            for attempt, model in enumerate(candidates, 1):
                print(f"Selected model: {model} (attempt {attempt})")
                input_tokens = 0
                output_tokens = 0
                try:
''' + '\n'.join('        '+line if line.strip() else '' for line in block.splitlines()) + '''
                    if not answer.strip():
                        raise RuntimeError("Model returned no text")
                    break
                except Exception as provider_error:
                    if selected_model == "auto" and can_fallback(provider_error):
                        mark_unavailable(model)
                        if not answer and attempt < len(candidates):
                            print(f"Auto fallback: {model} -> {candidates[attempt]}")
                            continue
                    raise

'''
s = s[:start] + wrapped + s[end:]
replace('            yield emit("done", {\n                "sources": sources,', '            yield emit("done", {\n                "model": model,\n                "sources": sources,')
compile(s, str(p), 'exec')
# Verify router can be imported and contains expected functions before writing.
from model_router import MODELS, get_model_candidates, can_fallback, mark_unavailable
assert 'auto' in MODELS
assert all(get_model_candidates(m) == [m] for m in MODELS if m != 'auto')
backup = p.with_name('app.before-smart-routing-' + datetime.now().strftime('%Y%m%d-%H%M%S') + '.py')
shutil.copy2(p, backup)
p.write_text(s, encoding='utf-8')
print('SUCCESS: Smart model routing integrated')
print('SUCCESS: Manual selection preserved')
print('SUCCESS: Syntax verified')
print('Backup:', backup)
