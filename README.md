# Evol-Instruct Synthetic Data Generation App

A modern web application that implements the Evol-Instruct methodology for generating high-quality synthetic question-answer pairs from documents. Built with FastAPI, LangGraph, and OpenAI.

## Features

- **Evol-Instruct Pipeline**: Implements the complete Evol-Instruct methodology with multiple evolution stages
- **Modern Web Interface**: Clean, responsive UI with real-time progress updates
- **Multi-File Support**: Upload and process multiple documents simultaneously
- **OpenAI Integration**: Leverages GPT-4o-mini and text-embedding-3-small models
- **Real-Time Progress**: Server-Sent Events (SSE) for live progress tracking
- **FastAPI Backend**: High-performance API with automatic documentation
- **Responsive Design**: Works seamlessly on desktop and mobile devices

## Architecture

The application follows a modern web architecture:

```
Frontend (HTML/CSS/JS) ←→ FastAPI Backend ←→ LangGraph ←→ OpenAI API
```

### Tech Stack

- **Backend**: FastAPI, Uvicorn, Python 3.11+
- **AI/ML**: LangChain, LangGraph, OpenAI API
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)
- **Deployment**: Vercel (Serverless)

## Quick Start

### Local Development

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd s07-bonus-evol-instruct-app
   ```

2. **Install dependencies**
   ```bash
   uv sync
   ```

3. **Set up environment variables**
   ```bash
   export OPENAI_API_KEY="your-openai-api-key"
   ```

4. **Start the development server**
   ```bash
   uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
   ```

5. **Open your browser**
   Navigate to `http://localhost:8000`

### Deployment to Vercel

1. **Install Vercel CLI** (if not already installed)
   ```bash
   npm install -g vercel
   ```

2. **Login to Vercel**
   ```bash
   vercel login
   ```

3. **Deploy using the provided script**
   ```bash
   ./deploy.sh
   ```

   Or deploy manually:
   ```bash
   vercel --prod
   ```

4. **Set environment variables**
   - Go to your Vercel dashboard
   - Navigate to your project settings
   - Add `OPENAI_API_KEY` with your OpenAI API key

5. **Access your deployed app**
   Your app will be available at the URL provided by Vercel

## API Endpoints

- `GET /` - Main application interface
- `GET /health` - Health check endpoint
- `GET /docs` - Interactive API documentation
- `POST /generate` - Generate synthetic questions from uploaded documents
- `POST /generate-demo` - Generate demo questions (no file upload required)
- `GET /progress-stream` - Server-Sent Events stream for progress updates

## Configuration

### Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key (required)

### File Upload Limits

- Maximum 10 documents per request
- Supported formats: PDF, DOCX, TXT, CSV, JSON

## Development

### Project Structure

```
├── api/
│   ├── main.py          # FastAPI application
│   ├── evol_graph.py    # LangGraph implementation
│   └── models.py        # Pydantic models
├── static/
│   ├── index.html       # Main frontend
│   ├── styles.css       # Styling
│   └── script.js        # Frontend logic
├── requirements.txt     # Python dependencies
├── vercel.json         # Vercel configuration
├── runtime.txt         # Python runtime version
└── deploy.sh          # Deployment script
```

### Running Tests

```bash
# Test the API endpoints
python -m pytest tests/ -v

# Test with curl
curl -X GET http://localhost:8000/health
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For issues and questions, please open an issue on GitHub.