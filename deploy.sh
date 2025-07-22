#!/bin/bash

echo "🚀 Deploying to Vercel..."

# Check if Vercel CLI is installed
if ! command -v vercel &> /dev/null; then
    echo "❌ Vercel CLI not found. Installing..."
    npm install -g vercel
fi

# Check if user is logged in to Vercel
if ! vercel whoami &> /dev/null; then
    echo "🔐 Please log in to Vercel..."
    vercel login
fi

# Deploy to Vercel
echo "📦 Deploying application..."
vercel --prod

echo "✅ Deployment complete!"
echo "🌐 Your app should be live at the URL provided above"
echo "💡 Don't forget to set your OPENAI_API_KEY environment variable in the Vercel dashboard!" 