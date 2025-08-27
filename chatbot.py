import google.generativeai as genai
from typing import List, Dict, Any, Optional
import json
from datetime import datetime
from config import Config
from knowledge_base import KnowledgeBase
import re

class PersonalChatbot:
    def __init__(self):
        self.config = Config()
        self.knowledge_base = KnowledgeBase()
        
        # Set Google API key
        if self.config.GOOGLE_API_KEY:
            genai.configure(api_key=self.config.GOOGLE_API_KEY)
        else:
            print("Warning: GOOGLE_API_KEY not set. Chatbot may not work properly.")
        
        # Initialize Gemini model
        try:
            self.model = genai.GenerativeModel(self.config.LLM_MODEL)
        except Exception as e:
            print(f"Warning: Could not initialize Gemini model: {e}")
            self.model = None
        
        # Chat history for context
        self.chat_histories = {}  # Track conversations by session_id
        
        # System prompt for the chatbot
        self.system_prompt = """You are Shravan Shenoy's personal AI representative, designed to help recruiters and potential employers understand his background, skills, and experience.

Your personality should be:
- Professional yet approachable
- Knowledgeable about Shravan's background
- Enthusiastic about his work and achievements
- Honest and transparent about his experience level
- Helpful in answering questions about his capabilities

Key guidelines:
1. Always base your responses on the information available in the knowledge base
2. If you're unsure about something, say so rather than making assumptions
3. Highlight specific examples and achievements when relevant
4. Be conversational but maintain professionalism
5. Ask clarifying questions if needed to provide better answers
6. Show enthusiasm for Shravan's work and potential opportunities
7. Consider temporal context when discussing experiences - distinguish between current ongoing work and completed past projects

Remember: You are representing Shravan, so be authentic and honest about his experience level and capabilities."""

    def get_relevant_context(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Get relevant context from knowledge base for a query"""
        try:
            # For course queries, increase n_results to get more comprehensive coverage
            query_lower = query.lower()
            if any(word in query_lower for word in ['course', 'class', 'syllabus', 'assignment', 'project', 'academic', 'student']):
                n_results = max(n_results, 15)  # Get more chunks for course queries
            
            # Stage 1: Try enriched metadata search first (highest priority)
            enriched_results = self._search_with_enriched_metadata(query, n_results)
            if enriched_results:
                # Ensure org/role/timeline alignment if explicitly mentioned in the query
                enriched_results = self._ensure_organization_coverage(query, enriched_results, n_results)
                return enriched_results
            
            # Stage 2: Try semantic search as fallback
            results = self.knowledge_base.search(query, n_results)
            
            # Stage 3: If semantic search fails or returns irrelevant results, use intelligent routing
            if not results or not self._is_search_relevant(query, results):
                results = self._intelligent_document_routing(query, n_results)
            
            # Final guard: ensure org/role/timeline alignment if mentioned
            results = self._ensure_organization_coverage(query, results or [], n_results)
            return results if results else []
            
        except Exception as e:
            print(f"Error searching knowledge base: {e}")
            return []
    
    def _intelligent_document_routing(self, query: str, n_results: int) -> List[Dict[str, Any]]:
        """Intelligent routing to specific document types based on query analysis"""
        query_lower = query.lower()
        
        # Fallback to document-specific routing
        # Research-related queries
        if any(word in query_lower for word in ['research', 'paper', 'study', 'investigation']):
            if any(word in query_lower for word in ['iisc', 'indian institute', 'bangalore']):
                return self._search_in_specific_document("IISC", query, n_results)
            elif any(word in query_lower for word in ['tracker', 'current', 'ongoing', 'sam2']):
                return self._search_in_specific_document("Research Tracker", query, n_results)
            else:
                # General research - try both
                results = self._search_in_specific_document("IISC", query, n_results)
                if not results:
                    results = self._search_in_specific_document("Research Tracker", query, n_results)
                return results
        
        # Internship-related queries
        elif any(word in query_lower for word in ['internship', 'work experience', 'job', 'employment']):
            if 'netradyne' in query_lower:
                return self._search_in_specific_document("Internship Report", query, n_results)
            elif 'abb' in query_lower:
                return self._search_in_specific_document("ABB internship", query, n_results)
            else:
                # General internship - try both
                results = self._search_in_specific_document("internship", query, n_results)
                if not results:
                    results = self._search_in_specific_document("ABB", query, n_results)
                return results
        
        # Academic/coursework queries
        elif any(word in query_lower for word in ['course', 'class', 'syllabus', 'assignment', 'project']):
            # Fetch more chunks from courses CSV so multiple rows surface together
            return self._search_in_specific_document("courses", query, max(n_results, 15))
        
        # Business/racing queries
        elif any(word in query_lower for word in ['ashwa', 'racing', 'business', 'planning']):
            return self._search_in_specific_document("ASHWA", query, n_results)
        
        # If no specific routing, try broader search with fallback
        else:
            # Try semantic search again with more results
            results = self.knowledge_base.search(query, n_results * 2)
            if results:
                return results[:n_results]
            
            # Last resort: search in all documents
            return self.knowledge_base.get_all_documents()[:n_results]
    
    def _search_with_enriched_metadata(self, query: str, n_results: int) -> List[Dict[str, Any]]:
        """Search using enriched metadata for better relevance"""
        try:
            query_lower = query.lower()
            query_words = query_lower.split()
            query_has_abb = 'abb' in query_lower
            query_has_netradyne = 'netradyne' in query_lower
            query_has_iisc = 'iisc' in query_lower or 'indian institute' in query_lower
            query_has_drcl = 'drcl' in query_lower
            query_wants_current = any(w in query_lower for w in ['current', 'now', 'ongoing', 'present'])
            
            # Special handling for course-related queries
            query_is_course_related = any(word in query_lower for word in ['course', 'class', 'syllabus', 'assignment', 'project', 'academic', 'student'])
            
            # Get all documents with enriched metadata
            all_docs = self.knowledge_base.get_all_documents()
            scored_docs = []
            
            for doc in all_docs:
                metadata = doc.get('metadata', {})
                content = doc.get('content', '').lower()
                
                score = 0.0
                
                # Score based on document type (highest priority)
                doc_type = metadata.get('document_type', '')
                if doc_type:
                    # Exact matches get highest score
                    if any(word in doc_type.lower() for word in query_words):
                        score += 5.0
                    # Research queries should prioritize research documents
                    if 'research' in query_lower and doc_type == 'research':
                        score += 4.0
                    # Current work queries should prioritize current experience
                    if 'current' in query_lower and metadata.get('experience_type') == 'current':
                        score += 3.0
                    # SAM2 queries should heavily prioritize research documents
                    if 'sam2' in query_lower and doc_type == 'research':
                        score += 6.0
                    # Course queries should heavily prioritize academic documents
                    if query_is_course_related and doc_type == 'academic':
                        score += 12.0  # Increased from 8.0 to 12.0 for higher priority
                
                # Score based on semantic tags
                semantic_tags = metadata.get('semantic_tags', '')
                if semantic_tags and semantic_tags != 'none':
                    for tag in semantic_tags.split(', '):
                        if any(word in tag.lower() for word in query_words):
                            score += 2.5
                
                # Score based on skill domains
                skill_domains = metadata.get('skill_domains', '')
                if skill_domains and skill_domains != 'none':
                    for domain in skill_domains.split(', '):
                        if any(word in domain.lower() for word in query_words):
                            score += 2.0
                
                # Score based on technologies
                technologies = metadata.get('technologies', '')
                if technologies and technologies != 'none':
                    for tech in technologies.split(', '):
                        if any(word in tech.lower() for word in query_words):
                            score += 1.5
                
                # Score based on organizations (very high priority)
                organizations = metadata.get('organizations', '')
                if organizations and organizations != 'none':
                    for org in organizations.split(', '):
                        if any(word in org.lower() for word in query_words):
                            score += 4.0
                        # Special handling for IISc queries
                        if 'iisc' in query_lower or 'indian institute' in query_lower:
                            if 'iisc' in org.lower():
                                score += 6.0
                # Also consider singular organization field if present
                organization = metadata.get('organization', '')
                if organization:
                    org_l = organization.lower()
                    if query_has_abb and 'abb' in org_l:
                        score += 6.0
                    if query_has_netradyne and 'netradyne' in org_l:
                        score += 6.0
                    if query_has_iisc and 'iisc' in org_l:
                        score += 6.0
                    if query_has_drcl and 'drcl' in org_l:
                        score += 6.0
                # Content-based org detection (fallback when metadata is missing)
                if query_has_netradyne and 'netradyne' in content:
                    score += 6.0
                if query_has_abb and 'abb' in content:
                    score += 4.0
                if query_has_iisc and ('iisc' in content or 'indian institute of science' in content):
                    score += 5.0
                if query_has_drcl and 'drcl' in content:
                    score += 5.0
                
                # Score based on locations
                locations = metadata.get('locations', '')
                if locations and locations != 'none':
                    for location in locations.split(', '):
                        if any(word in location.lower() for word in query_words):
                            score += 2.0
                
                # Score based on content relevance
                relevance_keywords = metadata.get('relevance_keywords', '')
                if relevance_keywords and relevance_keywords != 'none':
                    for keyword in relevance_keywords.split(', '):
                        if any(word in keyword.lower() for word in query_words):
                            score += 1.0
                
                # Score based on experience type
                experience_type = metadata.get('experience_type', '')
                if 'current' in query_lower and experience_type == 'current':
                    score += 1.5
                elif 'past' in query_lower or 'previous' in query_lower and experience_type == 'completed':
                    score += 1.5
                
                # Score based on timeline information (your temporal context)
                timeline = metadata.get('timeline', {})
                if timeline and isinstance(timeline, dict):
                    start_date = timeline.get('start', '')
                    end_date = timeline.get('end', '')
                    duration = timeline.get('duration', '')
                    
                    # Current work queries should prioritize recent/ongoing work
                    if 'current' in query_lower:
                        if '2024' in start_date or '2025' in start_date:
                            score += 3.0
                        elif '2023' in start_date:
                            score += 1.5
                    
                    # Past work queries should prioritize completed work
                    if any(word in query_lower for word in ['past', 'previous', 'completed', 'finished']):
                        if '2023' in end_date or '2022' in end_date:
                            score += 2.0
                
                # Score based on role information (your temporal context)
                role = metadata.get('role', '')
                if role and role != 'N/A':
                    role_lower = role.lower()
                    
                    # Intern queries should prioritize intern roles
                    if 'intern' in query_lower and 'intern' in role_lower:
                        score += 4.0
                    
                    # Research queries should prioritize researcher roles
                    if 'research' in query_lower and any(word in role_lower for word in ['research', 'researcher', 'contributor']):
                        score += 3.0
                    
                    # Current work queries should prioritize current roles
                    if 'current' in query_lower and 'researcher' in role_lower:
                        score += 2.0
                
                # Score based on organization information (your temporal context)
                organization = metadata.get('organization', '')
                if organization and organization != 'N/A':
                    org_lower = organization.lower()
                    
                    # IISc queries should prioritize IISc organization
                    if 'iisc' in query_lower and 'iisc' in org_lower:
                        score += 5.0
                    
                    # ABB queries should prioritize ABB organization
                    if 'abb' in query_lower and 'abb' in org_lower:
                        score += 4.0
                    
                    # Netradyne queries should prioritize Netradyne organization
                    if 'netradyne' in query_lower and 'netradyne' in org_lower:
                        score += 4.0
                    
                    # DRCL queries should prioritize DRCL organization
                    if 'drcl' in query_lower and 'drcl' in org_lower:
                        score += 4.0
                
                # Score based on complexity and impact
                complexity_score = metadata.get('complexity_score', 0.0)
                impact_score = metadata.get('impact_score', 0.0)
                score += (complexity_score + impact_score) * 0.2
                
                # Content-based scoring as fallback
                content_score = sum(1 for word in query_words if word in content)
                score += content_score * 0.5
                
                # Special boost for SAM2 in research content
                if 'sam2' in query_lower and 'sam2' in content:
                    score += 8.0
                
                # Special boost for current work in current experience
                if 'current' in query_lower and metadata.get('experience_type') == 'current':
                    score += 2.0
                
                # Special boost for courses in academic documents
                if query_is_course_related and 'course' in content:
                    score += 3.0
                
                # Add document to scored list if it has any relevance
                if score > 0:
                    scored_docs.append({
                        'content': doc['content'],
                        'metadata': doc['metadata'],
                        'distance': 1.0 / (score + 1),  # Lower distance = more relevant
                        'score': score
                    })
            
            # Sort by score (highest first) and return top results
            scored_docs.sort(key=lambda x: x['score'], reverse=True)
            
            # Debug: Print top 5 scores for course queries
            if query_is_course_related:
                print(f"\nDEBUG: Top 5 scores for course query '{query}':")
                for i, doc in enumerate(scored_docs[:5]):
                    filename = doc['metadata'].get('filename', 'N/A')
                    doc_type = doc['metadata'].get('document_type', 'N/A')
                    print(f"  {i+1}. {filename} (type: {doc_type}) - Score: {doc['score']:.2f}")
            
            return scored_docs[:n_results]
            
        except Exception as e:
            print(f"Error in enriched metadata search: {e}")
            return []

    def _ensure_organization_coverage(self, query: str, results: List[Dict[str, Any]], n_results: int) -> List[Dict[str, Any]]:
        """If query mentions specific organizations or roles, ensure at least one matching doc is present.
        Keeps existing order, appends a best-match if missing (up to n_results)."""
        try:
            q = query.lower()
            requested_orgs: List[str] = []
            if 'abb' in q:
                requested_orgs.append('abb')
            if 'netradyne' in q:
                requested_orgs.append('netradyne')
            if 'iisc' in q or 'indian institute' in q:
                requested_orgs.append('iisc')
            if 'drcl' in q:
                requested_orgs.append('drcl')

            if not requested_orgs:
                return results

            present = set()
            for r in results:
                md = r.get('metadata', {})
                org = (md.get('organization') or '').lower()
                content_l = r.get('content', '').lower()
                for want in requested_orgs:
                    if want in org or want in content_l:
                        present.add(want)

            missing = [o for o in requested_orgs if o not in present]
            if not missing or len(results) >= n_results:
                return results

            # Find candidates from all docs
            all_docs = self.knowledge_base.get_all_documents()
            for miss in missing:
                best = None
                best_score = -1.0
                for doc in all_docs:
                    md = doc.get('metadata', {})
                    org = (md.get('organization') or '').lower()
                    content_l = doc.get('content', '').lower()
                    if miss in org or miss in content_l:
                        # simple heuristic: prefer higher impact/complexity
                        score = float(md.get('impact_score', 0.0)) + float(md.get('complexity_score', 0.0))
                        if score > best_score:
                            best = doc
                            best_score = score
                if best:
                    # Append if not already included and space remains
                    if len(results) < n_results:
                        results.append(best)
            return results[:n_results]
        except Exception as e:
            print(f"Error ensuring organization coverage: {e}")
            return results
    
    def _is_search_relevant(self, query: str, results: List[Dict[str, Any]]) -> bool:
        """Check if search results are relevant to the query"""
        query_lower = query.lower()
        
        # Check if results contain the expected document types
        for result in results:
            filename = result['metadata'].get('filename', '').lower()
            content = result['content'].lower()
            
            # For research questions, check if we have research content
            if 'research' in query_lower and ('research tracker' in filename or 'iisc' in filename or 'research' in content.lower()):
                return True
            
            # For internship questions, check if we have internship content
            if 'internship' in query_lower and ('internship' in filename or 'abb' in filename or 'netradyne' in content.lower()):
                return True
            
            # For racing questions, check if we have racing content
            if ('ashwa' in query_lower or 'racing' in query_lower) and 'ashwa' in filename:
                return True
            
            # For general queries, be more lenient - if content contains query terms, consider it relevant
            query_words = query_lower.split()
            content_relevance = sum(1 for word in query_words if word in content.lower())
            if content_relevance >= 2:  # At least 2 query words found in content
                return True
        
        return False
    
    def get_temporal_context_info(self, query: str) -> str:
        """Get temporal context information for a query"""
        try:
            # Search for relevant documents
            results = self.get_relevant_context(query, n_results=3)
            
            if not results:
                return "No temporal context information available."
            
            # Extract temporal information
            temporal_info = []
            for result in results:
                temporal_context = result['metadata'].get('temporal_context', {})
                if temporal_context:
                    filename = result['metadata'].get('filename', 'Unknown')
                    experience_type = temporal_context.get('experience_type', 'unknown')
                    time_period = temporal_context.get('time_period', 'unknown')
                    status = temporal_context.get('status', 'unknown')
                    current = temporal_context.get('current', False)
                    
                    temporal_info.append(f"• {filename}: {experience_type} ({time_period}, {status}, Current: {current})")
            
            if temporal_info:
                return "Temporal Context:\n" + "\n".join(temporal_info)
            else:
                return "No temporal context information available."
                
        except Exception as e:
            return f"Error getting temporal context: {e}"
    
    def _search_in_specific_document(self, document_pattern: str, query: str, n_results: int) -> List[Dict[str, Any]]:
        """Search for content in a specific document type"""
        try:
            # Get all documents and filter by filename pattern
            all_docs = self.knowledge_base.get_all_documents()
            filtered_docs = []
            
            for doc in all_docs:
                filename = doc['metadata'].get('filename', '')
                if document_pattern.lower() in filename.lower():
                    filtered_docs.append(doc)
            
            # If we found matching documents, search within them
            if filtered_docs:
                # Enhanced search with temporal context consideration
                relevant_docs = []
                q_lower = query.lower()
                query_words = q_lower.split()
                
                for doc in filtered_docs:
                    content_lower = doc['content'].lower()
                    relevance_score = sum(1 for word in query_words if word in content_lower)
                    
                    # Special handling for courses: include rows even with low match so we return multiple courses
                    if 'courses' in document_pattern.lower():
                        # Boost completed/graded rows and rows with course codes
                        if any(x in content_lower for x in ['completed', 'grade', 'csci', 'cs231n', 'assignment', 'project']):
                            relevance_score += 3
                        # Ensure inclusion even if minimal match
                        if relevance_score == 0:
                            relevance_score = 1
                    
                    # Boost relevance based on temporal context
                    temporal_context = doc['metadata'].get('temporal_context', {})
                    if temporal_context:
                        # Boost current/recent work for "current" queries
                        if 'current' in q_lower and temporal_context.get('current', False):
                            relevance_score += 3
                        elif 'current' in q_lower and temporal_context.get('time_period') == 'current':
                            relevance_score += 2
                        
                        # Boost research work for research queries
                        if 'research' in q_lower and temporal_context.get('experience_type') == 'research':
                            relevance_score += 2
                        
                        # Boost internship work for internship queries
                        if 'internship' in q_lower and temporal_context.get('experience_type') == 'internship':
                            relevance_score += 2
                
                    if relevance_score > 0:
                        relevant_docs.append({
                            'content': doc['content'],
                            'metadata': doc['metadata'],
                            'distance': 1.0 / (relevance_score + 1)  # Lower distance = more relevant
                        })
                
                # Sort by relevance and return top results
                relevant_docs.sort(key=lambda x: x['distance'])
                return relevant_docs[:n_results]
            
            return []
        except Exception as e:
            print(f"Error in document-specific search: {e}")
            return []
    
    def generate_response(self, user_message: str, session_id: str = "default", conversation_history: List[Dict] = None) -> str:
        """Generate a response based on user message and conversation context"""
        if not self.model:
            return "I apologize, but I'm experiencing technical difficulties. Please check your API configuration and try again."
        
        # Get relevant context from knowledge base
        relevant_context = self.get_relevant_context(user_message)
        
        # Prepare conversation history
        if conversation_history is None:
            conversation_history = self.chat_histories.get(session_id, [])
        
        # Create context string from relevant documents
        context_string = ""
        if relevant_context:
            context_string = "Relevant information from Shravan's background:\n\n"
            for i, result in enumerate(relevant_context):
                # Include temporal context if available
                md = result.get('metadata', {})
                org = md.get('organization') or md.get('organizations')
                role = md.get('role')
                timeline = md.get('timeline')
                # Heuristic org detection from content when metadata is incomplete
                detected_orgs = []
                content_l = result.get('content', '').lower()
                if 'netradyne' in content_l and (not org or 'netradyne' not in str(org).lower()):
                    detected_orgs.append('Netradyne')
                if 'abb' in content_l and (not org or 'abb' not in str(org).lower()):
                    detected_orgs.append('ABB')
                if ('iisc' in content_l or 'indian institute of science' in content_l) and (not org or 'iisc' not in str(org).lower()):
                    detected_orgs.append('IISc')
                why_bits = []
                if org:
                    why_bits.append(f"Org: {org}")
                if detected_orgs:
                    why_bits.append(f"DetectedOrg: {', '.join(detected_orgs)}")
                if role:
                    why_bits.append(f"Role: {role}")
                if timeline:
                    why_bits.append(f"Timeline: {timeline}")
                why = f" ({' | '.join(why_bits)})" if why_bits else ""
                context_string += f"Source {i+1}{why}:\n{result['content']}\n\n"
        
        # Prepare conversation context for Gemini
        conversation_context = f"{self.system_prompt}\n\n"
        conversation_context += f"Use this context to inform your response:\n{context_string}\n\n"
        
        # Add conversation history (limit to last few exchanges for context)
        if conversation_history:
            conversation_context += "Recent conversation context:\n"
            for msg in conversation_history[-6:]:  # Last 3 exchanges
                conversation_context += f"{msg['role']}: {msg['content']}\n"
        
        # Add current user message
        conversation_context += f"\nUser: {user_message}\n\n"
        conversation_context += "Please respond as Shravan's AI representative:"
        
        try:
            response = self.model.generate_content(conversation_context)
            ai_response = response.text
            
            # Update conversation history
            if session_id not in self.chat_histories:
                self.chat_histories[session_id] = []
            
            self.chat_histories[session_id].extend([
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": ai_response}
            ])
            
            # Keep history manageable
            if len(self.chat_histories[session_id]) > 20:
                self.chat_histories[session_id] = self.chat_histories[session_id][-20:]
            
            return ai_response
            
        except Exception as e:
            error_msg = f"I apologize, but I'm experiencing technical difficulties. Please try again later. Error: {str(e)}"
            print(f"Error generating response: {e}")
            return error_msg
    
    def handle_specific_questions(self, query: str) -> Optional[str]:
        """Handle specific types of questions with structured responses"""
        query_lower = query.lower()
        
        # Skills questions
        if any(word in query_lower for word in ['skill', 'technology', 'programming', 'language', 'framework']):
            return self._handle_skills_question(query)
        
        # Experience questions
        if any(word in query_lower for word in ['experience', 'work', 'job', 'project', 'role']):
            return self._handle_experience_question(query)
        
        # Education questions
        if any(word in query_lower for word in ['education', 'degree', 'university', 'college', 'course']):
            return self._handle_education_question(query)
        
        # Availability questions
        if any(word in query_lower for word in ['available', 'start date', 'when can you', 'timeline']):
            return self._handle_availability_question(query)
        
        return None
    
    def _handle_skills_question(self, query: str) -> str:
        """Handle questions about skills and technologies"""
        # Search for skills-related information
        skills_context = self.get_relevant_context("skills technologies programming languages frameworks", n_results=3)
        
        if skills_context:
            response = "Based on my knowledge of Shravan's background, here are his key skills:\n\n"
            for i, context in enumerate(skills_context):
                response += f"• {context['content'][:200]}...\n\n"
            return response
        else:
            return "I'd be happy to discuss Shravan's skills! Could you be more specific about which area you're interested in?"
    
    def _handle_experience_question(self, query: str) -> str:
        """Handle questions about work experience"""
        experience_context = self.get_relevant_context("work experience job role project", n_results=3)
        
        if experience_context:
            response = "Here's what I know about Shravan's experience:\n\n"
            for i, context in enumerate(experience_context):
                response += f"• {context['content'][:200]}...\n\n"
            return response
        else:
            return "I'd love to tell you about Shravan's experience! What specific aspect would you like to know more about?"
    
    def _handle_education_question(self, query: str) -> str:
        """Handle questions about education"""
        education_context = self.get_relevant_context("education degree university college course", n_results=2)
        
        if education_context:
            response = "Here's Shravan's educational background:\n\n"
            for i, context in enumerate(education_context):
                response += f"• {context['content'][:200]}...\n\n"
            return response
        else:
            return "I'd be happy to discuss Shravan's education! What would you like to know?"
    
    def _handle_availability_question(self, query: str) -> str:
        """Handle questions about availability and timeline"""
        return ("I'd be happy to discuss Shravan's availability and timeline! However, for specific scheduling and availability questions, "
                "it would be best to connect directly with him. I can tell you about his current situation and general timeline, "
                "but for detailed planning, a direct conversation would be more helpful.")
    
    def get_conversation_summary(self, session_id: str = "default") -> str:
        """Generate a summary of the conversation"""
        if session_id not in self.chat_histories:
            return "No conversation history found."
        
        history = self.chat_histories[session_id]
        if not history:
            return "No conversation history found."
        
        if not self.model:
            return "Error: Gemini model not initialized. Please check your API key."
        
        # Create summary prompt
        summary_prompt = f"""Summarize this conversation between a recruiter and Shravan's AI representative:

{json.dumps(history, indent=2)}

Provide a brief summary highlighting:
1. Key topics discussed
2. Questions asked by the recruiter
3. Information shared about Shravan
4. Any follow-up actions needed

Keep it concise and professional:"""

        try:
            response = self.model.generate_content(summary_prompt)
            return response.text
            
        except Exception as e:
            return f"Could not generate summary due to technical error: {str(e)}"
    
    def clear_conversation_history(self, session_id: str = "default"):
        """Clear conversation history for a session"""
        if session_id in self.chat_histories:
            del self.chat_histories[session_id]
            print(f"Cleared conversation history for session: {session_id}")
        else:
            print(f"No conversation history found for session: {session_id}")
    
    def get_chatbot_stats(self) -> Dict[str, Any]:
        """Get statistics about chatbot usage"""
        stats = {
            'total_sessions': len(self.chat_histories),
            'total_conversations': sum(len(history) for history in self.chat_histories.values()),
            'knowledge_base_stats': self.knowledge_base.get_statistics(),
            'active_since': datetime.now().isoformat()
        }
        return stats
    
    def export_conversation(self, session_id: str = "default", filename: str = None) -> str:
        """Export conversation history to file"""
        if session_id not in self.chat_histories:
            return "No conversation history found for this session."
        
        if filename is None:
            filename = f"conversation_export_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        export_data = {
            'session_id': session_id,
            'export_date': datetime.now().isoformat(),
            'conversation': self.chat_histories[session_id],
            'summary': self.get_conversation_summary(session_id)
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        print(f"Conversation exported to: {filename}")
        return filename
