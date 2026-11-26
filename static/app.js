const $=id=>document.getElementById(id);const csrf=document.querySelector('meta[name="csrf-token"]').content;
let chatId=null,registerMode=false,busy=false,settings=null,docs=[];
function toast(msg){$('toast').textContent=msg;$('toast').style.display='block';setTimeout(()=>$('toast').style.display='none',3500)}
async function api(url,opts={}){const r=await fetch(url,{credentials:'same-origin',...opts,headers:{'X-CSRF-Token':csrf,...(opts.body instanceof FormData?{}:{'Content-Type':'application/json'}),...(opts.headers||{})}});let d=await r.json().catch(()=>({error:'Unexpected response'}));if(!r.ok)throw Error(d.error||'Request failed');return d}
const json=(method,body)=>({method,body:JSON.stringify(body)});
function showPage(name){for(const p of ['chat','documents','usage','settings','admin','github'])$(p+'-page').hidden=p!==name;$('page-title').textContent=({chat:'AI Search',documents:'Document intelligence',usage:'Usage dashboard',settings:'Settings',admin:'Admin dashboard',github:'GitHub Repository'})[name];document.querySelector('.sidebar').classList.remove('open');document.querySelectorAll('.side-bottom button').forEach(b=>b.classList.toggle('workspace-active',b.id===name+'-tab'))}
async function init(){const me=await api('/api/me');$('auth').hidden=me.authenticated;$('workspace').hidden=!me.authenticated;if(!me.authenticated)return;$('user-email').textContent=me.email;$('admin-tab').hidden=!me.admin;settings=await api('/api/settings');$('model').innerHTML=settings.models.map(m=>`<option value="${m}">${m}</option>`).join('');$('model').value=settings.model;initChatModelSelector(settings);$('theme').value=settings.theme;$('instructions').value=settings.instructions;applyTheme(settings.theme);await Promise.all([refreshChats(),refreshDocs()]);showPage('chat')}
$('toggle-auth').onclick=()=>{registerMode=!registerMode;$('auth-title').textContent=registerMode?'Create your account':'Welcome back';$('auth-submit').textContent=registerMode?'Register':'Sign in';$('toggle-auth').textContent=registerMode?'Already registered? Sign in':'Create an account';$('auth-error').textContent=''};
$('auth-form').onsubmit=async e=>{e.preventDefault();try{await api(registerMode?'/api/register':'/api/login',json('POST',{email:$('email').value,password:$('password').value}));$('password').value='';await init()}catch(err){$('auth-error').textContent=err.message}};
$('logout').onclick=async()=>{await api('/api/logout',json('POST',{}));chatId=null;await init()};
async function refreshChats(){const chats=await api('/api/chats?q='+encodeURIComponent($('chat-filter').value));const list=$('chat-list');list.replaceChildren();for(const c of chats){const row=document.createElement('div');row.className='chat-item'+(chatId===c.id?' active':'');const open=document.createElement('button');open.className='chat-open';open.textContent='▤ '+c.title;open.onclick=()=>openChat(c.id);const rename=document.createElement('button');rename.className='chat-action';rename.textContent='✎';rename.title='Rename';rename.onclick=async()=>{const title=prompt('Rename conversation:',c.title);if(title===null)return;try{await api('/api/chats/'+c.id,json('PATCH',{title}));refreshChats()}catch(e){toast(e.message)}};const del=document.createElement('button');del.className='chat-action';del.textContent='×';del.title='Delete';del.onclick=async()=>{if(!confirm('Delete this chat?'))return;await api('/api/chats/'+c.id,{method:'DELETE'});if(chatId===c.id){chatId=null;$('messages').replaceChildren()}refreshChats()};row.append(open,rename,del);list.append(row)}}
$('chat-filter').oninput=()=>refreshChats().catch(e=>toast(e.message));
function emptyChat(){const e=document.createElement('div');e.className='empty';e.innerHTML='<div class="sparkle">✦</div><h1>What can I help you discover?</h1><p>Ask anything, search the web, or analyze a document.</p>';return e}
async function newChat(){const d=await api('/api/chats',json('POST',{}));chatId=d.id;$('messages').replaceChildren(emptyChat());showPage('chat');refreshChats()}
$('new-chat').onclick=()=>newChat().catch(e=>toast(e.message));
function addMessage(role,text,sources=[]){const div=document.createElement('div');div.className='message '+role;const label=document.createElement('div');label.className='role';label.textContent=role==='user'?'YOU':'✦ SEARCH AI';const content=document.createElement('div');content.className='message-content';if(role==='assistant'){renderMarkdown(content,text)}else{content.textContent=text;}div.append(label,content);if(role==='assistant'){const links=document.createElement('div');links.className='sources';for(const s of sources){if(!/^https?:\/\//.test(s.url))continue;const a=document.createElement('a');a.href=s.url;a.target='_blank';a.rel='noopener noreferrer';a.textContent=s.title||s.url;links.append(a)}div.append(links);const copy=document.createElement('button');copy.className='copy';copy.textContent='Copy';copy.onclick=()=>navigator.clipboard.writeText(content.dataset.raw||content.textContent).then(()=>toast('Copied'));div.append(copy)}$('messages').append(div);$('messages').scrollTop=$('messages').scrollHeight;return {content,div}}
async function openChat(id){chatId=id;const d=await api('/api/chats/'+id);$('messages').replaceChildren();if(!d.messages.length)$('messages').append(emptyChat());else for(const m of d.messages)addMessage(m.role,m.content,m.sources);showPage('chat');refreshChats()}
function parseSSE(raw,onEvent){const blocks=raw.replace(/\r/g,'').split('\n\n');for(const block of blocks){if(!block.trim())continue;let event='message',data='';for(const line of block.split('\n')){if(line.startsWith('event:'))event=line.slice(6).trim();if(line.startsWith('data:'))data+=line.slice(5).trim()}if(data){try{onEvent(event,JSON.parse(data))}catch(e){console.warn('Invalid SSE payload',e)}}}}
// STOP_GENERATION_V1
let generationController = null;

async function send(){if(busy)return;const text=$('prompt').value.trim()||(pendingImageData?'Describe this image.':'');if(!text)return;busy=true;$('chat-model').disabled=true;
generationController = new AbortController();
setGenerating(true);let retryInfo=null,retryOut=null,retryFailed=false;try{if(!chatId)await newChat();if($('messages').querySelector('.empty'))$('messages').replaceChildren();addMessage('user',text);$('prompt').value='';const out=addMessage('assistant','');retryOut=out;retryInfo={chat:chatId,text,model:$('chat-model').value,search:$('web-search').value,document:$('document-select').value};let raw='',done=false;const r=await fetch('/api/chats/'+chatId+'/stream',{signal:generationController.signal,method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:JSON.stringify({message:text,image_data:pendingImageData,model:$('chat-model').value,search_mode:$('web-search').value,document_id:$('document-select').value||null})});if(!r.ok){const d=await r.json();throw Error(d.error||'Request failed')}clearPendingImage();const reader=r.body.getReader();const decoder=new TextDecoder();while(true){const {value,done:ended}=await reader.read();raw+=decoder.decode(value||new Uint8Array(),{stream:!ended});const cut=raw.lastIndexOf('\n\n');if(cut>=0){const completed=raw.slice(0,cut+2);raw=raw.slice(cut+2);parseSSE(completed,(event,d)=>{if(event==='delta'){renderMarkdown(out.content,(out.content.dataset.raw||'')+d.text);$('messages').scrollTop=$('messages').scrollHeight}if(event==='error'){renderMarkdown(out.content,(out.content.dataset.raw||'')+'\n\nError: '+d.error);toast(d.error)}if(event==='done'){done=true;const links=document.createElement('div');links.className='sources';for(const s of d.sources||[]){if(!/^https?:\/\//.test(s.url))continue;const a=document.createElement('a');a.href=s.url;a.target='_blank';a.rel='noopener noreferrer';a.textContent=s.title||s.url;links.append(a)}out.div.append(links)}})}if(ended)break}if(!done){retryFailed=true;toast('Stream ended before completion');}await refreshChats()}catch(e){
    if(e.name === 'AbortError'){
        toast('Generation stopped');
    }else{
        retryFailed=true;toast(e.message);
    }
}finally{
    busy=false;$('chat-model').disabled=false;
    generationController=null;
    setGenerating(false);if(retryFailed&&retryInfo&&retryOut)attachRetry(retryOut.div,retryInfo);
}}
$('send').onclick=()=>{
    if(busy){
        stopGeneration();
    }else{
        send();
    }
};$('prompt').onkeydown=e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send()}};
document.querySelectorAll('[data-prompt]').forEach(b=>b.onclick=()=>{$('prompt').value=b.dataset.prompt;send()});
async function refreshDocs(){docs=await api('/api/documents');const sel=$('document-select');const selected=sel.value;sel.replaceChildren(new Option('General AI Chat',''),new Option('All my documents','all'));const list=$('document-list');list.replaceChildren();for(const d of docs){sel.add(new Option(d.name,d.id));const row=document.createElement('div');row.className='doc-row';const title=document.createElement('span');title.textContent='📄 '+d.name+' ('+d.chars+' characters)';const del=document.createElement('button');del.textContent='Delete';del.onclick=async()=>{if(!confirm('Delete document?'))return;await api('/api/documents/'+d.id,{method:'DELETE'});refreshDocs()};row.append(title,del);list.append(row)}sel.value=selected;if(!sel.value)sel.value=''}
$('upload-btn').onclick=async()=>{const f=$('upload').files[0];if(!f)return toast('Select a file');const body=new FormData();body.append('file',f);try{await api('/api/documents',{method:'POST',body});$('upload').value='';await refreshDocs();toast('Document uploaded')}catch(e){toast(e.message)}};
function statCard(label,value){const d=document.createElement('div');d.className='stat';const b=document.createElement('b');b.textContent=value;const s=document.createElement('span');s.textContent=label;d.append(b,s);return d}
$('usage-tab').onclick=async()=>{showPage('usage');const u=await api('/api/usage');$('usage-stats').replaceChildren(statCard('AI requests',u.requests),statCard('Your chats',u.chats),statCard('Input tokens',u.input_tokens),statCard('Output tokens',u.output_tokens),statCard('Estimated token cost','$'+Number(u.cost).toFixed(5)))};
$('admin-tab').onclick=async()=>{showPage('admin');try{const u=await api('/api/admin/stats');$('admin-stats').replaceChildren(statCard('Users',u.users),statCard('Chats',u.chats),statCard('Requests',u.requests),statCard('Estimated token cost','$'+Number(u.estimated_cost).toFixed(5)))}catch(e){toast(e.message)}};
$('documents-tab').onclick=()=>showPage('documents');$('settings-tab').onclick=()=>showPage('settings');

function applyTheme(theme) {
    theme = theme === 'light' ? 'light' : 'dark';

    document.body.classList.remove('light', 'dark');
    document.body.classList.add(theme);
    document.documentElement.style.colorScheme = theme;
}

$('theme').addEventListener('change', function () {
    applyTheme(this.value);
});

$('save-settings').onclick=async()=>{try{await api('/api/settings',json('PUT',{model:$('model').value,theme:$('theme').value,instructions:$('instructions').value}));applyTheme($('theme').value);toast('Settings saved')}catch(e){toast(e.message)}};
$('delete-all').onclick=async()=>{if(!confirm('Permanently delete all your conversations?'))return;await api('/api/chats',{method:'DELETE'});chatId=null;$('messages').replaceChildren(emptyChat());refreshChats();toast('Chats deleted')};
$('menu').onclick=()=>document.querySelector('.sidebar').classList.toggle('open');
$('voice').onclick=()=>{const Speech=window.SpeechRecognition||window.webkitSpeechRecognition;if(!Speech)return toast('Speech recognition is not available in this browser');const rec=new Speech();rec.lang=navigator.language||'en-US';rec.interimResults=false;rec.onresult=e=>{$('prompt').value=(($('prompt').value||'')+' '+e.results[0][0].transcript).trim()};rec.onerror=e=>toast('Microphone: '+e.error);rec.start()};
// Export link is exposed as a chat action in the header's title menu.
const exportBtn=document.createElement('button');exportBtn.textContent='↓ PDF';exportBtn.title='Export current conversation as PDF';exportBtn.onclick=()=>{if(!chatId)return toast('Open a conversation first');window.location.href='/api/chats/'+chatId+'/export.pdf'};document.querySelector('header').insertBefore(exportBtn,$('user-email'));
init().catch(e=>toast(e.message));


// UI_UPGRADE_V2
(function () {
    function setupUI() {
        const sun = `<svg viewBox="0 0 24 24" fill="none"
        stroke="currentColor" stroke-width="1.8">
        <circle cx="12" cy="12" r="4"/>
        <path d="M12 2v3M12 19v3M2 12h3M19 12h3
        M5 5l2 2M17 17l2 2M5 19l2-2M17 7l-2 2"/>
        </svg>`;

        const moon = `<svg viewBox="0 0 24 24" fill="none"
        stroke="currentColor" stroke-width="1.8">
        <path d="M21 12.8A9 9 0 1 1 11.2 3
        A7 7 0 0 0 21 12.8Z"/>
        </svg>`;

        const eye = `<svg viewBox="0 0 24 24" fill="none"
        stroke="currentColor" stroke-width="1.8">
        <path d="M2 12s4-7 10-7 10 7 10 7
        -4 7-10 7-10-7-10-7Z"/>
        <circle cx="12" cy="12" r="3"/>
        </svg>`;

        const eyeOff = `<svg viewBox="0 0 24 24" fill="none"
        stroke="currentColor" stroke-width="1.8">
        <path d="M3 3l18 18M10 5h2c6 0 10 7 10 7
        a15 15 0 0 1-3 4M6 6C3 9 2 12 2 12
        s4 7 10 7a10 10 0 0 0 5-1"/>
        </svg>`;

        const email = document.getElementById("user-email");
        const themeSelect = document.getElementById("theme");

        if (email && !document.getElementById("quick-theme-toggle")) {
            const button = document.createElement("button");

            button.id = "quick-theme-toggle";
            button.type = "button";
            button.className = "ui-icon-button";
            button.style.verticalAlign = "middle";
            button.style.marginLeft = "12px";

            function updateIcon() {
                const light = document.body.classList.contains("light");

                button.innerHTML = light ? moon : sun;
                button.title = light ? "Dark mode" : "Light mode";
                button.setAttribute("aria-label", button.title);
            }

            email.insertAdjacentElement("afterend", button);
            updateIcon();

            button.onclick = async function () {
                const next = document.body.classList.contains("light")
                    ? "dark" : "light";

                applyTheme(next);

                if (themeSelect) {
                    themeSelect.value = next;
                }

                updateIcon();
                button.disabled = true;

                try {
                    const current = await api("/api/settings");

                    await api("/api/settings", json("PUT", {
                        model: current.model,
                        theme: next,
                        instructions: current.instructions
                    }));

                    settings.theme = next;

                } catch (error) {
                    console.error("Theme saving failed:", error);
                    button.title = "Theme applied but not saved";
                } finally {
                    button.disabled = false;
                }
            };

            new MutationObserver(updateIcon).observe(
                document.body,
                {
                    attributes: true,
                    attributeFilter: ["class"]
                }
            );

            if (themeSelect) {
                const label = themeSelect.closest("label");

                if (label) {
                    label.style.display = "none";
                } else {
                    themeSelect.style.display = "none";

                    document.querySelectorAll('label[for="theme"]')
                        .forEach(el => el.style.display = "none");
                }
            }
        }

        document.querySelectorAll('input[type="password"]')
            .forEach(function (password) {

                if (password.closest(".password-wrapper")) return;

                const wrapper = document.createElement("div");
                wrapper.className = "password-wrapper";
                wrapper.style.position = "relative";
                wrapper.style.width = "100%";

                password.parentNode.insertBefore(wrapper, password);
                wrapper.appendChild(password);

                const toggle = document.createElement("button");

                toggle.type = "button";
                toggle.className = "password-toggle";
                toggle.innerHTML = eye;
                toggle.title = "Show password";
                toggle.setAttribute("aria-label", "Show password");

                Object.assign(toggle.style, {
                    position: "absolute",
                    right: "8px",
                    top: "50%",
                    transform: "translateY(-50%)",
                    width: "34px",
                    height: "34px",
                    padding: "6px",
                    border: "none",
                    background: "transparent",
                    color: "inherit",
                    cursor: "pointer"
                });

                password.style.paddingRight = "48px";

                toggle.onclick = function () {
                    const show = password.type === "password";

                    password.type = show ? "text" : "password";
                    toggle.innerHTML = show ? eyeOff : eye;
                    toggle.title = show ? "Hide password" : "Show password";
                    toggle.setAttribute("aria-label", toggle.title);
                };

                wrapper.appendChild(toggle);
            });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", setupUI);
    } else {
        setupUI();
    }
})();


// MARKDOWN_UPGRADE_V1

function renderMarkdown(element, text) {
    element.dataset.raw = text;
    element.classList.add('markdown-body');

    if (!window.marked || !window.DOMPurify) {
        element.textContent = text;
        return;
    }

    const html = marked.parse(text, {
        gfm: true,
        breaks: false
    });

    element.innerHTML = DOMPurify.sanitize(html, {
        ALLOWED_TAGS: [
            'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'strong', 'em', 'del', 'ul', 'ol', 'li',
            'blockquote', 'pre', 'code', 'a', 'hr',
            'br', 'table', 'thead', 'tbody', 'tr',
            'th', 'td'
        , 'span', 'div'],
        ALLOWED_ATTR: ['href', 'title', 'class', 'start'],
        ALLOW_DATA_ATTR: false
    });

    element.querySelectorAll('a').forEach(link => {
        if (!/^https?:\/\//i.test(link.getAttribute('href') || '')) {
            link.removeAttribute('href');
        }
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
    });

    element.querySelectorAll('table').forEach(table => {
        const wrapper = document.createElement('div');
        wrapper.className = 'markdown-table';

        table.replaceWith(wrapper);
        wrapper.appendChild(table);
    });

    element.querySelectorAll('pre').forEach(pre => {
        const code = pre.querySelector('code');

        if (!code) return;

        const originalCode = code.textContent;

        const languageClass = [...code.classList].find(
            name => name.startsWith('language-')
        );

        const language = languageClass
            ? languageClass.replace('language-', '')
            : 'code';

        code.textContent = originalCode;

        if (window.hljs) {
            try {
                hljs.highlightElement(code);
            } catch (error) {
                console.warn(error);
            }
        }

        const wrapper = document.createElement('div');
        wrapper.className = 'code-wrapper';

        const header = document.createElement('div');
        header.className = 'code-header';

        const label = document.createElement('span');
        label.textContent = language;

        const copy = document.createElement('button');
        copy.type = 'button';
        copy.className = 'copy-code';
        copy.textContent = 'Copy code';

        copy.onclick = async () => {
            try {
                await navigator.clipboard.writeText(originalCode);
                copy.textContent = 'Copied!';

                setTimeout(() => {
                    copy.textContent = 'Copy code';
                }, 2000);

            } catch (error) {
                toast('Unable to copy code');
            }
        };

        header.append(label, copy);

        pre.replaceWith(wrapper);
        wrapper.append(header, pre);
    });
}


let originalSendHTML = null;

function setGenerating(active){
    const button = $('send');

    if(originalSendHTML === null){
        originalSendHTML = button.innerHTML;
    }

    button.disabled = false;
    button.type = 'button';

    if(active){
        button.innerHTML = `
            <svg width="20" height="20"
                 viewBox="0 0 24 24">
                <rect x="5" y="5"
                      width="14" height="14"
                      rx="2" fill="currentColor"/>
            </svg>
        `;

        button.title = 'Stop generating';
        button.setAttribute(
            'aria-label', 'Stop generating'
        );

        button.classList.add('generating');
    }else{
        button.innerHTML = originalSendHTML;
        button.title = 'Send message';

        button.setAttribute(
            'aria-label', 'Send message'
        );

        button.classList.remove('generating');
    }
}

function stopGeneration(){
    if(generationController){
        generationController.abort();
    }
}


// TEXT_TO_SPEECH_V1

(function () {

    if (!('speechSynthesis' in window)) return;

    let activeButton = null;

    function resetSpeech() {
        if (activeButton) {
            activeButton.textContent = '\uD83D\uDD0A Read aloud';
            activeButton = null;
        }
    }

    function addSpeechButtons() {

        document.querySelectorAll(
            '.message.assistant'
        ).forEach(message => {

            if (message.querySelector('.speech-btn')) return;

            const content = message.querySelector(
                '.message-content'
            );

            if (!content) return;

            const button = document.createElement('button');

            button.type = 'button';
            button.className = 'speech-btn';
            button.textContent = '\uD83D\uDD0A Read aloud';
            button.title = 'Listen to AI response';

            button.onclick = function () {

                if (activeButton === button) {
                    speechSynthesis.cancel();
                    resetSpeech();
                    return;
                }

                if (busy) {
                    toast('Please wait for the response');
                    return;
                }

                speechSynthesis.cancel();
                resetSpeech();

                const text = content.innerText.trim();

                if (!text) return;

                const speech = new SpeechSynthesisUtterance(text);

                speech.lang = 'en-IN';
                speech.rate = 1;
                speech.pitch = 1;
                speech.volume = 1;

                activeButton = button;
                button.textContent = '\u23F9 Stop reading';

                speech.onend = speech.onerror = () => {
                    if (activeButton === button) {
                        resetSpeech();
                    }
                };

                speechSynthesis.speak(speech);
            };

            message.appendChild(button);
        });
    }

    const observer = new MutationObserver(addSpeechButtons);

    observer.observe(
        document.getElementById('messages'),
        {
            childList: true,
            subtree: true
        }
    );

    addSpeechButtons();

    window.addEventListener('beforeunload', () => {
        speechSynthesis.cancel();
    });

})();


// KATEX_UPGRADE_V1

(function () {

    if (!window.katex || !window.marked) return;

    function escapeMath(text) {
        return text.replace(/&/g, '&amp;')
                   .replace(/</g, '&lt;')
                   .replace(/>/g, '&gt;');
    }

    marked.use({
        extensions: [
            {
                name: 'displayMath',
                level: 'block',

                tokenizer(src) {
                    const match = src.match(
                        /^(?:\$\$([\s\S]+?)\$\$|\\\[([\s\S]+?)\\\])/
                    );

                    if (match) {
                        return {
                            type: 'displayMath',
                            raw: match[0],
                            text: match[1] ?? match[2]
                        };
                    }
                },

                renderer(token) {
                    return '<div class="math-display-source">' +
                        escapeMath(token.text) +
                        '</div>';
                }
            },

            {
                name: 'inlineMath',
                level: 'inline',

                start(src) {
                    return src.search(/\$|\\\(/);
                },

                tokenizer(src) {
                    const match = src.match(
                        /^(?:\$\$([\s\S]+?)\$\$|\\\[([\s\S]+?)\\\]|\\\(([\s\S]+?)\\\)|\$(?!\$|\s)([^$\n]+?)\$)/
                    );

                    if (match) {
                        return {
                            type: 'inlineMath',
                            raw: match[0],
                            text: match[1] ?? match[2] ??
                                  match[3] ?? match[4],
                            display: match[1] !== undefined ||
                                     match[2] !== undefined
                        };
                    }
                },

                renderer(token) {
                    const cls = token.display
                        ? 'math-display-source'
                        : 'math-inline-source';

                    return '<span class="' + cls + '">' +
                        escapeMath(token.text) +
                        '</span>';
                }
            }
        ]
    });

    const originalRenderMarkdown = renderMarkdown;

    renderMarkdown = function(element, text) {

        originalRenderMarkdown(element, text);

        element.querySelectorAll(
            '.math-display-source, .math-inline-source'
        ).forEach(node => {

            const formula = node.textContent;

            try {
                katex.render(formula, node, {
                    displayMode: node.classList.contains(
                        'math-display-source'
                    ),
                    throwOnError: false,
                    trust: false,
                    maxExpand: 1000,
                    maxSize: 20
                });

            } catch (error) {
                console.warn('Math rendering failed:', error);
            }
        });
    };

})();


// MERMAID_UPGRADE_V1

(function () {

    if (!window.mermaid || !window.DOMPurify) {
        console.warn('Mermaid dependencies unavailable');
        return;
    }

    mermaid.initialize({
        startOnLoad: false,
        securityLevel: 'strict',
        
// MERMAID_COLOR_V2
theme: 'base',

themeVariables: {
    primaryColor: '#dcfce7',
    primaryTextColor: '#14532d',
    primaryBorderColor: '#16a34a',

    secondaryColor: '#dbeafe',
    secondaryTextColor: '#1e40af',
    secondaryBorderColor: '#2563eb',

    tertiaryColor: '#ede9fe',
    tertiaryTextColor: '#5b21b6',
    tertiaryBorderColor: '#8b5cf6',

    lineColor: '#64748b',
    background: '#f8fafc',
    mainBkg: '#dcfce7',
    nodeBorder: '#16a34a',
    clusterBkg: '#f0fdf4',
    clusterBorder: '#86efac',

    fontFamily: 'Arial, sans-serif',
    fontSize: '15px'
},

        maxTextSize: 10000,
        maxEdges: 100,
        flowchart: {
            htmlLabels: false,
            curve: 'basis',
            nodeSpacing: 45,
            rankSpacing: 55,
            useMaxWidth: true
        }
    });

    let diagramCounter = 0;
    const timers = new WeakMap();

    async function renderDiagrams(element) {

        if (!element.isConnected) return;

        const blocks = element.querySelectorAll(
            'pre code.language-mermaid'
        );

        for (const code of blocks) {

            if (!code.isConnected) continue;

            
const source = code.textContent.trim()
    .replace(/<\/?(?:b|strong|i|em|u)>/gi, '');


            if (!source || source.length > 10000) continue;

            // Block diagram configuration overrides.
            if (/%%\{|^\s*---/m.test(source)) continue;

            const wrapper = code.closest('.code-wrapper')
                || code.closest('pre');

            if (!wrapper) continue;

            try {

                const id = 'diagram-' + (++diagramCounter);

                const result = await mermaid.render(
                    id,
                    source
                );

                if (!wrapper.isConnected) continue;

                const diagram = document.createElement('div');

                diagram.className = 'mermaid-diagram';

                diagram.innerHTML = DOMPurify.sanitize(
                    result.svg,
                    {
                        USE_PROFILES: {
                            svg: true,
                            svgFilters: true
                        },
                        FORBID_TAGS: [
                            'script',
                            'foreignObject',
                            'a',
                            'image'
                        ],
                        FORBID_ATTR: [
                            'href',
                            'xlink:href'
                        ]
                    }
                );

                const button = document.createElement('button');

                button.type = 'button';
                button.className = 'diagram-copy';
                button.textContent = 'Copy diagram code';

                button.onclick = () => {
                    navigator.clipboard.writeText(source)
                        .then(() => toast('Diagram code copied'))
                        .catch(() => toast('Copy failed'));
                };

                diagram.appendChild(button);

                wrapper.replaceWith(diagram);

            } catch (error) {

                // Preserve original code if rendering fails.
                console.warn('Diagram rendering failed', error);
            }
        }
    }

    const previousRender = renderMarkdown;

    renderMarkdown = function(element, text) {

        previousRender(element, text);

        clearTimeout(timers.get(element));

        timers.set(element, setTimeout(() => {

            renderDiagrams(element);

        }, 800));
    };

})();


// SEARCH_AI_LOGO_V1

(function () {

    const header = document.querySelector('header');

    if (!header) return;

    const logo = document.createElement('img');

    logo.src = '/static/images/search-ai-logo.png';
    logo.alt = 'Search AI Pro';
    logo.title = 'Search AI Pro';
    logo.className = 'search-ai-brand-logo';

    header.prepend(logo);

})();


// COPY_PROMPT_V1

(function () {

    function addCopyPromptButtons() {

        document.querySelectorAll(
            '.message.user'
        ).forEach(message => {

            if (message.querySelector('.copy-prompt-btn')) {
                return;
            }

            const content = message.querySelector(
                '.message-content'
            ) || message.children[1];

            if (!content) return;

            const button = document.createElement('button');

            button.type = 'button';
            button.className = 'copy-prompt-btn';
            button.title = 'Copy prompt';
            button.setAttribute('aria-label', 'Copy prompt');

            const copyIcon = `
                <svg width="15" height="15"
                     viewBox="0 0 24 24"
                     fill="none"
                     stroke="currentColor"
                     stroke-width="1.8">
                    <rect x="8" y="8" width="12"
                          height="12" rx="2"/>
                    <path d="M16 8V5a2 2 0 0 0-2-2H5
                             a2 2 0 0 0-2 2v9
                             a2 2 0 0 0 2 2h3"/>
                </svg>
                <span>Copy prompt</span>
            `;

            button.innerHTML = copyIcon;

            button.onclick = async function () {

                try {

                    const text = content.dataset.raw
                        ?? content.textContent;

                    await navigator.clipboard.writeText(text);

                    button.textContent = '\u2713 Copied';
                    button.classList.add('copied');

                    toast('Prompt copied successfully');

                    setTimeout(() => {
                        button.innerHTML = copyIcon;
                        button.classList.remove('copied');
                    }, 1500);

                } catch (error) {

                    toast('Unable to copy prompt');

                }
            };

            message.appendChild(button);

        });
    }

    const messages = document.getElementById('messages');

    if (!messages) return;

    const observer = new MutationObserver(
        addCopyPromptButtons
    );

    observer.observe(messages, {
        childList: true,
        subtree: true
    });

    addCopyPromptButtons();

})();

// CHAT_MODEL_SELECTOR_V1
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

// AI_MEMORY_V1
(function(){
 const el=id=>document.getElementById(id);
 async function req(path,method='GET',data){
   const r=await fetch('/api/memory'+path,{method,headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},...(data===undefined?{}:{body:JSON.stringify(data)})});
   const d=await r.json(); if(!r.ok)throw Error(d.error||'Memory request failed'); return d;
 }
 async function load(){
   const d=await req(''); el('memory-enabled').checked=d.enabled; el('memory-add').disabled=!d.enabled;
   const list=el('memory-list'); list.replaceChildren();
   for(const m of d.memories){const row=document.createElement('div'); const t=document.createElement('textarea');t.value=m.content;t.maxLength=500;t.rows=2;row.append(t);
     for(const [label,fn] of [['Save',()=>req('/'+m.id,'PATCH',{content:t.value})],['Delete',()=>req('/'+m.id,'DELETE')]]){const b=document.createElement('button');b.type='button';b.textContent=label;b.onclick=()=>run(fn);row.append(b);}list.append(row);}
 }
 async function run(fn){try{await fn();await load();}catch(e){toast(e.message);}}
 el('memory-enabled').onchange=()=>run(()=>req('','PUT',{enabled:el('memory-enabled').checked}));
 el('memory-add').onclick=()=>run(async()=>{await req('','POST',{content:el('memory-new').value});el('memory-new').value='';});
 el('memory-clear').onclick=()=>{if(confirm('Delete all saved memories?'))run(()=>req('','DELETE'));};
 const page=el('settings-page'); new MutationObserver(()=>{if(!page.hidden)load().catch(e=>toast(e.message));}).observe(page,{attributes:true,attributeFilter:['hidden']});
})();

// KNOWLEDGE_BASE_V1
async function refreshKnowledgeBase(){
 const panel=document.getElementById('kb-status');
 try{
  const rows=await api('/api/knowledge-base');
  panel.replaceChildren();
  const summary=document.createElement('p');
  summary.textContent=`Documents: ${rows.length} | Indexed: ${rows.filter(d=>d.indexed).length} | Chunks: ${rows.reduce((n,d)=>n+d.chunks,0)}`;
  panel.append(summary);
  for(const d of rows){
   const row=document.createElement('div');row.className='doc-row';
   const label=document.createElement('span');label.textContent=d.name+' — '+(d.indexed?'Indexed ('+d.chunks+' chunks)':'Pending');
   const btn=document.createElement('button');btn.textContent='Reindex';
   btn.onclick=async()=>{btn.disabled=true;try{await api('/api/knowledge-base/'+d.id+'/reindex',{method:'POST'});await refreshKnowledgeBase();toast('Document indexed')}catch(e){toast(e.message)}finally{btn.disabled=false}};
   row.append(label,btn);panel.append(row);
  }
 }catch(e){panel.textContent='Knowledge base status unavailable: '+e.message;}
}
document.getElementById('kb-refresh').onclick=refreshKnowledgeBase;

// GITHUB_UI_V1
(function(){
 const el=$; let activeRepo='', working=false, epoch=0, originalFiles=[];
 const status=t=>el('gh-status').textContent=t;
 function node(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;}
 function clear(){hideRepoChat();clearAI();activeRepo='';originalFiles=[];el('gh-summary').replaceChildren();el('gh-analysis').replaceChildren();el('gh-files').replaceChildren();el('gh-file-title').textContent='Source code';el('gh-code').textContent='Select a file to view its content.';}
 async function run(fn){if(working)return;working=true;const version=epoch;const controls=[...el('github-page').querySelectorAll('button,input,select')];controls.forEach(b=>b.disabled=true);status('Loading from GitHub…');try{await fn(version);}catch(e){if(version===epoch)status(e.message);}finally{working=false;controls.forEach(b=>b.disabled=false);}}
 const req=(route,params)=>api('/api/github/'+route+'?'+new URLSearchParams(params));
 function repo(){const r=el('gh-repo').value.trim();if(!r)throw Error('Enter a repository URL');return r;}
 function stats(d){const r=d.repository||{};const root=el('gh-summary');root.replaceChildren();for(const [label,value] of [['Repository',r.full_name],['Files',d.total_files],['Folders',d.total_folders],['Language',r.language||'Unknown'],['Stars',r.stars],['Size (KB)',Math.round((d.total_bytes||0)/1024)]]){const card=node('div',undefined,'gh-stat');card.append(node('small',label),node('strong',String(value??'—')));root.append(card);} }
 function files(rows){const root=el('gh-files');root.replaceChildren();if(!rows.length)root.append(node('p','No matching files.'));for(const f of rows){const b=node('button',f.path+(f.line?' : '+f.line:''),'gh-file');b.type='button';if(f.reason)b.title=f.reason;if(f.category)b.append(node('small',f.category,'gh-tag'));if(f.content)b.append(node('small',f.content,'gh-snippet'));b.onclick=()=>{if(f.type==='folder'){el('gh-query').value=f.path;el('gh-mode').value='filename';el('gh-search-form').requestSubmit();return;}run(async v=>{const d=await req('file',{repository:activeRepo,path:f.path});if(v!==epoch)return;el('gh-file-title').textContent=d.path;const code=node('code',d.content);el('gh-code').replaceChildren(code);status('File loaded · '+(d.lines??d.content.split('\n').length)+' lines');});};root.append(b);} }
 function analysis(d){const root=el('gh-analysis');root.replaceChildren();const cards=node('div',undefined,'gh-summary');const bar=node('div',undefined,'gh-bar');for(const [key,label] of [['useful','Useful'],['review','Needs review'],['unnecessary','Possibly unnecessary']]){const x=d.categories?.[key]||{};const pct=Math.max(0,Math.min(100,Number(x.file_percentage)||0));const card=node('div',undefined,'gh-stat gh-'+key);card.append(node('small',label),node('strong',pct+'%'),node('small',(x.files||0)+' files · '+(x.size_percentage||0)+'% of bytes'));cards.append(card);const seg=node('span',undefined,'gh-'+key);seg.style.width=pct+'%';bar.append(seg);}root.append(cards,bar,node('p','Duplicate groups: '+(d.duplicate_group_count||0)+' · Classification is heuristic; review before deleting.'));for(const g of (d.duplicate_groups||[]).slice(0,20)){const details=node('details');details.append(node('summary','Duplicate group · '+g.count+' files'));for(const p of g.files||[])details.append(node('div',typeof p==='string'?p:p.path));root.append(details);}const ext=node('details');ext.append(node('summary','File types'));for(const [k,v] of Object.entries(d.extensions||{}))ext.append(node('div',k+': '+(typeof v==='object'?JSON.stringify(v):v)));root.append(ext);}
 function load(analyze){run(async v=>{const r=repo();clear();const d=await req(analyze?'analyze':'repository',{repository:r});if(v!==epoch)return;activeRepo=r;originalFiles=d.files||[];stats(d);files(originalFiles);remember(d,r,analyze);if(analyze)analysis(d);status((d.truncated?'Partial repository listing · ':'')+(d.total_files||0)+' files loaded');});}

 // GITHUB_HISTORY_V1
 const historyKey=()=>{const email=el('user-email').textContent.trim().toLowerCase();return email?'search-ai.github.history.v1:'+email:null;};
 function readHistory(){try{const k=historyKey();const a=k?JSON.parse(localStorage.getItem(k)||'[]'):[];return Array.isArray(a)?a:[];}catch(e){return [];}}
 function saveHistory(a){try{const k=historyKey();if(!k)throw Error('Login required');localStorage.setItem(k,JSON.stringify(a));return true;}catch(e){toast('Repository history could not be saved');return false;}}
 function remember(d,r,analyzed){const name=d.repository?.full_name;if(!name)return;const a=readHistory();const old=a.find(x=>x.name===name);saveHistory([{name,url:'https://github.com/'+name,date:new Date().toISOString(),analyzed:analyzed||!!old?.analyzed},...a.filter(x=>x.name!==name)].slice(0,50));renderHistory();}
 function renderHistory(){const root=el('gh-history-list');root.replaceChildren();const a=readHistory();if(!a.length)root.append(node('p','No repository history yet.'));for(const x of a){const row=node('div',undefined,'gh-history-row');const info=node('div');info.append(node('strong',x.name),node('small',new Date(x.date).toLocaleString()+(x.analyzed?' · Analyzed':'')));const open=node('button','Reopen');open.type='button';open.onclick=()=>{if(working)return;el('gh-repo').value=x.url;load(!!x.analyzed);};const del=node('button','Delete');del.type='button';del.onclick=()=>{if(working)return;if(saveHistory(readHistory().filter(y=>y.name!==x.name)))renderHistory();};row.append(info,open,del);root.append(row);}}
 function resetRepo(){if(working)return;clear();el('gh-repo').value='';el('gh-query').value='';el('gh-mode').value='filename';status('Enter a repository URL to begin.');}
 el('gh-clear-repo').onclick=resetRepo;
 el('gh-clear-search').onclick=()=>{if(working)return;el('gh-query').value='';el('gh-mode').value='filename';if(activeRepo)files(originalFiles);else el('gh-files').replaceChildren();status(activeRepo?'Search cleared · Repository files restored':'Enter a repository URL to begin.');};
 el('gh-history-toggle').onclick=()=>{const p=el('gh-history-panel');p.hidden=!p.hidden;el('gh-history-toggle').setAttribute('aria-expanded',String(!p.hidden));if(!p.hidden)renderHistory();};
 el('gh-history-clear').onclick=()=>{if(!working&&confirm('Delete all saved repository history for this account?')){if(saveHistory([]))renderHistory();}};
 el('logout').addEventListener('click',()=>{el('gh-history-list').replaceChildren();el('gh-history-panel').hidden=true;el('gh-history-toggle').setAttribute('aria-expanded','false');});
 // GITHUB_AI_UI_V1
 function clearAI(){el('gh-ai-panel').hidden=true;el('gh-ai-status').textContent='';el('gh-ai-meta').textContent='';el('gh-ai-files').replaceChildren();el('gh-ai-details').hidden=true;el('gh-ai-report').replaceChildren();delete el('gh-ai-report').dataset.raw;el('gh-ai-copy').disabled=true;}
 el('gh-ai-clear').onclick=()=>{if(!working)clearAI();};
 el('gh-ai-copy').onclick=async()=>{const raw=el('gh-ai-report').dataset.raw;if(!raw)return;try{await navigator.clipboard.writeText(raw);toast('Report copied');}catch(e){toast('Unable to copy report');}};
 el('gh-repo').addEventListener('input',()=>{if(!working)clearAI();});
 el('gh-ai-analyze').onclick=()=>{if(working)return;let r;try{r=repo();if(!r)throw Error('Enter a repository URL first');}catch(e){status(e.message);return;}if(!confirm('Send selected public repository source excerpts to Gemini for AI analysis? This uses API tokens.'))return;run(async v=>{clearAI();el('gh-ai-panel').hidden=false;el('gh-ai-status').textContent='Analyzing source code with Gemini…';el('gh-ai-analyze').classList.add('gh-ai-loading');status('AI analysis in progress…');try{const d=await api('/api/github/ai-analyze',json('POST',{repository:r}));if(v!==epoch)return;const reviewed=d.files_reviewed||[];el('gh-ai-meta').textContent=d.repository+' · '+d.model+' · '+reviewed.length+'/'+d.total_files+' listed files · Input: '+(d.input_tokens??'Unknown')+' · Output: '+(d.output_tokens??'Unknown')+' · Thinking: '+(d.thinking_tokens??'Not reported')+(d.truncated?' · Partial listing':'');for(const f of reviewed)el('gh-ai-files').append(node('li',f.path+' · '+f.characters+' characters'+(f.partial?' · Partial excerpt':'')));el('gh-ai-details').hidden=false;renderMarkdown(el('gh-ai-report'),d.report);el('gh-ai-copy').disabled=false;el('gh-ai-status').textContent='Analysis complete';status('AI analysis complete');}catch(e){if(v===epoch){el('gh-ai-status').textContent=e.message;status(e.message);}}finally{el('gh-ai-analyze').classList.remove('gh-ai-loading');}});};
 // GITHUB_CHAT_UI_V1
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
 el('github-tab').onclick=()=>showPage('github');el('gh-open-form').onsubmit=e=>{e.preventDefault();load(false);};el('gh-analyze').onclick=()=>load(true);
 el('gh-search-form').onsubmit=e=>{e.preventDefault();run(async v=>{if(!activeRepo||repo()!==activeRepo)throw Error('Open the repository first');const d=await req('search',{repository:activeRepo,query:el('gh-query').value.trim(),mode:el('gh-mode').value});if(v!==epoch)return;files(d.results||[]);status(d.total_results+' matches'+(d.limited?' · Search limit reached':'')+(d.truncated?' · Partial repository':''));});};
 el('logout').addEventListener('click',()=>{epoch++;clear();el('gh-repo').value='';el('gh-query').value='';status('Enter a repository URL to begin.');});
 const go=()=>{if(busy){toast('Stop the current response first');return;}newChat().catch(e=>toast(e.message));};
 for(const n of document.querySelectorAll('.sidebar .brand, header .search-ai-brand-logo, header #page-title')){n.classList.add('gh-brand-link');n.tabIndex=0;n.setAttribute('role','button');n.title='Start a new chat';n.addEventListener('click',go);n.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();go();}});}
})();

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
   renderMarkdown(e('gh-arch-report'),String(d.report||'').replace(/```mermaid\s*\n[\s\S]*?```/gi,''));
   source=String(d.diagram||'');e('gh-arch-diagram').dataset.pdfSource=source;
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

// REPOSITORY_PDF_V1
(function(){
 const e=id=>document.getElementById(id);
 const button=e('gh-report-pdf');
 const text=id=>e(id)?.textContent.trim()||'';
 const key=s=>String(s||'').trim().replace(/^https:\/\/github\.com\//i,'').replace(/\/$/,'').replace(/\.git$/i,'').toLowerCase();
 const safe=s=>String(s??'').replace(/[\r\n|]/g,' ').replace(/[<>]/g,'');
 button.onclick=async()=>{
  const repository=e('gh-repo').value.trim(), k=key(repository), sections=[];
  if(!k){toast('Enter repository URL first');return;}
  const cards=[...e('gh-summary').querySelectorAll('.gh-stat')];
  if(cards.length && key(cards[0].querySelector('strong')?.textContent)===k){
   let s='## Repository overview\n\n| Metric | Value |\n|---|---|\n';
   for(const c of cards)s+='| '+safe(c.querySelector('small')?.textContent)+' | '+safe(c.querySelector('strong')?.textContent)+' |\n';
   const a=e('gh-analysis');
   if(a.textContent.trim()){
    s+='\n## File classification\n\n| Category | Percentage | Details |\n|---|---|---|\n';
    for(const c of a.querySelectorAll('.gh-stat')){const sm=c.querySelectorAll('small');s+='| '+safe(sm[0]?.textContent)+' | '+safe(c.querySelector('strong')?.textContent)+' | '+safe(sm[1]?.textContent)+' |\n';}
    for(const p of a.querySelectorAll('p, details'))s+='\n'+p.innerText+'\n';
   }
   sections.push(s);
  }
  if(!e('gh-ai-panel').hidden && key(text('gh-ai-meta').split(' · ')[0])===k && e('gh-ai-report').dataset.raw){sections.push('## AI repository analysis\n\n'+text('gh-ai-meta')+'\n\n'+e('gh-ai-report').dataset.raw+'\n\nReviewed files:\n'+text('gh-ai-files'));}
  if(!e('gh-architecture-panel').hidden && key(text('gh-arch-meta').split(' · ')[0])===k && e('gh-arch-report').dataset.raw){
   let s='## Project architecture\n\n'+text('gh-arch-meta')+'\n\n'+e('gh-arch-report').dataset.raw+'\n\nReviewed files:\n'+text('gh-arch-files');
   const diagram=e('gh-arch-diagram').dataset.pdfSource;
   if(diagram && !e('gh-arch-copy').disabled)s+='\n\n```mermaid\n'+diagram+'\n```\n';
   sections.push(s);
  }
  if(!sections.length){toast('Analyze this repository first');return;}
  button.disabled=true;
  try{const r=await fetch('/api/github/report.pdf',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:JSON.stringify({repository,sections})});if(!r.ok){const d=await r.json().catch(()=>({}));throw Error(d.error||'PDF export failed');}if(!r.headers.get('Content-Type')?.includes('application/pdf'))throw Error('PDF response expected');const url=URL.createObjectURL(await r.blob());const a=document.createElement('a');a.href=url;a.download='repository-report.pdf';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}catch(err){toast(err.message);}finally{button.disabled=false;}
 };
})();
