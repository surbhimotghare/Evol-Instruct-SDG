import logging
import time
from typing import Dict, Any, List, Optional
import json
import asyncio
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import ValidationError
import uuid

from .models import EvolInstructRequest, EvolInstructResponse, HealthResponse, ErrorResponse, Document
from .evol_graph import EvolInstructGraph

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Evol-Instruct API",
    description="Professional Synthetic Data Generation with LangGraph",
    version="1.0.0",
    docs_url=None,  # Disable default docs
    redoc_url=None   # Disable default redoc
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Global variable to store progress updates
current_progress = {
    "session_id": None,
    "steps": [],
    "current_step": "",
    "completed": False,
    "error": None
}

# Progress callback function
def progress_callback(step_info: Dict[str, Any]):
    """Callback function to receive progress updates from the graph"""
    global current_progress
    current_progress["steps"].append(step_info)
    current_progress["current_step"] = step_info.get("message", "")
    
    # Log the progress
    logger.info(f"Progress Update: {step_info}")

# Initialize the EvolInstructGraph
graph = EvolInstructGraph()

# Demo documents for testing
demo_docs = [
    Document(
        page_content="Artificial Intelligence (AI) is a branch of computer science that aims to create intelligent machines that work and react like humans. Some of the activities computers with artificial intelligence are designed for include speech recognition, learning, planning, and problem solving.",
        metadata={"source": "demo_ai_intro.txt", "size": 1024, "type": "text/plain", "extension": "txt"}
    ),
    Document(
        page_content="Machine Learning is a subset of AI that enables computers to learn and improve from experience without being explicitly programmed. It focuses on developing computer programs that can access data and use it to learn for themselves.",
        metadata={"source": "demo_ml_basics.txt", "size": 1024, "type": "text/plain", "extension": "txt"}
    )
]

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main application frontend"""
    return FileResponse("static/index.html")

@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Check the health status of the API"""
    return HealthResponse(
        status="healthy",
        message="Evol-Instruct API is running",
        version="1.0.0",
        graph_status="initialized"
    )

