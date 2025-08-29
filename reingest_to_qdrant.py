#!/usr/bin/env python3
"""
Re-ingest Updated Structured Summaries to Qdrant
This script will clear the existing Qdrant collection and re-ingest all updated structured summaries
"""

import os
import json
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the current directory to Python path
sys.path.append(str(Path(__file__).parent))

from direct_qdrant_ingestion import DirectQdrantIngestion

def clear_qdrant_collection():
    """Clear the existing Qdrant collection"""
    print("🧹 CLEARING EXISTING QDRANT COLLECTION")
    print("=" * 60)
    
    try:
        from qdrant_client import QdrantClient
        
        url = os.getenv("QDRANT_URL")
        api_key = os.getenv("QDRANT_API_KEY")
        collection_name = os.getenv("QDRANT_COLLECTION", "personal_knowledge")
        
        print(f"🔗 Connecting to Qdrant: {url}")
        print(f"📚 Collection: {collection_name}")
        
        client = QdrantClient(url=url, api_key=api_key)
        
        # Check if collection exists
        try:
            collection_info = client.get_collection(collection_name=collection_name)
            print(f"📊 Current collection has {collection_info.vectors_count} vectors")
            
            # Delete and recreate collection
            print("🔄 Deleting existing collection...")
            client.delete_collection(collection_name=collection_name)
            print("✅ Collection deleted")
            
        except Exception as e:
            print(f"📚 Collection '{collection_name}' not found or already deleted")
        
        # Recreate collection
        print("🔄 Recreating collection...")
        from qdrant_client.models import VectorParams, Distance
        
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE)
        )
        print("✅ Collection recreated")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to clear Qdrant collection: {e}")
        import traceback
        traceback.print_exc()
        return False

