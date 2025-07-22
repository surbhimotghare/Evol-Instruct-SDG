
# 🚀 **MVP Plan: FastAPI + LangGraph Evol-Instruct on Vercel**

## **Simplified Architecture**

### **Core MVP Scope**
- **Single evolution round** (no multi-round iterations)
- **Essential 3 evolution types** (Simple, Multi-Context, Reasoning)
- **Basic quality filtering** (no complex validation)
- **REST API** with FastAPI
- **Vercel deployment** ready

---

## **1. Project Structure**

```
evol-instruct-api/
├── api/
│   ├── __init__.py
│   ├── main.py              # FastAPI app
│   ├── models.py            # Pydantic models
│   └── evol_graph.py        # LangGraph implementation
├── requirements.txt         # Dependencies
├── vercel.json             # Vercel config
└── README.md
```

---

## **2. Simplified State Schema**

```python
# api/models.py
from typing import List, Dict, Optional, Literal
from pydantic import BaseModel

class Document(BaseModel):
    page_content: str
    metadata: Dict = {}

class EvolvedQuestion(BaseModel):
    id: str
    question: str
    evolution_type: Literal["simple", "multi_context", "reasoning"]
    parent_id: Optional[str] = None

class QuestionAnswer(BaseModel):
    question_id: str
    answer: str

class QuestionContext(BaseModel):
    question_id: str
    contexts: List[str]

class EvolInstructRequest(BaseModel):
    documents: List[Document]
    target_questions: int = 9  # MVP: 3 per evolution type

class EvolInstructResponse(BaseModel):
    evolved_questions: List[EvolvedQuestion]
    question_answers: List[QuestionAnswer] 
    question_contexts: List[QuestionContext]
    processing_time: float
```

---

## **3. Minimal LangGraph Implementation**

