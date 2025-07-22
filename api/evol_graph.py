from typing import TypedDict, List, Dict, Any, Callable, Optional
from langgraph.graph import StateGraph
from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings
import random
import uuid
import asyncio
import logging
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EvolState(TypedDict):
    """State for the Evol-Instruct graph"""
    documents: List[Dict[str, Any]]
    seed_questions: List[Dict[str, Any]]
    evolved_questions: List[Dict[str, Any]]
    question_answers: List[Dict[str, Any]]
    question_contexts: List[Dict[str, Any]]
    current_phase: str
    error: str
    target_questions: int
    progress_callback: Optional[Callable]

class EvolInstructGraph:
    """LangGraph implementation of Evol-Instruct methodology"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini", 
            temperature=0.7,
            max_tokens=1000
        )
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        self.graph = self._build_graph()

    def _emit_progress(self, state: EvolState, step_type: str, message: str, details: Dict[str, Any] = None):
        """Emit progress update if callback is available"""
        if state.get("progress_callback"):
            progress_data = {
                "type": step_type,
                "phase": state["current_phase"],
                "message": message,
                "timestamp": time.time(),
                "details": details or {}
            }
            try:
                state["progress_callback"](progress_data)
            except Exception as e:
                logger.warning(f"Progress callback failed: {e}")

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""
        workflow = StateGraph(EvolState)
        
        # Add nodes for each phase
        workflow.add_node("generate_seeds", self.generate_seed_questions)
        workflow.add_node("simple_evolution", self.simple_evolution)
        workflow.add_node("multi_context_evolution", self.multi_context_evolution)
        workflow.add_node("reasoning_evolution", self.reasoning_evolution)
        workflow.add_node("generate_answers", self.generate_answers)
        workflow.add_node("extract_contexts", self.extract_contexts)
        
        # Define the flow
        workflow.set_entry_point("generate_seeds")
        workflow.add_edge("generate_seeds", "simple_evolution")
        workflow.add_edge("simple_evolution", "multi_context_evolution")
        workflow.add_edge("multi_context_evolution", "reasoning_evolution")
        workflow.add_edge("reasoning_evolution", "generate_answers")
        workflow.add_edge("generate_answers", "extract_contexts")
        workflow.set_finish_point("extract_contexts")
        
        return workflow.compile()

    def generate_seed_questions(self, state: EvolState) -> EvolState:
        """Generate initial seed questions from documents"""
        state["current_phase"] = "seed_generation"
        self._emit_progress(state, "phase_start", "🌱 Generating seed questions...", {
            "total_documents": len(state["documents"])
        })
        
        try:
            seed_questions = []
            target_seeds = min(3, state.get("target_questions", 9) // 3)  # Roughly 1/3 for seeds
            
            # Generate questions from up to 3 documents to keep it manageable
            for i, doc in enumerate(state["documents"][:target_seeds]):
                self._emit_progress(state, "step", f"📄 Processing document {i+1}/{min(len(state['documents']), target_seeds)}", {
                    "document_source": doc.get("metadata", {}).get("source", f"document_{i+1}")
                })
                
                content = doc["page_content"][:1500]  # Limit content length
                
                prompt = f"""Based on this document, generate one clear, specific question that can be answered using the information provided.

Document content:
{content}

Requirements:
- Question should be specific and answerable from the document
- Avoid yes/no questions
- Focus on key information or concepts
- Keep it concise but meaningful