def reingest_structured_summaries():
    """Re-ingest all updated structured summaries to Qdrant"""
    print("\n🚀 RE-INGESTING UPDATED STRUCTURED SUMMARIES")
    print("=" * 60)
    
    try:
        # Initialize Qdrant ingestion
        print("🔧 Initializing Qdrant ingestion...")
        qdrant_ingestion = DirectQdrantIngestion()
        
        # Get structured summaries directory
        summaries_dir = Path("structured_summaries")
        if not summaries_dir.exists():
            print("❌ Structured summaries directory not found")
            return False
        
        # Get all JSON files
        json_files = list(summaries_dir.glob("*.json"))
        print(f"📚 Found {len(json_files)} structured summary files")
        
        if not json_files:
            print("❌ No structured summary files found")
            return False
        
        # Process each file
        successful_ingestions = 0
        total_chunks = 0
        
        for json_file in json_files:
            print(f"\n📄 Processing: {json_file.name}")
            
            try:
                # Load structured summary
                with open(json_file, 'r', encoding='utf-8') as f:
                    summary_data = json.load(f)
                
                # Extract key information
                title = summary_data.get('title', 'Unknown Title')
                organization = summary_data.get('organization', 'Unknown Organization')
                role = summary_data.get('role', 'Unknown Role')
                timeline = summary_data.get('timeline', {})
                objectives = summary_data.get('objectives', '')
                responsibilities = summary_data.get('responsibilities', [])
                technologies = summary_data.get('technologies', [])
                achievements = summary_data.get('achievements', [])
                skills = summary_data.get('skills', {})
                notes = summary_data.get('notes', '')
                challenges = summary_data.get('challenges', [])
                
                # Create comprehensive content for ingestion
                content_parts = [
                    f"Title: {title}",
                    f"Organization: {organization}",
                    f"Role: {role}",
                    f"Timeline: {timeline.get('start', 'N/A')} - {timeline.get('end', 'N/A')} ({timeline.get('duration', 'N/A')})",
                    f"Objectives: {objectives}",
                    f"Responsibilities: {', '.join(responsibilities) if responsibilities else 'N/A'}",
                    f"Technologies: {', '.join(technologies) if technologies else 'N/A'}",
                    f"Achievements: {', '.join(achievements) if achievements else 'N/A'}",
                    f"Technical Skills: {', '.join(skills.get('technical', [])) if skills.get('technical') else 'N/A'}",
                    f"Soft Skills: {', '.join(skills.get('soft', [])) if skills.get('soft') else 'N/A'}",
                    f"Notes: {notes}",
                    f"Challenges: {', '.join(challenges) if challenges else 'N/A'}"
                ]
                
                comprehensive_content = "\n\n".join(content_parts)
                
                # Create metadata
                metadata = {
                    'source': str(json_file),
                    'filename': json_file.name,
                    'title': title,
                    'organization': organization,
                    'role': role,
                    'document_type': 'structured_summary',
                    'processed_at': summary_data.get('processed_at', '2024-01-01T00:00:00'),
                    'timeline_start': timeline.get('start', ''),
                    'timeline_end': timeline.get('end', ''),
                    'technologies_list': technologies,
                    'achievements_list': achievements,
                    'technical_skills': skills.get('technical', []),
                    'soft_skills': skills.get('soft', [])
                }
                
                # Ingest to Qdrant
                doc_id = qdrant_ingestion.add_single_document(comprehensive_content, metadata)
                
                if doc_id:
                    successful_ingestions += 1
                    total_chunks += 1
                    print(f"   ✅ Successfully ingested: {title}")
                else:
                    print(f"   ❌ Failed to ingest: {title}")
                
            except Exception as e:
                print(f"   ❌ Error processing {json_file.name}: {e}")
                continue
        
        print("\n" + "=" * 60)
        print("📊 RE-INGESTION SUMMARY")
        print("=" * 60)
        print(f"📚 Total files processed: {len(json_files)}")
        print(f"✅ Successful ingestions: {successful_ingestions}")
        print(f"📊 Total chunks ingested: {total_chunks}")
        
        if successful_ingestions == len(json_files):
            print("\n🎉 All updated structured summaries successfully re-ingested to Qdrant!")
            return True
        else:
            print(f"\n⚠️  {len(json_files) - successful_ingestions} files failed to ingest")
            return False
            
    except Exception as e:
        print(f"❌ Re-ingestion failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_qdrant_after_reingestion():
    """Test Qdrant after re-ingestion"""
    print("\n🧪 TESTING QDRANT AFTER RE-INGESTION")
    print("=" * 60)
    
    try:
        from qdrant_client import QdrantClient
        
        client = QdrantClient(
            url=os.getenv("QDRANT_URL"),
            api_key=os.getenv("QDRANT_API_KEY")
        )
        
        collection_name = os.getenv("QDRANT_COLLECTION")
        
        # Get collection info
        collection_info = client.get_collection(collection_name=collection_name)
        print(f"📊 Collection '{collection_name}':")
        print(f"   📏 Vectors: {collection_info.vectors_count}")
        print(f"   📐 Vector size: {collection_info.config.params.vectors.size}")
        print(f"   📐 Distance: {collection_info.config.params.vectors.distance}")
        
        # Test search functionality
        print("\n🔍 Testing search functionality...")
        
        from sentence_transformers import SentenceTransformer
        embedding_model = SentenceTransformer('sentence-transformers/paraphrase-MiniLM-L3-v2', device='cpu')
        
        test_queries = [
            "DRCL research",
            "robotics experience",
            "SAM2 segmentation",
            "ABB internship"
        ]
        
        for query in test_queries:
            print(f"\nQuery: '{query}'")
            try:
                # Generate embedding
                query_embedding = embedding_model.encode(query).tolist()
                
                # Search in Qdrant
                search_results = client.search(
                    collection_name=collection_name,
                    query_vector=query_embedding,
                    limit=3
                )
                
                if search_results:
                    print(f"   ✅ Found {len(search_results)} results")
                    for i, result in enumerate(search_results[:2], 1):
                        content_preview = result.payload.get('content', '')[:150] + "..." if len(result.payload.get('content', '')) > 150 else result.payload.get('content', '')
                        print(f"   📝 Result {i}: {content_preview}")
                        print(f"   📁 Source: {result.payload.get('source', 'Unknown')}")
                        print(f"   🎯 Score: {result.score:.3f}")
                else:
                    print(f"   ⚠️  No results found")
                    
            except Exception as e:
                print(f"   ❌ Search failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Qdrant testing failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Starting Qdrant Re-ingestion Process...")
    
    # Step 1: Clear existing collection
    clear_success = clear_qdrant_collection()
    
    if clear_success:
        # Step 2: Re-ingest updated structured summaries
        reingestion_success = reingest_structured_summaries()
        
        if reingestion_success:
            # Step 3: Test Qdrant after re-ingestion
            test_success = test_qdrant_after_reingestion()
            
            # Summary
            print("\n" + "=" * 80)
            print("📋 QDRANT RE-INGESTION SUMMARY")
            print("=" * 80)
            
            tests = [
                ("Collection Clear", clear_success),
                ("Structured Summaries Re-ingestion", reingestion_success),
                ("Qdrant Functionality Testing", test_success)
            ]
            
            all_passed = True
            for test_name, success in tests:
                status = "✅ PASSED" if success else "❌ FAILED"
                print(f"{test_name:30} : {status}")
                if not success:
                    all_passed = False
            
            print("=" * 80)
            if all_passed:
                print("🎉 Qdrant re-ingestion completed successfully!")
                print("\n📋 NEXT STEPS:")
                print("1. ✅ Updated structured summaries ingested")
                print("2. ✅ Qdrant backend refreshed")
                print("3. 🚀 Ready for Railway deployment testing")
                print("4. 🌐 Ready for API deployment")
                print("5. 🎨 Ready for webpage integration")
            else:
                print("⚠️  Some steps failed. Check the output above for details.")
        else:
            print("❌ Cannot test Qdrant without successful re-ingestion")
    else:
        print("❌ Cannot proceed without clearing the collection")
