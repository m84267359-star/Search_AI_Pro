from pathlib import Path
from datetime import datetime
import shutil, subprocess, re

paths = [Path(x) for x in ('github_tools/architecture_analyzer.py','github_tools/repository_routes.py','templates/index.html','static/app.js','static/style.css')]
a,r,h,j,c = [p.read_text(encoding='utf-8') for p in paths]
if 'ARCHITECTURE_UI_V1' in j: raise SystemExit('Already installed')
if not re.search(r'^\s*match\s*=',a,re.M):
    a=a.replace("    answer = result['answer']", "    answer = result['answer']\n    match = re.search(r'```mermaid\\s*\\n(.*?)```', answer, re.S | re.I)")
if 'def repository_ask():' in r:
    before, tail=r.split('def repository_ask():',1)
    anchor="        return jsonify(error='JSON object required'), 400"
    if not re.search(r'^\s*repository\s*=',tail,re.M):
        tail=tail.replace(anchor,anchor+"\n    repository = data.get('repository')\n    question = data.get('question')",1)
    r=before+'def repository_ask():'+tail
r+='''\n# ARCHITECTURE_UI_V1
@github_bp.post('/architecture')
@login_required
def repository_architecture():
    from .architecture_analyzer import analyze_architecture
    data = request.get_json(silent=True)
    repository = data.get('repository') if isinstance(data, dict) else None
    if not isinstance(repository, str) or not 1 <= len(repository.strip()) <= 300:
        return jsonify(error='Valid repository URL required'), 400
    return execute(analyze_architecture, repository.strip())
'''
# Require existing global CSRF protection to be verified by user before installing.
anchor='<button id="gh-ask" type="button" class="primary">Ask AI</button>'
if h.count(anchor)!=1: raise SystemExit('Toolbar anchor not found')
h=h.replace(anchor,anchor+'<button id="gh-architecture" type="button" class="primary">Architecture</button>')
anchor='<form id="gh-search-form"'
if h.count(anchor)!=1: raise SystemExit('Search form anchor not found')
h=h.replace(anchor,'''<section id="gh-architecture-panel" class="gh-pane" hidden><div class="gh-history-actions"><h3>Project Architecture</h3><button type="button" id="gh-arch-copy" disabled>Copy Mermaid</button><button type="button" id="gh-arch-export" disabled>Export SVG</button><button type="button" id="gh-arch-retry">Regenerate</button><button type="button" id="gh-arch-clear">Clear</button></div><p id="gh-arch-status" role="status"></p><p id="gh-arch-meta"></p><div id="gh-arch-diagram"></div><details><summary>Reviewed source files</summary><ul id="gh-arch-files"></ul></details><div id="gh-arch-report"></div><p class="hint">Sampled public source only. Verify AI-generated connections.</p></section>\n'''+anchor)
j+='''
// ARCHITECTURE_UI_V1
(function(){
 const e=id=>document.getElementById(id);
 let epoch=0, pending=false, source='', svg='';
 const status=t=>e('gh-arch-status').textContent=t;
 function clear(){epoch++;source='';svg='';e('gh-architecture-panel').hidden=true;e('gh-arch-diagram').replaceChildren();e('gh-arch-report').replaceChildren();e('gh-arch-files').replaceChildren();e('gh-arch-meta').textContent='';status('');e('gh-arch-copy').disabled=true;e('gh-arch-export').disabled=true;}
 async function generate(){
  if(pending)return;
  const repository=e('gh-repo').value.trim();
  if(!repository){toast('Enter a repository URL first');return;}
  if(!confirm('Send sampled public source code to Gemini? This uses API tokens.'))return;
  clear();const v=epoch;pending=true;e('gh-architecture').disabled=true;e('gh-arch-retry').disabled=true;e('gh-architecture-panel').hidden=false;status('Generating architecture...');
  try{
   const d=await api('/api/github/architecture',json('POST',{repository}));
   if(v!==epoch)return;
   e('gh-arch-meta').textContent=d.repository+' · '+d.model+' · Input: '+(d.input_tokens??'Unknown')+' · Output: '+(d.output_tokens??'Unknown');
   for(const f of d.files_reviewed||[]){const li=document.createElement('li');li.textContent=f.path+' · line '+f.start_line;e('gh-arch-files').append(li);}
   renderMarkdown(e('gh-arch-report'),String(d.report||'').replace(/```mermaid\\s*\\n[\\s\\S]*?```/gi,''));
   source=String(d.diagram||'');
   if(!source){status('Report ready; no valid diagram returned.');return;}
   e('gh-arch-copy').disabled=false;
   try{
    if(!window.mermaid||!window.DOMPurify)throw Error('Diagram libraries unavailable');
    const result=await mermaid.render('architecture-'+Date.now(),source);
    if(v!==epoch)return;
    svg=DOMPurify.sanitize(result.svg,{USE_PROFILES:{svg:true,svgFilters:true},FORBID_TAGS:['script','foreignObject','a','image'],FORBID_ATTR:['href','xlink:href']});
    e('gh-arch-diagram').innerHTML=svg;e('gh-arch-export').disabled=false;status('Architecture complete');
   }catch(err){if(v===epoch){const pre=document.createElement('pre');pre.textContent=source;e('gh-arch-diagram').replaceChildren(pre);status('Diagram rendering failed; Mermaid source available.');}}
  }catch(err){if(v===epoch)status(err.message);}
  finally{pending=false;e('gh-architecture').disabled=false;e('gh-arch-retry').disabled=false;}
 }
 e('gh-architecture').onclick=generate;e('gh-arch-retry').onclick=generate;e('gh-arch-clear').onclick=clear;
 e('gh-arch-copy').onclick=()=>navigator.clipboard.writeText(source).then(()=>toast('Mermaid copied')).catch(()=>toast('Copy failed'));
 e('gh-arch-export').onclick=()=>{if(!svg)return;const url=URL.createObjectURL(new Blob([svg],{type:'image/svg+xml'}));const link=document.createElement('a');link.href=url;link.download='repository-architecture.svg';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
 for(const id of ['gh-clear-repo','logout'])e(id).addEventListener('click',clear);
 e('gh-repo').addEventListener('input',clear);
 e('gh-open-form').addEventListener('submit',clear);
})();
'''
c+='''\n/* ARCHITECTURE_UI_V1 */
#gh-architecture-panel{margin:16px 0;min-width:0}#gh-arch-diagram{overflow:auto;padding:16px;background:#f8fafc;border-radius:12px}#gh-arch-diagram:empty{display:none}#gh-arch-diagram svg{display:block;max-width:100%;height:auto;margin:auto}#gh-arch-meta{overflow-wrap:anywhere}#gh-arch-report{overflow-wrap:anywhere}#gh-architecture-panel[hidden]{display:none!important}
'''
for p,s in zip(paths,[a,r,h,j,c]):
    if p.suffix=='.py':compile(s,str(p),'exec')
subprocess.run(['node','--check','-'],input=j,encoding='utf-8',check=True)
backup=Path('backups')/('before-architecture-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
for p in paths:
    dest=backup/p;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
try:
    for p,s in zip(paths,[a,r,h,j,c]):p.write_text(s,encoding='utf-8')
except Exception:
    for p in paths:shutil.copy2(backup/p,p)
    raise
print('SUCCESS: Architecture UI installed; syntax checked')
print('Backup:',backup)