Question:"""

                try:
                    response = self.llm.invoke(prompt)
                    question_text = response.content.strip()
                    
                    # Clean up the question
                    if question_text.startswith('"') and question_text.endswith('"'):
                        question_text = question_text[1:-1]
                    
                    seed_questions.append({
                        "id": f"seed_{i}",
                        "question": question_text,
                        "source_doc_index": i,
                        "metadata": doc.get("metadata", {})
                    })
                    
                    logger.info(f"Generated seed question {i+1}: {question_text[:50]}...")
                    self._emit_progress(state, "success", f"✅ Generated seed question {i+1}", {
                        "question_preview": question_text[:100] + "..." if len(question_text) > 100 else question_text
                    })
                    
                except Exception as e:
                    logger.error(f"Error generating seed question {i+1}: {str(e)}")
                    self._emit_progress(state, "error", f"❌ Failed to generate seed question {i+1}: {str(e)}")
                    continue
            
            state["seed_questions"] = seed_questions
            logger.info(f"Generated {len(seed_questions)} seed questions")
            
            self._emit_progress(state, "phase_complete", f"🎯 Generated {len(seed_questions)} seed questions", {
                "total_questions": len(seed_questions),
                "next_phase": "simple_evolution"
            })
            
            return state
            
        except Exception as e:
            error_msg = f"Error in seed generation: {str(e)}"
            logger.error(error_msg)
            state["error"] = error_msg
            self._emit_progress(state, "error", f"❌ {error_msg}")
            return state

    def simple_evolution(self, state: EvolState) -> EvolState:
        """Apply simple evolution to questions"""
        if state.get("error"):
            return state
            
        state["current_phase"] = "simple_evolution"
        self._emit_progress(state, "phase_start", "🔧 Applying simple evolution...", {
            "evolution_type": "Simple Evolution",
            "description": "Adding constraints, deepening questions, and making them more specific"
        })
        
        try:
            simple_questions = []
            target_count = state.get("target_questions", 9) // 3  # 1/3 for simple evolution
            
            evolution_prompts = [
                "Add specific constraints or conditions to make this question more challenging:",
                "Deepen this question by asking for more detailed analysis or explanation:",
                "Make this question more concrete by asking for specific examples or details:"
            ]
            
            for i, seed_q in enumerate(state["seed_questions"][:target_count]):
                self._emit_progress(state, "step", f"⚙️ Evolving question {i+1}/{min(len(state['seed_questions']), target_count)}", {
                    "original_question": seed_q["question"][:100] + "..." if len(seed_q["question"]) > 100 else seed_q["question"]
                })
                
                evolution_prompt = evolution_prompts[i % len(evolution_prompts)]
                
                prompt = f"""{evolution_prompt}

Original question: {seed_q['question']}

Requirements:
- Make the question more challenging while keeping it answerable
- Maintain relevance to the original document content
- Ensure the evolved question is clear and specific
- Don't change the core topic, just add complexity

Evolved question:"""

                try:
                    response = self.llm.invoke(prompt)
                    evolved_question = response.content.strip()
                    
                    # Clean up the question
                    if evolved_question.startswith('"') and evolved_question.endswith('"'):
                        evolved_question = evolved_question[1:-1]
                    
                    simple_questions.append({
                        "id": f"simple_{i}",
                        "question": evolved_question,
                        "evolution_type": "simple",
                        "source_question_id": seed_q["id"],
                        "source_doc_index": seed_q.get("source_doc_index"),
                        "metadata": seed_q.get("metadata", {})
                    })
                    
                    logger.info(f"Simple evolution {i+1}: {evolved_question[:50]}...")
                    self._emit_progress(state, "success", f"✅ Evolved question {i+1} (Simple)", {
                        "evolved_question": evolved_question[:100] + "..." if len(evolved_question) > 100 else evolved_question
                    })
                    
                except Exception as e:
                    logger.error(f"Error in simple evolution {i+1}: {str(e)}")
                    self._emit_progress(state, "error", f"❌ Failed simple evolution {i+1}: {str(e)}")
                    continue
            
            # Add to evolved questions
            state["evolved_questions"].extend(simple_questions)
            logger.info(f"Generated {len(simple_questions)} simple evolution questions")
            
            self._emit_progress(state, "phase_complete", f"✨ Generated {len(simple_questions)} simple evolution questions", {
                "total_questions": len(simple_questions),
                "next_phase": "multi_context_evolution"
            })
            
            return state
            
        except Exception as e:
            error_msg = f"Error in simple evolution: {str(e)}"
            logger.error(error_msg)
            state["error"] = error_msg
            self._emit_progress(state, "error", f"❌ {error_msg}")
            return state

    def multi_context_evolution(self, state: EvolState) -> EvolState:
        """Create questions requiring multiple document contexts"""
        if state.get("error"):
            return state
            
        state["current_phase"] = "multi_context_evolution"
        self._emit_progress(state, "phase_start", "🔗 Applying multi-context evolution...", {
            "evolution_type": "Multi-Context Evolution",
            "description": "Creating questions that require multiple documents",
            "available_docs": len(state["documents"])
        })
        
        try:
            if len(state["documents"]) < 2:
                logger.warning("Not enough documents for multi-context evolution, using single document")
                self._emit_progress(state, "warning", "⚠️ Limited to single document (only 1 document available)")
                # Fallback to creating complex single-document questions
                return self._single_doc_multi_aspect_evolution(state)
            
            multi_context_questions = []
            target_count = state.get("target_questions", 9) // 3  # 1/3 for multi-context
            
            for i, seed in enumerate(state["seed_questions"][:target_count]):
                self._emit_progress(state, "step", f"🔗 Creating multi-context question {i+1}/{min(len(state['seed_questions']), target_count)}", {
                    "base_question": seed["question"][:100] + "..." if len(seed["question"]) > 100 else seed["question"]
                })
                
                try:
                    # Get content from multiple documents
                    doc_contents = []
                    for j, doc in enumerate(state["documents"][:3]):
                        content_preview = doc["page_content"][:800]
                        doc_contents.append(f"Document {j+1}: {content_preview}")
                    
                    combined_context = "\n\n".join(doc_contents)
                    
                    prompt = f"""You are creating questions that require synthesizing information from multiple documents.