```python
# api/evol_graph.py
from typing import TypedDict, List
from langgraph import StateGraph
from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings
import random
import uuid

class State(TypedDict):
    documents: List[dict]
    seed_questions: List[dict]
    evolved_questions: List[dict]
    question_answers: List[dict]
    question_contexts: List[dict]
    current_round: int

class EvolInstructGraph:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(State)
        
        # Add nodes
        workflow.add_node("generate_seeds", self.generate_seed_questions)
        workflow.add_node("simple_evolution", self.simple_evolution)
        workflow.add_node("multi_context_evolution", self.multi_context_evolution)
        workflow.add_node("reasoning_evolution", self.reasoning_evolution)
        workflow.add_node("generate_answers", self.generate_answers)
        workflow.add_node("extract_contexts", self.extract_contexts)
        
        # Add edges
        workflow.set_entry_point("generate_seeds")
        workflow.add_edge("generate_seeds", "simple_evolution")
        workflow.add_edge("simple_evolution", "multi_context_evolution")
        workflow.add_edge("multi_context_evolution", "reasoning_evolution")
        workflow.add_edge("reasoning_evolution", "generate_answers")
        workflow.add_edge("generate_answers", "extract_contexts")
        workflow.set_finish_point("extract_contexts")
        
        return workflow.compile()

    def generate_seed_questions(self, state: State) -> State:
        """Generate 3-5 simple questions from documents"""
        seed_questions = []
        
        for i, doc in enumerate(state["documents"][:3]):  # MVP: limit to 3 docs
            prompt = f"""
            Based on this document content, generate 1 clear, answerable question:
            
            Document: {doc['page_content'][:1000]}...
            
            Return only the question, no explanation.
            """
            
            response = self.llm.invoke(prompt)
            seed_questions.append({
                "id": f"seed_{i}",
                "question": response.content.strip(),
                "source_doc": i
            })
        
        state["seed_questions"] = seed_questions
        state["evolved_questions"] = []
        return state

    def simple_evolution(self, state: State) -> State:
        """Create 3 simple evolved questions"""
        operations = [
            "Add specific constraints to make this question more challenging: {question}",
            "Make this question require more detailed analysis: {question}", 
            "Add complexity by including multiple conditions: {question}"
        ]
        
        evolved = []
        for i, seed in enumerate(state["seed_questions"]):
            if i >= 3:  # MVP: limit to 3
                break
                
            operation = random.choice(operations)
            prompt = f"Rewrite this question: {operation.format(question=seed['question'])}"
            
            response = self.llm.invoke(prompt)
            evolved.append({
                "id": f"simple_{i}",
                "question": response.content.strip(),
                "evolution_type": "simple",
                "parent_id": seed["id"]
            })
        
        state["evolved_questions"].extend(evolved)
        return state

    def multi_context_evolution(self, state: State) -> State:
        """Create 3 multi-context questions"""
        if len(state["documents"]) < 2:
            # Fallback to simple evolution
            return self.simple_evolution(state)
        
        evolved = []
        for i in range(3):  # MVP: exactly 3
            if i >= len(state["seed_questions"]):
                break
                
            seed = state["seed_questions"][i]
            prompt = f"""
            Create a question that requires information from multiple documents.
            Base question: {seed['question']}
            
            Make it require comparing, synthesizing, or connecting information across different sources.
            """
            
            response = self.llm.invoke(prompt)
            evolved.append({
                "id": f"multi_context_{i}",
                "question": response.content.strip(),
                "evolution_type": "multi_context", 
                "parent_id": seed["id"]
            })
        
        state["evolved_questions"].extend(evolved)
        return state

    def reasoning_evolution(self, state: State) -> State:
        """Create 3 reasoning questions"""
        evolved = []
        for i in range(3):  # MVP: exactly 3
            if i >= len(state["seed_questions"]):
                break
                
            seed = state["seed_questions"][i]
            prompt = f"""
            Transform this into a question requiring logical reasoning, cause-effect analysis, or step-by-step thinking:
            
            Original: {seed['question']}
            
            Make it require: "If X, then what would happen to Y?" or "Given conditions A and B, how would you approach C?"
            """
            
            response = self.llm.invoke(prompt)
            evolved.append({
                "id": f"reasoning_{i}",
                "question": response.content.strip(),
                "evolution_type": "reasoning",
                "parent_id": seed["id"]
            })
        
        state["evolved_questions"].extend(evolved)
        return state

    def generate_answers(self, state: State) -> State:
        """Generate answers for evolved questions"""
        answers = []
        all_content = "\n\n".join([doc["page_content"] for doc in state["documents"]])
        
        for q in state["evolved_questions"]:
            prompt = f"""
            Answer this question based on the provided context. Be comprehensive and accurate.
            
            Context: {all_content[:3000]}...
            
            Question: {q['question']}
            """
            
            response = self.llm.invoke(prompt)
            answers.append({
                "question_id": q["id"],
                "answer": response.content.strip()
            })
        
        state["question_answers"] = answers
        return state

    def extract_contexts(self, state: State) -> State:
        """Extract relevant contexts for each question"""
        contexts = []
        
        for q in state["evolved_questions"]:
            # Simple context extraction - find most relevant document chunks
            relevant_contexts = []
            for doc in state["documents"][:2]:  # MVP: limit contexts
                if len(doc["page_content"]) > 200:
                    # Take first meaningful chunk
                    chunk = doc["page_content"][:500]
                    relevant_contexts.append(chunk)
            
            contexts.append({
                "question_id": q["id"],
                "contexts": relevant_contexts
            })
        
        state["question_contexts"] = contexts
        return state

    async def run(self, documents: List[dict]) -> dict:
        """Main execution method"""
        initial_state = {
            "documents": documents,
            "seed_questions": [],
            "evolved_questions": [],
            "question_answers": [],
            "question_contexts": [],
            "current_round": 1
        }
        
        final_state = await self.graph.ainvoke(initial_state)
        
        return {
            "evolved_questions": final_state["evolved_questions"],
            "question_answers": final_state["question_answers"], 
            "question_contexts": final_state["question_contexts"]
        }
```

