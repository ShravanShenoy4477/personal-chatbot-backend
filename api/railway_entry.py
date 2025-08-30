#!/usr/bin/env python3
"""
Railway Entry Point for Full Chatbot API
Handles imports carefully and provides better error handling
"""

import os
import sys
import traceback
from pathlib import Path

# Add the parent directory to Python path for imports
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

def create_railway_app():
    """Create the FastAPI app with careful error handling"""
    try:
        print("🚀 Starting Railway Chatbot API...")
        
        # Test environment variables first
        required_vars = ["GOOGLE_API_KEY", "QDRANT_URL", "QDRANT_API_KEY", "QDRANT_COLLECTION"]
        missing_vars = []
        
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(f"Missing environment variables: {missing_vars}")
        
        print("✅ Environment variables loaded")
        
        # Test imports step by step
        print("🔍 Testing imports...")
        
        # 1. Test config
        try:
            from config import Config
            config = Config()
            print("✅ Config loaded")
        except Exception as e:
            print(f"❌ Config import failed: {e}")
            raise
        
        # 2. Test knowledge base import (instance will be created by web_interface)
        try:
            from knowledge_base import KnowledgeBase
            print("✅ Knowledge base class imported successfully")
        except Exception as e:
            print(f"❌ Knowledge base import failed: {e}")
            raise
        
        # 3. Test chatbot import (instance will be created by web_interface)
        try:
            from chatbot import PersonalChatbot
            print("✅ Chatbot class imported successfully")
        except Exception as e:
            print(f"❌ Chatbot import failed: {e}")
            raise
        
        # 4. Import web interface
        try:
            from web_interface import app
            print("✅ Web interface imported")
            return app
        except Exception as e:
            print(f"❌ Web interface import failed: {e}")
            traceback.print_exc()
            raise
            
    except Exception as e:
        print(f"❌ Failed to create Railway app: {e}")
        traceback.print_exc()
        
        # Create a fallback app with error information
        from fastapi import FastAPI, HTTPException
        from fastapi.middleware.cors import CORSMiddleware
        
        fallback_app = FastAPI(title="Railway Chatbot API - Error Mode")
        fallback_app.add_middleware(CORSMiddleware, allow_origins=["*"])
        
        @fallback_app.get("/")
        async def root():
            return {
                "status": "error",
                "message": "Failed to initialize full chatbot API",
                "error": str(e),
                "traceback": traceback.format_exc()
            }
        
        @fallback_app.get("/health")
        async def health():
            return {
                "status": "unhealthy",
                "message": "API failed to initialize properly",
                "error": str(e)
            }
        
        return fallback_app

# Create the app
app = create_railway_app()

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    print(f"🚀 Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