Base question: {seed['question']}

Available document contexts:
{combined_context}

Create a new question that:
- Requires information from at least 2 different documents
- Asks for comparison, connection, or synthesis across documents
- Is more complex than the original question
- Can still be answered using the provided documents

Examples of multi-context questions:
- "How do the requirements in Document 1 relate to the processes described in Document 2?"
- "Compare and contrast the approaches described in Documents 1 and 2"
- "What are the implications of Document 1's policies for the scenarios in Document 2?"

Multi-context question:"""

                    response = self.llm.invoke(prompt)
                    evolved_text = response.content.strip()
                    
                    # Clean up the response
                    if evolved_text.startswith('"') and evolved_text.endswith('"'):
                        evolved_text = evolved_text[1:-1]
                    
                    multi_context_questions.append({
                        "id": f"multi_context_{i}",
                        "question": evolved_text,
                        "evolution_type": "multi_context",
                        "source_question_id": seed["id"],
                        "requires_multiple_docs": True,
                        "metadata": seed.get("metadata", {})
                    })
                    
                    logger.info(f"Multi-context evolution {i+1}: {evolved_text[:50]}...")
                    self._emit_progress(state, "success", f"✅ Created multi-context question {i+1}", {
                        "question_preview": evolved_text[:100] + "..." if len(evolved_text) > 100 else evolved_text
                    })
                    
                except Exception as e:
                    logger.error(f"Error in multi-context evolution {i+1}: {str(e)}")
                    self._emit_progress(state, "error", f"❌ Failed multi-context evolution {i+1}: {str(e)}")
                    continue
            
            state["evolved_questions"].extend(multi_context_questions)
            logger.info(f"Generated {len(multi_context_questions)} multi-context questions")
            
            self._emit_progress(state, "phase_complete", f"🔗 Generated {len(multi_context_questions)} multi-context questions", {
                "total_questions": len(multi_context_questions),
                "next_phase": "reasoning_evolution"
            })
            
            return state
            
        except Exception as e:
            error_msg = f"Error in multi-context evolution: {str(e)}"
            logger.error(error_msg)
            state["error"] = error_msg
            self._emit_progress(state, "error", f"❌ {error_msg}")
            return state

    def _single_doc_multi_aspect_evolution(self, state: EvolState) -> EvolState:
        """Fallback for multi-context when only one document is available"""
        evolved_questions = []
        seeds_to_use = state["seed_questions"][:3]
        
        for i, seed in enumerate(seeds_to_use):
            try:
                prompt = f"""Create a more complex question that examines multiple aspects of the topic.

Original question: {seed['question']}

Transform this into a question that:
- Examines multiple facets or aspects of the topic
- Requires connecting different concepts within the document
- Is more comprehensive and analytical

