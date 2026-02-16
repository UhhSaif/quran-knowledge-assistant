"""Main FastAPI application for Quran Knowledge Assistant."""

import os
import time
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from google import genai

from src.rag.rag_manager import RAGManager
from src.tools.web_search import WebSearchTool
from src.agents.researcher_agent import ResearcherAgent
from src.agents.context_agent import ContextAgent
from src.agents.orchestrator_agent import OrchestratorAgent
from src.observability.logging import logger

# Load environment variables
load_dotenv()

# Global state
rag_manager = None
orchestrator_agent = None
genai_client = None
ingestion_thread = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle management for FastAPI app."""
    global rag_manager, orchestrator_agent, genai_client, ingestion_thread

    logger.info("Starting Quran Knowledge Assistant API")

    # Initialize paths
    knowledge_base_dir = Path("knowledge_base")
    index_dir = Path("index")

    knowledge_base_dir.mkdir(exist_ok=True)
    index_dir.mkdir(exist_ok=True)

    # Initialize RAG Manager
    logger.info("Initializing RAG Manager")
    rag_manager = RAGManager(
        knowledge_base_dir=knowledge_base_dir,
        index_dir=index_dir
    )

    # Try to load existing index, otherwise start background ingestion
    if not rag_manager.load_index():
        logger.info("Starting background document ingestion")
        ingestion_thread = rag_manager.ingest_in_background()
    else:
        logger.info("Loaded existing index")

    # Initialize Google GenAI client
    api_key = os.getenv("GOOGLE_GENAI_API_KEY")
    use_vertexai = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "false").lower() == "true"

    if use_vertexai:
        project = os.getenv("GOOGLE_CLOUD_PROJECT")
        location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
        genai_client = genai.Client(
            vertexai=True,
            project=project,
            location=location
        )
        logger.info("Initialized Vertex AI client", project=project, location=location)
    elif api_key:
        genai_client = genai.Client(api_key=api_key)
        logger.info("Initialized GenAI client with API key")
    else:
        raise ValueError("Either GOOGLE_GENAI_API_KEY or GOOGLE_GENAI_USE_VERTEXAI must be set")

    # Initialize agents
    logger.info("Initializing agents")

    web_search_tool = WebSearchTool()
    researcher_agent = ResearcherAgent(rag_manager=rag_manager)
    context_agent = ContextAgent(web_search_tool=web_search_tool)

    orchestrator_agent = OrchestratorAgent(
        researcher_agent=researcher_agent,
        context_agent=context_agent,
        client=genai_client
    )

    logger.info("All agents initialized successfully")

    yield

    # Cleanup
    logger.info("Shutting down Quran Knowledge Assistant API")


# Create FastAPI app
app = FastAPI(
    title="Quran Knowledge Assistant",
    description="Multi-Agent system for Quranic knowledge using Google ADK",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for the web UI
static_dir = Path(__file__).parent.parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# Request/Response models
class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


class ChatResponse(BaseModel):
    response: str
    session_id: str
    latency_ms: float


class HealthResponse(BaseModel):
    status: str
    rag_ready: bool
    agents_initialized: bool


# Endpoints
@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    logger.info("Health check requested")

    return HealthResponse(
        status="healthy",
        rag_ready=rag_manager.is_ready if rag_manager else False,
        agents_initialized=orchestrator_agent is not None
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Main chat endpoint for querying the Quran assistant.

    Example queries:
    - "What does the Quran say about patience?"
    - "Find verses about Prophet Moses"
    - "What's the context of Surah Al-Fatiha?"
    """
    start_time = time.time()

    logger.info(
        "Chat request received",
        message_preview=request.message[:100],
        session_id=request.session_id
    )

    try:
        if not orchestrator_agent:
            raise HTTPException(
                status_code=503,
                detail="Agents not initialized yet"
            )

        if not rag_manager.is_ready:
            logger.warning("RAG system not ready, query may have limited results")

        # Process query with orchestrator
        response = orchestrator_agent.process_query(request.message)

        latency_ms = (time.time() - start_time) * 1000

        logger.info(
            "Chat request completed",
            session_id=request.session_id,
            latency_ms=latency_ms,
            response_length=len(response)
        )

        return ChatResponse(
            response=response,
            session_id=request.session_id,
            latency_ms=latency_ms
        )

    except Exception as e:
        logger.error(
            "Chat request failed",
            session_id=request.session_id,
            error=str(e),
            error_type=type(e).__name__
        )

        raise HTTPException(
            status_code=500,
            detail=f"Error processing query: {str(e)}"
        )


@app.get("/test-error")
async def test_error() -> Dict[str, Any]:
    """Test endpoint to verify error handling and logging."""
    logger.info("Test error endpoint called")

    try:
        raise ValueError("This is a test error for observability testing")
    except ValueError as e:
        logger.error(
            "Test error triggered",
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@app.get("/")
async def root():
    """Serve the chat UI."""
    static_dir = Path(__file__).parent.parent / "static"
    return FileResponse(static_dir / "index.html")


@app.get("/api/info")
async def api_info() -> Dict[str, Any]:
    """API information endpoint."""
    return {
        "service": "Quran Knowledge Assistant",
        "version": "1.0.0",
        "description": "Multi-Agent system using Google ADK for Quranic knowledge",
        "endpoints": {
            "/": "Chat UI",
            "/health": "Health check",
            "/chat": "Chat with the assistant (POST)",
            "/test-error": "Test error handling"
        }
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8080"))

    logger.info(
        "Starting uvicorn server",
        port=port,
        host="0.0.0.0"
    )

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )
