from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json
import uuid
from datetime import datetime
import os

from config import Config
from chatbot import PersonalChatbot
from knowledge_base import KnowledgeBase
try:
    from resume_generator import ResumeGenerator
except Exception:
    ResumeGenerator = None  # Optional in production

# Initialize FastAPI app
app = FastAPI(
    title="Shravan's Personal AI Assistant",
    description="AI-powered chatbot representing Shravan Shenoy's experience and skills",
    version="1.0.0"
)

# CORS (allow GitHub Pages frontend)
try:
    from fastapi.middleware.cors import CORSMiddleware
    allowed_origins = [
        "*",  # Replace with your exact site for tighter security, e.g., "https://shravanshenoy4477.github.io"
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
except Exception:
    pass

# Initialize components
config = Config()
chatbot = PersonalChatbot()
knowledge_base = KnowledgeBase()
resume_generator = ResumeGenerator() if ResumeGenerator is not None else None

# Mount static files and templates
templates = Jinja2Templates(directory="templates")

# Pydantic models for API requests
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str
    timestamp: str

class ResumeRequest(BaseModel):
    job_description: str
    user_info: Dict[str, str]

class DailyUpdateRequest(BaseModel):
    update_text: str
    category: Optional[str] = "daily_update"

# API Routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page with chatbot interface"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    """Chat interface page"""
    return templates.TemplateResponse("chat.html", {"request": request})

@app.get("/resume", response_class=HTMLResponse)
async def resume_page(request: Request):
    """Resume generator page"""
    if resume_generator is None:
        return templates.TemplateResponse("chat.html", {"request": request})
    return templates.TemplateResponse("resume.html", {"request": request})

@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    """Admin panel for managing knowledge base"""
    return templates.TemplateResponse("admin.html", {"request": request})

# API Endpoints
@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Chat with the AI assistant"""
    try:
        # Generate session ID if not provided
        session_id = request.session_id or str(uuid.uuid4())
        
        # Generate response
        response = chatbot.generate_response(
            user_message=request.message,
            session_id=session_id
        )
        
        return ChatResponse(
            response=response,
            session_id=session_id,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

@app.post("/api/resume/generate")
async def generate_resume(request: ResumeRequest):
    """Generate tailored resume"""
    if resume_generator is None:
        raise HTTPException(status_code=501, detail="Resume generation not available in this deployment")
    try:
        resume_data = resume_generator.generate_tailored_resume(
            job_description=request.job_description,
            user_info=request.user_info
        )
        
        if resume_data and 'error' not in resume_data:
            # Save resume
            filename = resume_generator.save_resume(resume_data)
            
            return {
                "success": True,
                "resume": resume_data,
                "filename": filename,
                "formatted_resume": resume_generator.format_resume_for_display(resume_data)
            }
        else:
            return {
                "success": False,
                "error": resume_data.get('error', 'Unknown error')
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Resume generation error: {str(e)}")

@app.post("/api/resume/cover-letter")
async def generate_cover_letter(request: ResumeRequest):
    """Generate cover letter"""
    if resume_generator is None:
        raise HTTPException(status_code=501, detail="Cover letter generation not available in this deployment")
    try:
        # First generate resume to get context
        resume_data = resume_generator.generate_tailored_resume(
            job_description=request.job_description,
            user_info=request.user_info
        )
        
        if resume_data and 'error' not in resume_data:
            cover_letter = resume_generator.generate_cover_letter(
                job_description=request.job_description,
                resume_data=resume_data
            )
            
            # Save cover letter
            filename = resume_generator.save_cover_letter(cover_letter)
            
            return {
                "success": True,
                "cover_letter": cover_letter,
                "filename": filename
            }
        else:
            return {
                "success": False,
                "error": resume_data.get('error', 'Unknown error')
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cover letter generation error: {str(e)}")

@app.post("/api/daily-update")
async def add_daily_update(request: DailyUpdateRequest):
    """Add daily update to knowledge base"""
    try:
        update_chunk = chatbot.knowledge_base.add_documents([{
            'content': request.update_text,
            'metadata': {
                'source': 'daily_update',
                'filename': f"daily_update_{datetime.now().strftime('%Y%m%d')}",
                'file_type': 'daily_update',
                'category': request.category,
                'date': datetime.now().isoformat(),
                'chunk_index': 0,
                'total_chunks': 1,
                'token_count': len(request.update_text.split())
            }
        }])
        
        return {
            "success": True,
            "message": "Daily update added successfully",
            "update": update_chunk
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Daily update error: {str(e)}")

@app.get("/api/stats")
async def get_stats():
    """Get system statistics"""
    try:
        return {
            "chatbot_stats": chatbot.get_chatbot_stats(),
            "knowledge_base_stats": knowledge_base.get_statistics(),
            "system_info": {
                "version": "1.0.0",
                "status": "active",
                "last_updated": datetime.now().isoformat()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stats error: {str(e)}")

@app.get("/api/search")
async def search_knowledge_base(query: str, n_results: int = 5):
    """Search knowledge base using intelligent context retrieval"""
    try:
        # Use the chatbot's intelligent context retrieval instead of basic search
        results = chatbot.get_relevant_context(query, n_results)
        return {
            "query": query,
            "results": results,
            "total_results": len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")

@app.post("/api/conversation/summary")
async def get_conversation_summary(session_id: str):
    """Get conversation summary"""
    try:
        summary = chatbot.get_conversation_summary(session_id)
        return {
            "session_id": session_id,
            "summary": summary,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summary error: {str(e)}")

@app.delete("/api/conversation/{session_id}")
async def clear_conversation(session_id: str):
    """Clear conversation history"""
    try:
        chatbot.clear_conversation_history(session_id)
        return {
            "success": True,
            "message": f"Conversation history cleared for session {session_id}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Clear error: {str(e)}")

@app.post("/api/export/conversation/{session_id}")
async def export_conversation(session_id: str):
    """Export conversation to file"""
    try:
        filename = chatbot.export_conversation(session_id)
        return {
            "success": True,
            "filename": filename,
            "message": "Conversation exported successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export error: {str(e)}")

@app.post("/api/backup")
async def backup_knowledge_base():
    """Create backup of knowledge base"""
    try:
        backup_file = knowledge_base.backup()
        return {
            "success": True,
            "backup_file": backup_file,
            "message": "Backup created successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backup error: {str(e)}")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=404,
        content={"error": "Not found", "detail": "The requested resource was not found"}
    )

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": "An unexpected error occurred"}
    )

if __name__ == "__main__":
    import uvicorn
    
    print("Starting Shravan's Personal AI Assistant...")
    print(f"Server will be available at: http://{config.HOST}:{config.PORT}")
    print("Press Ctrl+C to stop the server")
    
    uvicorn.run(
        "web_interface:app",
        host=config.HOST,
        port=config.PORT,
        reload=True
    )
