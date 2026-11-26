from pathlib import Path
from datetime import datetime
import shutil, subprocess
p=Path('static/app.js'); c=Path('static/style.css')
s=p.read_text(encoding='utf-8-sig'); css=c.read_text(encoding='utf-8-sig')
assert 'def branch_chat(' in Path('app.py').read_text(encoding='utf-8-sig'), 'Install Edit Prompt first'
assert 'RETRY_RESPONSE_V1' not in s, 'Already installed'
def replace(old,new):
    global s
    assert s.count(old)==1, 'Expected code not found: '+old[:80]
    s=s.replace(old,new,1)
replace("setGenerating(true);try{", "setGenerating(true);let retryInfo=null,retryOut=null,retryFailed=false;try{")
replace("const out=addMessage('assistant','');", "const out=addMessage('assistant','');retryOut=out;retryInfo={chat:chatId,text,model:$('chat-model').value,search:$('web-search').value,document:$('document-select').value};")
replace("if(!done)toast('Stream ended before completion');", "if(!done){retryFailed=true;toast('Stream ended before completion');}")
replace("toast(e.message);\n    }\n}finally{", "retryFailed=true;toast(e.message);\n    }\n}finally{")
replace("setGenerating(false);\n}}", "setGenerating(false);if(retryFailed&&retryInfo&&retryOut)attachRetry(retryOut.div,retryInfo);\n}}")
s+=r'''
// RETRY_RESPONSE_V1
function attachRetry(message, info){
  const button=document.createElement('button');button.type='button';button.className='retry-response-btn';button.textContent='Retry response';
  button.onclick=async()=>{
    if(busy||chatId!==info.chat||$('prompt').value.trim()){toast('Open the failed conversation and clear your draft first');return;}
    button.disabled=true;
    try{
      const data=await api('/api/chats/'+info.chat);
      if(busy||chatId!==info.chat)throw Error('Conversation changed');
      const last=data.messages.at(-1);
      if(!last||last.role!=='user'||last.content!==info.text)throw Error('Failed prompt is not the last saved message. Refresh the conversation before retrying.');
      const r=await fetch('/api/chats/'+info.chat+'/branch',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:JSON.stringify({message_id:last.id})});
      if(!r.ok)throw Error('Could not create retry conversation');
      const branch=await r.json();
      if(busy||chatId!==info.chat||$('prompt').value.trim())throw Error('Retry branch created. Open it from the sidebar.');
      await openChat(branch.id);
      if(busy||chatId!==branch.id||$('prompt').value.trim())throw Error('Open the retry conversation to continue');
      for(const [id,value] of [['chat-model',info.model],['web-search',info.search],['document-select',info.document]]){
        if(![...$(id).options].some(o=>o.value===value))throw Error('Original request option is no longer available');
        $(id).value=value;
      }
      $('prompt').value=info.text;await send();
    }catch(e){toast(e.message);}finally{button.disabled=false;}
  };message.append(button);
}
'''
css+='\n/* RETRY_RESPONSE_V1 */\n.retry-response-btn{margin:8px;font-size:12px;cursor:pointer}.retry-response-btn:disabled{opacity:.5;cursor:wait}\n'
subprocess.run(['node','--check','-'],input=s,encoding='utf-8',check=True)
b=Path('backups')/('before-retry-'+datetime.now().strftime('%Y%m%d-%H%M%S'));b.mkdir(parents=True,exist_ok=False)
for f in (p,c):shutil.copy2(f,b/f.name)
p.write_text(s,encoding='utf-8');c.write_text(css,encoding='utf-8')
print('SUCCESS: Retry response integrated');print('SUCCESS: JavaScript syntax verified');print('Backup:',b)
