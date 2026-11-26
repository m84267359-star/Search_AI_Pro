from pathlib import Path
from datetime import datetime
import shutil
p=Path('static/style.css')
if not p.is_file():
    raise SystemExit('Run this script from the Search AI Pro project folder.')
marker='/* GITHUB_DASHBOARD_UI_V4 */'
css=r'''
/* GITHUB_DASHBOARD_UI_V4 */
#github-page { min-width:0; }
#github-page #gh-open-form {
 display:flex; flex-wrap:wrap; gap:10px; padding:18px;
 border:1px solid rgba(128,128,160,.25); border-radius:14px;
 background:rgba(128,128,160,.045);
}
#github-page #gh-repo { flex:0 0 100%; width:100%; min-width:0; box-sizing:border-box; min-height:48px; }
#github-page #gh-open-form button { flex:1 1 auto; min-height:43px; border-radius:9px; font-weight:600; white-space:nowrap; }
#github-page #gh-open-form button[type=submit] { background:#6654d9; color:white; }
#github-page #gh-analyze { background:#245bb5; color:white; }
#github-page #gh-ai-analyze { background:#7040c8; color:white; }
#github-page #gh-ask { background:#03698a; color:white; }
#github-page #gh-open-form button:nth-last-child(2) { background:#0f766e; color:white; }
#github-page #gh-open-form button:last-child { background:#187348; color:white; }
#github-page button { transition:transform .15s ease, filter .15s ease; }
#github-page button:not(:disabled):hover { transform:translateY(-2px); filter:brightness(1.12); }
#github-page button:not(:disabled):active { transform:scale(.97); }
#github-page button:focus-visible { outline:2px solid #9584ff; outline-offset:3px; }
#github-page button:disabled { opacity:.55; cursor:not-allowed; }
#github-page #gh-status { padding:12px; border-left:3px solid #8270ef; border-radius:8px; background:rgba(128,128,160,.07); }
#github-page .gh-history-actions { display:flex; flex-wrap:wrap; gap:10px; }
#github-page #gh-search-form { display:flex; flex-wrap:wrap; gap:10px; padding:14px; border:1px solid rgba(128,128,160,.25); border-radius:12px; }
#github-page #gh-query { flex:1 1 240px; min-width:0; }
#github-page .gh-browser { display:grid; grid-template-columns:minmax(0,1fr) minmax(0,2fr); gap:14px; }
#github-page .gh-browser > .gh-pane { min-width:0; min-height:240px; padding:18px; border-radius:14px; }
#github-page .gh-browser h3 { padding-bottom:12px; border-bottom:1px solid rgba(128,128,160,.2); }
#github-page #gh-files { max-height:550px; overflow:auto; }
#github-page #gh-files:empty::after { content:'Open a repository to browse files.'; opacity:.7; font-size:14px; }
#github-page #gh-code { max-height:600px; overflow:auto; padding:14px; border-radius:8px; background:rgba(128,128,160,.06); }
@media(max-width:1000px) { #github-page .gh-browser { grid-template-columns:minmax(0,1fr); } #github-page #gh-open-form button { flex:1 1 140px; } }
@media(prefers-reduced-motion:reduce) { #github-page button { transition:none; } #github-page button:not(:disabled):hover, #github-page button:not(:disabled):active { transform:none; } }
'''
original=p.read_bytes()
if marker.encode() in original:
    print('CSS upgrade already installed.'); raise SystemExit(0)
backup=Path('backups')/('before-github-css-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
backup.mkdir(parents=True)
shutil.copy2(p,backup/'style.css')
p.write_bytes(original+b'\n'+css.encode('utf-8'))
print('SUCCESS: GitHub dashboard CSS updated')
print('Backup:',backup/'style.css')