Multi-aspect question:"""

                response = self.llm.invoke(prompt)
                evolved_text = response.content.strip()
                
                if evolved_text.startswith('"') and evolved_text.endswith('"'):
                    evolved_text = evolved_text[1:-1]
                
                evolved_questions.append({
                    "id": f"multi_context_{i}",
                    "question": evolved_text,
                    "evolution_type": "multi_context",
                    "parent_id": seed["id"],
                    "source_doc_index": seed["source_doc_index"]
                })
                
            except Exception as e:
                logger.error(f"Error in single-doc multi-aspect evolution {i}: {str(e)}")
                continue
        
        state["evolved_questions"].extend(evolved_questions)
        return state

    def reasoning_evolution(self, state: EvolState) -> EvolState:
        """Create questions requiring logical reasoning"""
        if state.get("error"):
            return state
            
        state["current_phase"] = "reasoning_evolution"
        self._emit_progress(state, "phase_start", "🧠 Applying reasoning evolution...", {
            "evolution_type": "Reasoning Evolution",
            "description": "Creating questions that require logical inference and reasoning"
        })
        
        try:
            reasoning_questions = []
            target_count = state.get("target_questions", 9) // 3  # 1/3 for reasoning
            
            reasoning_patterns = [
                "If the information in the document is true, what logical conclusions can be drawn?",
                "What would be the implications if the conditions described in the document changed?",
                "Based on the patterns or trends in the document, what predictions can be made?"
            ]
            
            for i, seed in enumerate(state["seed_questions"][:target_count]):
                self._emit_progress(state, "step", f"🧠 Creating reasoning question {i+1}/{min(len(state['seed_questions']), target_count)}", {
                    "base_question": seed["question"][:100] + "..." if len(seed["question"]) > 100 else seed["question"]
                })
                
                try:
                    reasoning_type = reasoning_patterns[i % len(reasoning_patterns)]
                    
                    # Get relevant document content
                    doc_index = seed.get("source_doc_index", 0)
                    doc_content = state["documents"][doc_index]["page_content"][:1000]
                    
                    prompt = f"""Transform this question to require logical reasoning and inference.

Original question: {seed['question']}
Document context: {doc_content}

Reasoning approach: {reasoning_type}

Create a new question that:
- Requires logical reasoning beyond just finding information
- Asks for inference, implications, or predictions
- Is answerable but requires thinking and analysis
- Uses "If...", "Why might...", "What would happen if...", "How could..." patterns

Reasoning question:"""

                    response = self.llm.invoke(prompt)
                    evolved_text = response.content.strip()
                    
                    # Clean up the response
                    if evolved_text.startswith('"') and evolved_text.endswith('"'):
                        evolved_text = evolved_text[1:-1]
                    
                    reasoning_questions.append({
                        "id": f"reasoning_{i}",
                        "question": evolved_text,
                        "evolution_type": "reasoning",
                        "source_question_id": seed["id"],
                        "requires_reasoning": True,
                        "source_doc_index": seed.get("source_doc_index"),
                        "metadata": seed.get("metadata", {})
                    })
                    
                    logger.info(f"Reasoning evolution {i+1}: {evolved_text[:50]}...")
                    self._emit_progress(state, "success", f"✅ Created reasoning question {i+1}", {
                        "question_preview": evolved_text[:100] + "..." if len(evolved_text) > 100 else evolved_text
                    })
                    
                except Exception as e:
                    logger.error(f"Error in reasoning evolution {i+1}: {str(e)}")
                    self._emit_progress(state, "error", f"❌ Failed reasoning evolution {i+1}: {str(e)}")
                    continue
            
            state["evolved_questions"].extend(reasoning_questions)
            logger.info(f"Generated {len(reasoning_questions)} reasoning questions")
            
            self._emit_progress(state, "phase_complete", f"🧠 Generated {len(reasoning_questions)} reasoning questions", {
                "total_questions": len(reasoning_questions),
                "next_phase": "generate_answers"
            })
            
            return state
            
        except Exception as e:
            error_msg = f"Error in reasoning evolution: {str(e)}"
            logger.error(error_msg)
            state["error"] = error_msg
            self._emit_progress(state, "error", f"❌ {error_msg}")
            return state

    def generate_answers(self, state: EvolState) -> EvolState:
        """Generate answers for all evolved questions"""
        if state.get("error"):
            return state
            
        state["current_phase"] = "generate_answers"
        total_questions = len(state["evolved_questions"])
        self._emit_progress(state, "phase_start", "💡 Generating answers...", {
            "total_questions": total_questions,
            "description": "Creating comprehensive answers for all evolved questions"
        })
        
        try:
            answers = []
            
            for i, question in enumerate(state["evolved_questions"]):
                self._emit_progress(state, "step", f"💡 Generating answer {i+1}/{total_questions}", {
                    "question_id": question["id"],
                    "question_type": question.get("evolution_type", "unknown")
                })
                
                try:
                    # Get relevant document content
                    if question.get("requires_multiple_docs"):
                        # Use multiple documents for multi-context questions
                        context_parts = []
                        for doc in state["documents"][:3]:
                            context_parts.append(doc["page_content"][:1000])
                        context = "\n\n".join(context_parts)
                    else:
                        # Use single document
                        doc_index = question.get("source_doc_index", 0)
                        if doc_index < len(state["documents"]):
                            context = state["documents"][doc_index]["page_content"]
                        else:
                            context = state["documents"][0]["page_content"]
                    
                    prompt = f"""Answer this question comprehensively using the provided context.

