#!/bin/bash

# Personal Chatbot Backend Deployment Script
echo "🚀 Deploying Personal Chatbot Backend..."

# Check if we're in the right directory
if [ ! -f "web_interface.py" ]; then
    echo "❌ Error: web_interface.py not found. Are you in the right directory?"
    exit 1
fi

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo "❌ Error: Git not initialized. Run 'git init' first."
    exit 1
fi

# Check if we have a remote
if ! git remote get-url origin > /dev/null 2>&1; then
    echo "⚠️  No remote origin found. You'll need to add one:"
    echo "   git remote add origin <your-repo-url>"
    echo "   git push -u origin main"
    exit 1
fi

# Push to remote
echo "📤 Pushing to remote repository..."
git add .
git commit -m "Update: $(date)"
git push origin main

echo "✅ Code pushed successfully!"
echo ""
echo "🌐 Next steps:"
echo "1. Deploy to Heroku/Railway/Vercel"
echo "2. Set environment variables (GOOGLE_API_KEY)"
echo "3. Test API endpoints"
echo "4. Integrate with your GitHub Pages website"
echo ""
echo "📚 See DEPLOYMENT.md for detailed instructions"
