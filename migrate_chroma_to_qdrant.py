#!/usr/bin/env python3
"""
Migrate existing local ChromaDB data (./chroma_db, collection 'personal_knowledge')
into Qdrant using current environment variables for Qdrant connection.

Usage:
  1) Ensure .env has VECTOR_BACKEND=qdrant, QDRANT_URL, QDRANT_API_KEY, QDRANT_COLLECTION
  2) pip install -r requirements.txt
  3) python migrate_chroma_to_qdrant.py
"""

import os
from typing import List, Dict, Any
from dotenv import load_dotenv

# Local Chroma read
import chromadb

# Our abstractions
from knowledge_base import KnowledgeBase


def read_chroma_documents(chroma_path: str = "chroma_db", collection_name: str = "personal_knowledge") -> List[Dict[str, Any]]:
    client = chromadb.PersistentClient(path=chroma_path)
    try:
        coll = client.get_collection(collection_name)
    except Exception:
        print(f"No existing Chroma collection '{collection_name}' at {chroma_path}.")
        return []

    data = coll.get()
    docs = data.get("documents", [])
    metas = data.get("metadatas", [])
    ids = data.get("ids", [])

    chunks: List[Dict[str, Any]] = []
    for i, content in enumerate(docs):
        meta = metas[i] if i < len(metas) else {}
        chunks.append({
            "content": content,
            "metadata": meta,
            "id": ids[i] if i < len(ids) else f"doc_{i}"
        })
    print(f"Read {len(chunks)} documents from local Chroma.")
    return chunks


def migrate_to_qdrant(chunks: List[Dict[str, Any]]):
    if not chunks:
        print("Nothing to migrate.")
        return

    # Ensure we target Qdrant
    os.environ.setdefault("VECTOR_BACKEND", "qdrant")

    kb = KnowledgeBase()
    
    # Process in smaller batches to avoid memory issues
    batch_size = 50
    total_batches = (len(chunks) + batch_size - 1) // batch_size
    
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        batch_num = i // batch_size + 1
        print(f"Processing batch {batch_num}/{total_batches} ({len(batch)} documents)")
        
        try:
            kb.add_documents(batch, batch_size=batch_size, source_file=f"migration_batch_{batch_num}")
            print(f"✅ Batch {batch_num} completed")
        except Exception as e:
            print(f"❌ Batch {batch_num} failed: {e}")
            # Continue with next batch
    
    print("Migration completed.")


if __name__ == "__main__":
    load_dotenv()
    chunks = read_chroma_documents()
    migrate_to_qdrant(chunks)
