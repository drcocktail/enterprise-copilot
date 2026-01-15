# Enterprise Copilot Backend

IAM-First Agentic Enterprise Assistant with RAG, Code Intelligence, and Action Execution.

## Architecture

```
backend/
├── main.py                      # FastAPI application
├── config/
│   └── iam_config.py           # IAM personas & permissions
├── services/
│   ├── audit_logger.py         # Immutable audit logging
│   ├── rag_service.py          # Document RAG with ChromaDB
│   ├── code_intelligence.py   # AST-based code indexing
│   ├── llm_service.py          # Ollama LLM integration
│   └── action_executor.py      # Validated action execution
└── requirements.txt
```

## Setup

### 1. Install Dependencies

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Install Ollama

```bash
# macOS
brew install ollama

# Start Ollama service
ollama serve

# Pull models (in another terminal)
ollama pull llama3.2
ollama pull nomic-embed-text
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your configuration
```

### 4. Ingest Documents

```bash
# Start the server first
python main.py

# In another terminal, trigger document ingestion
curl -X POST http://localhost:8000/api/ingest/documents \
  -H "x-iam-role: CHIEF_STRATEGY_OFFICER"
```

### 5. Index Codebase (Optional)

```bash
curl -X POST "http://localhost:8000/api/ingest/codebase?path=/path/to/your/code" \
  -H "x-iam-role: SR_DEVOPS_ENGINEER"
```

## API Endpoints

### Core Endpoints

- `POST /api/chat` - Main chat interface with IAM enforcement
- `GET /api/personas` - Get available personas
- `GET /api/audit/logs` - Get audit logs
- `WS /ws/audit` - Real-time audit log streaming

### Admin Endpoints

- `POST /api/ingest/documents` - Ingest PDF documents
- `POST /api/ingest/codebase` - Index codebase
- `GET /api/health` - Service health check

## IAM Personas

### C-Suite Executive (CHIEF_STRATEGY_OFFICER)
- Access: Financial reports, strategy documents
- Actions: Schedule meetings, view analytics
- Denied: Source code, employee PII

### HR Director (HR_DIRECTOR)
- Access: Employee data, policies
- Actions: Draft policies, schedule interviews
- Denied: Source code, detailed financials

### DevOps Engineer (SR_DEVOPS_ENGINEER)
- Access: Codebase, logs, technical docs
- Actions: Create JIRA tickets, search code
- Denied: Employee PII, salary data

## Testing

### Test Chat Endpoint

```bash
# C-Suite: Financial query (ALLOWED)
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "x-iam-role: CHIEF_STRATEGY_OFFICER" \
  -d '{"query": "Summarize Q3 revenue from the annual report"}'

# C-Suite: Code query (DENIED)
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "x-iam-role: CHIEF_STRATEGY_OFFICER" \
  -d '{"query": "Show me the authentication function code"}'

# DevOps: Code query (ALLOWED)
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "x-iam-role: SR_DEVOPS_ENGINEER" \
  -d '{"query": "Find the auth middleware function"}'
```

## Development

```bash
# Run with auto-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Or use the main.py directly
python main.py
```

## Production Deployment

For production, consider:

1. **Database**: Replace in-memory audit logs with PostgreSQL/MongoDB
2. **Vector Store**: Use hosted Pinecone or Weaviate for scalability
3. **Authentication**: Add JWT/OAuth for real user authentication
4. **Rate Limiting**: Implement rate limiting per user/role
5. **Monitoring**: Add Prometheus metrics and error tracking
6. **HTTPS**: Enable TLS for secure communication

## Troubleshooting

### Ollama Connection Issues
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Restart Ollama
ollama serve
```

### ChromaDB Issues
```bash
# Delete and recreate collection
rm -rf chroma_db/
# Restart server to recreate
```

### Import Errors
```bash
# Ensure virtual environment is activated
source venv/bin/activate
pip install -r requirements.txt
```
