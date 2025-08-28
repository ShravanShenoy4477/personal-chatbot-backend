import os
import json
from typing import List, Dict, Any, Optional
import pandas as pd
from pathlib import Path
from sentence_transformers import SentenceTransformer
import numpy as np
from datetime import datetime
import hashlib
from qdrant_client import QdrantClient, models

# Conditional imports for backends
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    chromadb = None
    Settings = None

class KnowledgeBase:
    def __init__(self, persist_directory: str = "chroma_db"):
        self.persist_directory = persist_directory
        self.backend = os.getenv("VECTOR_BACKEND", "chroma").lower()
        self.qdrant_collection = os.getenv("QDRANT_COLLECTION", "personal_knowledge")

        if self.backend == "qdrant":
            self.client = self._get_qdrant_client()
            print(f"Knowledge base initialized with Qdrant collection: {self.qdrant_collection}")
        else:
            if not CHROMADB_AVAILABLE:
                raise RuntimeError("ChromaDB backend requested but chromadb is not installed. Set VECTOR_BACKEND=qdrant or install chromadb.")
            self.client = chromadb.PersistentClient(path=persist_directory)
            print(f"Knowledge base initialized at: {persist_directory}")

        # Document tracking system (still local for now)
        self.tracking_file = "document_tracking.json"
        self.parsed_documents = self._load_tracking_index()

        # Initialize embedding model
        self.embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2', device='cpu')

        if self.backend == "chroma":
            if not CHROMADB_AVAILABLE:
                raise RuntimeError("ChromaDB backend requested but chromadb is not installed. Set VECTOR_BACKEND=qdrant or install chromadb.")
            # Get or create collection for Chroma
            self.collection = self.client.get_or_create_collection(
                name="personal_knowledge",
                metadata={"hnsw:space": "cosine"}
            )
        elif self.backend == "qdrant":
            # Ensure Qdrant collection exists or create it
            try:
                self.client.get_collection(collection_name=self.qdrant_collection)
                print(f"Qdrant collection '{self.qdrant_collection}' already exists.")
            except Exception:
                print(f"Qdrant collection '{self.qdrant_collection}' not found, creating...")
                self.client.recreate_collection(
                    collection_name=self.qdrant_collection,
                    vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE),
                )
                print(f"Qdrant collection '{self.qdrant_collection}' created.")

    def _get_qdrant_client(self):
        """Get Qdrant client with environment variables"""
        url = os.getenv("QDRANT_URL")
        api_key = os.getenv("QDRANT_API_KEY")
        
        if not url:
            raise ValueError("QDRANT_URL environment variable not set")
        
        if api_key:
            return QdrantClient(url=url, api_key=api_key)
        else:
            return QdrantClient(url=url)

    def _encode_text(self, texts: List[str]) -> List[List[float]]:
        """Encode text to embeddings using sentence-transformers"""
        return self.embedding_model.encode(texts).tolist()
    
    def _load_tracking_index(self) -> Dict[str, Any]:
        """Load the document tracking index from disk"""
        if os.path.exists(self.tracking_file):
            try:
                with open(self.tracking_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                print("⚠️  Warning: Could not load tracking index, starting fresh")
                return {}
        return {}
    
    def _save_tracking_index(self):
        """Save the document tracking index to disk"""
        try:
            with open(self.tracking_file, 'w') as f:
                json.dump(self.parsed_documents, f, indent=2)
        except Exception as e:
            print(f"⚠️  Warning: Could not save tracking index: {e}")
    
    def _get_document_hash(self, file_path: str) -> str:
        """Generate a unique hash for a document based on path and modification time"""
        stat = os.stat(file_path)
        content = f"{file_path}_{stat.st_mtime}_{stat.st_size}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def is_document_parsed(self, file_path: str) -> bool:
        """Check if a document has already been parsed and added to the knowledge base"""
        doc_hash = self._get_document_hash(file_path)
        return doc_hash in self.parsed_documents
    
    def mark_document_parsed(self, file_path: str, chunks_count: int, processing_time: float):
        """Mark a document as successfully parsed and track metadata"""
        doc_hash = self._get_document_hash(file_path)
        self.parsed_documents[doc_hash] = {
            'file_path': file_path,
            'file_name': os.path.basename(file_path),
            'chunks_count': chunks_count,
            'processing_time': processing_time,
            'parsed_at': datetime.now().isoformat(),
            'status': 'completed'
        }
        self._save_tracking_index()
        print(f"✅ Document tracked: {os.path.basename(file_path)} ({chunks_count} chunks)")
    
    def mark_document_failed(self, file_path: str, error: str):
        """Mark a document as failed to parse"""
        doc_hash = self._get_document_hash(file_path)
        self.parsed_documents[doc_hash] = {
            'file_path': file_path,
            'file_name': os.path.basename(file_path),
            'error': error,
            'failed_at': datetime.now().isoformat(),
            'status': 'failed'
        }
        self._save_tracking_index()
        print(f"❌ Document marked as failed: {os.path.basename(file_path)}")
    
    def get_parsed_documents_summary(self) -> Dict[str, Any]:
        """Get a summary of all parsed documents"""
        summary = {
            'total_documents': len(self.parsed_documents),
            'completed': 0,
            'failed': 0,
            'total_chunks': 0,
            'total_processing_time': 0.0,
            'documents': []
        }
        
        for doc_hash, doc_info in self.parsed_documents.items():
            if doc_info.get('status') == 'completed':
                summary['completed'] += 1
                summary['total_chunks'] += doc_info.get('chunks_count', 0)
                summary['total_processing_time'] += doc_info.get('processing_time', 0.0)
            elif doc_info.get('status') == 'failed':
                summary['failed'] += 1
            
            summary['documents'].append({
                'file_name': doc_info.get('file_name', 'Unknown'),
                'status': doc_info.get('status', 'Unknown'),
                'chunks_count': doc_info.get('chunks_count', 0),
                'parsed_at': doc_info.get('parsed_at', doc_info.get('failed_at', 'Unknown'))
            })
        
        return summary

    def _clean_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Clean metadata to ensure ChromaDB compatibility"""
        cleaned = {}
        for key, value in metadata.items():
            if value is None:
                cleaned[key] = "N/A"
            elif isinstance(value, list):
                if len(value) == 0:
                    cleaned[key] = "N/A"
                else:
                    # Convert list to string representation
                    cleaned[key] = str(value)
            elif isinstance(value, (str, int, float, bool)):
                cleaned[key] = value
            else:
                # Convert any other type to string
                cleaned[key] = str(value)
            
            # Debug: Check if any problematic values remain
            if isinstance(cleaned[key], list):
                print(f"Warning: Metadata field '{key}' still contains list: {cleaned[key]}")
                cleaned[key] = str(cleaned[key])
        
        return cleaned

    def add_documents(self, chunks: List[Dict[str, Any]], batch_size: int = 100, source_file: str = None):
        """Add document chunks to the knowledge base"""
        if not chunks:
            print("No chunks to add")
            return False
        
        print(f"Adding {len(chunks)} chunks to knowledge base...")
        
        # Generate unique IDs based on source file and timestamp
        import time
        timestamp = int(time.time() * 1000)  # milliseconds
        base_id = timestamp
        
        # Process in batches
        for batch_idx in range(0, len(chunks), batch_size):
            batch = chunks[batch_idx:batch_idx + batch_size]
            
            # Prepare batch data with unique IDs
            if self.backend == "qdrant":
                # Qdrant needs integer IDs
                ids = [base_id + i for i in range(len(batch))]
            else:
                # Chroma can use string IDs
                ids = [f"{base_id}_chunk_{batch_idx + j}" for j in range(len(batch))]
            
            documents = [chunk['content'] for chunk in batch]
            metadatas = [self._clean_metadata(chunk['metadata']) for chunk in batch]
            
            # Final validation - ensure no lists remain
            for i, metadata in enumerate(metadatas):
                for key, value in metadata.items():
                    if isinstance(value, list):
                        print(f"Error: Batch {batch_idx}, field '{key}' still contains list: {value}")
                        metadatas[i][key] = str(value)
            
            # Generate embeddings
            embeddings = self._encode_text(documents)
            
            if self.backend == "qdrant":
                # Upsert into Qdrant
                points = []
                for i in range(len(documents)):
                    points.append(
                        models.PointStruct(
                            id=ids[i],
                            vector=embeddings[i],
                            payload={
                                "content": documents[i],
                                **metadatas[i],
                            },
                        )
                    )
                self.client.upsert(collection_name=self.qdrant_collection, points=points)
            else:
                # Add to Chroma collection
                self.collection.add(
                    ids=ids,
                    documents=documents,
                    metadatas=metadatas,
                    embeddings=embeddings
                )
            
            print(f"Added batch {batch_idx//batch_size + 1}/{(len(chunks) + batch_size - 1)//batch_size}")
        
        print("All chunks added successfully!")
        
        # Track document if source_file is provided
        if source_file:
            processing_time = 0.1  # Small default time since we can't measure it accurately here
            self.mark_document_parsed(source_file, len(chunks), processing_time)
        
        return True
    
    def search(self, query: str, n_results: int = 5, filter_metadata: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Search the knowledge base for relevant information"""
        try:
            # Generate query embedding
            query_embedding = self._encode_text([query])[0]
            
            if self.backend == "qdrant":
                # Build filter
                q_filter = None
                if filter_metadata:
                    must = []
                    for k, v in filter_metadata.items():
                        must.append(models.FieldCondition(key=k, match=models.MatchValue(value=v)))
                    q_filter = models.Filter(must=must)

                search_result = self.client.search(
                    collection_name=self.qdrant_collection,
                    query_vector=query_embedding,
                    limit=n_results,
                    with_payload=True,
                    with_vectors=False,
                    query_filter=q_filter,
                )
                formatted_results = []
                for pt in search_result:
                    payload = pt.payload or {}
                    content = payload.pop("content", "")
                    formatted_results.append({
                        "content": content,
                        "metadata": payload,
                        "distance": float(pt.score),
                    })
                return formatted_results
            else:
                # Perform search in Chroma
                results = self.collection.query(
                    query_embeddings=query_embedding,
                    n_results=n_results,
                    where=filter_metadata
                )
                
                # Format results - ChromaDB returns nested lists
                formatted_results = []
                
                if results and 'documents' in results:
                    documents = results['documents']
                    metadatas = results.get('metadatas', [])
                    distances = results.get('distances', [])
                    
                    # ChromaDB returns: documents[0] = list of actual documents
                    if isinstance(documents, list) and len(documents) > 0 and isinstance(documents[0], list):
                        doc_list = documents[0]
                        meta_list = metadatas[0] if metadatas and len(metadatas) > 0 else []
                        dist_list = distances[0] if distances and len(distances) > 0 else []
                        
                        for i in range(len(doc_list)):
                            result = {
                                'content': doc_list[i],
                                'metadata': meta_list[i] if i < len(meta_list) else {},
                                'distance': dist_list[i] if i < len(dist_list) else 0.0
                            }
                            formatted_results.append(result)
                
                return formatted_results
            
        except Exception as e:
            print(f"❌ Search error: {e}")
            return []
    
    def get_all_documents(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retrieve all documents from the knowledge base"""
        try:
            if self.backend == "qdrant":
                scroll = self.client.scroll(
                    collection_name=self.qdrant_collection,
                    with_payload=True,
                    with_vectors=False,
                    limit=limit or 1000,
                )
                points = scroll[0]
                formatted_results = []
                for pt in points:
                    payload = pt.payload or {}
                    content = payload.pop("content", "")
                    formatted_results.append({
                        'content': content,
                        'metadata': payload,
                        'id': str(pt.id),
                    })
                return formatted_results
            results = self.collection.get()
            
            formatted_results = []
            if results and 'documents' in results:
                documents = results.get('documents', [])
                metadatas = results.get('metadatas', [])
                ids = results.get('ids', [])
                
                for i in range(len(documents)):
                    result = {
                        'content': documents[i],
                        'metadata': metadatas[i] if i < len(metadatas) else {},
                        'id': ids[i] if i < len(ids) else f"unknown_{i}"
                    }
                    formatted_results.append(result)
            
            if limit:
                formatted_results = formatted_results[:limit]
            
            return formatted_results
            
        except Exception as e:
            print(f"❌ Error getting all documents: {e}")
            return []
    
    def update_document(self, doc_id: str, new_content: str, new_metadata: Optional[Dict] = None):
        """Update an existing document"""
        # Generate new embedding
        new_embedding = self._encode_text([new_content])[0]
        
        # Update metadata if provided
        if new_metadata:
            self.collection.update(
                ids=[doc_id],
                documents=[new_content],
                metadatas=[new_metadata],
                embeddings=new_embedding
            )
        else:
            self.collection.update(
                ids=[doc_id],
                documents=[new_content],
                embeddings=new_embedding
            )
        
        print(f"Updated document: {doc_id}")
    
    def delete_document(self, doc_id: str):
        """Delete a document from the knowledge base"""
        if self.backend == "qdrant":
            self.client.delete(collection_name=self.qdrant_collection, points_selector=models.PointIdsList(points=[doc_id]))
            print(f"Deleted document: {doc_id}")
            return
        self.collection.delete(ids=[doc_id])
        print(f"Deleted document: {doc_id}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the knowledge base"""
        if self.backend == "qdrant":
            count = self.client.count(self.qdrant_collection).count
            # For tokens and metadata distributions, do a limited scroll (approximate)
            docs = self.get_all_documents(limit=1000)
            stats = {
                'total_documents': count,
                'total_tokens': sum(len(doc['content'].split()) for doc in docs),
                'file_types': {},
                'sources': set(),
            }
            for r in docs:
                meta = r.get('metadata', {})
                file_type = meta.get('file_type', 'unknown')
                stats['file_types'][file_type] = stats['file_types'].get(file_type, 0) + 1
                stats['sources'].add(meta.get('source', 'unknown'))
            stats['sources'] = list(stats['sources'])
            stats['unique_files'] = len(stats['sources'])
            return stats
        results = self.collection.get()
        
        stats = {
            'total_documents': len(results['documents']),
            'total_tokens': sum(
                len(doc.split()) for doc in results['documents']
            ),
            'file_types': {},
            'sources': set()
        }
        
        for metadata in results['metadatas']:
            # Count file types
            file_type = metadata.get('file_type', 'unknown')
            stats['file_types'][file_type] = stats['file_types'].get(file_type, 0) + 1
            
            # Collect sources
            source = metadata.get('source', 'unknown')
            stats['sources'].add(source)
        
        stats['sources'] = list(stats['sources'])
        stats['unique_files'] = len(stats['sources'])
        
        return stats
    
    def export_to_json(self, output_file: str = None):
        """Export the entire knowledge base to JSON"""
        output_file = output_file or f"knowledge_base_export_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        results = self.collection.get()
        
        export_data = {
            'export_date': pd.Timestamp.now().isoformat(),
            'total_documents': len(results['documents']),
            'documents': []
        }
        
        for i in range(len(results['documents'])):
            doc_data = {
                'id': results['ids'][i],
                'content': results['documents'][i],
                'metadata': results['metadatas'][i]
            }
            export_data['documents'].append(doc_data)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        print(f"Knowledge base exported to: {output_file}")
        return output_file
    
    def clear_all(self):
        """Clear all documents from the knowledge base"""
        self.collection.delete(where={})
        print("Knowledge base cleared")
    
    def backup(self, backup_dir: str = "./backups"):
        """Create a backup of the knowledge base"""
        backup_path = Path(backup_dir)
        backup_path.mkdir(exist_ok=True)
        
        backup_file = backup_path / f"knowledge_base_backup_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        self.export_to_json(str(backup_file))
        print(f"Backup created at: {backup_file}")
        
        return str(backup_file)
