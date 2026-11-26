from pathlib import Path
from datetime import datetime
import shutil

p = Path('app.py')
s = p.read_text(encoding='utf-8-sig')
marker = '# INPUT_OPTIMIZATION_V1'
if marker in s:
    raise SystemExit('Upgrade already installed.')
helper = '''# INPUT_OPTIMIZATION_V1
def estimate_input_tokens(text):
    # Local heuristic, not the Gemini tokenizer.
    return (len(text.encode("utf-8")) + 2) // 3


def optimize_input(messages, prompt, instructions):
    budget = max(128, int(os.getenv("MAX_INPUT_TOKENS", "8192")))
    history_limit = max(0, min(100, int(os.getenv("MAX_HISTORY_MESSAGES", "6"))))
    current = prompt.strip()
    full = messages[-1]["content"]
    if not full.startswith(current):
        raise ValueError("Current prompt mismatch")
    context = full[len(current):]
    remaining = budget - estimate_input_tokens(instructions) - estimate_input_tokens(current) - 128
    if remaining < 0:
        raise ValueError("Prompt and instructions exceed estimated input budget")
    # Reserve up to half of available space for history when it exists.
    context_budget = remaining // 2 if messages[:-1] and history_limit else remaining
    context_bytes = context.encode("utf-8")[:context_budget * 3]
    context = context_bytes.decode("utf-8", errors="ignore")
    remaining -= estimate_input_tokens(context)
    history = []
    for item in reversed(messages[:-1][-history_limit:] if history_limit else []):
        cost = estimate_input_tokens(item["content"]) + 16
        if cost > remaining:
            break
        history.append(item)
        remaining -= cost
    history.reverse()
    while history and history[0]["role"] != "user":
        history.pop(0)
    result = history + [{"role": "user", "content": current + context}]
    print("History messages:", len(history))
    print("Estimated input tokens:", estimate_input_tokens(instructions) + sum(estimate_input_tokens(item["content"]) + 16 for item in result))
    print("Input token budget:", budget)
    return result


'''
anchor = 'app = Flask(__name__)'
assert s.count(anchor) == 1, 'Flask anchor not found'
s = s.replace(anchor, helper + anchor, 1)
old = "ORDER BY id DESC LIMIT 6', (chat_id,)).fetchall()"
new = "ORDER BY id DESC LIMIT ?', (chat_id, max(0, min(100, int(os.getenv('MAX_HISTORY_MESSAGES', '6')))))).fetchall()"
assert s.count(old) == 1, 'History query not found'
s = s.replace(old, new, 1)
anchor = '            contents = ['
assert s.count(anchor) == 1, 'Contents anchor not found'
s = s.replace(anchor, '''            try:
                inputs[:] = optimize_input(inputs, prompt, instructions)
            except ValueError:
                yield emit("error", {"error": "Input exceeds the configured budget or input configuration is invalid."})
                return

''' + anchor, 1)
compile(s, str(p), 'exec')
backup = p.with_name('app.before-input-optimization-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.py')
shutil.copy2(p, backup)
p.write_text(s, encoding='utf-8')
print('SUCCESS: Input budget and history optimization integrated')
print('SUCCESS: Python syntax verified')
print('Backup:', backup)
