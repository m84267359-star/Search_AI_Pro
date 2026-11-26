from pathlib import Path
from datetime import datetime
import shutil, subprocess

p=Path('app.py'); j=Path('static/app.js'); c=Path('static/style.css')
s=p.read_text(encoding='utf-8-sig'); js=j.read_text(encoding='utf-8-sig'); css=c.read_text(encoding='utf-8-sig')
assert 'EDIT_PROMPT_V1' not in s and 'EDIT_PROMPT_V1' not in js, 'Upgrade already installed'
anchor="@app.patch('/api/chats/<int:chat_id>')"
assert s.count(anchor)==1, 'Chat route not found'
route='''# EDIT_PROMPT_V1
@app.post('/api/chats/<int:chat_id>/branch')
@login_required
@csrf_required
@limiter.limit('25 per hour')
def branch_chat(chat_id):
    chat = owned_chat(chat_id)
    message_id = payload().get('message_id')
    if type(message_id) is not int:
        return fail('Invalid message ID')
    conn = db()
    target = conn.execute("SELECT id FROM messages WHERE chat_id=? AND id=? AND role='user'", (chat_id, message_id)).fetchone()
    if not target:
        return fail('Message not found', 404)
    t = stamp()
    try:
        cur = conn.execute('INSERT INTO chats(user_id,title,created_at,updated_at) VALUES (?,?,?,?)', (current_user.id, ('Edited: ' + chat['title'])[:100], t, t))
        new_id = cur.lastrowid
        conn.execute('INSERT INTO messages(chat_id,role,content,sources,created_at) SELECT ?,role,content,sources,created_at FROM messages WHERE chat_id=? AND id<? ORDER BY id', (new_id, chat_id, message_id))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return jsonify(id=new_id), 201


'''
s=s.replace(anchor,route+anchor,1)
# Resolve message IDs from the server at edit time, including newly streamed messages.
js+='''
// EDIT_PROMPT_V1
(function(){
  function attach(){
    document.querySelectorAll('#messages .message.user').forEach(message=>{
      if(message.querySelector('.edit-prompt-btn'))return;
      const content=message.querySelector('.message-content');
      if(!content)return;
      const button=document.createElement('button');
      button.type='button';button.className='edit-prompt-btn';button.textContent='✎ Edit prompt';
      button.onclick=async()=>{
        if(busy||!chatId||message.querySelector('.edit-prompt-form'))return;
        const originalChat=chatId;
        const form=document.createElement('div');form.className='edit-prompt-form';
        const field=document.createElement('textarea');field.value=content.textContent;field.maxLength=8000;
        const cancel=document.createElement('button');cancel.type='button';cancel.textContent='Cancel';
        const save=document.createElement('button');save.type='button';save.textContent='Save & Submit';
        form.append(field,cancel,save);message.append(form);content.hidden=true;button.hidden=true;field.focus();
        cancel.onclick=()=>{form.remove();content.hidden=false;button.hidden=false;};
        save.onclick=async()=>{
          const text=field.value.trim();if(!text||busy||chatId!==originalChat)return;
          save.disabled=true;cancel.disabled=true;
          try{
            const data=await api('/api/chats/'+originalChat);
            if(busy||chatId!==originalChat)throw Error('Conversation changed. Please retry.');
            const visible=[...document.querySelectorAll('#messages .message.user')];
            const stored=data.messages.filter(m=>m.role==='user');
            const index=visible.indexOf(message);
            if(index<0||visible.length!==stored.length||!visible.every((m,i)=>m.querySelector('.message-content')?.textContent===stored[i].content))throw Error('Refresh the conversation before editing.');
            const response=await fetch('/api/chats/'+originalChat+'/branch',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:JSON.stringify({message_id:stored[index].id})});
            if(!response.ok)throw Error('Could not create edited conversation');
            const branch=await response.json();
            if(busy||chatId!==originalChat)throw Error('Edited conversation created. Open it from the sidebar.');
            await openChat(branch.id);
            if(chatId!==branch.id||busy)throw Error('Open the edited conversation to continue.');
            $('prompt').value=text;await send();
          }catch(e){toast(e.message);save.disabled=false;cancel.disabled=false;}
        };
      };
      message.append(button);
    });
  }
  const root=$('messages');if(root){new MutationObserver(attach).observe(root,{childList:true,subtree:true});attach();}
})();
'''
css+='''\n/* EDIT_PROMPT_V1 */
.edit-prompt-btn{margin:8px 0 0 8px;font-size:12px;cursor:pointer}
.edit-prompt-form{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px;justify-content:flex-end}
.edit-prompt-form textarea{width:100%;min-height:90px;resize:vertical;padding:10px;font:inherit;color:inherit;background:transparent;border:1px solid #8171ed;border-radius:8px}
.edit-prompt-form button{padding:7px 12px;cursor:pointer}
.edit-prompt-form button:last-child{background:#8171ed;color:white;border-radius:8px}
'''
compile(s,str(p),'exec')
subprocess.run(['node','--check','-'],input=js,encoding='utf-8',check=True)
backup=Path('backups')/('before-edit-prompt-'+datetime.now().strftime('%Y%m%d-%H%M%S'));backup.mkdir(parents=True,exist_ok=False)
for path in (p,j,c): shutil.copy2(path,backup/path.name)
for path,content in ((p,s),(j,js),(c,css)):path.write_text(content,encoding='utf-8')
print('SUCCESS: Edit prompt integrated')
print('SUCCESS: Python and JavaScript syntax verified')
print('Backup:',backup)
