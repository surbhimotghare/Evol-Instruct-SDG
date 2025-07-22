from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class Document(BaseModel):
    """Document model for LangChain compatibility"""
    page_content: str = Field(..., description="The content of the document page")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata about the document")

    model_config = {
        "json_schema_extra": {
            "example": {
                "page_content": "This is sample document content about student loans and federal aid programs.",
                "metadata": {"source": "student_loans.pdf", "page": 1}
            }
        }
    }

class EvolvedQuestion(BaseModel):
    """Model for evolved questions"""
    id: str = Field(..., description="Unique identifier for the question")
    question: str = Field(..., description="The evolved question text")
    evolution_type: str = Field(..., description="Type of evolution applied (simple, multi_context, reasoning)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "simple_0",
                "question": "What are the specific eligibility requirements for federal student aid programs?",
                "evolution_type": "simple"
            }
        }
    }

class QuestionAnswer(BaseModel):
    """Model for question-answer pairs"""
    question_id: str = Field(..., description="ID of the question this answer corresponds to")
    answer: str = Field(..., description="Generated answer text")

    model_config = {
        "json_schema_extra": {
            "example": {
                "question_id": "simple_0",
                "answer": "To be eligible for federal student aid, students must meet several requirements..."
            }
        }
    }

class QuestionContext(BaseModel):
    """Model for question contexts"""
    question_id: str = Field(..., description="ID of the question this context corresponds to")
    contexts: List[str] = Field(..., description="Relevant document contexts for the question")

    model_config = {
        "json_schema_extra": {
            "example": {
                "question_id": "simple_0",
                "contexts": [
                    "Students must complete the FAFSA form annually...",
                    "Eligibility is determined by financial need..."
                ]
            }
        }
    }

class EvolInstructRequest(BaseModel):
    """Request model for the Evol-Instruct API"""
    documents: List[Document] = Field(..., min_length=1, description="Input documents to generate questions from")
    target_questions: int = Field(default=9, ge=3, le=15, description="Target number of questions to generate")

    model_config = {
        "json_schema_extra": {
            "example": {
                "documents": [
                    {
                        "page_content": "Student loans are financial aid that help students pay for college expenses...",
                        "metadata": {"source": "loan_basics.pdf"}
                    }
                ],
                "target_questions": 9
            }
        }
    }

class EvolInstructResponse(BaseModel):
    """Response model for the Evol-Instruct API"""
    evolved_questions: List[EvolvedQuestion] = Field(..., description="Generated evolved questions")
    question_answers: List[QuestionAnswer] = Field(..., description="Answers for the evolved questions")
    question_contexts: List[QuestionContext] = Field(..., description="Relevant contexts for each question")
    total_questions: int = Field(..., description="Total number of questions generated")
    processing_time: float = Field(..., description="Processing time in seconds")

    model_config = {
        "json_schema_extra": {
            "example": {
                "evolved_questions": [
                    {
                        "id": "simple_0",
                        "question": "What are the specific eligibility requirements for federal student aid?",
                        "evolution_type": "simple"
                    }
                ],
                "question_answers": [
                    {
                        "question_id": "simple_0",
                        "answer": "To be eligible for federal student aid, students must meet several requirements..."
                    }
                ],
                "question_contexts": [
                    {
                        "question_id": "simple_0", 
                        "contexts": ["Students must complete the FAFSA form annually..."]
                    }
                ],
                "total_questions": 9,
                "processing_time": 45.2
            }
        }
    }

class HealthResponse(BaseModel):
    """Health check response model"""
    status: str = Field(..., description="Service health status")
    message: str = Field(..., description="Health status message")
    version: str = Field(..., description="API version")
    graph_status: str = Field(..., description="Graph initialization status")

class ErrorResponse(BaseModel):
    """Error response model"""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[str] = Field(None, description="Additional error details") 