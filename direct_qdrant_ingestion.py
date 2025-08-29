#!/usr/bin/env python3
"""
Direct Qdrant Ingestion Script
Use this to add new documents directly to Qdrant Cloud
"""

import os
import json
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient, models
from pathlib import Path
import hashlib

# Load environment variables
load_dotenv()

class DirectQdrantIngestion:
    def __init__(self):
        """Initialize direct Qdrant ingestion"""
        self.client = QdrantClient(
            url=os.getenv("QDRANT_URL"),
            api_key=os.getenv("QDRANT_API_KEY")
        )
        self.collection_name = os.getenv("QDRANT_COLLECTION")
        self.embedding_model = SentenceTransformer('sentence-transformers/paraphrase-MiniLM-L3-v2', device='cpu')
        
        # Ensure collection exists
        self._ensure_collection()
    
    def _ensure_collection(self):
        """Ensure Qdrant collection exists"""
        try:
            self.client.get_collection(collection_name=self.collection_name)
            print(f"✅ Collection '{self.collection_name}' exists")
        except Exception:
            print(f"🔄 Creating collection '{self.collection_name}'...")
            self.client.recreate_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE),
            )
            print(f"✅ Collection '{self.collection_name}' created")
    
    def add_single_document(self, content: str, metadata: dict = None):
        """Add a single document directly to Qdrant"""
        try:
            # Generate embedding
            embedding = self.embedding_model.encode(content).tolist()
            
            # Generate unique ID
            doc_id = int(hashlib.md5(content.encode()).hexdigest()[:16], 16)
            
            # Prepare payload
            payload = {
                'content': content,
                'processed_at': metadata.get('processed_at', '2024-01-01T00:00:00'),
                'source': metadata.get('source', 'direct_ingestion'),
                'document_type': metadata.get('document_type', 'text'),
                **(metadata or {})
            }
            
            # Add to Qdrant
            self.client.upsert(
                collection_name=self.collection_name,
                points=[models.PointStruct(
                    id=doc_id,
                    vector=embedding,
                    payload=payload
                )]
            )
            
            print(f"✅ Document added with ID: {doc_id}")
            return doc_id
            
        except Exception as e:
            print(f"❌ Error adding document: {e}")
            return None
    
    def add_documents_from_folder(self, folder_path: str):
        """Add all documents from a folder"""
        folder = Path(folder_path)
        if not folder.exists():
            print(f"❌ Folder not found: {folder_path}")
            return
        
        # Process different file types
        supported_extensions = {'.txt', '.md', '.pdf', '.docx', '.json'}
        
        for file_path in folder.rglob('*'):
            if file_path.suffix.lower() in supported_extensions:
                print(f"📄 Processing: {file_path.name}")
                
                try:
                    # Read file content
                    if file_path.suffix.lower() == '.json':
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            content = json.dumps(data, indent=2)
                    else:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                    
                    # Prepare metadata
                    metadata = {
                        'filename': file_path.name,
                        'source': str(file_path),
                        'document_type': file_path.suffix.lower()[1:],
                        'processed_at': '2024-01-01T00:00:00'
                    }
                    
                    # Add to Qdrant
                    self.add_single_document(content, metadata)
                    
                except Exception as e:
                    print(f"⚠️  Error processing {file_path.name}: {e}")
    
    def add_text_directly(self, text: str, title: str = None, source: str = None):
        """Add text directly without file processing"""
        metadata = {
            'title': title or 'Direct Text Input',
            'source': source or 'manual_input',
            'document_type': 'text',
            'processed_at': '2024-01-01T00:00:00'
        }
        
        return self.add_single_document(text, metadata)

def main():
    """Main function for direct ingestion"""
    print("🚀 Direct Qdrant Ingestion Tool")
    print("=" * 50)
    
    # Initialize ingestion
    ingestion = DirectQdrantIngestion()
    
    while True:
        print("\n📚 Choose an option:")
        print("1. Add documents from folder")
        print("2. Add single text document")
        print("3. Check collection status")
        print("4. Exit")
        
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == "1":
            folder_path = input("Enter folder path: ").strip()
            ingestion.add_documents_from_folder(folder_path)
            
        elif choice == "2":
            text = input("Enter document text: ").strip()
            title = input("Enter title (optional): ").strip() or None
            source = input("Enter source (optional): ").strip() or None
            ingestion.add_text_directly(text, title, source)
            
        elif choice == "3":
            try:
                collection_info = ingestion.client.get_collection(ingestion.collection_name)
                print(f"📊 Collection: {ingestion.collection_name}")
                print(f"📄 Total documents: {collection_info.points_count}")
                print(f"🔢 Vector dimension: {collection_info.config.params.vectors.size}")
            except Exception as e:
                print(f"❌ Error getting collection info: {e}")
                
        elif choice == "4":
            print("👋 Goodbye!")
            break
            
        else:
            print("❌ Invalid choice. Please try again.")

if __name__ == "__main__":
    main()
