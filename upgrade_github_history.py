from pathlib import Path
from datetime import datetime
import shutil, subprocess
paths=[Path('templates/index.html'),Path('static/app.js'),Path('static/style.css')]
h,j,c=[p.read_text(encoding='utf-8-sig') for p in paths]
if 'GITHUB_HISTORY_V1' in j: raise SystemExit('Already installed')
def rep(s,a,b):
    if s.count(a)!=1: raise SystemExit('Expected marker missing or repeated: '+a[:100])
    return s.replace(a,b,1)
h=rep(h,'<p id="gh-status"', '''<div class="gh-history-actions"><button type="button" id="gh-clear-repo">Clear Repository</button><button type="button" id="gh-clear-all">Clear All</button><button type="button" id="gh-history-toggle" aria-expanded="false">History</button></div>
<div id="gh-history-panel" class="gh-pane" hidden><div class="gh-history-actions"><h3>Repository history</h3><button type="button" id="gh-history-clear">Clear History</button></div><div id="gh-history-list"></div></div><p id="gh-status"''')
h=rep(h,'<button type="submit">Search</button></form>','<button type="submit">Search</button><button type="button" id="gh-clear-search">Clear Search</button></form>')
j=rep(j,"let activeRepo='', working=false, epoch=0;","let activeRepo='', working=false, epoch=0, originalFiles=[];")
j=rep(j,"function clear(){activeRepo='';","function clear(){activeRepo='';originalFiles=[];")
j=rep(j,"activeRepo=r;stats(d);files(d.files||[]);","activeRepo=r;originalFiles=d.files||[];stats(d);files(originalFiles);remember(d,r,analyze);")
anchor=" el('github-tab').onclick=()=>showPage('github');"
addition=r'''
 // GITHUB_HISTORY_V1
 const historyKey=()=>{const email=el('user-email').textContent.trim().toLowerCase();return email?'search-ai.github.history.v1:'+email:null;};
 function readHistory(){try{const k=historyKey();const a=k?JSON.parse(localStorage.getItem(k)||'[]'):[];return Array.isArray(a)?a:[];}catch(e){return [];}}
 function saveHistory(a){try{const k=historyKey();if(!k)throw Error('Login required');localStorage.setItem(k,JSON.stringify(a));return true;}catch(e){toast('Repository history could not be saved');return false;}}
 function remember(d,r,analyzed){const name=d.repository?.full_name;if(!name)return;const a=readHistory();const old=a.find(x=>x.name===name);saveHistory([{name,url:'https://github.com/'+name,date:new Date().toISOString(),analyzed:analyzed||!!old?.analyzed},...a.filter(x=>x.name!==name)].slice(0,50));renderHistory();}
 function renderHistory(){const root=el('gh-history-list');root.replaceChildren();const a=readHistory();if(!a.length)root.append(node('p','No repository history yet.'));for(const x of a){const row=node('div',undefined,'gh-history-row');const info=node('div');info.append(node('strong',x.name),node('small',new Date(x.date).toLocaleString()+(x.analyzed?' · Analyzed':'')));const open=node('button','Reopen');open.type='button';open.onclick=()=>{if(working)return;el('gh-repo').value=x.url;load(!!x.analyzed);};const del=node('button','Delete');del.type='button';del.onclick=()=>{if(working)return;if(saveHistory(readHistory().filter(y=>y.name!==x.name)))renderHistory();};row.append(info,open,del);root.append(row);}}
 function resetRepo(){if(working)return;clear();el('gh-repo').value='';el('gh-query').value='';el('gh-mode').value='filename';status('Enter a repository URL to begin.');}
 el('gh-clear-repo').onclick=resetRepo;
 el('gh-clear-search').onclick=()=>{if(working)return;el('gh-query').value='';el('gh-mode').value='filename';if(activeRepo)files(originalFiles);else el('gh-files').replaceChildren();status(activeRepo?'Search cleared · Repository files restored':'Enter a repository URL to begin.');};
 el('gh-clear-all').onclick=()=>{if(!working&&confirm('Clear the current GitHub workspace? Saved history will be kept.')){resetRepo();el('gh-history-panel').hidden=true;el('gh-history-toggle').setAttribute('aria-expanded','false');}};
 el('gh-history-toggle').onclick=()=>{const p=el('gh-history-panel');p.hidden=!p.hidden;el('gh-history-toggle').setAttribute('aria-expanded',String(!p.hidden));if(!p.hidden)renderHistory();};
 el('gh-history-clear').onclick=()=>{if(!working&&confirm('Delete all saved repository history for this account?')){if(saveHistory([]))renderHistory();}};
 el('logout').addEventListener('click',()=>{el('gh-history-list').replaceChildren();el('gh-history-panel').hidden=true;el('gh-history-toggle').setAttribute('aria-expanded','false');});
'''
j=rep(j,anchor,addition+anchor)
c+='''\n/* GITHUB_HISTORY_V1 */
.gh-history-actions{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:12px 0}.gh-history-actions h3{margin:0 auto 0 0}.gh-history-row{display:flex;align-items:center;gap:8px;padding:12px 0;border-bottom:1px solid var(--line)}.gh-history-row>div{flex:1;min-width:0;overflow-wrap:anywhere}.gh-history-row small{display:block;color:var(--muted);margin-top:4px}#gh-history-panel[hidden]{display:none}#gh-history-list{max-height:320px;overflow:auto}#gh-clear-all,#gh-history-clear{color:#e45d6b}
'''
subprocess.run(['node','--check','-'],input=j,encoding='utf-8',check=True)
backup=Path('backups')/('before-github-history-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
for p in paths:
    dest=backup/p;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
try:
    for p,s in zip(paths,[h,j,c]):p.write_text(s,encoding='utf-8')
except Exception:
    for p in paths:shutil.copy2(backup/p,p)
    raise
print('SUCCESS: GitHub history and clear controls installed')
print('Backup:',backup)
