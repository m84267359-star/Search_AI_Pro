from pathlib import Path
from datetime import datetime
import shutil, subprocess

p=Path('app.py'); jpath=Path('static/app.js'); csspath=Path('static/style.css')
s=p.read_text(encoding='utf-8-sig'); j=jpath.read_text(encoding='utf-8-sig'); css=csspath.read_text(encoding='utf-8-sig')
assert 'IMAGE_UPLOAD_V1' not in s and 'IMAGE_UPLOAD_V1' not in j, 'Already installed'
def replace_once(text, old, new):
    assert text.count(old)==1, 'Expected exactly one match: '+old[:100]
    return text.replace(old,new,1)
anchor='def chat_stream(chat_id):\n    chat = owned_chat(chat_id)\n    data = payload()'
s=replace_once(s,anchor,anchor+'''
    # IMAGE_UPLOAD_V1
    image_bytes = None
    image_data = data.get('image_data')
    if image_data is not None:
        try:
            import base64
            import warnings
            from PIL import Image, ImageOps
            from io import BytesIO
            if not isinstance(image_data, str) or len(image_data) > 7000000:
                raise ValueError('Invalid image size')
            raw_image = base64.b64decode(image_data, validate=True)
            if not raw_image or len(raw_image) > 5 * 1024 * 1024:
                raise ValueError('Invalid image size')
            with warnings.catch_warnings():
                warnings.simplefilter('error', Image.DecompressionBombWarning)
                with Image.open(BytesIO(raw_image)) as picture:
                    if picture.format not in ('PNG', 'JPEG', 'WEBP') or picture.width * picture.height > 20000000:
                        raise ValueError('Unsupported image')
                    picture = ImageOps.exif_transpose(picture)
                    picture.thumbnail((1600, 1600))
                    rgba = picture.convert('RGBA')
                    background = Image.new('RGB', rgba.size, 'white')
                    background.paste(rgba, mask=rgba.getchannel('A'))
                    buffer = BytesIO()
                    background.save(buffer, format='JPEG', quality=88)
                    image_bytes = buffer.getvalue()
        except Exception:
            return fail('Invalid image. Use PNG, JPEG or WEBP up to 5 MB.')
''')
anchor='            for attempt, model in enumerate(candidates, 1):'
s=replace_once(s,anchor,'''            if image_bytes is not None:
                contents[-1].parts.append(types.Part.from_bytes(data=image_bytes, mime_type='image/jpeg'))
'''+anchor)
anchor="const text=$('prompt').value.trim();if(!text)return;"
j=replace_once(j,anchor,"const text=$('prompt').value.trim()||(pendingImageData?'Describe this image.':'');if(!text)return;")
anchor="message:text,model:$('chat-model').value"
j=replace_once(j,anchor,"message:text,image_data:pendingImageData,model:$('chat-model').value")
anchor="if(!r.ok){const d=await r.json();throw Error(d.error||'Request failed')}const reader=r.body.getReader();"
j=replace_once(j,anchor,"if(!r.ok){const d=await r.json();throw Error(d.error||'Request failed')}clearPendingImage();const reader=r.body.getReader();")
j+='''
// IMAGE_UPLOAD_V1
let pendingImageData = null;
let imageReadVersion = 0;
let imagePreview = null;
function clearPendingImage(){
    imageReadVersion++;
    pendingImageData=null;
    if(imagePreview) imagePreview.replaceChildren();
    const picker=document.getElementById('image-picker');
    if(picker) picker.value='';
}
(function installImagePicker(){
    const tools=document.querySelector('.composer-tools');
    if(!tools)return;
    const picker=document.createElement('input');
    picker.type='file'; picker.id='image-picker'; picker.accept='image/png,image/jpeg,image/webp'; picker.hidden=true;
    const button=document.createElement('button'); button.type='button'; button.className='image-attach-btn'; button.textContent='Attach image';
    button.onclick=()=>{if(!busy)picker.click();};
    imagePreview=document.createElement('div'); imagePreview.className='image-upload-preview';
    tools.append(button,picker); tools.parentNode.insertBefore(imagePreview,tools);
    picker.onchange=()=>{
        if(busy)return;
        const file=picker.files[0]; clearPendingImage();
        if(!file)return;
        if(!['image/png','image/jpeg','image/webp'].includes(file.type)||file.size>5*1024*1024){toast('Choose PNG, JPEG or WEBP up to 5 MB');return;}
        const version=imageReadVersion;
        const reader=new FileReader();
        reader.onerror=()=>toast('Unable to read image');
        reader.onload=()=>{
            if(version!==imageReadVersion||busy)return;
            const url=String(reader.result);
            pendingImageData=url.split(',')[1];
            const img=document.createElement('img'); img.src=url; img.alt='Selected image';
            const name=document.createElement('span'); name.textContent=file.name;
            const remove=document.createElement('button'); remove.type='button'; remove.textContent='Remove'; remove.onclick=()=>{if(!busy)clearPendingImage();};
            imagePreview.replaceChildren(img,name,remove);
        };
        reader.readAsDataURL(file);
    };
})();
'''
css+='''\n/* IMAGE_UPLOAD_V1 */\n.image-upload-preview:empty{display:none}.image-upload-preview{display:flex;align-items:center;gap:12px;padding:8px;flex-wrap:wrap}.image-upload-preview img{width:76px;height:76px;object-fit:contain;border-radius:8px}.image-upload-preview span{overflow-wrap:anywhere}.image-attach-btn{cursor:pointer}\n'''
compile(s,str(p),'exec')
subprocess.run(['node','--check','-'],input=j,text=True,encoding='utf-8',check=True)
backup=Path('backups')/('before-image-upload-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
for f in (p,jpath,csspath):
    dest=backup/f; dest.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(f,dest)
for f,value in ((p,s),(jpath,j),(csspath,css)): f.write_text(value,encoding='utf-8')
print('SUCCESS: Image upload integrated')
print('SUCCESS: Python and JavaScript syntax verified')
print('Backup:',backup)
