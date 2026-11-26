from pathlib import Path
from datetime import datetime
import shutil, subprocess
j=Path('static/app.js'); c=Path('static/style.css'); p=Path('app.py')
js=j.read_text(encoding='utf-8-sig'); css=c.read_text(encoding='utf-8-sig')
assert 'def branch_chat(' in p.read_text(encoding='utf-8-sig'), 'Install Edit Prompt first'
assert 'REGENERATE_RESPONSE_V1' not in js, 'Already installed'
addon=r'''
// REGENERATE_RESPONSE_V1
(function(){
  let pending=false;
  function attach(){
    document.querySelectorAll('#messages .message.assistant').forEach(message=>{
      if(message.querySelector('.regenerate-btn'))return;
      const button=document.createElement('button');
      button.type='button';button.className='regenerate-btn';button.textContent='↻ Regenerate';
      button.onclick=async()=>{
        if(busy||pending||!chatId){toast('Wait for the current response to finish');return;}
        if($('prompt').value.trim()){toast('Clear or save your draft before regenerating');return;}
        const original=chatId;pending=true;button.disabled=true;
        try{
          const data=await api('/api/chats/'+original);
          if(busy||chatId!==original)throw Error('Conversation changed. Please retry.');
          const visible=[...document.querySelectorAll('#messages .message')];
          const index=visible.indexOf(message);
          if(index<1||visible.length!==data.messages.length||!visible.every((m,i)=>m.classList.contains(data.messages[i].role)&&(m.querySelector('.message-content')?.dataset.raw||m.querySelector('.message-content')?.textContent)===data.messages[i].content))throw Error('Refresh this conversation before regenerating.');
          const target=data.messages[index-1];
          if(data.messages[index].role!=='assistant'||target.role!=='user')throw Error('Original prompt not found');
          const response=await fetch('/api/chats/'+original+'/branch',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:JSON.stringify({message_id:target.id})});
          if(!response.ok)throw Error('Could not create conversation branch');
          const branch=await response.json();
          if(busy||chatId!==original||$('prompt').value.trim())throw Error('Branch created. Open it from the sidebar.');
          await openChat(branch.id);
          if(busy||chatId!==branch.id||$('prompt').value.trim())throw Error('Open the new conversation to continue.');
          $('prompt').value=target.content;await send();
        }catch(e){toast(e.message);}finally{pending=false;button.disabled=false;}
      };
      message.append(button);
    });
  }
  const root=$('messages');if(root){new MutationObserver(attach).observe(root,{childList:true,subtree:true});attach();}
})();
'''
js+=addon
css+='\n/* REGENERATE_RESPONSE_V1 */\n.regenerate-btn{margin:8px 0 0 8px;font-size:12px;cursor:pointer}\n.regenerate-btn:disabled{opacity:.5;cursor:wait}\n'
subprocess.run(['node','--check','-'],input=js,encoding='utf-8',check=True)
backup=Path('backups')/('before-regenerate-'+datetime.now().strftime('%Y%m%d-%H%M%S'));backup.mkdir(parents=True,exist_ok=False)
for path in (j,c):shutil.copy2(path,backup/path.name)
for path,content in ((j,js),(c,css)):path.write_text(content,encoding='utf-8')
print('SUCCESS: Regenerate response integrated')
print('SUCCESS: JavaScript syntax verified')
print('Backup:',backup)
