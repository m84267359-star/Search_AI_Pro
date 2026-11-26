from pathlib import Path
from datetime import datetime
import ast
import shutil

p = Path('app.py')
s = p.read_text(encoding='utf-8-sig')
if '# RAG_INTEGRATION_V1' in s:
    raise SystemExit('RAG integration already installed')
if not Path('rag_engine.py').exists():
    raise SystemExit('rag_engine.py is missing')

def replace(old, new):
    global s
    if s.count(old) != 1:
        raise SystemExit('Expected exactly one matching anchor: ' + old[:100])
    s = s.replace(old, new, 1)

helper = '''# RAG_INTEGRATION_V1
def rag_enabled():
    return os.getenv('RAG_ENABLED', 'true').lower() == 'true'


def rag_reference(doc, question):
    fallback = doc['extracted_text'][:30000]
    if not rag_enabled():
        return fallback
    try:
        import rag_engine as rag
        import hashlib
        uid, did = int(doc['user_id']), int(doc['id'])
        fingerprint = hashlib.sha256(doc['extracted_text'].encode('utf-8')).hexdigest()
        collection = rag.get_collection(uid)
        existing = collection.get(where={'document_id': did}, include=['metadatas'])
        if not existing['ids'] or any(m.get('fingerprint') != fingerprint for m in existing['metadatas']):
            rag.index_document(uid, did, doc['name'], doc['extracted_text'])
            existing = collection.get(where={'document_id': did}, include=['metadatas'])
            collection.update(ids=existing['ids'], metadatas=[{**m, 'fingerprint': fingerprint} for m in existing['metadatas']])
        hits = rag.search_documents(uid, question, did)
        budget = max(100, min(1500, int(os.getenv('RAG_MAX_CONTEXT_TOKENS', '1500'))))
        tokenizer = rag.get_model().tokenizer
        blocks = []
        for hit in hits:
            meta = hit['metadata']
            block = f"[Document: {doc['name']}; chunk {meta['chunk']}]\\n{hit['text']}"
            tokens = tokenizer.encode(block, add_special_tokens=False)
            if len(tokens) > budget:
                break
            blocks.append(block)
            budget -= len(tokens)
        if blocks:
            print('RAG retrieval successful:', len(blocks), 'chunks')
            return '\\n\\n'.join(blocks) + '\\n\\nCite relevant document and chunk labels. If evidence is insufficient, say so.'
    except Exception:
        app.logger.exception('RAG retrieval failed; using original document context')
    return fallback


'''
replace("@app.post('/api/documents')", helper + "@app.post('/api/documents')")
replace("    return jsonify(id=cur.lastrowid, name=name, chars=len(text)), 201", '''    if rag_enabled():
        try:
            import rag_engine as rag
            import hashlib
            uid, did = int(current_user.id), int(cur.lastrowid)
            count = rag.index_document(uid, did, name, text)
            collection = rag.get_collection(uid)
            existing = collection.get(where={'document_id': did}, include=['metadatas'])
            fingerprint = hashlib.sha256(text.encode('utf-8')).hexdigest()
            collection.update(ids=existing['ids'], metadatas=[{**m, 'fingerprint': fingerprint} for m in existing['metadatas']])
            print('RAG indexed:', count, 'chunks')
        except Exception:
            app.logger.exception('RAG indexing failed; document remains available')
    return jsonify(id=cur.lastrowid, name=name, chars=len(text)), 201''')
replace("    db().execute('DELETE FROM documents WHERE id=?', (doc_id,))", '''    try:
        import rag_engine as rag
        rag.delete_document(int(current_user.id), doc_id)
    except Exception:
        app.logger.exception('RAG deletion failed')
        return fail('Could not remove document index. Please retry.', 503)
    db().execute('DELETE FROM documents WHERE id=?', (doc_id,))''')
replace("+ doc['extracted_text'][:30000]", "+ rag_reference(doc, prompt)")
ast.parse(s)
compile(s, str(p), 'exec')
backup = Path('backups') / ('before-rag-integration-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
backup.mkdir(parents=True, exist_ok=True)
shutil.copy2(p, backup / p.name)
p.write_text(s, encoding='utf-8')
print('SUCCESS: RAG integration installed')
print('SUCCESS: Python syntax verified')
print('Backup:', backup)