@app.get("/docs", response_class=HTMLResponse)
async def api_documentation():
    """Serve comprehensive API documentation"""
    return HTMLResponse(content="""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Evol-Instruct API Documentation</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #1a1a1a;
            background: #f3f6fd;
            min-height: 100vh;
        }
        
        body::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: linear-gradient(135deg, #0077b5 0%, #004182 25%, #00283d 50%, #1a1a1a 100%);
            z-index: -1;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 20px;
        }
        
        .header {
            padding: 3rem 0 2rem;
            text-align: center;
            color: white;
        }
        
        .header h1 {
            font-size: 3rem;
            font-weight: 700;
            margin-bottom: 1rem;
            background: linear-gradient(135deg, #ffffff 0%, #e8f4f8 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .header p {
            font-size: 1.3rem;
            opacity: 0.9;
            color: #b8d4e3;
        }
        
        .content {
            background: rgba(255, 255, 255, 0.98);
            border-radius: 20px;
            padding: 2.5rem;
            margin-bottom: 2rem;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.3);
        }
        
        .section {
            margin-bottom: 3rem;
        }
        
        .section h2 {
            color: #0077b5;
            font-size: 1.8rem;
            margin-bottom: 1.5rem;
            display: flex;
            align-items: center;
            gap: 0.8rem;
        }
        
        .section h3 {
            color: #1a1a1a;
            font-size: 1.4rem;
            margin: 2rem 0 1rem 0;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid #e1ecf2;
        }
        
        .endpoint {
            background: #f8fcff;
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            border: 1px solid #e1ecf2;
            transition: all 0.3s ease;
        }
        
        .endpoint:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0, 119, 181, 0.1);
        }
        
        .method {
            display: inline-block;
            padding: 0.4rem 1rem;
            border-radius: 20px;
            font-weight: 600;
            font-size: 0.9rem;
            margin-bottom: 1rem;
        }
        
        .method.get { background: #10b981; color: white; }
        .method.post { background: #0077b5; color: white; }
        
        .url {
            font-family: 'SF Mono', Consolas, monospace;
            background: #1a1a1a;
            color: #00ff88;
            padding: 0.8rem 1rem;
            border-radius: 8px;
            margin: 1rem 0;
            font-size: 0.95rem;
            overflow-x: auto;
        }
        
        .description {
            color: #5a6c7d;
            margin-bottom: 1.5rem;
            line-height: 1.7;
        }
        
        .code-block {
            background: #1a1a1a;
            color: #e2e8f0;
            padding: 1.5rem;
            border-radius: 8px;
            margin: 1rem 0;
            overflow-x: auto;
            font-family: 'SF Mono', Consolas, monospace;
            font-size: 0.9rem;
            line-height: 1.5;
        }
        
        .example {
            background: #f0f8ff;
            border: 1px solid #e1ecf2;
            border-radius: 8px;
            padding: 1.5rem;
            margin: 1rem 0;
        }
        
        .example h4 {
            color: #0077b5;
            margin-bottom: 1rem;
            font-size: 1.1rem;
        }
        
        .response-example {
            background: #f0f8ff;
            border-left: 4px solid #0077b5;
            padding: 1rem;
            margin: 1rem 0;
            border-radius: 0 8px 8px 0;
        }
        
        .note {
            background: #fff7e6;
            border: 1px solid #fbbf24;
            border-radius: 8px;
            padding: 1rem;
            margin: 1rem 0;
            color: #92400e;
        }
        
        .warning {
            background: #fef2f2;
            border: 1px solid #f87171;
            border-radius: 8px;
            padding: 1rem;
            margin: 1rem 0;
            color: #991b1b;
        }
        
        .table {
            width: 100%;
            border-collapse: collapse;
            margin: 1rem 0;
        }
        
        .table th, .table td {
            padding: 0.8rem;
            text-align: left;
            border-bottom: 1px solid #e1ecf2;
        }
        
        .table th {
            background: #f8fcff;
            font-weight: 600;
            color: #0077b5;
        }
        
        .back-btn {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.8rem 1.5rem;
            background: linear-gradient(135deg, #0077b5, #004d7a);
            color: white;
            text-decoration: none;
            border-radius: 8px;
            font-weight: 600;
            transition: all 0.3s ease;
            margin-bottom: 2rem;
        }
        
        .back-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0, 119, 181, 0.3);
        }
        
        .feature-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1.5rem;
            margin: 2rem 0;
        }
        
        .feature-card {
            background: #f8fcff;
            border-radius: 12px;
            padding: 1.5rem;
            border: 1px solid #e1ecf2;
            transition: all 0.3s ease;
        }
        
        .feature-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0, 119, 181, 0.1);
        }
        
        .feature-card h4 {
            color: #0077b5;
            margin-bottom: 0.8rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        @media (max-width: 768px) {
            .container {
                padding: 0 15px;
            }
            
            .content {
                padding: 1.5rem;
            }
            
            .header h1 {
                font-size: 2rem;
            }
            
            .url {
                font-size: 0.8rem;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1><i class="fas fa-book"></i> API Documentation</h1>
            <p>Evol-Instruct Synthetic Data Generation API</p>
        </div>
        
        <div class="content">
            <a href="/" class="back-btn">
                <i class="fas fa-arrow-left"></i>
                Back to Application
            </a>
            
            <div class="section">
                <h2><i class="fas fa-info-circle"></i> Overview</h2>
                <p class="description">
                    The Evol-Instruct API provides a sophisticated synthetic data generation service based on the Evol-Instruct methodology from the WizardLM paper. 
                    It uses LangGraph to orchestrate complex AI workflows that generate high-quality question-answer pairs through multiple evolution types.
                </p>
                
                <div class="feature-grid">
                    <div class="feature-card">
                        <h4><i class="fas fa-cog"></i> Simple Evolution</h4>
                        <p>Enhances questions with more detail and complexity while maintaining the core meaning.</p>
                    </div>
                    <div class="feature-card">
                        <h4><i class="fas fa-project-diagram"></i> Multi-Context Evolution</h4>
                        <p>Creates questions that span multiple documents or contexts for comprehensive analysis.</p>
                    </div>
                    <div class="feature-card">
                        <h4><i class="fas fa-brain"></i> Reasoning Evolution</h4>
                        <p>Generates questions that require logical reasoning and analytical thinking.</p>
                    </div>
                </div>
            </div>
            
            <div class="section">
                <h2><i class="fas fa-server"></i> Base URL</h2>
                <div class="code-block">https://your-domain.com</div>
                <p class="description">All API endpoints are relative to this base URL.</p>
            </div>
            
            <div class="section">
                <h2><i class="fas fa-key"></i> Authentication</h2>
                <p class="description">
                    The API supports OpenAI API key authentication. You can provide your key in two ways:
                </p>
                <ul style="margin-left: 2rem; color: #5a6c7d;">
                    <li><strong>Header:</strong> Include <code>x-openai-api-key</code> header with your OpenAI API key</li>
                    <li><strong>Server Default:</strong> The server uses its own configured OpenAI API key if no user key is provided</li>
                </ul>
                <div class="note">
                    <strong>Note:</strong> Your API key is stored locally in your browser and never sent to our servers unless explicitly provided in API calls.
                </div>
            </div>
            
            <div class="section">
                <h2><i class="fas fa-list"></i> Endpoints</h2>
                
                <div class="endpoint">
                    <span class="method get">GET</span>
                    <div class="url">/health</div>
                    <p class="description">Check the health status of the API and verify it's running properly.</p>
                    
                    <h4>Response Example:</h4>
                    <div class="code-block">{
  "status": "healthy",
  "message": "Evol-Instruct API is running",
  "version": "1.0.0",
  "graph_status": "initialized"
}</div>
                </div>
                
                <div class="endpoint">
                    <span class="method post">POST</span>
                    <div class="url">/generate</div>
                    <p class="description">Generate evolved questions from uploaded documents using the Evol-Instruct methodology.</p>
                    
                    <h4>Request Body:</h4>
                    <div class="code-block">{
  "documents": [
    {
      "page_content": "Document text content...",
      "metadata": {
        "source": "document.txt",
        "size": 1024,
        "type": "text/plain",
        "extension": "txt"
      }
    }
  ],
  "target_questions": 9
}</div>
                    
                    <h4>Response Example:</h4>
                    <div class="code-block">{
  "evolved_questions": [
    {
      "id": "Q001",
      "question": "What are the key differences between AI and machine learning?",
      "evolution_type": "simple"
    }
  ],
  "question_answers": [
    {
      "question_id": "Q001",
      "answer": "AI is a broader field that includes machine learning..."
    }
  ],
  "question_contexts": [
    {
      "question_id": "Q001",
      "contexts": ["Context 1", "Context 2"]
    }
  ],
  "total_questions": 9,
  "processing_time": 45.2
}</div>
                    
                    <div class="note" style="margin-top: 1rem; padding: 1rem; background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 8px; color: #856404;">
                        <strong>⚠️ Important:</strong> A maximum of 10 documents can be uploaded per request. This limit ensures optimal performance and prevents timeout issues during processing.
                    </div>
                </div>
                
                <div class="endpoint">
                    <span class="method post">POST</span>
                    <div class="url">/generate-demo</div>
                    <p class="description">Generate questions using predefined demo documents for testing purposes.</p>
                    
                    <h4>Request:</h4>
                    <p class="description">No request body required. Uses built-in demo documents about AI and machine learning.</p>
                    
                    <h4>Response:</h4>
                    <p class="description">Same format as the <code>/generate</code> endpoint response.</p>
                </div>
                
                <div class="endpoint">
                    <span class="method get">GET</span>
                    <div class="url">/progress-stream</div>
                    <p class="description">Server-Sent Events (SSE) endpoint for real-time progress updates during question generation.</p>
                    
                    <h4>Event Types:</h4>
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Type</th>
                                <th>Description</th>
                                <th>Example</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td><code>phase_start</code></td>
                                <td>Start of a new processing phase</td>
                                <td>"🚀 Starting Simple Evolution phase"</td>
                            </tr>
                            <tr>
                                <td><code>step</code></td>
                                <td>Individual processing step</td>
                                <td>"⚙️ Generating question 3/9"</td>
                            </tr>
                            <tr>
                                <td><code>success</code></td>
                                <td>Successful completion of a step</td>
                                <td>"✅ Question generated successfully"</td>
                            </tr>
                            <tr>
                                <td><code>error</code></td>
                                <td>Error during processing</td>
                                <td>"❌ Failed to generate question"</td>
                            </tr>
                            <tr>
                                <td><code>complete</code></td>
                                <td>All processing completed</td>
                                <td>"✅ All questions generated successfully!"</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
            
            <div class="section">
                <h2><i class="fas fa-file-upload"></i> Supported File Types</h2>
                <table class="table">
                    <thead>
                        <tr>
                            <th>File Type</th>
                            <th>Extension</th>
                            <th>Description</th>
                            <th>Max Size</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>Text Files</td>
                            <td><code>.txt</code></td>
                            <td>Plain text documents</td>
                            <td>2MB</td>
                        </tr>
                        <tr>
                            <td>PDF Documents</td>
                            <td><code>.pdf</code></td>
                            <td>Portable Document Format</td>
                            <td>2MB</td>
                        </tr>
                        <tr>
                            <td>CSV Files</td>
                            <td><code>.csv</code></td>
                            <td>Comma-separated values</td>
                            <td>2MB</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            
            <div class="section">
                <h2><i class="fas fa-code"></i> Usage Examples</h2>
                
                <h3>JavaScript Example</h3>
                <div class="code-block">// Generate questions from documents
const response = await fetch('/generate', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'x-openai-api-key': 'your-openai-key' // Optional
  },
  body: JSON.stringify({
    documents: [
      {
        page_content: "Your document content here...",
        metadata: {
          source: "document.txt",
          size: 1024,
          type: "text/plain",
          extension: "txt"
        }
      }
    ],
    target_questions: 9
  })
});

const data = await response.json();
console.log(data.evolved_questions);</div>
                
                <h3>cURL Example</h3>
                <div class="code-block">curl -X POST "https://your-domain.com/generate" \\
  -H "Content-Type: application/json" \\
  -H "x-openai-api-key: your-openai-key" \\
  -d '{
    "documents": [
      {
        "page_content": "Your document content here...",
        "metadata": {
          "source": "document.txt",
          "size": 1024,
          "type": "text/plain",
          "extension": "txt"
        }
      }
    ],
    "target_questions": 9
  }'</div>
            </div>
            
            <div class="section">
                <h2><i class="fas fa-exclamation-triangle"></i> Error Handling</h2>
                
                <h3>Common Error Responses</h3>
                
                <div class="warning">
                    <h4>400 Bad Request</h4>
                    <p>Invalid request format or missing required fields.</p>
                    <div class="code-block">{
  "detail": "Validation error: documents field required"
}</div>
                </div>
                
                <div class="warning">
                    <h4>422 Unprocessable Entity</h4>
                    <p>Request validation failed (e.g., invalid document format).</p>
                    <div class="code-block">{
  "detail": [
    {
      "loc": ["body", "target_questions"],
      "msg": "ensure this value is greater than or equal to 3",
      "type": "value_error.number.not_ge"
    }
  ]
}</div>
                </div>
                
                <div class="warning">
                    <h4>500 Internal Server Error</h4>
                    <p>Server-side error during processing.</p>
                    <div class="code-block">{
  "detail": "Failed to generate questions: OpenAI API error"
}</div>
                </div>
            </div>
            
            <div class="section">
                <h2><i class="fas fa-lightbulb"></i> Best Practices</h2>
                <ul style="margin-left: 2rem; color: #5a6c7d; line-height: 1.8;">
                    <li><strong>Document Quality:</strong> Ensure your documents contain meaningful, readable text content</li>
                    <li><strong>File Size:</strong> Keep individual files under 2MB for optimal processing</li>
                    <li><strong>Question Count:</strong> Use 3-15 questions for balanced results (3 questions per evolution type)</li>
                    <li><strong>Progress Monitoring:</strong> Use the SSE endpoint to track real-time progress</li>
                    <li><strong>Error Handling:</strong> Always implement proper error handling for API calls</li>
                    <li><strong>Rate Limiting:</strong> Be mindful of OpenAI API rate limits when using your own key</li>
                </ul>
            </div>
            
            <div class="section">
                <h2><i class="fas fa-link"></i> Related Links</h2>
                <ul style="margin-left: 2rem; color: #5a6c7d;">
                    <li><a href="https://arxiv.org/pdf/2304.12244" target="_blank" style="color: #0077b5;">WizardLM Paper (Evol-Instruct Methodology)</a></li>
                    <li><a href="https://langchain.com/langgraph" target="_blank" style="color: #0077b5;">LangGraph Documentation</a></li>
                    <li><a href="https://platform.openai.com/docs" target="_blank" style="color: #0077b5;">OpenAI API Documentation</a></li>
                </ul>
            </div>
        </div>
    </div>
</body>
</html>
    """)

