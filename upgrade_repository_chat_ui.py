from pathlib import Path
from datetime import datetime
import shutil, subprocess
paths=list(map(Path,['app.py','github_tools/repository_routes.py','templates/index.html','static/app.js','static/style.css']))
a,r,h,j,c=[p.read_text(encoding='utf-8-sig') for p in paths]
marker='GITHUB_CHAT_UI_V1'
if any(marker in s for s in (a,r,h,j,c)): raise SystemExit('Already installed or partially installed')
def rep(s,x,y):
    if s.count(x)!=1: raise SystemExit('Expected one match: '+x[:100])
    return s.replace(x,y,1)
r+='''\n# GITHUB_CHAT_UI_V1
@github_bp.post('/ask')
@login_required
def repository_ask():
    from .repository_chat import ask_repository
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error='JSON object required'), 400
    repository, question = data.get('repository'), data.get('question')
    if not isinstance(repository, str) or not 1 <= len(repository.strip()) <= 300:
        return jsonify(error='Valid repository URL required'), 400
    if not isinstance(question, str) or not 1 <= len(question.strip()) <= 2000:
        return jsonify(error='Question must contain 1-2000 characters'), 400
    return execute(ask_repository, repository.strip(), question.strip())
'''
a=rep(a,'app.register_blueprint(github_bp)', '''app.register_blueprint(github_bp)
# GITHUB_CHAT_UI_V1
_ask_endpoint = 'github_repository.repository_ask'
app.view_functions[_ask_endpoint] = csrf_required(
    limiter.limit('3 per minute; 15 per hour')(app.view_functions[_ask_endpoint])
)''')
h=rep(h,'AI Analyze</button></form>','AI Analyze</button><button id="gh-ask" type="button" class="primary">Ask AI</button></form>')
h=rep(h,'<form id="gh-search-form"', '''<!-- GITHUB_CHAT_UI_V1 -->
<section id="gh-chat-panel" class="gh-pane" hidden><div class="gh-history-actions"><h3>Repository AI Chat</h3><button id="gh-chat-clear" type="button">Clear chat</button></div><p id="gh-chat-repo"></p><div id="gh-chat-messages" aria-live="polite"></div><div class="gh-history-actions"><button type="button" data-gh-question="Find potential bugs">Find bugs</button><button type="button" data-gh-question="Explain the architecture">Explain architecture</button><button type="button" data-gh-question="Suggest security improvements">Improve security</button></div><form id="gh-chat-form"><textarea id="gh-chat-question" maxlength="2000" rows="3" required placeholder="Ask about this repository..."></textarea><button class="primary" type="submit">Send</button></form><p id="gh-chat-status" role="status"></p><p class="hint">Public source excerpts and your question are sent to Gemini. Each question is independent. Do not enter secrets.</p></section>
<form id="gh-search-form"''')
anchor="el('github-tab').onclick=()=>showPage('github');"
j=rep(j,anchor,r'''// GITHUB_CHAT_UI_V1
 const chatHistory=new Map();let chatRepo='';
 function hideRepoChat(){chatRepo='';el('gh-chat-panel').hidden=true;el('gh-chat-messages').replaceChildren();el('gh-chat-question').value='';el('gh-chat-status').textContent='';}
 function showRepoChat(){chatRepo=repo();el('gh-chat-panel').hidden=false;el('gh-chat-repo').textContent=chatRepo;drawRepoChat();}
 function drawRepoChat(){const list=el('gh-chat-messages');list.replaceChildren();for(const item of chatHistory.get(chatRepo)||[]){const q=node('div',item.question);q.className='gh-chat-user';const answer=document.createElement('div');answer.className='gh-chat-answer';renderMarkdown(answer,item.data.answer);const details=document.createElement('details');details.append(node('summary','Reviewed files · '+item.data.model+' · Input: '+(item.data.input_tokens??'Unknown')+' · Output: '+(item.data.output_tokens??'Unknown')));const ul=document.createElement('ul');for(const f of item.data.files_reviewed||[])ul.append(node('li',f.path+' · line '+f.start_line+(f.partial?' · Partial excerpt':'')));details.append(ul);const copy=node('button','Copy response');copy.type='button';copy.onclick=async()=>{try{await navigator.clipboard.writeText(item.data.answer);toast('Copied');}catch(e){toast('Unable to copy');}};const retry=node('button','Regenerate');retry.type='button';retry.onclick=()=>askRepoChat(item.question,item);answer.append(details,copy,retry);list.append(q,answer);}list.scrollTop=list.scrollHeight;}
 function askRepoChat(question,replaceItem=null){if(working)return;const r=chatRepo;if(!r||r!==el('gh-repo').value.trim()){status('Select Ask AI for this repository first');return;}question=question.trim();if(!question||question.length>2000)return;if(!confirm('Send question and selected public source excerpts to Gemini? This uses API tokens.'))return;run(async v=>{el('gh-chat-status').textContent='Generating answer…';el('gh-chat-question').disabled=true;try{const d=await api('/api/github/ask',json('POST',{repository:r,question}));if(v!==epoch||chatRepo!==r)return;const items=chatHistory.get(r)||[];const item={question,data:d};const i=items.indexOf(replaceItem);if(i>=0)items[i]=item;else items.push(item);chatHistory.set(r,items.slice(-20));if(chatHistory.size>20)chatHistory.delete(chatHistory.keys().next().value);el('gh-chat-question').value='';drawRepoChat();el('gh-chat-status').textContent='Answer complete';status('Repository answer complete');}catch(e){if(v===epoch&&chatRepo===r){el('gh-chat-status').textContent=e.message;status(e.message);}}finally{el('gh-chat-question').disabled=false;}});}
 el('gh-ask').onclick=()=>{if(!working)try{showRepoChat();}catch(e){status(e.message);}};
 el('gh-chat-form').onsubmit=e=>{e.preventDefault();askRepoChat(el('gh-chat-question').value);};
 el('gh-chat-clear').onclick=()=>{if(!working&&confirm('Clear this repository chat?')){chatHistory.delete(chatRepo);drawRepoChat();el('gh-chat-status').textContent='';}};
 for(const b of el('gh-chat-panel').querySelectorAll('[data-gh-question]'))b.onclick=()=>{el('gh-chat-question').value=b.dataset.ghQuestion;el('gh-chat-question').focus();};
 el('gh-repo').addEventListener('input',hideRepoChat);el('gh-clear-repo').addEventListener('click',hideRepoChat);el('logout').addEventListener('click',()=>{chatHistory.clear();hideRepoChat();});
 '''+anchor)
