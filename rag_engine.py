import os
from pathlib import Path
from functools import lru_cache

import chromadb
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

MODEL_NAME = os.getenv(
    "RAG_EMBEDDING_MODEL", "all-MiniLM-L6-v2"
)

CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "200"))
OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "40"))
TOP_K = int(os.getenv("RAG_TOP_K", "5"))

DB_PATH = ROOT / os.getenv("RAG_DB_PATH", "vector_db")


@lru_cache(maxsize=1)
def get_model():
    return SentenceTransformer(MODEL_NAME)


@lru_cache(maxsize=1)
def get_client():
    return chromadb.PersistentClient(path=str(DB_PATH))


def get_collection(user_id):
    return get_client().get_or_create_collection(
        name=f"user_{int(user_id)}_documents",
        embedding_function=None
    )


def chunk_text(text):
    tokenizer = get_model().tokenizer

    tokens = tokenizer.encode(
        text, add_special_tokens=False
    )

    if not 0 <= OVERLAP < CHUNK_SIZE <= 254:
        raise ValueError("Invalid chunk configuration")

    chunks = []
    step = CHUNK_SIZE - OVERLAP

    for start in range(0, len(tokens), step):
        part = tokens[start:start + CHUNK_SIZE]

        chunk = tokenizer.decode(
            part, skip_special_tokens=True
        ).strip()

        if chunk:
            chunks.append(chunk)

        if start + CHUNK_SIZE >= len(tokens):
            break

    return chunks


def index_document(user_id, document_id, name, text):
    chunks = chunk_text(text)

    if not chunks:
        raise ValueError("Document has no readable text")

    embeddings = get_model().encode(
        chunks, normalize_embeddings=True
    ).tolist()

    collection = get_collection(user_id)

    collection.delete(
        where={"document_id": int(document_id)}
    )

    collection.upsert(
        ids=[
            f"{document_id}_{i}"
            for i in range(len(chunks))
        ],
        documents=chunks,
        embeddings=embeddings,
        metadatas=[
            {
                "document_id": int(document_id),
                "name": name,
                "chunk": i + 1
            }
            for i in range(len(chunks))
        ]
    )

    return len(chunks)


def search_documents(user_id, query, document_id=None):
    collection = get_collection(user_id)

    if collection.count() == 0:
        return []

    embedding = get_model().encode(
        query, normalize_embeddings=True
    ).tolist()

    options = {
        "query_embeddings": [embedding],
        "n_results": min(TOP_K, collection.count()),
        "include": [
            "documents", "metadatas", "distances"
        ]
    }

    if document_id is not None:
        options["where"] = {
            "document_id": int(document_id)
        }

    results = collection.query(**options)

    return [
        {
            "text": text,
            "metadata": metadata,
            "distance": distance
        }
        for text, metadata, distance in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        )
    ]


def delete_document(user_id, document_id):
    get_collection(user_id).delete(
        where={"document_id": int(document_id)}
    )