@app.post("/generate", response_model=EvolInstructResponse, tags=["Generation"])
async def generate_questions(request: EvolInstructRequest):
    """Generate evolved questions from uploaded documents"""
    try:
        # Reset progress
        global current_progress
        current_progress = {
            "session_id": str(uuid.uuid4()),
            "steps": [],
            "current_step": "",
            "completed": False,
            "error": None
        }
        
        # Run the evolution graph
        result = await graph.run(
            request.documents,
            target_questions=request.target_questions,
            progress_callback=progress_callback
        )
        
        # Mark as completed
        current_progress["completed"] = True
        
        return EvolInstructResponse(**result)
        
    except Exception as e:
        current_progress["error"] = str(e)
        logger.error(f"Generation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate questions: {str(e)}"
        )

@app.post("/generate-demo", response_model=EvolInstructResponse, tags=["Demo"])
async def generate_demo():
    """Generate questions using demo documents"""
    try:
        # Reset progress
        global current_progress
        current_progress = {
            "session_id": str(uuid.uuid4()),
            "steps": [],
            "current_step": "",
            "completed": False,
            "error": None
        }
        
        # Run with demo documents
        result = await graph.run(demo_docs, target_questions=9, progress_callback=progress_callback)
        
        # Mark as completed
        current_progress["completed"] = True
        
        return EvolInstructResponse(**result)
        
    except Exception as e:
        current_progress["error"] = str(e)
        logger.error(f"Demo generation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate demo questions: {str(e)}"
        )

