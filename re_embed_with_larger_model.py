#!/usr/bin/env python3
"""
Re-embed all documents with the larger all-MiniLM-L6-v2 model
This will improve search quality and fix DRCL search issues
"""

import os
import sys
from dotenv import load_dotenv
from knowledge_base import KnowledgeBase
import time

# Load environment variables
load_dotenv()

def re_embed_all_documents():
    """Re-embed all documents with the new larger model"""
    print("🚀 Starting Re-embedding with all-MiniLM-L6-v2 Model")
    print("=" * 60)
    
    try:
        # Initialize knowledge base with new model
        print("📚 Initializing knowledge base...")
        kb = KnowledgeBase()
        
        # Get all documents from Qdrant
        print("🔍 Retrieving all documents from Qdrant...")
        all_docs = kb.get_all_documents()
        
        if not all_docs:
            print("❌ No documents found in knowledge base")
            return
        
        print(f"📄 Found {len(all_docs)} documents to re-embed")
        
        # Clear the existing collection to start fresh
        print("🧹 Clearing existing Qdrant collection...")
        kb.client.recreate_collection(
            collection_name=kb.qdrant_collection,
            vectors_config=kb.client.models.VectorParams(size=384, distance=kb.client.models.Distance.COSINE),
        )
        print("✅ Collection cleared and recreated")
        
        # Re-add all documents with new embeddings
        print("\n🔄 Re-adding documents with new embeddings...")
        total_chunks = 0
        start_time = time.time()
        
        for i, doc in enumerate(all_docs):
            try:
                print(f"\n   📄 Processing document {i+1}/{len(all_docs)}: {doc.get('metadata', {}).get('filename', 'Unknown')}")
                
                # Extract content and metadata
                content = doc.get('content', '')
                metadata = doc.get('metadata', {})
                
                if content:
                    # Add document back to knowledge base
                    kb.add_documents([content], [metadata])
                    total_chunks += 1
                    print(f"   ✅ Added successfully")
                else:
                    print(f"   ⚠️ No content found, skipping")
                    
            except Exception as e:
                print(f"   ❌ Error processing document: {e}")
                continue
        
        elapsed_time = time.time() - start_time
        
        print("\n" + "=" * 60)
        print("🎉 Re-embedding Complete!")
        print(f"📊 Documents processed: {len(all_docs)}")
        print(f"📊 Total chunks: {total_chunks}")
        print(f"⏱️ Time taken: {elapsed_time:.2f} seconds")
        print(f"🧠 New model: all-MiniLM-L6-v2 (384 dimensions)")
        
        # Test the new embeddings
        print("\n🧪 Testing new embeddings...")
        test_queries = [
            "DRCL experience",
            "USC research",
            "Shravan Research Tracker",
            "SAM2 segmentation"
        ]
        
        for query in test_queries:
            try:
                print(f"\n   Testing: '{query}'")
                results = kb.search(query, n_results=3)
                
                if results:
                    print(f"   Results found: {len(results)}")
                    for j, result in enumerate(results[:2]):
                        filename = result.get('metadata', {}).get('filename', 'Unknown')
                        content_preview = result.get('content', '')[:100]
                        print(f"     Result {j+1}: {filename}")
                        print(f"     Content: {content_preview}...")
                else:
                    print("   ❌ No results found")
                    
            except Exception as e:
                print(f"   ❌ Error testing query: {e}")
        
        print("\n✅ Re-embedding completed successfully!")
        print("💡 Your DRCL experience should now be much more searchable!")
        
    except Exception as e:
        print(f"❌ Error during re-embedding: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main function"""
    print("🔄 Document Re-embedding with Larger Model")
    print("This will:")
    print("1. Clear existing Qdrant collection")
    print("2. Re-embed all documents with all-MiniLM-L6-v2")
    print("3. Improve search quality significantly")
    print("4. Fix DRCL search issues")
    
    response = input("\n🤔 Proceed with re-embedding? (y/N): ").strip().lower()
    
    if response in ['y', 'yes']:
        re_embed_all_documents()
    else:
        print("❌ Re-embedding cancelled")

if __name__ == "__main__":
    main()
