# Multi-Agent Quran Knowledge Assistant

A sophisticated multi-agent intelligence system built with Google ADK for answering questions about the Holy Quran. This system combines RAG (Retrieval-Augmented Generation) with web search capabilities to provide accurate, contextual answers with proper citations.

## 🏗️ Architecture

### Multi-Agent System (Google ADK)

The system implements 3 specialized agents with 2 communication patterns:

#### Agents

1. **ResearcherAgent**
   - Searches FAISS vector store for Quran verses
   - Retrieves citations in Surah:Ayah format
   - Finds thematically related passages
   - Uses RAG pipeline for semantic search

2. **ContextAgent**
   - Uses Tavily API for scholarly tafsir and interpretations
   - Searches for historical context (asbab al-nuzul)
   - Provides scholarly perspectives from web sources

3. **OrchestratorAgent**
   - Routes queries intelligently
   - Decides between RAG vs Web Search based on query type
   - Combines outputs from sub-agents
   - Performs QA checks and synthesis

#### Communication Patterns

- **Sequential Flow**: Orchestrator → Researcher → Context → Orchestrator
- **Hierarchical Delegation**: Orchestrator manages both sub-agents

## 🔧 Technical Stack

- **Google ADK**: Multi-agent framework
- **Vertex AI**: text-embedding-005 for embeddings
- **FAISS**: Vector similarity search
- **Tavily API**: Web search for scholarly content
- **FastAPI**: REST API endpoints
- **Google Cloud Run**: Serverless deployment
- **Structured Logging**: GCP Cloud Logging compatible

## 📁 Project Structure

```
SynapseAI_QuranProject/
├── src/
│   ├── agents/              # Agent implementations
│   │   ├── researcher_agent.py
│   │   ├── context_agent.py
│   │   └── orchestrator_agent.py
│   ├── rag/                 # RAG pipeline
│   │   ├── document_processor.py
│   │   ├── embeddings.py
│   │   ├── vector_store.py
│   │   └── rag_manager.py
│   ├── tools/               # Custom tools
│   │   └── web_search.py
│   ├── observability/       # Logging and monitoring
│   │   └── logging.py
│   └── main.py              # FastAPI application
├── knowledge_base/          # Quran PDFs
├── deployment/              # Cloud Run configs
├── requirements.txt
├── Dockerfile
└── README.md
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Google Cloud Project with Vertex AI enabled
- Tavily API key
- Quran translation PDF (place in `knowledge_base/`)

### Local Development

1. **Clone and setup**:
```bash
git clone <your-repo>
cd SynapseAI_QuranProject
```

2. **Create virtual environment**:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Configure environment**:
```bash
cp .env.example .env
# Edit .env with your credentials
```

Required environment variables:
```bash
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_GENAI_USE_VERTEXAI=true  # or use GOOGLE_GENAI_API_KEY
TAVILY_API_KEY=your-tavily-key
```

5. **Add Quran PDF**:
Place an English translation of the Quran (PDF format) in the `knowledge_base/` directory.

6. **Run the application**:
```bash
uvicorn src.main:app --reload --port 8080
```

The API will be available at `http://localhost:8080`

## 📡 API Endpoints

### Health Check
```bash
GET /health
```

Response:
```json
{
  "status": "healthy",
  "rag_ready": true,
  "agents_initialized": true
}
```

### Chat
```bash
POST /chat
Content-Type: application/json

{
  "message": "What does the Quran say about patience?",
  "session_id": "user123"
}
```

Response:
```json
{
  "response": "...",
  "session_id": "user123",
  "latency_ms": 1234.56
}
```

### Test Error (for observability testing)
```bash
GET /test-error
```

## 💬 Example Queries

The system can handle various types of questions:

### Verse Search
- "What does the Quran say about patience?"
- "Find verses about Prophet Moses"
- "Show me all references to charity"

### Historical Context
- "What was happening when Surah Al-Kahf was revealed?"
- "What's the context of Surah Al-Fatiha?"

### Tafsir/Interpretation
- "What is the meaning of Ayat al-Kursi?"
- "Explain the interpretation of Surah Al-Ikhlas"

## ☁️ Cloud Run Deployment

### Option 1: Using the deployment script

```bash
# Set environment variables
export GOOGLE_CLOUD_PROJECT=your-project-id
export TAVILY_API_KEY=your-tavily-key

# Run deployment script
./deployment/deploy.sh
```

### Option 2: Manual deployment

```bash
# Build and push image
docker build -t gcr.io/YOUR_PROJECT/quran-assistant .
docker push gcr.io/YOUR_PROJECT/quran-assistant

# Deploy to Cloud Run
gcloud run deploy quran-assistant \
  --image gcr.io/YOUR_PROJECT/quran-assistant \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=YOUR_PROJECT,GOOGLE_GENAI_USE_VERTEXAI=true" \
  --set-secrets "TAVILY_API_KEY=TAVILY_API_KEY:latest"
```

### Option 3: Cloud Build

```bash
gcloud builds submit --config deployment/cloudbuild.yaml
```

## 🧪 Testing

### Test locally
```bash
# Health check
curl http://localhost:8080/health

# Chat request
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What does the Quran say about patience?",
    "session_id": "test"
  }'

# Test error handling
curl http://localhost:8080/test-error
```

### Test on Cloud Run
Replace `YOUR_SERVICE_URL` with your Cloud Run service URL:

```bash
curl https://YOUR_SERVICE_URL/health
curl -X POST https://YOUR_SERVICE_URL/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Find verses about gratitude"}'
```

## 📊 RAG Pipeline

The RAG system processes documents through the following pipeline:

1. **PDF Extraction**: Extract text from Quran PDFs
2. **Semantic Chunking**: Split into meaningful verse-based chunks
3. **Embedding Generation**: Vertex AI text-embedding-005 (768 dimensions)
4. **Vector Storage**: FAISS IndexFlatL2 for similarity search
5. **Retrieval**: Top-k semantic search with distance scores

## 🔍 Observability

### Structured Logging

All logs are in JSON format compatible with GCP Cloud Logging:

```json
{
  "timestamp": "2026-02-15T10:30:00Z",
  "severity": "INFO",
  "logger": "quran-assistant",
  "message": "Chat request completed",
  "session_id": "user123",
  "latency_ms": 1234.56
}
```

### Metrics Tracked

- Request latency
- RAG retrieval performance
- Agent execution times
- Error rates and types

## 🔐 Security Notes

- API keys stored in Google Secret Manager
- No sensitive data in logs
- CORS configured for web access
- Environment variables for all credentials

## 📝 Project Requirements Met

- ✅ Google ADK Multi-Agent System (40%)
  - 3 specialized agents (Orchestrator, Researcher, Context)
  - 2 communication patterns (Sequential, Hierarchical)
  - State management with sessions

- ✅ RAG Support (25%)
  - PDF extraction and semantic chunking
  - Vertex AI text-embedding-005
  - FAISS vector storage

- ✅ Web Search Capabilities (15%)
  - Tavily API integration
  - Intelligent routing between RAG and web search

- ✅ Custom Tools (10%)
  - Web search tool
  - RAG retrieval tool

- ✅ Observability (10%)
  - Structured JSON logging
  - Request latency tracking
  - Error monitoring

## 🎓 Academic Use

This project was created as a class assignment demonstrating:
- Multi-agent system design
- RAG implementation
- Cloud-native deployment
- Production-ready observability

## 📄 License

This is an educational project for academic purposes.

## 🤝 Contributing

This is a class assignment project. For educational reference only.

## 📧 Support

For questions about this implementation, please refer to the Google ADK documentation and course materials.
