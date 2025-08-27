#!/usr/bin/env python3
import json
import datetime
from knowledge_base import KnowledgeBase
import google.generativeai as genai
from config import Config
from typing import List, Dict

class DailyUpdater:
    def __init__(self):
        self.knowledge_base = KnowledgeBase()
        
        # Initialize Gemini for smart categorization
        genai.configure(api_key=Config.GOOGLE_API_KEY)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        # Load existing projects
        self.existing_projects = self._get_existing_projects()
    
    def _get_existing_projects(self):
        """Get list of existing projects from knowledge base"""
        try:
            all_docs = self.knowledge_base.get_all_documents()
            projects = set()
            
            for doc in all_docs:
                metadata = doc.get('metadata', {})
                title = metadata.get('title', '')
                if title and title != 'N/A' and title not in ['Career Knowledge Base - Courses', 'Career Knowledge Base: Coursework']:
                    projects.add(title)
            
            return list(projects)
        except Exception as e:
            print(f"Error loading projects: {e}")
            return []
    
    def add_daily_update(self, daily_text: str, project_title: str = None):
        """Add a daily update to the knowledge base"""
        try:
            now = datetime.datetime.now()
            date_str = now.strftime('%Y-%m-%d')
            
            # If no project specified, try to auto-categorize
            if not project_title:
                project_title = self._auto_categorize(daily_text)
            
            # Get clarifying answers
            clarifications = self._get_clarifying_answers(daily_text, project_title)
            
            # Create enhanced content with clarifications
            content = f"""
            Daily Update - {date_str}
            Project: {project_title}
            
            {daily_text}
            """
            
            # Add clarifications if any
            if clarifications:
                content += "\n\nClarifications:\n"
                for key, answer in clarifications.items():
                    if answer != "Not specified":
                        content += f"• {answer}\n"
            
            content += f"""
            
            Entry Type: Daily Progress Update
            Timestamp: {now.isoformat()}
            """
            
            # Enhanced metadata with clarifications
            metadata = {
                'source': 'daily_update',
                'filename': f"daily_update_{date_str}",
                'document_type': 'daily_update',
                'project_title': project_title,
                'date': date_str,
                'entry_type': 'daily_update',
                'processed_at': now.isoformat()
            }
            
            # Add clarification metadata
            for key, value in clarifications.items():
                if value != "Not specified":
                    metadata[key] = value
            
            # Add to knowledge base
            self.knowledge_base.add_documents([{'content': content, 'metadata': metadata}])
            
            print(f"✅ Daily update added to: {project_title}")
            if clarifications:
                print(f"💡 Enhanced with {len([v for v in clarifications.values() if v != 'Not specified'])} clarifications")
            return True
            
        except Exception as e:
            print(f"❌ Error adding daily update: {e}")
            return False
    
    def _auto_categorize(self, daily_text: str):
        """Auto-categorize daily update into existing project or create new one"""
        try:
            if not self.existing_projects:
                return self._create_new_project(daily_text)
            
            # Create simple categorization prompt
            projects_str = "\n".join([f"- {p}" for p in self.existing_projects[:15]])
            
            prompt = f"""
            Given this daily work update, which existing project does it belong to?
            
            EXISTING PROJECTS:
            {projects_str}
            
            DAILY UPDATE:
            {daily_text}
            
            Return ONLY the exact project title from the list above, or "NEW_PROJECT" if this represents a completely new project/initiative.
            """
            
            response = self.model.generate_content(prompt)
            project = response.text.strip()
            
            # Validate the response
            if project in self.existing_projects:
                return project
            elif project == "NEW_PROJECT":
                return self._create_new_project(daily_text)
            else:
                return self._create_new_project(daily_text)
                
        except Exception as e:
            print(f"Auto-categorization failed: {e}")
            return self._create_new_project(daily_text)
    
    def _create_new_project(self, daily_text: str):
        """Create a new project based on the daily update content"""
        try:
            prompt = f"""
            Based on this daily work update, create a concise, professional project title.
            
            DAILY UPDATE:
            {daily_text}
            
            Create a project title that:
            1. Is 3-8 words long
            2. Describes the main initiative or work area
            3. Is professional and resume-ready
            4. Captures the essence of what this work represents
            
            Return ONLY the project title, nothing else.
            """
            
            response = self.model.generate_content(prompt)
            new_project_title = response.text.strip()
            
            # Clean up the title
            new_project_title = new_project_title.replace('"', '').replace("'", "")
            
            print(f"🆕 Creating new project: {new_project_title}")
            
            # Add to existing projects list
            self.existing_projects.append(new_project_title)
            
            return new_project_title
            
        except Exception as e:
            print(f"Error creating new project: {e}")
            # Fallback to a generic title based on date
            now = datetime.datetime.now()
            return f"New Project - {now.strftime('%B %Y')}"
    
    def _generate_clarifying_questions(self, daily_text: str, project_title: str) -> List[str]:
        """Generate clarifying questions to extract deeper insights"""
        try:
            prompt = f"""
            Based on this daily update, generate 2-4 clarifying questions to extract deeper insights.
            
            DAILY UPDATE:
            {daily_text}
            
            PROJECT: {project_title}
            
            Generate questions that will help understand:
            1. Specific technologies/tools used
            2. Quantifiable achievements or metrics
            3. Challenges overcome
            4. Skills demonstrated
            5. Business impact or learning outcomes
            
            Return ONLY the questions, one per line, starting with "Q: ". If no clarification is needed, return "NO_QUESTIONS".
            
            Example format:
            Q: What specific programming languages or frameworks did you use?
            Q: Can you quantify the performance improvement (e.g., speed, accuracy)?
            Q: What was the main challenge you faced and how did you solve it?
            """
            
            response = self.model.generate_content(prompt)
            questions_text = response.text.strip()
            
            if "NO_QUESTIONS" in questions_text:
                return []
            
            # Parse questions
            questions = []
            for line in questions_text.split('\n'):
                line = line.strip()
                if line.startswith('Q: '):
                    questions.append(line[3:])  # Remove "Q: " prefix
            
            return questions[:4]  # Limit to 4 questions
            
        except Exception as e:
            print(f"Error generating clarifying questions: {e}")
            return []
    
    def _get_clarifying_answers(self, daily_text: str, project_title: str) -> Dict[str, str]:
        """Get clarifying answers from user"""
        questions = self._generate_clarifying_questions(daily_text, project_title)
        
        if not questions:
            print("✅ No clarifying questions needed for this update.")
            return {}
        
        print(f"\n🔍 Clarifying Questions for: {project_title}")
        print("=" * 50)
        
        answers = {}
        for i, question in enumerate(questions, 1):
            print(f"\nQ{i}: {question}")
            answer = input("Your answer (press Enter to skip): ").strip()
            if answer:
                answers[f"clarification_{i}"] = answer
            else:
                answers[f"clarification_{i}"] = "Not specified"
        
        return answers
    
    def list_projects(self):
        """List all available projects"""
        print("\n📋 Available Projects:")
        for i, project in enumerate(self.existing_projects, 1):
            print(f"{i}. {project}")
        print(f"{len(self.existing_projects) + 1}. Create New Project")
    
    def get_recent_updates(self, days: int = 7):
        """Get recent daily updates"""
        try:
            query = "daily update"
            results = self.knowledge_base.search(query, n_results=50)
            
            recent_updates = []
            cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)
            
            for result in results:
                metadata = result.get('metadata', {})
                if metadata.get('entry_type') == 'daily_update':
                    date_str = metadata.get('date', '')
                    try:
                        update_date = datetime.datetime.strptime(date_str, '%Y-%m-%d')
                        if update_date >= cutoff_date:
                            # Extract clarifications from metadata
                            clarifications = []
                            for key, value in metadata.items():
                                if key.startswith('clarification_') and value != 'Not specified':
                                    clarifications.append(value)
                            
                            recent_updates.append({
                                'date': date_str,
                                'project': metadata.get('project_title', 'Unknown'),
                                'content': result.get('content', '')[:200] + '...',
                                'clarifications': clarifications
                            })
                    except:
                        continue
            
            # Sort by date
            recent_updates.sort(key=lambda x: x['date'], reverse=True)
            
            return recent_updates
            
        except Exception as e:
            print(f"Error getting recent updates: {e}")
            return []

