#!/usr/bin/env python3
"""
Simple Chatbot API for Railway
Simplified version without complex imports
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
import json
from datetime import datetime

# Create FastAPI app
app = FastAPI(
    title="Simple Chatbot API",
    description="Simplified version for Railway testing",
    version="1.0.0"
)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str
    timestamp: str

class SearchRequest(BaseModel):
    query: str
    n_results: int = 5

# Simple in-memory storage for testing
chat_history = {}
knowledge_base = []

# Initialize with some sample data
def init_sample_data():
    """Initialize with sample knowledge base data"""
    global knowledge_base
    knowledge_base = [
        {
            "content": "Shravan Shenoy is a computer science student at RV College of Engineering.",
            "metadata": {"source": "profile", "type": "education"}
        },
        {
            "content": "He has experience in machine learning, Python programming, and software development.",
            "metadata": {"source": "skills", "type": "technical"}
        },
        {
            "content": "Shravan worked on projects including Ashwa Racing Formula Bharat and ABB internship.",
            "metadata": {"source": "projects", "type": "experience"}
        }
    ]

# Initialize sample data
init_sample_data()

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Simple Chatbot API is working!",
        "endpoints": ["/health", "/chat", "/search", "/knowledge"],
        "status": "ready"
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "message": "Simple Chatbot API deployed successfully on Railway"
    }

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Simple chat endpoint"""
    try:
        # Generate session ID if not provided
        session_id = request.session_id or f"session_{datetime.now().timestamp()}"
        
        # Simple response logic
        message_lower = request.message.lower()
        
        if "hello" in message_lower or "hi" in message_lower:
            response = "Hello! I'm Shravan's AI assistant. How can I help you today?"
        elif "experience" in message_lower or "work" in message_lower:
            response = "Shravan has experience in machine learning, software development, and has worked on projects like Ashwa Racing Formula Bharat and ABB internship."
        elif "skills" in message_lower or "technology" in message_lower:
            response = "Shravan's skills include Python programming, machine learning, software engineering, and database management."
        elif "education" in message_lower or "college" in message_lower:
            response = "Shravan is a computer science student at RV College of Engineering, focusing on software engineering and AI."
        elif "projects" in message_lower or "ashwa" in message_lower:
            response = "Shravan worked on the Ashwa Racing Formula Bharat project, which involved engineering design and team collaboration."
        else:
            response = "I'm here to help you learn about Shravan's background, skills, and experience. Feel free to ask about his education, projects, or technical skills!"
        
        # Store in chat history
        if session_id not in chat_history:
            chat_history[session_id] = []
        
        chat_history[session_id].append({
            "user": request.message,
            "assistant": response,
            "timestamp": datetime.now().isoformat()
        })
        
        return ChatResponse(
            response=response,
            session_id=session_id,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

@app.get("/api/search")
async def search_endpoint(query: str, n_results: int = 5):
    """Simple search endpoint"""
    try:
        query_lower = query.lower()
        results = []
        
        for item in knowledge_base:
            if query_lower in item["content"].lower():
                results.append(item)
                if len(results) >= n_results:
                    break
        
        return {
            "query": query,
            "results": results,
            "total_results": len(results)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")

@app.get("/api/knowledge")
async def knowledge_endpoint():
    """Get all knowledge base items"""
    return {
        "total_items": len(knowledge_base),
        "items": knowledge_base
    }

@app.get("/api/chat/history/{session_id}")
async def chat_history_endpoint(session_id: str):
    """Get chat history for a session"""
    if session_id in chat_history:
        return {
            "session_id": session_id,
            "messages": chat_history[session_id],
            "total_messages": len(chat_history[session_id])
        }
    else:
        return {
            "session_id": session_id,
            "messages": [],
            "total_messages": 0
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
