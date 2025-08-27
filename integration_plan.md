# Personal Chatbot + GitHub Pages Integration Plan

## Overview
This document outlines how to integrate your personal AI chatbot with your GitHub Pages website, maintaining both projects in sync.

## Repository Structure

### 1. Personal Chatbot Repository (`personal_chatbot/`)
- **Purpose**: Backend AI logic, knowledge base, document processing
- **Contains**: All Python files, ChromaDB, document tracking
- **Deployment**: Backend API service (Heroku/Railway/Vercel)

### 2. Website Repository (`your-website/`)
- **Purpose**: Frontend interface, GitHub Pages hosting
- **Contains**: HTML, CSS, JavaScript, chatbot integration
- **Deployment**: GitHub Pages (automatic)

## Integration Methods

### Method A: API-Based Integration (Recommended)

#### Backend Deployment
1. **Deploy to Heroku/Railway/Vercel**
   ```bash
   # In personal_chatbot directory
   pip install gunicorn
   echo "web: gunicorn web_interface:app" > Procfile
   ```

2. **Environment Variables**
   ```bash
   GOOGLE_API_KEY=your_key
   CHROMA_DB_PATH=./chroma_db
   ```

3. **API Endpoints**
   - `POST /api/chat` - Chat with AI
   - `GET /api/knowledge` - Get knowledge base info
   - `POST /api/daily-update` - Add daily updates

#### Frontend Integration
```javascript
// In your website's JavaScript
async function chatWithAI(message) {
    const response = await fetch('https://your-api.herokuapp.com/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, session_id: sessionId })
    });
    return await response.json();
}
```

### Method B: Static Integration (Simpler)

#### Export Chatbot Knowledge
1. **Generate Static Responses**
   ```python
   # In personal_chatbot
   python export_knowledge.py
   ```

2. **Create Response Database**
   ```json
   {
     "responses": {
       "about_abb": "I worked at ABB as...",
       "about_iisc": "At IISc, I researched...",
       "skills": "My technical skills include..."
     }
   }
   ```

3. **Frontend Integration**
   ```javascript
   // Load responses from static JSON
   const responses = await fetch('./chatbot_responses.json');
   const aiResponse = responses[userQuery] || "I don't have information about that.";
   ```

## Implementation Steps

### Phase 1: Backend Preparation
1. ✅ **Complete** - Your chatbot is fully functional
2. ✅ **Complete** - Web interface exists with FastAPI
3. **Next** - Deploy backend to cloud service
4. **Next** - Test API endpoints

### Phase 2: Frontend Integration
1. **Create** - Chatbot interface in your website
2. **Integrate** - API calls to backend
3. **Style** - Match your website's design
4. **Test** - End-to-end functionality

### Phase 3: Sync & Maintenance
1. **Automate** - Daily knowledge base updates
2. **Monitor** - API performance and usage
3. **Update** - Both repositories simultaneously

## File Structure for Website Integration

```
your-website/
├── index.html                 # Main page
├── chatbot/
│   ├── index.html            # Chatbot interface
│   ├── chat.js               # Chat functionality
│   └── chat.css              # Chat styling
├── assets/
│   ├── css/
│   ├── js/
│   └── images/
└── .github/
    └── workflows/
        └── sync-chatbot.yml   # Auto-sync workflow
```

## Benefits of This Approach

1. **Clean Separation**: Backend logic separate from frontend
2. **Easy Updates**: Update chatbot without touching website
3. **Scalability**: Can handle multiple users simultaneously
4. **Maintenance**: Each repo has single responsibility
5. **Cost-Effective**: GitHub Pages free, minimal backend costs

## Next Steps

1. **Choose integration method** (API vs Static)
2. **Deploy backend** to cloud service
3. **Create chatbot interface** in your website
4. **Test integration** end-to-end
5. **Set up automated sync** between repositories

## Questions to Consider

- Do you want real-time chat or pre-generated responses?
- What's your budget for backend hosting?
- How often will you update the knowledge base?
- Do you need user authentication/sessions?