@app.get("/progress-stream", tags=["Progress"])
async def progress_stream():
    """Stream real-time progress updates using Server-Sent Events"""
    async def event_generator():
        global current_progress
        last_step_count = 0
        
        while not current_progress["completed"] and current_progress["error"] is None:
            if len(current_progress["steps"]) > last_step_count:
                for step in current_progress["steps"][last_step_count:]:
                    yield f"data: {json.dumps(step)}\n\n"
                last_step_count = len(current_progress["steps"])
            
            status_data = {
                "type": "status",
                "current_step": current_progress["current_step"],
                "total_steps": len(current_progress["steps"]),
                "completed": current_progress["completed"]
            }
            yield f"data: {json.dumps(status_data)}\n\n"
            await asyncio.sleep(0.5)
        
        if current_progress["error"]:
            final_data = {"type": "error", "message": current_progress["error"]}
        else:
            final_data = {
                "type": "completed", 
                "message": "✅ All questions generated successfully!", 
                "total_steps": len(current_progress["steps"])
            }
        yield f"data: {json.dumps(final_data)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )

# Exception handlers
@app.exception_handler(ValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            error="Validation Error",
            message="Invalid request data",
            details=str(exc)
        ).dict()
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error="HTTP Error",
            message=exc.detail,
            details=None
        ).dict()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="Internal Server Error",
            message="An unexpected error occurred",
            details=str(exc)
        ).dict()
    ) 