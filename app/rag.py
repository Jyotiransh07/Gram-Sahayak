"""Grounded PDF/text retrieval. SQLite FTS5 works immediately; optional Chroma hybrid index."""
import json
import re
from pathlib import Path
from . import config, db


def split_text(text, max_chars=850, overlap=120):
    text = re.sub(r'[ \t]+', ' ', text.replace('\r', ''))
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    if not text:
        return []
    out, start = [], 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        if end < len(text):
            last_space = text.rfind(' ', max(start + max_chars // 2, start), end)
            if last_space > start:
                end = last_space
        out.append(text[start:end].strip())
        if end == len(text):
            break
        start = max(start + 1, end - overlap)
    return [x for x in out if x]


def get_source_map():
    path = config.DOCUMENTS / 'sources.json'
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding='utf-8'))


def ingest(replace=True, use_vectors=False):
    """Ingest PDF, text and markdown; source URLs must be supplied in sources.json."""
    try:
        import pymupdf
    except ImportError as exc:
        raise RuntimeError('Install PyMuPDF from requirements.txt to ingest PDF documents.') from exc
    sources = get_source_map()
    inputs = [p for p in config.DOCUMENTS.rglob('*') if p.suffix.lower() in ('.pdf', '.txt', '.md')]
    docs = []
    for path in inputs:
        pages = []
        if path.suffix.lower() == '.pdf':
            with pymupdf.open(path) as pdf:
                pages = [(i + 1, p.get_text()) for i, p in enumerate(pdf)]
        else:
            pages = [(1, path.read_text(encoding='utf-8', errors='ignore'))]
        mapped = sources.get(path.name, {})
        for page, content in pages:
            for chunk in split_text(content):
                docs.append({'body': chunk, 'source': path.name, 'page': page,
                             'source_url': mapped.get('url', '')})
    with db.connect() as conn:
        if replace:
            conn.execute('DELETE FROM docs_fts')
        conn.executemany('INSERT INTO docs_fts(body, source, page, source_url) VALUES(?, ?, ?, ?)',
                         [(v['body'], v['source'], v['page'], v['source_url']) for v in docs])
    vector_status = 'not installed / disabled'
    if use_vectors and docs:
        try:
            import chromadb
            from sentence_transformers import SentenceTransformer
            import hashlib
            model = SentenceTransformer(config.RAG_MODEL)
            chroma = chromadb.PersistentClient(path=str(config.DATA / 'chroma'))
            try:
                chroma.delete_collection('farm_documents')
            except Exception:
                pass
            collection = chroma.get_or_create_collection('farm_documents')
            for offset in range(0, len(docs), 32):
                batch = docs[offset:offset+32]
                vectors = model.encode(['passage: ' + d['body'] for d in batch], normalize_embeddings=True).tolist()
                ids = [hashlib.sha256((d['source'] + str(d['page']) + d['body']).encode()).hexdigest() for d in batch]
                collection.upsert(ids=ids, embeddings=vectors,
                                  documents=[d['body'] for d in batch],
                                  metadatas=[{'source': d['source'], 'page': int(d['page']), 'source_url': d['source_url']} for d in batch])
            vector_status = f'{len(docs)} vectorized chunks'
        except ImportError:
            vector_status = 'install requirements-rag.txt first'
    return {'files': len(inputs), 'chunks': len(docs), 'semantic_index': vector_status}


def search(query: str, k=5):
    words = re.findall(r'\w+', query, flags=re.UNICODE)[:12]
    outputs = []
    if words:
        fts_query = ' OR '.join(f'"{w}"' for w in words if w)
        try:
            with db.connect() as conn:
                rows = conn.execute('SELECT body, source, page, source_url FROM docs_fts WHERE docs_fts MATCH ? ORDER BY rank LIMIT ?',
                                    (fts_query, k)).fetchall()
            outputs = [dict(row) for row in rows]
        except Exception:
            outputs = []
    # Optional hybrid semantic retrieval, only if semantic index exists and dependencies installed.
    try:
        chroma_path = config.DATA / 'chroma'
        if chroma_path.exists():
            import chromadb
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer(config.RAG_MODEL)
            client = chromadb.PersistentClient(path=str(chroma_path))
            coll = client.get_collection('farm_documents')
            vector = model.encode(['query: ' + query], normalize_embeddings=True).tolist()
            fetched = coll.query(query_embeddings=vector, n_results=k)
            for body, meta in zip(fetched.get('documents', [[]])[0], fetched.get('metadatas', [[]])[0]):
                item = {'body': body, 'source': meta['source'], 'page': meta['page'], 'source_url': meta.get('source_url', '')}
                if not any(item['body'] == row['body'] for row in outputs):
                    outputs.append(item)
    except (ImportError, ValueError, KeyError, RuntimeError):
        pass
    return outputs[:k]


def knowledge_evidence(query, k=5):
    from .tools import evidence
    found = search(query, k)
    return [evidence(row['body'], row['source_url'] or f'local document: {row["source"]}',
                     f'{row["source"]} (page {row["page"]})') for row in found]
