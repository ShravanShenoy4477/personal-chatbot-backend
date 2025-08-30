#!/usr/bin/env python3
"""
Ingest Courses Separately
Process courses_template.csv to create individual JSON objects for each course
instead of collapsing them into one combined object
"""

import os
import json
import csv
from pathlib import Path
from datetime import datetime

def ingest_courses_separately():
    """Ingest each course from CSV as a separate JSON object"""
    print("🚀 INGESTING COURSES AS SEPARATE OBJECTS")
    print("=" * 60)
    
    # Paths
    csv_file = Path("documents/courses_template.csv")
    output_dir = Path("structured_summaries")
    output_dir.mkdir(exist_ok=True)
    
    if not csv_file.exists():
        print(f"❌ CSV file not found: {csv_file}")
        return False
    
    try:
        # Read CSV file
        print(f"📄 Reading CSV file: {csv_file}")
        courses = []
        
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                courses.append(row)
        
        print(f"✅ Found {len(courses)} courses in CSV")
        
        # Process each course separately
        for i, course in enumerate(courses, 1):
            print(f"\n🔧 Processing course {i}/{len(courses)}: {course['course_name']}")
            
            # Create course-specific metadata
            course_data = {
                "title": course['course_name'],
                "course_code": course['course_code'],
                "institution": course['institution'],
                "category": course['category'],
                "delivery_mode": course['delivery_mode'],
                "credit_type": course['credit_type'],
                "level": course['level'],
                "term": course['term'],
                "year": course['year'],
                "status": course['status'],
                "credits": course['credits'],
                "instructor": course['instructor'],
                "workload_hrs": course['workload_hrs'],
                "grade": course['grade'],
                "proof_link": course['proof_link'],
                "role": _get_role_for_category(course['category']),
                "timeline": {
                    "start": f"{course['term']} {course['year']}",
                    "end": course['status'],
                    "duration": _calculate_duration(course['term'], course['year'], course['status'])
                },
                "objectives": course['course_description'],
                "responsibilities": _extract_responsibilities(course['projects_assignments']),
                "technologies": _extract_technologies(course['skills_covered']),
                "achievements": _extract_achievements(course['projects_assignments']),
                "skills": {
                    "technical": _parse_skills_list(course['skills_covered']),
                    "soft": _get_soft_skills_for_category(course['category'])
                },
                "notes": course['notes'],
                "challenges": [],
                "missing_fields": [],
                "clarifying_questions": []
            }
            
            # Add category-specific context
            if course['category'] == 'University':
                course_data["organization"] = course['institution']
                course_data["location"] = "Los Angeles, CA" if "USC" in course['institution'] else "Stanford, CA"
                course_data["experience_type"] = "formal_coursework"
                course_data["temporal_context"] = "current" if course['status'] == 'ongoing' else "past"
            elif course['category'] == 'Online':
                course_data["organization"] = course['institution']
                course_data["location"] = "Online"
                course_data["experience_type"] = "supplementary_learning"
                course_data["temporal_context"] = "current" if course['status'] == 'ongoing' else "past"
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{course['course_code']}_{course['course_name'].replace(' ', '_')}_{timestamp}.json"
            filename = filename.replace('/', '_').replace('\\', '_')  # Clean filename
            
            # Save individual course JSON
            output_file = output_dir / filename
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(course_data, f, indent=2, ensure_ascii=False)
            
            print(f"   ✅ Saved: {filename}")
        
        print(f"\n�� SUCCESS: Created {len(courses)} separate course JSON files")
        print(f"📁 Output directory: {output_dir}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error processing courses: {e}")
        import traceback
        traceback.print_exc()
        return False

def _get_role_for_category(category):
    """Get appropriate role based on course category"""
    if category == 'University':
        return 'Graduate Student'
    elif category == 'Online':
        return 'Self-paced Learner'
    else:
        return 'Student'

def _calculate_duration(term, year, status):
    """Calculate duration based on term and status"""
    if status == 'ongoing':
        return 'Ongoing'
    elif status == 'completed':
        return '1 semester'
    else:
        return 'Self-paced'

