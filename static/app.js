const $=id=>document.getElementById(id);const csrf=document.querySelector('meta[name="csrf-token"]').content;
let chatId=null,registerMode=false,busy=false,settings=null,docs=[];
function toast(msg){$('toast').textContent=msg;$('toast').style.display='block';setTimeout(()=>$('toast').style.display='none',3500)}
async function api(url,opts={}){const r=await fetch(url,{credentials:'same-origin',...opts,headers:{'X-CSRF-Token':csrf,...(opts.body instanceof FormData?{}:{'Content-Type':'application/json'}),...(opts.headers||{})}});let d=await r.json().catch(()=>({error:'Unexpected response'}));if(!r.ok)throw Error(d.error||'Request failed');return d}
const json=(method,body)=>({method,body:JSON.stringify(body)});
function showPage(name){for(const p of ['chat','documents','usage','settings','admin'])$(p+'-page').hidden=p!==name;$('page-title').textContent=({chat:'AI Search',documents:'Document intelligence',usage:'Usage dashboard',settings:'Settings',admin:'Admin dashboard'})[name];document.querySelector('.sidebar').classList.remove('open')}
async function init(){const me=await api('/api/me');$('auth').hidden=me.authenticated;$('workspace').hidden=!me.authenticated;if(!me.authenticated)return;$('user-email').textContent=me.email;$('admin-tab').hidden=!me.admin;settings=await api('/api/settings');$('model').innerHTML=settings.models.map(m=>`<option value="${m}">${m}</option>`).join('');$('model').value=settings.model;$('theme').value=settings.theme;$('instructions').value=settings.instructions;applyTheme(settings.theme);await Promise.all([refreshChats(),refreshDocs()]);showPage('chat')}
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

async function send(){if(busy)return;const text=$('prompt').value.trim();if(!text)return;busy=true;
generationController = new AbortController();
setGenerating(true);try{if(!chatId)await newChat();if($('messages').querySelector('.empty'))$('messages').replaceChildren();addMessage('user',text);$('prompt').value='';const out=addMessage('assistant','');let raw='',done=false;const r=await fetch('/api/chats/'+chatId+'/stream',{signal:generationController.signal,method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:JSON.stringify({message:text,web_search:$('web-search').checked,document_id:$('document-select').value||null})});if(!r.ok){const d=await r.json();throw Error(d.error||'Request failed')}const reader=r.body.getReader();const decoder=new TextDecoder();while(true){const {value,done:ended}=await reader.read();raw+=decoder.decode(value||new Uint8Array(),{stream:!ended});const cut=raw.lastIndexOf('\n\n');if(cut>=0){const completed=raw.slice(0,cut+2);raw=raw.slice(cut+2);parseSSE(completed,(event,d)=>{if(event==='delta'){renderMarkdown(out.content,(out.content.dataset.raw||'')+d.text);$('messages').scrollTop=$('messages').scrollHeight}if(event==='error'){renderMarkdown(out.content,(out.content.dataset.raw||'')+'\n\nError: '+d.error);toast(d.error)}if(event==='done'){done=true;const links=document.createElement('div');links.className='sources';for(const s of d.sources||[]){if(!/^https?:\/\//.test(s.url))continue;const a=document.createElement('a');a.href=s.url;a.target='_blank';a.rel='noopener noreferrer';a.textContent=s.title||s.url;links.append(a)}out.div.append(links)}})}if(ended)break}if(!done)toast('Stream ended before completion');await refreshChats()}catch(e){
    if(e.name === 'AbortError'){
        toast('Generation stopped');
    }else{
        toast(e.message);
    }
}finally{
    busy=false;
    generationController=null;
    setGenerating(false);
}}
$('send').onclick=()=>{
    if(busy){
        stopGeneration();
    }else{
        send();
    }
};$('prompt').onkeydown=e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send()}};
document.querySelectorAll('[data-prompt]').forEach(b=>b.onclick=()=>{$('prompt').value=b.dataset.prompt;send()});
async function refreshDocs(){docs=await api('/api/documents');const sel=$('document-select');const selected=sel.value;sel.replaceChildren(new Option('No document selected',''));const list=$('document-list');list.replaceChildren();for(const d of docs){sel.add(new Option(d.name,d.id));const row=document.createElement('div');row.className='doc-row';const title=document.createElement('span');title.textContent='📄 '+d.name+' ('+d.chars+' characters)';const del=document.createElement('button');del.textContent='Delete';del.onclick=async()=>{if(!confirm('Delete document?'))return;await api('/api/documents/'+d.id,{method:'DELETE'});refreshDocs()};row.append(title,del);list.append(row)}sel.value=selected;if(!sel.value)sel.value=''}
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
