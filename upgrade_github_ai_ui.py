from pathlib import Path
from datetime import datetime
import shutil, subprocess

paths = [Path(x) for x in ('app.py','github_tools/repository_routes.py','templates/index.html','static/app.js','static/style.css')]
a,r,h,j,c = [p.read_text(encoding='utf-8-sig') for p in paths]
marker='GITHUB_AI_UI_V1'
if any(marker in s for s in (a,r,h,j,c)):
    raise SystemExit('Patch already present or partially installed. Check files before retrying.')
def replace(s,old,new):
    if s.count(old)!=1: raise SystemExit('Expected exactly one match: '+old[:100])
    return s.replace(old,new,1)
r += '''\n# GITHUB_AI_UI_V1
@github_bp.post("/ai-analyze")
@login_required
def repository_ai_analysis():
    from .ai_analyzer import analyze_repository_ai
    data = request.get_json(silent=True)
    repository = data.get("repository") if isinstance(data, dict) else None
    if not isinstance(repository, str) or not repository.strip() or len(repository) > 300:
        return jsonify(error="Valid repository URL is required"), 400
    return execute(analyze_repository_ai, repository.strip())
'''
a=replace(a,'app.register_blueprint(github_bp)','''app.register_blueprint(github_bp)
# GITHUB_AI_UI_V1
_ai_endpoint = "github_repository.repository_ai_analysis"
app.view_functions[_ai_endpoint] = csrf_required(
    limiter.limit("3 per minute; 15 per hour")(app.view_functions[_ai_endpoint])
)''')
h=replace(h,'<button id="gh-analyze" type="button">Analyze</button>','<button id="gh-analyze" type="button">Analyze</button><button id="gh-ai-analyze" class="primary" type="button">&#10022; AI Analyze</button>')
h=replace(h,'<div id="gh-analysis"></div>','''<div id="gh-analysis"></div>
<section id="gh-ai-panel" class="gh-pane" hidden><div class="gh-history-actions"><h3>AI Repository Report</h3><button type="button" id="gh-ai-copy" disabled>Copy report</button><button type="button" id="gh-ai-clear">Clear report</button></div><p id="gh-ai-status" role="status"></p><p id="gh-ai-meta"></p><details id="gh-ai-details" hidden><summary>Reviewed source files</summary><ul id="gh-ai-files"></ul></details><div id="gh-ai-report"></div><p class="hint">Sampled public source excerpts only. AI findings require verification; partial excerpts are not proof of bugs. Source excerpts are sent to Gemini.</p></section>''')
j=replace(j,"function clear(){activeRepo='';", "function clear(){clearAI();activeRepo='';")
anchor="el('github-tab').onclick=()=>showPage('github');"
j=replace(j,anchor,r'''// GITHUB_AI_UI_V1
 function clearAI(){el('gh-ai-panel').hidden=true;el('gh-ai-status').textContent='';el('gh-ai-meta').textContent='';el('gh-ai-files').replaceChildren();el('gh-ai-details').hidden=true;el('gh-ai-report').replaceChildren();delete el('gh-ai-report').dataset.raw;el('gh-ai-copy').disabled=true;}
 el('gh-ai-clear').onclick=()=>{if(!working)clearAI();};
 el('gh-ai-copy').onclick=async()=>{const raw=el('gh-ai-report').dataset.raw;if(!raw)return;try{await navigator.clipboard.writeText(raw);toast('Report copied');}catch(e){toast('Unable to copy report');}};
 el('gh-repo').addEventListener('input',()=>{if(!working)clearAI();});
 el('gh-ai-analyze').onclick=()=>{if(working)return;let r;try{r=repo();if(!activeRepo||r!==activeRepo)throw Error('Open the repository first');}catch(e){status(e.message);return;}if(!confirm('Send selected public repository source excerpts to Gemini for AI analysis? This uses API tokens.'))return;run(async v=>{clearAI();el('gh-ai-panel').hidden=false;el('gh-ai-status').textContent='Analyzing source code with Gemini…';el('gh-ai-analyze').classList.add('gh-ai-loading');status('AI analysis in progress…');try{const d=await api('/api/github/ai-analyze',json('POST',{repository:r}));if(v!==epoch)return;const reviewed=d.files_reviewed||[];el('gh-ai-meta').textContent=d.repository+' · '+d.model+' · '+reviewed.length+'/'+d.total_files+' listed files · Input: '+(d.input_tokens??'Unknown')+' · Output: '+(d.output_tokens??'Unknown')+' · Thinking: '+(d.thinking_tokens??'Not reported')+(d.truncated?' · Partial listing':'');for(const f of reviewed)el('gh-ai-files').append(node('li',f.path+' · '+f.characters+' characters'+(f.partial?' · Partial excerpt':'')));el('gh-ai-details').hidden=false;renderMarkdown(el('gh-ai-report'),d.report);el('gh-ai-copy').disabled=false;el('gh-ai-status').textContent='Analysis complete';status('AI analysis complete');}catch(e){if(v===epoch){el('gh-ai-status').textContent=e.message;status(e.message);}}finally{el('gh-ai-analyze').classList.remove('gh-ai-loading');}});};
 '''+anchor)
c+='''\n/* GITHUB_AI_UI_V1 */
#gh-ai-panel{margin:18px 0;overflow-wrap:anywhere}#gh-ai-panel[hidden],#gh-ai-details[hidden]{display:none}#gh-ai-meta,#gh-ai-status{color:var(--muted);font-size:13px}#gh-ai-report{margin-top:18px;min-width:0;overflow:auto}#gh-ai-report table{width:100%}#gh-ai-analyze.gh-ai-loading{animation:gh-ai-pulse 1.3s ease-in-out infinite}@keyframes gh-ai-pulse{50%{opacity:.55}}@media(prefers-reduced-motion:reduce){#gh-ai-analyze.gh-ai-loading{animation:none}}
'''
# Validate proposed code before changing files.
compile(a,str(paths[0]),'exec');compile(r,str(paths[1]),'exec')
subprocess.run(['node','--check','-'],input=j,encoding='utf-8',check=True)
backup=Path('backups')/('before-github-ai-ui-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
for p in paths:
    dest=backup/p;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
try:
    for p,s in zip(paths,(a,r,h,j,c)):p.write_text(s,encoding='utf-8')
except Exception:
    for p in paths:shutil.copy2(backup/p,p)
    raise
print('SUCCESS: AI Analyze integration installed; Python and JavaScript syntax checked')
print('Backup:',backup)
