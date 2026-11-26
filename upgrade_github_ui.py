from pathlib import Path
from datetime import datetime
import shutil, subprocess
paths=[Path('templates/index.html'),Path('static/app.js'),Path('static/style.css')]
h,j,c=[p.read_text(encoding='utf-8-sig') for p in paths]
if 'GITHUB_UI_V1' in j: raise SystemExit('Upgrade already installed')
def replace(s,a,b):
    if s.count(a)!=1: raise SystemExit('Expected frontend marker missing or repeated: '+a[:80])
    return s.replace(a,b,1)
h=replace(h,'<div class="side-bottom">','<div class="side-bottom"><div class="side-label">WORKSPACE</div><button id="github-tab">&#9670; GitHub Repository</button>')
h=replace(h,'<section id="documents-page"', '''<section id="github-page" class="page panel github-page" hidden>
<div class="gh-heading"><div><small>DEVELOPER WORKSPACE</small><h2>GitHub Repository</h2><p>Explore source code and review repository files.</p></div></div>
<form id="gh-open-form" class="gh-toolbar"><input id="gh-repo" placeholder="https://github.com/owner/repository" maxlength="300" required aria-label="Repository URL"><button class="primary" type="submit">Open Repository</button><button id="gh-analyze" type="button">Analyze</button></form>
<p id="gh-status" role="status">Enter a repository URL to begin.</p><div id="gh-summary" class="gh-summary"></div><div id="gh-analysis"></div>
<form id="gh-search-form" class="gh-toolbar"><input id="gh-query" placeholder="Search files or source code" maxlength="200" required aria-label="Search repository"><select id="gh-mode" aria-label="Search mode"><option value="filename">Filename</option><option value="folder">Folder</option><option value="extension">Extension</option><option value="code">Code</option><option value="function">Function</option><option value="class">Class</option></select><button type="submit">Search</button></form>
<div class="gh-browser"><div class="gh-pane"><h3>Repository files</h3><div id="gh-files"></div></div><div class="gh-pane"><h3 id="gh-file-title">Source code</h3><pre id="gh-code"><code>Select a file to view its content.</code></pre></div></div>
</section><section id="documents-page"''')
j=replace(j,"['chat','documents','usage','settings','admin']","['chat','documents','usage','settings','admin','github']")
j=replace(j,"admin:'Admin dashboard'})[name]","admin:'Admin dashboard',github:'GitHub Repository'})[name]")
j=replace(j,"document.querySelector('.sidebar').classList.remove('open')}","document.querySelector('.sidebar').classList.remove('open');document.querySelectorAll('.side-bottom button').forEach(b=>b.classList.toggle('workspace-active',b.id===name+'-tab'))}")
j+=r'''
// GITHUB_UI_V1
(function(){
 const el=$; let activeRepo='', working=false, epoch=0;
 const status=t=>el('gh-status').textContent=t;
 function node(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;}
 function clear(){activeRepo='';el('gh-summary').replaceChildren();el('gh-analysis').replaceChildren();el('gh-files').replaceChildren();el('gh-file-title').textContent='Source code';el('gh-code').textContent='Select a file to view its content.';}
 async function run(fn){if(working)return;working=true;const version=epoch;const controls=[...el('github-page').querySelectorAll('button,input,select')];controls.forEach(b=>b.disabled=true);status('Loading from GitHub…');try{await fn(version);}catch(e){if(version===epoch)status(e.message);}finally{working=false;controls.forEach(b=>b.disabled=false);}}
 const req=(route,params)=>api('/api/github/'+route+'?'+new URLSearchParams(params));
 function repo(){const r=el('gh-repo').value.trim();if(!r)throw Error('Enter a repository URL');return r;}
 function stats(d){const r=d.repository||{};const root=el('gh-summary');root.replaceChildren();for(const [label,value] of [['Repository',r.full_name],['Files',d.total_files],['Folders',d.total_folders],['Language',r.language||'Unknown'],['Stars',r.stars],['Size (KB)',Math.round((d.total_bytes||0)/1024)]]){const card=node('div',undefined,'gh-stat');card.append(node('small',label),node('strong',String(value??'—')));root.append(card);} }
 function files(rows){const root=el('gh-files');root.replaceChildren();if(!rows.length)root.append(node('p','No matching files.'));for(const f of rows){const b=node('button',f.path+(f.line?' : '+f.line:''),'gh-file');b.type='button';if(f.reason)b.title=f.reason;if(f.category)b.append(node('small',f.category,'gh-tag'));if(f.content)b.append(node('small',f.content,'gh-snippet'));b.onclick=()=>{if(f.type==='folder'){el('gh-query').value=f.path;el('gh-mode').value='filename';el('gh-search-form').requestSubmit();return;}run(async v=>{const d=await req('file',{repository:activeRepo,path:f.path});if(v!==epoch)return;el('gh-file-title').textContent=d.path;const code=node('code',d.content);el('gh-code').replaceChildren(code);status('File loaded · '+(d.lines??d.content.split('\n').length)+' lines');});};root.append(b);} }
 function analysis(d){const root=el('gh-analysis');root.replaceChildren();const cards=node('div',undefined,'gh-summary');const bar=node('div',undefined,'gh-bar');for(const [key,label] of [['useful','Useful'],['review','Needs review'],['unnecessary','Possibly unnecessary']]){const x=d.categories?.[key]||{};const pct=Math.max(0,Math.min(100,Number(x.file_percentage)||0));const card=node('div',undefined,'gh-stat gh-'+key);card.append(node('small',label),node('strong',pct+'%'),node('small',(x.files||0)+' files · '+(x.size_percentage||0)+'% of bytes'));cards.append(card);const seg=node('span',undefined,'gh-'+key);seg.style.width=pct+'%';bar.append(seg);}root.append(cards,bar,node('p','Duplicate groups: '+(d.duplicate_group_count||0)+' · Classification is heuristic; review before deleting.'));for(const g of (d.duplicate_groups||[]).slice(0,20)){const details=node('details');details.append(node('summary','Duplicate group · '+g.count+' files'));for(const p of g.files||[])details.append(node('div',typeof p==='string'?p:p.path));root.append(details);}const ext=node('details');ext.append(node('summary','File types'));for(const [k,v] of Object.entries(d.extensions||{}))ext.append(node('div',k+': '+(typeof v==='object'?JSON.stringify(v):v)));root.append(ext);}
 function load(analyze){run(async v=>{const r=repo();clear();const d=await req(analyze?'analyze':'repository',{repository:r});if(v!==epoch)return;activeRepo=r;stats(d);files(d.files||[]);if(analyze)analysis(d);status((d.truncated?'Partial repository listing · ':'')+(d.total_files||0)+' files loaded');});}
 el('github-tab').onclick=()=>showPage('github');el('gh-open-form').onsubmit=e=>{e.preventDefault();load(false);};el('gh-analyze').onclick=()=>load(true);
 el('gh-search-form').onsubmit=e=>{e.preventDefault();run(async v=>{if(!activeRepo||repo()!==activeRepo)throw Error('Open the repository first');const d=await req('search',{repository:activeRepo,query:el('gh-query').value.trim(),mode:el('gh-mode').value});if(v!==epoch)return;files(d.results||[]);status(d.total_results+' matches'+(d.limited?' · Search limit reached':'')+(d.truncated?' · Partial repository':''));});};
 el('logout').addEventListener('click',()=>{epoch++;clear();el('gh-repo').value='';el('gh-query').value='';status('Enter a repository URL to begin.');});
 const go=()=>{if(busy){toast('Stop the current response first');return;}newChat().catch(e=>toast(e.message));};
 for(const n of document.querySelectorAll('.sidebar .brand, header .search-ai-brand-logo, header #page-title')){n.classList.add('gh-brand-link');n.tabIndex=0;n.setAttribute('role','button');n.title='Start a new chat';n.addEventListener('click',go);n.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();go();}});}
})();
'''
c+='''\n/* GITHUB_UI_V1 */
.brand{font-style:italic}.gh-brand-link{cursor:pointer}.sidebar{gap:12px}.side-bottom{gap:5px}.side-bottom button{border:1px solid var(--line);background:var(--panel);padding:9px 12px}.side-bottom button:hover,.side-bottom button.workspace-active{border-color:var(--accent);background:var(--hover)}.chat-item{border:1px solid transparent}.chat-item.active{border-color:var(--line)}.chat-list{min-height:60px}button{transition:background .18s,border-color .18s,transform .15s,box-shadow .18s}button:not(:disabled):active{transform:scale(.97)}button:focus-visible,.gh-brand-link:focus-visible{outline:2px solid var(--accent);outline-offset:2px}.github-page{padding:28px clamp(16px,4vw,64px)}.gh-heading small{color:var(--accent);letter-spacing:2px;font-weight:700}.gh-heading h2{margin:8px 0}.gh-toolbar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:18px 0}.gh-toolbar input{flex:1;min-width:180px;width:auto}.gh-toolbar select{width:auto}.gh-summary{display:grid;grid-template-columns:repeat(auto-fit,minmax(135px,1fr));gap:12px;margin:16px 0}.gh-stat,.gh-pane{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px;min-width:0}.gh-stat small{display:block;color:var(--muted)}.gh-stat strong{display:block;font-size:21px;overflow-wrap:anywhere;margin:6px 0}.gh-useful strong{color:#22a76b}.gh-review strong{color:#c28b13}.gh-unnecessary strong{color:#e45d6b}.gh-bar{display:flex;height:10px;border-radius:8px;overflow:hidden;background:var(--line)}.gh-bar .gh-useful{background:#22a76b}.gh-bar .gh-review{background:#eab308}.gh-bar .gh-unnecessary{background:#e45d6b}.gh-browser{display:grid;grid-template-columns:minmax(200px,1fr) minmax(0,2fr);gap:14px}.gh-pane h3{margin-top:0;overflow-wrap:anywhere}#gh-files,#gh-code{max-height:55vh;overflow:auto}.gh-file{display:block;text-align:left;width:100%;border:0;border-bottom:1px solid var(--line);border-radius:0;overflow-wrap:anywhere;font-size:13px}.gh-tag,.gh-snippet{display:block;color:var(--muted);margin-top:4px}#gh-code{white-space:pre;line-height:1.6;font-size:13px;margin:0}#gh-analysis details{padding:8px;overflow-wrap:anywhere}#gh-status{font-size:13px}@media(max-width:780px){.gh-browser{grid-template-columns:1fr}.sidebar{overflow-y:auto}}@media(prefers-reduced-motion:reduce){button{transition:none!important;transform:none!important}}
'''
# Verify JS before touching project files.
subprocess.run(['node','--check','-'],input=j,encoding='utf-8',check=True)
backup=Path('backups')/('before-github-ui-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
for p in paths:
    dest=backup/p;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
try:
    for p,s in zip(paths,[h,j,c]):p.write_text(s,encoding='utf-8')
except Exception:
    for p in paths:shutil.copy2(backup/p,p)
    raise
print('SUCCESS: GitHub dashboard and UI installed')
print('Backup:',backup)
