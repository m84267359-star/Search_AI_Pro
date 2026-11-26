from pathlib import Path
from datetime import datetime
import shutil
import re

app = Path('app.py')
js = Path('static/app.js')
html = Path('templates/index.html')
s, j, h = [p.read_text(encoding='utf-8-sig') for p in (app, js, html)]
assert '# SMART_SEARCH_V1' not in s, 'Already installed'
helper = '''# SMART_SEARCH_V1
def should_search(prompt, mode):
    if mode == "always":
        return True
    if mode == "off":
        return False
    text = prompt.lower()
    return bool(re.search(
        r"\\b(latest|current|today|tonight|yesterday|breaking|recent|currently|news|weather|stock price|gold price|exchange rate|live score|near me|look up|search (?:the )?(?:web|internet)|browse (?:the )?web|online sources)\\b",
        text
    ))


'''
anchor = 'app = Flask(__name__)'
assert s.count(anchor) == 1
s = s.replace(anchor, helper + anchor, 1)
old = "    search = data.get('web_search', False) is True"
assert s.count(old) == 1, 'Search backend anchor not found'
s = s.replace(old, '''    search_mode = data.get('search_mode')
    if search_mode is None:
        search_mode = 'always' if data.get('web_search') is True else 'off'
    if search_mode not in ('auto', 'always', 'off'):
        return fail('Invalid search mode')
    search = should_search(prompt, search_mode)
    print('Search mode:', search_mode)
    print('Smart search decision:', search)''', 1)
old = "web_search:$('web-search').checked"
assert j.count(old) == 1, 'Frontend request anchor not found'
j = j.replace(old, "search_mode:$('web-search').value", 1)
pattern = r'<label>\s*<input\b[^>]*\bid=["\']web-search["\'][^>]*>[^<]*</label>'
h, count = re.subn(pattern, '<label>Web search <select id="web-search"><option value="auto">Auto</option><option value="always">Always On</option><option value="off">Off</option></select></label>', h)
assert count == 1, 'Search checkbox not found'
compile(s, str(app), 'exec')
# Test the helper independently without starting Flask.
ns = {'re': re}
exec(helper, ns)
f = ns['should_search']
assert not f('Hello', 'auto') and f('Latest Python news', 'auto')
assert f('Hello', 'always') and not f('Latest news', 'off')
backup = Path('backups') / ('before-smart-search-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
for p in (app, js, html):
    dest = backup / p
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(p, dest)
try:
    for p, content in zip((app, js, html), (s, j, h)):
        p.write_text(content, encoding='utf-8')
except Exception:
    for p in (app, js, html):
        shutil.copy2(backup / p, p)
    raise
print('SUCCESS: Smart web search integrated')
print('SUCCESS: Python syntax and search rules verified')
print('Backup:', backup)