def main():
    """Simple daily update interface"""
    updater = DailyUpdater()
    
    print("🚀 Daily Update System")
    print("=" * 40)
    
    while True:
        print("\nOptions:")
        print("1. Add daily update")
        print("2. List projects")
        print("3. View recent updates")
        print("4. Exit")
        
        choice = input("\nChoice (1-4): ").strip()
        
        if choice == "1":
            print("\n📝 Enter your daily update:")
            daily_text = input("> ").strip()
            
            if daily_text:
                updater.list_projects()
                project_choice = input("\nSelect project number (or press Enter for auto-categorization): ").strip()
                
                if project_choice.isdigit():
                    idx = int(project_choice) - 1
                    if 0 <= idx < len(updater.existing_projects):
                        project_title = updater.existing_projects[idx]
                    elif idx == len(updater.existing_projects):
                        # Create New Project option
                        project_title = updater._create_new_project(daily_text)
                    else:
                        project_title = None
                else:
                    project_title = None
                
                updater.add_daily_update(daily_text, project_title)
            else:
                print("❌ No text entered")
        
        elif choice == "2":
            updater.list_projects()
        
        elif choice == "3":
            updates = updater.get_recent_updates(7)
            if updates:
                print(f"\n📅 Recent Updates (Last 7 days):")
                for update in updates[:10]:
                    print(f"\n  {update['date']} - {update['project']}")
                    print(f"    {update['content']}")
                    if update['clarifications']:
                        print("    Clarifications:")
                        for clarification in update['clarifications']:
                            print(f"      - {clarification}")
            else:
                print("❌ No recent updates found")
        
        elif choice == "4":
            print("👋 Goodbye!")
            break
        
        else:
            print("❌ Invalid choice")

if __name__ == "__main__":
    main()
