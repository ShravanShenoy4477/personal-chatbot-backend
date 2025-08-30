#!/usr/bin/env python3
"""
Update Course Data in Qdrant
This script removes old course data and adds new structured course summaries
"""

import os
import json
import sys
from pathlib import Path
from dotenv import load_dotenv
from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer
import hashlib

# Load environment variables
load_dotenv()

class CourseDataUpdater:
    def __init__(self):
        """Initialize the course data updater"""
        self.client = QdrantClient(
            url=os.getenv("QDRANT_URL"),
            api_key=os.getenv("QDRANT_API_KEY")
        )
        self.collection_name = os.getenv("QDRANT_COLLECTION", "personal_knowledge")
        self.embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2', device='cpu')
        
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
    
    def remove_old_course_data(self):
        """Remove old course data from Qdrant"""
        print("🧹 REMOVING OLD COURSE DATA")
        print("=" * 50)
        
        try:
            # Get all documents to identify course-related ones
            scroll_result = self.client.scroll(
                collection_name=self.collection_name,
                with_payload=True,
                with_vectors=False,
                limit=1000
            )
            
            points = scroll_result[0]
            course_points_to_delete = []
            
            # Identify course-related documents
            for point in points:
                payload = point.payload or {}
                
                # Check if this is course-related data
                if self._is_course_related(payload):
                    course_points_to_delete.append(point.id)
                    print(f"   🎓 Found old course data: {payload.get('title', 'Unknown')} (ID: {point.id})")
            
            if course_points_to_delete:
                print(f"\n🗑️  Deleting {len(course_points_to_delete)} old course documents...")
                
                # Delete in batches to avoid overwhelming the API
                batch_size = 100
                for i in range(0, len(course_points_to_delete), batch_size):
                    batch = course_points_to_delete[i:i + batch_size]
                    self.client.delete(
                        collection_name=self.collection_name,
                        points_selector=models.PointIdsList(points=batch)
                    )
                    print(f"   ✅ Deleted batch {i//batch_size + 1}/{(len(course_points_to_delete) + batch_size - 1)//batch_size}")
                
                print(f"✅ Successfully deleted {len(course_points_to_delete)} old course documents")
            else:
                print("ℹ️  No old course data found to delete")
            
            return True
            
        except Exception as e:
            print(f"❌ Error removing old course data: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _is_course_related(self, payload):
        """Check if a document is course-related"""
        # Check for course-specific metadata
        if payload.get('document_type') == 'structured_summary':
            return True
        
        # Check for course-related content patterns
        content = payload.get('content', '')
        course_indicators = [
            'course', 'class', 'lecture', 'assignment', 'exam', 'grade',
            'credit', 'syllabus', 'instructor', 'professor', 'university',
            'college', 'academic', 'curriculum', 'semester', 'quarter'
        ]
        
        content_lower = content.lower()
        return any(indicator in content_lower for indicator in course_indicators)
    
    def add_new_course_data(self):
        """Add new structured course summaries to Qdrant"""
        print("\n🚀 ADDING NEW COURSE DATA")
        print("=" * 50)
        
        try:
            # Get structured summaries directory
            summaries_dir = Path("structured_summaries")
            if not summaries_dir.exists():
                print("❌ Structured summaries directory not found")
                return False
            
            # Get all course JSON files (filter for course-related ones)
            json_files = list(summaries_dir.glob("*.json"))
            course_files = []
            
            for json_file in json_files:
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Check if this is a course summary
                    if self._is_course_summary(data):
                        course_files.append((json_file, data))
                except Exception as e:
                    print(f"⚠️  Error reading {json_file.name}: {e}")
                    continue
            
            print(f"📚 Found {len(course_files)} course summary files")
            
            if not course_files:
                print("❌ No course summary files found")
                return False
            
            # Process each course file
            successful_additions = 0
            
            for json_file, summary_data in course_files:
                print(f"\n📄 Processing: {json_file.name}")
                
                try:
                    # Create comprehensive content for ingestion
                    content = self._create_course_content(summary_data)
                    
                    # Create metadata
                    metadata = self._create_course_metadata(json_file, summary_data)
                    
                    # Add to Qdrant
                    doc_id = self._add_course_to_qdrant(content, metadata)
                    
                    if doc_id:
                        successful_additions += 1
                        print(f"   ✅ Successfully added: {summary_data.get('title', 'Unknown Title')}")
                    else:
                        print(f"   ❌ Failed to add: {summary_data.get('title', 'Unknown Title')}")
                
                except Exception as e:
                    print(f"   ❌ Error processing {json_file.name}: {e}")
                    continue
            
            print(f"\n📊 Successfully added {successful_additions}/{len(course_files)} course summaries")
            return successful_additions == len(course_files)
            
        except Exception as e:
            print(f"❌ Error adding new course data: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _is_course_summary(self, data):
        """Check if JSON data represents a course summary"""
        # Look for course-specific fields
        course_fields = ['course_code', 'credits', 'instructor', 'term', 'year']
        return any(field in data for field in course_fields)
    
    def _create_course_content(self, summary_data):
        """Create comprehensive content from course summary data"""
        content_parts = [
            f"Title: {summary_data.get('title', 'Unknown Title')}",
            f"Course Code: {summary_data.get('course_code', 'N/A')}",
            f"Institution: {summary_data.get('institution', 'Unknown Institution')}",
            f"Category: {summary_data.get('category', 'N/A')}",
            f"Delivery Mode: {summary_data.get('delivery_mode', 'N/A')}",
            f"Credit Type: {summary_data.get('credit_type', 'N/A')}",
            f"Level: {summary_data.get('level', 'N/A')}",
            f"Term: {summary_data.get('term', 'N/A')}",
            f"Year: {summary_data.get('year', 'N/A')}",
            f"Status: {summary_data.get('status', 'N/A')}",
            f"Credits: {summary_data.get('credits', 'N/A')}",
            f"Instructor: {summary_data.get('instructor', 'N/A')}",
            f"Workload: {summary_data.get('workload_hrs', 'N/A')} hours",
            f"Grade: {summary_data.get('grade', 'N/A')}",
            f"Role: {summary_data.get('role', 'N/A')}"
        ]
        
        # Add timeline information
        timeline = summary_data.get('timeline', {})
        if timeline:
            content_parts.append(f"Timeline: {timeline.get('start', 'N/A')} - {timeline.get('end', 'N/A')} ({timeline.get('duration', 'N/A')})")
        
        # Add objectives
        objectives = summary_data.get('objectives', '')
        if objectives:
            content_parts.append(f"Objectives: {objectives}")
        
        # Add responsibilities
        responsibilities = summary_data.get('responsibilities', [])
        if responsibilities:
            content_parts.append(f"Responsibilities: {', '.join(responsibilities)}")
        
        # Add technologies
        technologies = summary_data.get('technologies', [])
        if technologies:
            content_parts.append(f"Technologies: {', '.join(technologies)}")
        
        # Add achievements
        achievements = summary_data.get('achievements', [])
        if achievements:
            content_parts.append(f"Achievements: {', '.join(achievements)}")
        
        # Add skills
        skills = summary_data.get('skills', {})
        if skills:
            technical_skills = skills.get('technical', [])
            soft_skills = skills.get('soft', [])
            
            if technical_skills:
                content_parts.append(f"Technical Skills: {', '.join(technical_skills)}")
            if soft_skills:
                content_parts.append(f"Soft Skills: {', '.join(soft_skills)}")
        
        # Add notes
        notes = summary_data.get('notes', '')
        if notes:
            content_parts.append(f"Notes: {notes}")
        
        # Add challenges
        challenges = summary_data.get('challenges', [])
        if challenges:
            content_parts.append(f"Challenges: {', '.join(challenges)}")
        
        return "\n\n".join(content_parts)
    
    def _create_course_metadata(self, json_file, summary_data):
        """Create metadata for course summary"""
        timeline = summary_data.get('timeline', {})
        
        return {
            'source': str(json_file),
            'filename': json_file.name,
            'title': summary_data.get('title', 'Unknown Title'),
            'course_code': summary_data.get('course_code', ''),
            'institution': summary_data.get('institution', ''),
            'category': summary_data.get('category', ''),
            'delivery_mode': summary_data.get('delivery_mode', ''),
            'credit_type': summary_data.get('credit_type', ''),
            'level': summary_data.get('level', ''),
            'term': summary_data.get('term', ''),
            'year': summary_data.get('year', ''),
            'status': summary_data.get('status', ''),
            'credits': summary_data.get('credits', ''),
            'instructor': summary_data.get('instructor', ''),
            'workload_hrs': summary_data.get('workload_hrs', ''),
            'grade': summary_data.get('grade', ''),
            'role': summary_data.get('role', ''),
            'document_type': 'course_summary',
            'processed_at': summary_data.get('processed_at', '2024-01-01T00:00:00'),
            'timeline_start': timeline.get('start', ''),
            'timeline_end': timeline.get('end', ''),
            'technologies_list': summary_data.get('technologies', []),
            'achievements_list': summary_data.get('achievements', []),
            'technical_skills': summary_data.get('skills', {}).get('technical', []),
            'soft_skills': summary_data.get('skills', {}).get('soft', []),
            'organization': summary_data.get('organization', ''),
            'location': summary_data.get('location', ''),
            'experience_type': summary_data.get('experience_type', ''),
            'temporal_context': summary_data.get('temporal_context', '')
        }
    
    def _add_course_to_qdrant(self, content, metadata):
        """Add a single course to Qdrant"""
        try:
            # Generate embedding
            embedding = self.embedding_model.encode(content).tolist()
            
            # Generate unique ID
            content_hash = hashlib.md5(content.encode()).hexdigest()
            doc_id = int(content_hash[:16], 16)
            
            # Prepare payload
            payload = {
                'content': content,
                **metadata
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
            
            return doc_id
            
        except Exception as e:
            print(f"❌ Error adding course to Qdrant: {e}")
            return None
    
    def get_collection_stats(self):
        """Get current collection statistics"""
        try:
            collection_info = self.client.get_collection(collection_name=self.collection_name)
            print(f"\n📊 COLLECTION STATISTICS")
            print("=" * 30)
            print(f"📚 Collection: {self.collection_name}")
            print(f"📄 Total documents: {collection_info.points_count}")
            print(f"🔢 Vector dimension: {collection_info.config.params.vectors.size}")
            print(f"📐 Distance metric: {collection_info.config.params.vectors.distance}")
            
            return collection_info.points_count
            
        except Exception as e:
            print(f"❌ Error getting collection stats: {e}")
            return 0

def main():
    """Main function for updating course data"""
    print("🚀 Course Data Updater for Qdrant")
    print("=" * 60)
    
    # Initialize updater
    updater = CourseDataUpdater()
    
    # Get initial stats
    initial_count = updater.get_collection_stats()
    
    # Step 1: Remove old course data
    print(f"\n📊 Initial document count: {initial_count}")
    removal_success = updater.remove_old_course_data()
    
    if removal_success:
        # Step 2: Add new course data
        addition_success = updater.add_new_course_data()
        
        if addition_success:
            # Step 3: Get final stats
            final_count = updater.get_collection_stats()
            
            print("\n" + "=" * 60)
            print("📋 COURSE DATA UPDATE SUMMARY")
            print("=" * 60)
            print(f"📊 Initial documents: {initial_count}")
            print(f"📊 Final documents: {final_count}")
            print(f"📈 Net change: {final_count - initial_count}")
            print("✅ Course data update completed successfully!")
            
            return True
        else:
            print("❌ Failed to add new course data")
            return False
    else:
        print("❌ Failed to remove old course data")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 Course data update completed successfully!")
        print("🚀 Ready for use with the updated course information!")
    else:
        print("\n❌ Course data update failed. Check the output above for details.")
        sys.exit(1)