Question: {question['question']}

Context:
{context}

Requirements:
- Provide a detailed, well-structured answer
- Use information directly from the context
- If the question requires reasoning, show your logical steps
- Be specific and accurate
- If information is insufficient, state what additional data would be needed

Answer:"""

                    response = self.llm.invoke(prompt)
                    answer_text = response.content.strip()
                    
                    answers.append({
                        "question_id": question["id"],
                        "answer": answer_text,
                        "question_type": question.get("evolution_type", "unknown")
                    })
                    
                    logger.info(f"Generated answer for {question['id']}")
                    self._emit_progress(state, "success", f"✅ Answer generated for {question['id']}", {
                        "answer_length": len(answer_text)
                    })
                    
                except Exception as e:
                    logger.error(f"Error generating answer for {question['id']}: {str(e)}")
                    self._emit_progress(state, "error", f"❌ Failed to generate answer for {question['id']}: {str(e)}")
                    continue
            
            state["question_answers"] = answers
            logger.info(f"Generated {len(answers)} answers")
            
            self._emit_progress(state, "phase_complete", f"💡 Generated {len(answers)} answers", {
                "total_answers": len(answers),
                "next_phase": "extract_contexts"
            })
            
            return state
            
        except Exception as e:
            error_msg = f"Error in answer generation: {str(e)}"
            logger.error(error_msg)
            state["error"] = error_msg
            self._emit_progress(state, "error", f"❌ {error_msg}")
            return state

    def extract_contexts(self, state: EvolState) -> EvolState:
        """Extract relevant contexts for each question"""
        if state.get("error"):
            return state
            
        state["current_phase"] = "extract_contexts"
        total_questions = len(state["evolved_questions"])
        self._emit_progress(state, "phase_start", "📚 Extracting contexts...", {
            "total_questions": total_questions,
            "description": "Finding relevant document snippets for each question"
        })
        
        try:
            contexts = []
            
            for i, question in enumerate(state["evolved_questions"]):
                self._emit_progress(state, "step", f"📚 Extracting context {i+1}/{total_questions}", {
                    "question_id": question["id"],
                    "question_type": question.get("evolution_type", "unknown")
                })
                
                try:
                    question_contexts = []
                    question_text = question["question"].lower()
                    
                    # For multi-context questions, check all documents
                    if question.get("requires_multiple_docs"):
                        docs_to_check = state["documents"][:3]
                    else:
                        # For single-doc questions, prioritize the source document
                        doc_index = question.get("source_doc_index", 0)
                        if doc_index < len(state["documents"]):
                            docs_to_check = [state["documents"][doc_index]]
                        else:
                            docs_to_check = [state["documents"][0]]
                    
                    for doc in docs_to_check:
                        content = doc["page_content"]
                        
                        # Split content into sentences/chunks for context extraction
                        chunks = [chunk.strip() for chunk in content.split('.') if chunk.strip()]
                        
                        # Simple keyword matching for context relevance
                        relevant_chunks = []
                        question_words = set(question_text.split())
                        
                        for chunk in chunks:
                            chunk_words = set(chunk.lower().split())
                            # Check for word overlap (simple relevance scoring)
                            overlap = len(question_words.intersection(chunk_words))
                            if overlap >= 2 or len(chunk) > 200:  # Either good overlap or substantial chunk
                                relevant_chunks.append(chunk)
                        
                        # Take top relevant chunks
                        if relevant_chunks:
                            question_contexts.extend(relevant_chunks[:2])  # Max 2 per document
                    
                    # If no contexts found, use document beginnings
                    if not question_contexts:
                        for doc in docs_to_check:
                            question_contexts.append(doc["page_content"][:300])
                    
                    contexts.append({
                        "question_id": question["id"],
                        "contexts": question_contexts[:3]  # Max 3 contexts per question
                    })
                    
                    logger.info(f"Extracted {len(question_contexts)} contexts for {question['id']}")
                    self._emit_progress(state, "success", f"✅ Contexts extracted for {question['id']}", {
                        "context_count": len(question_contexts)
                    })
                    
                except Exception as e:
                    logger.error(f"Error extracting contexts for {question['id']}: {str(e)}")
                    self._emit_progress(state, "error", f"❌ Failed to extract contexts for {question['id']}: {str(e)}")
                    continue
            
            state["question_contexts"] = contexts
            logger.info(f"Extracted contexts for {len(contexts)} questions")
            
            self._emit_progress(state, "phase_complete", f"📚 Extracted contexts for {len(contexts)} questions", {
                "total_contexts": len(contexts),
                "pipeline_complete": True
            })
            
            return state
            
        except Exception as e:
            error_msg = f"Error in context extraction: {str(e)}"
            logger.error(error_msg)
            state["error"] = error_msg
            self._emit_progress(state, "error", f"❌ {error_msg}")
            return state

    async def run(self, documents: List[Any], target_questions: int = 9, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Execute the full Evol-Instruct pipeline"""
        start_time = time.time()
        logger.info("Starting Evol-Instruct pipeline...")
        
        # Convert documents to dict format if they're Pydantic models
        if hasattr(documents[0], 'dict'):
            doc_dicts = [doc.dict() for doc in documents]
        else:
            doc_dicts = documents
        
        initial_state: EvolState = {
            "documents": doc_dicts,
            "seed_questions": [],
            "evolved_questions": [],
            "question_answers": [],
            "question_contexts": [],
            "current_phase": "initialized",
            "error": "",
            "target_questions": target_questions,
            "progress_callback": progress_callback
        }
        
        # Initial progress update
        if progress_callback:
            progress_callback({
                "type": "start",
                "phase": "initialization", 
                "message": "🚀 Initializing Evol-Instruct pipeline...",
                "timestamp": time.time(),
                "details": {
                    "total_documents": len(documents),
                    "target_questions": target_questions
                }
            })
        
        try:
            # Run the graph
            final_state = await self.graph.ainvoke(initial_state)
            
            if final_state.get("error"):
                raise Exception(f"Pipeline error: {final_state['error']}")
            
            processing_time = time.time() - start_time
            logger.info(f"Evol-Instruct pipeline completed successfully in {processing_time:.2f} seconds")
            
            # Final progress update
            if progress_callback:
                progress_callback({
                    "type": "complete",
                    "phase": "finished",
                    "message": "🎉 Pipeline completed successfully!",
                    "timestamp": time.time(),
                    "details": {
                        "total_questions": len(final_state["evolved_questions"]),
                        "total_answers": len(final_state["question_answers"]),
                        "total_contexts": len(final_state["question_contexts"]),
                        "processing_time": processing_time
                    }
                })
            
            return {
                "evolved_questions": final_state["evolved_questions"],
                "question_answers": final_state["question_answers"],
                "question_contexts": final_state["question_contexts"],
                "total_questions": len(final_state["evolved_questions"]),
                "processing_time": processing_time,
                "seed_questions": final_state["seed_questions"]  # For debugging
            }
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"Pipeline execution failed: {str(e)}"
            logger.error(f"Error running Evol-Instruct pipeline: {str(e)}")
            
            if progress_callback:
                progress_callback({
                    "type": "error",
                    "phase": "error",
                    "message": f"❌ {error_msg}",
                    "timestamp": time.time(),
                    "details": {"error": str(e), "processing_time": processing_time}
                })
                
            raise Exception(error_msg)

# Global instance for reuse
evol_graph_instance = None

def get_evol_graph() -> EvolInstructGraph:
    """Get singleton instance of EvolInstructGraph"""
    global evol_graph_instance
    if evol_graph_instance is None:
        evol_graph_instance = EvolInstructGraph()
    return evol_graph_instance 