---

## **4. FastAPI Application**

```python
# api/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import time
import asyncio
from .models import EvolInstructRequest, EvolInstructResponse
from .evol_graph import EvolInstructGraph

app = FastAPI(
    title="Evol-Instruct API",
    description="Generate synthetic data using Evol-Instruct method with LangGraph",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the graph once
evol_graph = EvolInstructGraph()

@app.get("/")
async def root():
    return {"message": "Evol-Instruct API is running!"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": time.time()}

@app.post("/generate", response_model=EvolInstructResponse)
async def generate_synthetic_data(request: EvolInstructRequest):
    """
    Generate synthetic data using Evol-Instruct method
    """
    try:
        start_time = time.time()
        
        # Convert Pydantic models to dicts
        documents = [doc.dict() for doc in request.documents]
        
        # Run the evolution process
        result = await evol_graph.run(documents)
        
        processing_time = time.time() - start_time
        
        return EvolInstructResponse(
            evolved_questions=result["evolved_questions"],
            question_answers=result["question_answers"],
            question_contexts=result["question_contexts"],
            processing_time=processing_time
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

@app.post("/generate-simple")
async def generate_simple_demo():
    """
    Demo endpoint with sample documents for testing
    """
    sample_docs = [
        {
            "page_content": "Student loans are financial aid that help students pay for college expenses. There are federal and private loan options available.",
            "metadata": {"source": "loan_basics.pdf"}
        },
        {
            "page_content": "Federal student loans offer fixed interest rates and flexible repayment options. Students must complete FAFSA to be eligible.",
            "metadata": {"source": "federal_loans.pdf"}
        }
    ]
    
    request = EvolInstructRequest(documents=sample_docs, target_questions=6)
    return await generate_synthetic_data(request)
```

---

## **5. Dependencies & Config**

```txt
# requirements.txt
fastapi==0.104.1
uvicorn==0.24.0
langchain==0.0.350
langchain-openai==0.0.5
langgraph==0.0.26
pydantic==2.5.0
python-multipart==0.0.6
```

```json
// vercel.json
{
  "builds": [
    {
      "src": "api/main.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "api/main.py"
    }
  ],
  "env": {
    "OPENAI_API_KEY": "@openai-api-key"
  }
}
```

---

## **6. MVP Features**

### ✅ **Included**
- **3 Evolution Types**: Simple, Multi-Context, Reasoning
- **FastAPI REST API** with proper error handling
- **Pydantic Models** for request/response validation
- **LangGraph Implementation** with essential nodes
- **Vercel Deployment** ready configuration
- **Demo Endpoint** for easy testing

### ❌ **Excluded from MVP**
- Multi-round evolution iterations
- Complex quality filtering
- Advanced embedding similarity matching
- Extensive error recovery
- Rate limiting & authentication
- Database persistence

---

## **7. Deployment Steps**

1. **Create Project**: `mkdir evol-instruct-api && cd evol-instruct-api`
2. **Add Files**: Copy all files above into structure
3. **Vercel Setup**: `vercel login && vercel`
4. **Set Environment**: Add `OPENAI_API_KEY` in Vercel dashboard
5. **Deploy**: `vercel --prod`

---

## **8. API Usage Example**

```bash
# Test the demo endpoint
curl -X POST "https://your-app.vercel.app/generate-simple"

# Custom documents
curl -X POST "https://your-app.vercel.app/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [
      {
        "page_content": "Your document content here...",
        "metadata": {"source": "doc1.pdf"}
      }
    ],
    "target_questions": 9
  }'
```

This MVP provides the core functionality while being deployable and testable, focusing on the essential requirements: **3 evolution types**, **proper output format**, and **web API accessibility**.
