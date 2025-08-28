#!/usr/bin/env python3
"""
Minimal FastAPI app for Railway testing
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Create minimal app
app = FastAPI(title="Minimal API Test")

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Minimal API is working!"}

@app.get("/health")
async def health():
    return {"status": "healthy", "message": "Minimal API deployed successfully"}

@app.get("/test")
async def test():
    return {"message": "This is a test endpoint"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
