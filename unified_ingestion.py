#!/usr/bin/env python3
"""
Enhanced Unified Ingestion Pipeline
Replaces the old ingestion system with comprehensive document processing
"""
import os
import sys
import json
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
import re

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_document_processor import EnhancedDocumentProcessor
from knowledge_base import KnowledgeBase
import google.generativeai as genai
from config import Config

class EnhancedUnifiedIngestion:
    def __init__(self):
        self.config = Config()
        self.enhanced_processor = EnhancedDocumentProcessor()
        self.knowledge_base = KnowledgeBase()
        genai.configure(api_key=self.config.GOOGLE_API_KEY)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        # Comprehensive extraction prompt
        self.extraction_prompt = """You are helping build a career knowledge base. Extract and summarize the following fields from the COMPLETE document below.

IMPORTANT: Read through the ENTIRE document to capture ALL information, including:
- Early achievements AND later updates/improvements
- Complete timeline of progress
- All technologies mentioned throughout
- Full scope of responsibilities
- Complete list of achievements (including updates/progress)

• Title / Project name
• Organization and location
• Role or course
• Timeline (start month/year – end month/year)
• Objectives and high-level description
• Specific responsibilities and tasks
• Technologies, frameworks and tools used
• Achievements and measurable outcomes (metrics, improvements, publications, awards) - INCLUDE ALL UPDATES
• Key skills demonstrated
• Notes or challenges

Return the summary as a JSON object with the following structure:

{{
  "title": "string",
  "organization": "string",
  "location": "string",
  "role": "string",
  "timeline": {{
    "start": "MM/YYYY",
    "end": "MM/YYYY",
    "duration": "string"
  }},
  "objectives": "string",
  "responsibilities": ["string"],
  "technologies": ["string"],
  "achievements": ["string"],
  "skills": {{
    "technical": ["string"],
    "soft": ["string"]
  }},
  "notes": "string",
  "challenges": ["string"],
  "missing_fields": ["string"],
  "clarifying_questions": ["string"]
}}

COMPLETE Document content:
{content}

IMPORTANT: Ensure you've read the ENTIRE document and captured ALL achievements, updates, and progress mentioned throughout. Return only the JSON object, no additional text."""

    def process_document_enhanced(self, file_path: str, interactive: bool = True) -> Dict[str, Any]:
        """Process a single document with enhanced extraction and validation"""
        print(f"🔍 Processing: {os.path.basename(file_path)}")
        
        # Get enhanced chunks
        chunks = self.enhanced_processor.process_document_enhanced(file_path)
        print(f"✅ Extracted {len(chunks)} cleaned chunks")
        
        # Debug: Check chunk structure
        if chunks:
            print(f"🔍 Sample chunk structure:")
            sample_chunk = chunks[0]
            print(f"   Keys: {list(sample_chunk.keys())}")
            if 'metadata' in sample_chunk:
                print(f"   Metadata keys: {list(sample_chunk['metadata'].keys())}")
            print(f"   Content type: {type(sample_chunk.get('content', ''))}")
            print(f"   Content length: {len(str(sample_chunk.get('content', '')))}")
        
        # Combine chunks intelligently for full context
        full_content = self._combine_chunks_intelligently(chunks)
        
        # Extract structured summary using Gemini
        summary = self._extract_structured_summary(full_content)
        if not summary:
            print("❌ Failed to extract structured summary")
            return {"success": False, "error": "Structured extraction failed"}
        
        print(f"📊 Structured extraction completed")
        
        # Run interactive clarification if requested
        if interactive:
            summary = self._run_clarification_loop(summary, file_path)
        
        # Create enhanced chunks with rich metadata
        enhanced_chunks = self._create_enhanced_chunks(chunks, summary, file_path)
        
        # Add to knowledge base
        print(f"Adding {len(enhanced_chunks)} chunks to knowledge base...")
        self.knowledge_base.add_documents(enhanced_chunks, source_file=file_path)
        
        # Save structured summary
        self._save_structured_summary(summary, file_path)
        
        return {"success": True, "chunks": len(enhanced_chunks), "summary": summary}

    def _combine_chunks_intelligently(self, chunks: List[Dict[str, Any]]) -> str:
        """Combine chunks intelligently for better context"""
        # Sort chunks by index for logical order, with fallback for missing metadata
        def get_chunk_index(chunk):
            try:
                metadata = chunk.get('metadata', {})
                if isinstance(metadata, dict):
                    return metadata.get('chunk_index', 0)
                else:
                    return 0
            except (TypeError, AttributeError):
                return 0
        
        sorted_chunks = sorted(chunks, key=get_chunk_index)
        
        # Combine with proper spacing - ensure we get the FULL document
        combined = []
        for chunk in sorted_chunks:
            try:
                content = chunk.get('content', '')
                if isinstance(content, str) and content.strip():
                    combined.append(content.strip())
                elif isinstance(content, (list, tuple)):
                    # Handle case where content might be a list
                    content_str = ' '.join(str(item) for item in content if item)
                    if content_str.strip():
                        combined.append(content_str.strip())
            except (TypeError, AttributeError) as e:
                print(f"⚠️  Warning: Skipping malformed chunk: {e}")
                continue
        
        # Create comprehensive document text
        full_document = "\n\n".join(combined)
        
        print(f"📄 Document length: {len(full_document)} characters")
        print(f"📊 Total chunks combined: {len(combined)}")
        
        return full_document

    def _extract_structured_summary(self, content: str) -> Optional[Dict[str, Any]]:
        """Extract structured summary using Gemini with FULL document context"""
        try:
            # Use the ENTIRE document content, not truncated
            print(f"🔍 Processing full document: {len(content)} characters")
            
            # Create comprehensive prompt
            comprehensive_prompt = f"""You are helping build a career knowledge base. Extract and summarize the following fields from the COMPLETE document below.

IMPORTANT: Read through the ENTIRE document to capture ALL information, including:
- Early achievements AND later updates/improvements
- Complete timeline of progress
- All technologies mentioned throughout
- Full scope of responsibilities
- Complete list of achievements (including updates/progress)

• Title / Project name
• Organization and location
• Role or course
• Timeline (start month/year – end month/year)
• Objectives and high-level description
• Specific responsibilities and tasks
• Technologies, frameworks and tools used
• Achievements and measurable outcomes (metrics, improvements, publications, awards) - INCLUDE ALL UPDATES
• Key skills demonstrated
• Notes or challenges

Return the summary as a JSON object with the following structure:

{{
  "title": "string",
  "organization": "string",
  "location": "string",
  "role": "string",
  "timeline": {{
    "start": "MM/YYYY",
    "end": "MM/YYYY",
    "duration": "string"
  }},
  "objectives": "string",
  "responsibilities": ["string"],
  "technologies": ["string"],
  "achievements": ["string"],
  "skills": {{
    "technical": ["string"],
    "soft": ["string"]
  }},
  "notes": "string",
  "challenges": ["string"],
  "missing_fields": ["string"],
  "clarifying_questions": ["string"]
}}

COMPLETE Document content:
{content}

IMPORTANT: Ensure you've read the ENTIRE document and captured ALL achievements, updates, and progress mentioned throughout. Return only the JSON object, no additional text."""
            
            response = self.model.generate_content(comprehensive_prompt)
            
            # Extract JSON from response
            response_text = response.text.strip()
            
            print(f"🔍 Gemini response (first 500 chars): {response_text[:500]}...")
            
            # Find JSON content (handle cases where Gemini adds extra text)
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_content = response_text[json_start:json_end]
                
                print(f"🔍 Extracted JSON content: {json_content[:500]}...")
                
                # Clean up common JSON formatting issues
                json_content = json_content.replace('\n', ' ').replace('  ', ' ')
                
                try:
                    return json.loads(json_content)
                except json.JSONDecodeError as e:
                    print(f"❌ JSON decode error: {e}")
                    print(f"   Raw JSON content: {json_content[:500]}...")
                    
                    # Try to fix common JSON issues
                    fixed_json = self._fix_json_content(json_content)
                    if fixed_json:
                        return json.loads(fixed_json)
                    
                    return None
            else:
                print(f"❌ No valid JSON found in response: {response_text[:200]}...")
                return None
                
        except Exception as e:
            print(f"❌ Error in structured extraction: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _fix_json_content(self, json_content: str) -> Optional[str]:
        """Try to fix common JSON formatting issues"""
        try:
            # Remove invalid control characters
            json_content = ''.join(char for char in json_content if ord(char) >= 32 or char in '\n\r\t')
            
            # Remove excessive whitespace
            json_content = re.sub(r'\s+', ' ', json_content)
            
            # Fix common quote issues
            json_content = json_content.replace('"', '"').replace('"', '"')
            
            # Fix common unicode issues
            json_content = json_content.replace('–', '-').replace('—', '-')
            json_content = json_content.replace('"', '"').replace('"', '"')
            json_content = json_content.replace(''', "'").replace(''', "'")
            
            # Try to parse again
            json.loads(json_content)
            return json_content
        except Exception as e:
            print(f"   🔧 JSON fix attempt failed: {e}")
            return None

    def _validate_extraction_completeness(self, summary: Dict[str, Any], original_content: str) -> Dict[str, Any]:
        """Validate that extraction captured comprehensive information"""
        validation_results = {
            'completeness_score': 0.0,
            'missing_achievements': [],
            'missing_technologies': [],
            'suggestions': []
        }
        
        # Check for common patterns that might indicate missed information
        content_lower = original_content.lower()
        
        # Look for performance metrics that might have been missed
        performance_patterns = [
            r'(\d+(?:\.\d+)?)\s*hz',
            r'(\d+(?:\.\d+)?)\s*fps',
            r'(\d+(?:\.\d+)?)\s*times?\s*faster',
            r'(\d+(?:\.\d+)?)\s*times?\s*speedup',
            r'(\d+(?:\.\d+)?)\s*times?\s*improvement'
        ]
        
        found_metrics = []
        for pattern in performance_patterns:
            matches = re.finditer(pattern, content_lower)
            for match in matches:
                found_metrics.append(match.group(0))
        
        # Check if all found metrics are in achievements
        achievements_text = ' '.join(summary.get('achievements', [])).lower()
        missing_metrics = []
        for metric in found_metrics:
            if metric not in achievements_text:
                missing_metrics.append(metric)
        
        if missing_metrics:
            validation_results['missing_achievements'].extend(missing_metrics)
            validation_results['suggestions'].append(f"Found performance metrics not in achievements: {missing_metrics}")
        
        # Check for technology mentions that might have been missed
        tech_mentions = []
        for tech in ['python', 'pytorch', 'tensorflow', 'cuda', 'gpu', 'jetson', 'tensorrt']:
            if tech in content_lower and tech not in ' '.join(summary.get('technologies', [])).lower():
                tech_mentions.append(tech)
        
        if tech_mentions:
            validation_results['missing_technologies'].extend(tech_mentions)
            validation_results['suggestions'].append(f"Found technology mentions not in technologies: {tech_mentions}")
        
        # Calculate completeness score
        total_fields = 8  # title, organization, role, timeline, objectives, responsibilities, technologies, achievements
        filled_fields = sum(1 for field in ['title', 'organization', 'role', 'timeline', 'objectives', 'responsibilities', 'technologies', 'achievements'] 
                           if summary.get(field) and summary[field] != [] and summary[field] != {})
        
        validation_results['completeness_score'] = filled_fields / total_fields
        
        return validation_results

    def _run_clarification_loop(self, summary: Dict[str, Any], file_path: str) -> Dict[str, Any]:
        """Run interactive clarification loop with validation"""
        print(f"\n🔍 Clarification needed for: {summary.get('title', 'Unknown Project')}")
        
        # Validate extraction completeness
        print(f"\n📊 Validation Results:")
        validation = self._validate_extraction_completeness(summary, self._get_original_content(file_path))
        
        print(f"   • Completeness Score: {validation['completeness_score']:.1%}")
        if validation['missing_achievements']:
            print(f"   • Missing Achievements: {', '.join(validation['missing_achievements'])}")
        if validation['missing_technologies']:
            print(f"   • Missing Technologies: {', '.join(validation['missing_technologies'])}")
        if validation['suggestions']:
            print(f"   • Suggestions: {validation['suggestions'][0]}")
        
        # Show current summary
        print(f"\n📊 Current Summary:")
        for key, value in summary.items():
            if key not in ['missing_fields', 'clarifying_questions']:
                print(f"   {key}: {value}")
        
        # Show missing fields
        missing = summary.get('missing_fields', [])
        if missing:
            print(f"\n❌ Missing fields: {', '.join(missing)}")
        
        # Show clarifying questions
        questions = summary.get('clarifying_questions', [])
        if questions:
            print(f"\n❓ Clarifying questions:")
            for i, question in enumerate(questions, 1):
                print(f"   {i}. {question}")
        
        # Get user input for missing information
        print(f"\n💬 Please provide missing information (press Enter to skip):")
        
        # Ask for basic missing fields
        if not summary.get('title'):
            title = input("Project title: ").strip()
            if title:
                summary['title'] = title
        
        if not summary.get('organization'):
            org = input("Organization: ").strip()
            if org:
                summary['organization'] = org
        
        if not summary.get('role'):
            role = input("Your role: ").strip()
            if role:
                summary['role'] = role
        
        # Ask for timeline
        timeline = summary.get('timeline', {})
        if not timeline.get('start'):
            start = input("Start date (MM/YYYY): ").strip()
            if start:
                timeline['start'] = start
        
        if not timeline.get('end'):
            end = input("End date (MM/YYYY or 'ongoing'): ").strip()
            if end:
                timeline['end'] = end
        
        summary['timeline'] = timeline
        
        # Ask for technologies
        if not summary.get('technologies'):
            techs = input("Technologies used (comma-separated): ").strip()
            if techs:
                summary['technologies'] = [t.strip() for t in techs.split(',')]
        
        # Ask for achievements - emphasize including ALL updates
        print(f"\n💡 IMPORTANT: Make sure to include ALL achievements, including:")
        print(f"   • Early results (e.g., 10Hz)")
        print(f"   • Later improvements (e.g., 20Hz)")
        print(f"   • Progress updates and optimizations")
        
        if not summary.get('achievements'):
            achievements = input("Key achievements (comma-separated, include ALL updates): ").strip()
            if achievements:
                summary['achievements'] = [a.strip() for a in achievements.split(',')]
        else:
            # Ask if there are additional achievements not captured
            additional = input("Any additional achievements or updates not captured above? (comma-separated): ").strip()
            if additional:
                additional_achievements = [a.strip() for a in additional.split(',')]
                summary['achievements'].extend(additional_achievements)
        
        # Ask for skills
        if not summary.get('skills', {}).get('technical'):
            tech_skills = input("Technical skills (comma-separated): ").strip()
            if tech_skills:
                summary.setdefault('skills', {})['technical'] = [s.strip() for t in tech_skills.split(',')]
        
        # Additional notes
        additional = input("Any additional notes: ").strip()
        if additional:
            summary['notes'] = (summary.get('notes', '') + ' ' + additional).strip()
        
        return summary

    def _get_original_content(self, file_path: str) -> str:
        """Get original document content for validation"""
        chunks = self.enhanced_processor.process_document_enhanced(file_path)
        return self._combine_chunks_intelligently(chunks)

    def _create_enhanced_chunks(self, chunks: List[Dict[str, Any]], summary: Dict[str, Any], file_path: str) -> List[Dict[str, Any]]:
        """Create enhanced chunks with rich metadata"""
        enhanced_chunks = []
        
        for i, chunk in enumerate(chunks):
            enhanced_chunk = {
                'content': chunk.get('content', ''),
                'metadata': {
                    'source': file_path,
                    'filename': os.path.basename(file_path),
                    'chunk_index': i,
                    'total_chunks': len(chunks),
                    'processed_at': datetime.now().isoformat(),
                    
                    # Rich metadata from structured summary
                    'title': summary.get('title', ''),
                    'organization': summary.get('organization', ''),
                    'role': summary.get('role', ''),
                    'timeline': summary.get('timeline', {}),
                    'objectives': summary.get('objectives', ''),
                    'technologies': summary.get('technologies', []),
                    'achievements': summary.get('achievements', []),
                    'skills': summary.get('skills', {}),
                    'challenges': summary.get('challenges', []),
                    
                    # Document type classification
                    'document_type': self._classify_document_type(file_path, summary),
                    
                    # Content analysis
                    'word_count': len(chunk.get('content', '').split()),
                    'has_technical_content': any(tech.lower() in chunk.get('content', '').lower() 
                                               for tech in summary.get('technologies', [])),
                    'has_achievements': any(achievement.lower() in chunk.get('content', '').lower() 
                                          for achievement in summary.get('achievements', []))
                }
            }
            enhanced_chunks.append(enhanced_chunk)
        
        return enhanced_chunks

    def _classify_document_type(self, file_path: str, summary: Dict[str, Any]) -> str:
        """Classify document type based on content and filename"""
        filename = os.path.basename(file_path).lower()
        role = summary.get('role', '').lower()
        
        if 'internship' in filename or 'intern' in role:
            return 'internship'
        elif 'research' in filename or 'paper' in filename or 'thesis' in filename:
            return 'research'
        elif 'course' in filename or 'coursework' in role:
            return 'coursework'
        elif 'project' in filename or 'project' in role:
            return 'project'
        else:
            return 'document'

    def _save_structured_summary(self, summary: Dict[str, Any], file_path: str) -> None:
        """Save the structured summary for future reference"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{os.path.basename(file_path)}_{timestamp}.json"
        
        # Ensure directory exists
        os.makedirs('structured_summaries', exist_ok=True)
        
        filepath = os.path.join('structured_summaries', filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Structured summary saved: {filepath}")

    def ingest_directory(self, directory_path: str = "documents", interactive: bool = True) -> Dict[str, Any]:
        """Process all supported files in a directory"""
        print(f"🚀 Starting enhanced ingestion for directory: {directory_path}")
        
        if not os.path.exists(directory_path):
            print(f"❌ Directory not found: {directory_path}")
            return {"success": False, "error": "Directory not found"}
        
        # Get all supported files
        supported_extensions = {'.pdf', '.docx', '.txt', '.csv', '.json', '.jpg', '.jpeg', '.png'}
        files_to_process = []
        
        for file_path in Path(directory_path).rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                files_to_process.append(str(file_path))
        
        if not files_to_process:
            print(f"❌ No supported files found in {directory_path}")
            return {"success": False, "error": "No supported files found"}
        
        print(f"📁 Found {len(files_to_process)} files to process")
        
        results = []
        for i, file_path in enumerate(files_to_process, 1):
            print(f"\n{'='*60}")
            print(f"📄 Processing file {i}/{len(files_to_process)}: {os.path.basename(file_path)}")
            print(f"{'='*60}")
            
            try:
                result = self.process_document_enhanced(file_path, interactive)
                results.append({
                    'file': file_path,
                    'success': result.get('success', False),
                    'chunks': result.get('chunks', 0),
                    'summary': result.get('summary', {})
                })
                
                if result.get('success'):
                    print(f"✅ File processing completed: {result['success']}")
                else:
                    print(f"❌ File processing failed: {result.get('error', 'Unknown error')}")
                
                # Test knowledge base after each document
                if result.get('success'):
                    print(f"\n🧪 Testing knowledge base after adding: {os.path.basename(file_path)}")
                    self._test_document_ingestion(file_path)
                
            except Exception as e:
                print(f"❌ Error processing {file_path}: {e}")
                results.append({
                    'file': file_path,
                    'success': False,
                    'error': str(e)
                })
        
        # Final knowledge base test
        print(f"\n{'='*60}")
        print(f"🧪 FINAL KNOWLEDGE BASE TEST")
        print(f"{'='*60}")
        self._test_final_knowledge_base()
        
        return {
            "success": True,
            "total_files": len(files_to_process),
            "successful_files": len([r for r in results if r.get('success')]),
            "results": results
        }

    def _test_document_ingestion(self, file_path: str) -> None:
        """Test knowledge base after adding a specific document"""
        try:
            filename = os.path.basename(file_path)
            
            # Test basic retrieval
            results = self.knowledge_base.search(f"information about {filename}", n_results=3)
            
            if results and len(results) > 0:
                print(f"   ✅ Retrieved {len(results)} chunks for {filename}")
                
                # Show a sample chunk
                sample_chunk = results[0]
                print(f"   📝 Sample content: {sample_chunk['content'][:100]}...")
                
                # Check metadata
                if 'metadata' in sample_chunk:
                    metadata = sample_chunk['metadata']
                    print(f"   🏷️  Metadata: {metadata.get('title', 'N/A')} | {metadata.get('role', 'N/A')}")
            else:
                print(f"   ⚠️  No results found for {filename}")
                
        except Exception as e:
            print(f"   ❌ Test failed: {e}")

    def _test_final_knowledge_base(self) -> None:
        """Comprehensive test of the final knowledge base"""
        try:
            print("🔍 Testing knowledge base functionality...")
            
            # Test 1: Basic search
            print("   📊 Test 1: Basic search...")
            results = self.knowledge_base.search("research projects and achievements", n_results=5)
            if results and len(results) > 0:
                print(f"      ✅ Found {len(results)} results")
            else:
                print("      ❌ No search results")
            
            # Test 2: Technology search
            print("   🔧 Test 2: Technology search...")
            tech_results = self.knowledge_base.search("Python PyTorch CUDA", n_results=3)
            if tech_results and len(tech_results) > 0:
                print(f"      ✅ Found {len(tech_results)} technology results")
            else:
                print("      ❌ No technology results")
            
            # Test 3: Achievement search
            print("   🏆 Test 3: Achievement search...")
            achievement_results = self.knowledge_base.search("performance improvements speedup", n_results=3)
            if achievement_results and len(achievement_results) > 0:
                print(f"      ✅ Found {len(achievement_results)} achievement results")
            else:
                print("      ❌ No achievement results")
            
            # Test 4: Document count
            print("   📚 Test 4: Document count...")
            try:
                collection = self.knowledge_base.collection
                count = collection.count()
                print(f"      ✅ Total documents in KB: {count}")
            except Exception as e:
                print(f"      ⚠️  Could not get document count: {e}")
            
            print("   🎉 Knowledge base testing completed!")
            
        except Exception as e:
            print(f"   ❌ Final test failed: {e}")

def main():
    """Command-line interface for the enhanced ingestion pipeline"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhanced Document Ingestion Pipeline")
    parser.add_argument("--file", help="Process a single file")
    parser.add_argument("--directory", default="documents", help="Process all files in directory")
    parser.add_argument("--non-interactive", action="store_true", help="Skip interactive clarification")
    
    args = parser.parse_args()
    
    pipeline = EnhancedUnifiedIngestion()
    
    if args.file:
        # Process single file
        if not os.path.exists(args.file):
            print(f"❌ File not found: {args.file}")
            sys.exit(1)
        
        result = pipeline.process_document_enhanced(args.file, not args.non_interactive)
        if result.get('success'):
            print(f"✅ File processing completed: {result['success']}")
        else:
            print(f"❌ File processing failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)
    else:
        # Process directory
        result = pipeline.ingest_directory(args.directory, not args.non_interactive)
        if result.get('success'):
            print(f"✅ Directory processing completed successfully!")
            print(f"   Processed: {result['total_files']} files")
            print(f"   Successful: {result['successful_files']} files")
        else:
            print(f"❌ Directory processing failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)

if __name__ == '__main__':
    sys.exit(main())
