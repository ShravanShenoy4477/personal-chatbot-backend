# Personal Chatbot Backend - Deployment Guide

## Overview
This is the backend API for your personal AI chatbot, designed to be deployed as a cloud service and integrated with your GitHub Pages website.

## Core Components

### 1. **chatbot.py** - Main AI Logic
- PersonalChatbot class with conversation management
- Multi-stage search strategy (enriched metadata + semantic + routing)
- Context-aware responses for recruiter interactions

### 2. **knowledge_base.py** - Vector Database Management
- ChromaDB integration for document storage
- Metadata enrichment and search optimization
- Document tracking and persistence

### 3. **web_interface.py** - FastAPI Backend
- RESTful API endpoints for chat functionality
- Session management and response generation
- Admin endpoints for knowledge base management

### 4. **unified_ingestion.py** - Document Processing
- Multi-format document ingestion (PDF, DOCX, CSV, images)
- Enhanced text cleaning and chunking
- Structured content extraction with Gemini

### 5. **daily_update.py** - Knowledge Base Updates
- Incremental daily updates system
- Project categorization and clarification loops
- Automated knowledge base evolution

## Deployment Options

### Option 1: Heroku (Recommended for beginners)
```bash
# Install Heroku CLI
brew install heroku/brew/heroku  # macOS
# or visit: https://devcenter.heroku.com/articles/heroku-cli

# Login and create app
heroku login
heroku create your-chatbot-api
heroku config:set GOOGLE_API_KEY=your_key_here

# Deploy
git push heroku main
```

### Option 2: Railway
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
railway init
railway up
```

### Option 3: Vercel
```bash
# Install Vercel CLI
npm install -g vercel

# Deploy
vercel --prod
```

## Environment Variables

Set these in your deployment platform:

```bash
GOOGLE_API_KEY=your_gemini_api_key
CHROMA_DB_PATH=./chroma_db
ENVIRONMENT=production
```

## API Endpoints

### Chat
- `POST /api/chat` - Main chat endpoint
- `GET /chat` - Chat interface page

### Knowledge Base
- `GET /api/knowledge` - Get KB statistics
- `POST /api/daily-update` - Add daily updates
- `GET /admin` - Admin panel

### Resume Generation
- `POST /api/resume/generate` - Generate tailored resumes
- `GET /resume` - Resume generator page

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
uvicorn web_interface:app --reload

# Access at http://localhost:8000
```

## Integration with Website

Once deployed, your website can integrate via:

```javascript
const API_BASE = 'https://your-api.herokuapp.com';

async function chatWithAI(message) {
    const response = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, session_id: sessionId })
    });
    return await response.json();
}
```

## Monitoring & Maintenance

- **Logs**: Check deployment platform logs
- **Performance**: Monitor API response times
- **Updates**: Use daily_update.py for knowledge base evolution
- **Backups**: ChromaDB data is persistent in deployment

## Troubleshooting

### Common Issues:
1. **Memory Limits**: Reduce chunk sizes in ingestion
2. **API Timeouts**: Optimize search queries
3. **Database Issues**: Check ChromaDB persistence
4. **Rate Limits**: Monitor Google API usage

### Support:
- Check deployment platform logs
- Test endpoints locally first
- Verify environment variables
- Monitor API response times
