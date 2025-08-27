import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # API Keys
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    
    # Model Configuration
    EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
    LLM_MODEL = "gemini-2.5-pro"  # Google Gemini 2.5 Pro
    
    # Vector Database
    CHROMA_PERSIST_DIR = "./chroma_db"
    
    # Document Processing
    CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 200
    
    # File Paths
    DOCUMENTS_DIR = "./documents"
    PROCESSED_DIR = "./processed_documents"
    
    # Chat Configuration
    MAX_HISTORY = 10
    TEMPERATURE = 0.7
    
    # Resume Generation
    RESUME_TEMPLATE_DIR = "./templates"
    
    # Web Interface
    HOST = "0.0.0.0"
    PORT = 8000