j=rep(j,"function clear(){clearAI();","function clear(){hideRepoChat();clearAI();")
c+='''\n/* GITHUB_CHAT_UI_V1 */
#gh-chat-panel{margin:18px 0;min-width:0}#gh-chat-panel[hidden]{display:none}#gh-chat-messages{max-height:650px;overflow:auto;display:flex;flex-direction:column;gap:12px} .gh-chat-user{align-self:flex-end;background:#6854c9;color:white;padding:12px;border-radius:12px;max-width:85%;white-space:pre-wrap;overflow-wrap:anywhere}.gh-chat-answer{border:1px solid var(--border);padding:14px;border-radius:12px;overflow:auto;overflow-wrap:anywhere}.gh-chat-answer button{margin:8px 8px 0 0}#gh-chat-form{display:flex;gap:8px;align-items:center;margin-top:12px}#gh-chat-question{flex:1;min-width:0;resize:vertical}#gh-chat-status{font-size:13px}#gh-chat-panel .gh-history-actions{flex-wrap:wrap}
'''
compile(a,str(paths[0]),'exec');compile(r,str(paths[1]),'exec')
subprocess.run(['node','--check','-'],input=j,encoding='utf-8',check=True)
backup=Path('backups')/('before-repository-chat-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
for p in paths:
    dest=backup/p;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
try:
    for p,s in zip(paths,(a,r,h,j,c)):p.write_text(s,encoding='utf-8')
except Exception:
    for p in paths:shutil.copy2(backup/p,p)
    raise
print('SUCCESS: Repository AI Chat installed; Python and JavaScript syntax checked')
print('Backup:',backup)
