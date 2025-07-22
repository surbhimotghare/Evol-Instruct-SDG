# Evol-Instruct Synthetic Data Generation App

<p align="center">
  <img src="https://img.shields.io/badge/FastAPI-0.116.1-009688?style=for-the-badge&logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/LangGraph-0.5.4-FF6B6B?style=for-the-badge&logo=python" alt="LangGraph">
  <img src="https://img.shields.io/badge/OpenAI-GPT--4o--mini-412991?style=for-the-badge&logo=openai" alt="OpenAI">
  <img src="https://img.shields.io/badge/React-Modern%20UI-61DAFB?style=for-the-badge&logo=react" alt="Modern UI">
</p>

## 🚀 Overview

A sophisticated synthetic data generation application built with **Evol-Instruct methodology** from the WizardLM paper. This app uses LangGraph to orchestrate complex AI workflows that generate high-quality question-answer pairs through multiple evolution types.

### ✨ Key Features

- **🎯 Evol-Instruct Pipeline**: Advanced synthetic data generation using LangGraph
- **🌐 Modern Web Interface**: LinkedIn-inspired, professional UI with real-time progress
- **📁 Multi-File Support**: Upload and process `.txt`, `.pdf`, and `.csv` files
- **🔑 OpenAI Integration**: User-configurable API keys with secure storage
- **📊 Real-Time Progress**: Server-Sent Events (SSE) for live progress updates
- **📚 Comprehensive API**: Full REST API with interactive documentation
- **⚡ FastAPI Backend**: High-performance async API server
- **🎨 Responsive Design**: Works seamlessly on desktop and mobile

## 🏗️ Architecture

### System Architecture

![System Architecture Diagram](https://i.imgur.com/58ktzG5.png)

*Clean, organized view of the Evol-Instruct synthetic data generation pipeline showing data flow from frontend to output generation*

### Evolution Types

1. **Simple Evolution** 🎯
   - Enhances questions with more detail and complexity
   - Maintains core meaning while adding sophistication

2. **Multi-Context Evolution** 🔗
   - Creates questions spanning multiple documents
   - Enables comprehensive cross-document analysis

3. **Reasoning Evolution** 🧠
   - Generates questions requiring logical reasoning
   - Promotes analytical thinking and problem-solving

### Tech Stack

- **Backend**: FastAPI + Uvicorn + LangGraph + LangChain
- **Frontend**: Modern HTML/CSS/JavaScript with Font Awesome
- **AI**: OpenAI GPT-4o-mini for question generation
- **File Processing**: PDF.js + Papa Parse for client-side parsing
- **Deployment**: Render.com cloud deployment

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- OpenAI API key (optional - server has default key)

### Installation

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

## 🌐 Live Demo

The app is deployed and available at: [https://evol-instruct-sdg.onrender.com/](https://evol-instruct-sdg.onrender.com/)

## Deployment (Render)

1. **Create a new Web Service on [Render](https://render.com/)**
2. Connect your GitHub repository.
3. Set the build and start commands:
   - **Build Command:** (leave blank or use `pip install -r requirements.txt`)
   - **Start Command:**
     ```bash
     uvicorn api.main:app --host 0.0.0.0 --port $PORT
     ```
4. Add the environment variable `OPENAI_API_KEY` in the Render dashboard.
5. Deploy! Your app will be available at the Render-provided URL (see above for the public demo).

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
├── runtime.txt          # Python runtime version
└── deploy.sh            # Deployment script
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