def _extract_responsibilities(projects_json):
    """Extract responsibilities from projects/assignments JSON"""
    try:
        if not projects_json or projects_json == 'N/A':
            return ["Complete course requirements", "Attend lectures", "Submit assignments"]
        
        projects = json.loads(projects_json)
        responsibilities = []
        
        for project in projects:
            if isinstance(project, dict) and 'actions' in project:
                responsibilities.append(project['actions'])
        
        return responsibilities if responsibilities else ["Complete course requirements"]
        
    except (json.JSONDecodeError, TypeError):
        return ["Complete course requirements", "Attend lectures", "Submit assignments"]

def _extract_technologies(skills_json):
    """Extract technologies from skills covered"""
    try:
        if not skills_json or skills_json == 'N/A':
            return []
        
        # Skills are semicolon-separated
        skills = [skill.strip() for skill in skills_json.split(';')]
        return [skill for skill in skills if skill]
        
    except (AttributeError, TypeError):
        return []

def _extract_achievements(projects_json):
    """Extract achievements from projects/assignments JSON"""
    try:
        if not projects_json or projects_json == 'N/A':
            return ["Completed course requirements", "Gained knowledge in subject area"]
        
        projects = json.loads(projects_json)
        achievements = []
        
        for project in projects:
            if isinstance(project, dict) and 'outcome' in project:
                achievements.append(project['outcome'])
        
        return achievements if achievements else ["Completed course requirements"]
        
    except (json.JSONDecodeError, TypeError):
        return ["Completed course requirements", "Gained knowledge in subject area"]

def _parse_skills_list(skills_str):
    """Parse skills string into list"""
    try:
        if not skills_str or skills_str == 'N/A':
            return []
        
        # Skills are semicolon-separated
        skills = [skill.strip() for skill in skills_str.split(';')]
        return [skill for skill in skills if skill]
        
    except (AttributeError, TypeError):
        return []

def _get_soft_skills_for_category(category):
    """Get soft skills based on course category"""
    base_skills = ["Problem Solving", "Analytical Thinking", "Time Management"]
    
    if category == 'University':
        base_skills.extend(["Academic Writing", "Research Skills", "Collaboration"])
    elif category == 'Online':
        base_skills.extend(["Self-motivation", "Independent Learning", "Focus"])
    
    return base_skills

def show_course_summary():
    """Show summary of created course files"""
    print("\n📋 COURSE INGESTION SUMMARY")
    print("=" * 60)
    
    output_dir = Path("structured_summaries")
    course_files = list(output_dir.glob("*course*"))
    
    if not course_files:
        print("❌ No course files found")
        return
    
    print(f"Found {len(course_files)} course files:")
    
    for i, file_path in enumerate(course_files, 1):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            category = data.get('category', 'Unknown')
            status = data.get('status', 'Unknown')
            print(f"   {i}. {data.get('course_code', 'N/A')} - {data.get('title', 'Unknown')}")
            print(f"      Category: {category}, Status: {status}")
            
        except Exception as e:
            print(f"   {i}. Error reading {file_path.name}: {e}")

if __name__ == "__main__":
    print("🚀 Starting Course Ingestion...")
    
    # Ingest courses
    success = ingest_courses_separately()
    
    if success:
        # Show summary
        show_course_summary()
        
        print("\n" + "=" * 80)
        print("🎯 COURSE INGESTION COMPLETED SUCCESSFULLY!")
        print("=" * 80)
        print("✅ Each course now has its own JSON object")
        print("✅ Category distinction preserved (University vs Online)")
        print("✅ All metadata fields maintained")
        print("✅ Proper temporal context for each course")
        print("\n📋 Next steps:")
        print("1. Review the generated course JSON files")
        print("2. Re-ingest to Qdrant with separate course objects")
        print("3. Test chatbot queries for individual courses")
    else:
        print("❌ Course ingestion failed. Check the output above for details.")
