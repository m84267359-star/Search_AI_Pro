from pathlib import Path
import datetime, shutil, subprocess
root=Path.cwd()
paths=['github_tools/repository_pdf.py','github_tools/repository_routes.py','templates/index.html','static/app.js']
old={p:Path(p).read_text(encoding='utf-8') for p in paths}
if 'REPOSITORY_PDF_V1' in old[paths[3]]: raise SystemExit('Already installed')
module='''import json
from datetime import datetime, timezone
from pdf_export import generate_chat_pdf

def generate_repository_pdf(repository, sections):
    if not isinstance(sections, list) or not 1 <= len(sections) <= 3:
        raise ValueError('Generate repository analysis first')
    messages = []
    for section in sections:
        if not isinstance(section, str) or len(section) > 60000:
            raise ValueError('Invalid report section')
        messages.append({'role':'assistant','content':section,'sources':'[]'})
    messages.insert(0, {'role':'assistant','content':'Generated: '+datetime.now(timezone.utc).isoformat(timespec='seconds')+'\\n\\nUser-provided dashboard snapshot. File classifications are heuristic; AI findings require verification.','sources':'[]'})
    return generate_chat_pdf('Repository Report: '+repository, messages)
'''
route='''
# REPOSITORY_PDF_V1
@github_bp.post('/report.pdf')
@login_required
def repository_pdf():
    from flask import send_file
    from io import BytesIO
    from .github_client import parse_repository
    from .repository_pdf import generate_repository_pdf
    if os.getenv('GITHUB_ENABLED','true').lower() != 'true':
        return jsonify(error='GitHub integration is disabled'), 503
    if request.content_length is None or request.content_length > 250000:
        return jsonify(error='Invalid report size'), 413
    data = request.get_json(silent=True)
    try:
        if not isinstance(data, dict) or not isinstance(data.get('repository'), str):
            raise ValueError('Repository required')
        owner, repo = parse_repository(data['repository'])
        pdf = generate_repository_pdf(owner+'/'+repo, data.get('sections'))
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    return send_file(BytesIO(pdf), mimetype='application/pdf', as_attachment=True, download_name='repository-report.pdf')
'''
js=r'''
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
'''
html=old[paths[2]]
anchor='id="gh-architecture" type="button" class="primary">Architecture</button>'
if html.count(anchor)!=1: raise SystemExit('Architecture toolbar anchor not found')
html=html.replace(anchor,anchor+'<button id="gh-report-pdf" type="button">Download Report</button>')
app=old[paths[3]]
anchor="source=String(d.diagram||'');"
if app.count(anchor)!=1: raise SystemExit('Diagram source anchor not found')
app=app.replace(anchor,anchor+"e('gh-arch-diagram').dataset.pdfSource=source;")
new=dict(zip(paths,[module,old[paths[1]]+route,html,app+js]))
for p in paths[:2]:compile(new[p],p,'exec')
subprocess.run(['node','--check','-'],input=new[paths[3]],encoding='utf-8',check=True)
backup=Path('backups')/('before-repository-pdf-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
for p in paths:
 target=backup/p;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
try:
 for p in paths:Path(p).write_text(new[p],encoding='utf-8')
except Exception:
 for p in paths:shutil.copy2(backup/p,p)
 raise
print('SUCCESS: Repository PDF installed; syntax checked')
print('Backup:',backup)
