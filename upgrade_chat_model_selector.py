from pathlib import Path
from datetime import datetime
import shutil
import subprocess

paths = [Path('app.py'), Path('static/app.js'), Path('static/style.css')]
s,j,c = [p.read_text(encoding='utf-8-sig') for p in paths]
assert 'CHAT_MODEL_SELECTOR_V1' not in j, 'Already installed'
def replace(text, old, new):
    assert text.count(old)==1, f'Expected one matching anchor: {old[:100]}'
    return text.replace(old,new,1)
s=replace(s,'    selected_model = settings["model"]','''    selected_model = data.get("model", settings["model"])
    if not isinstance(selected_model, str) or selected_model not in MODELS:
        return fail("Invalid model selected")''')
anchor="$('model').value=settings.model;"
j=replace(j,anchor,anchor+'initChatModelSelector(settings);')
j=replace(j,'body:JSON.stringify({message:text,','body:JSON.stringify({message:text,model:$(\'chat-model\').value,')
# Existing busy flag and send lifecycle remain authoritative.
j=replace(j,'busy=true;',"busy=true;$('chat-model').disabled=true;")
j=replace(j,'busy=false;',"busy=false;$('chat-model').disabled=false;") if j.count('busy=false;')==1 else replace(j,'finally{busy=false;',"finally{busy=false;$('chat-model').disabled=false;")
j+='''\n// CHAT_MODEL_SELECTOR_V1
function initChatModelSelector(config){
    let select = document.getElementById('chat-model');
    if(!select){
        select=document.createElement('select');
        select.id='chat-model';
        select.setAttribute('aria-label','AI model for this message');
        select.title='AI model for this message';
        document.querySelector('.composer-tools').append(select);
    }
    const labels={auto:'Auto - Token Efficient'};
    select.replaceChildren();
    for(const model of config.models){
        const option=document.createElement('option');
        option.value=model;
        option.textContent=labels[model]||model;
        select.append(option);
    }
    select.value=config.model;
    select.disabled=busy;
}
'''
c+='''\n/* CHAT_MODEL_SELECTOR_V1 */\n.composer-tools #chat-model {max-width:100%; min-width:0; font-size:12px;}\n.composer-tools {flex-wrap:wrap;}\n'''
compile(s,'app.py','exec')
# Check JS syntax if Node is available.
if shutil.which('node'):
    subprocess.run(['node','--check','-'],input=j,text=True,encoding='utf-8',check=True)
backup=Path('backups')/('before-chat-model-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
for p in paths:
    dest=backup/p; dest.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(p,dest)
try:
    for p,content in zip(paths,[s,j,c]): p.write_text(content,encoding='utf-8')
except Exception:
    for p in paths: shutil.copy2(backup/p,p)
    raise
print('SUCCESS: Chat model selector integrated')
print('SUCCESS: Python syntax verified')
print('Backup:',backup)
