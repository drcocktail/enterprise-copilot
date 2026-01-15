# Agentic Enterprise Copilot

**IAM-First Enterprise Assistant** with RAG, Code Intelligence, and Action Execution

> Privacy-first, role-aware corporate assistant serving multiple personas (C-Suite, HR, IT) from a single interface. Built with the philosophy: "The copilot can never exceed the authority of the user it serves."

## 🎯 Project Vision

Build a comprehensive enterprise copilot that:
- ✅ Enforces strict IAM controls at the query level
- ✅ Retrieves contextual information from documents and code
- ✅ Executes validated actions (Jira tickets, calendar events, etc.)
- ✅ Provides full audit trail with immutable logging
- ✅ Works with local LLMs (Ollama) for privacy

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       Frontend (React)                       │
│  Persona Switcher │ Chat UI │ Audit Viewer │ Dashboard      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Backend (FastAPI)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ IAM Middleware│  │ Audit Logger │  │  LLM Service │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ RAG Service  │  │Code Intel.   │  │Action Executor│     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
              ┌──────────┐        ┌──────────┐
              │ ChromaDB │        │  Ollama  │
              │ (Vectors)│        │  (LLM)   │
              └──────────┘        └──────────┘
```

## 📁 Project Structure

```
nlp-challenge-hcltech/
├── backend/                    # FastAPI Backend
│   ├── main.py                # API endpoints
│   ├── config/
│   │   └── iam_config.py     # IAM personas & permissions
│   ├── services/
│   │   ├── audit_logger.py   # Immutable audit logging
│   │   ├── rag_service.py    # Document RAG with ChromaDB
│   │   ├── code_intelligence.py  # AST-based code indexing
│   │   ├── llm_service.py    # Ollama integration
│   │   └── action_executor.py    # Validated action execution
│   ├── requirements.txt
│   └── README.md
├── frontend/                   # React Frontend
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── services/
│   │   │   └── api.js        # Backend API client
│   │   ├── App.jsx           # Main application
│   │   └── main.jsx
│   ├── package.json
│   └── README.md
├── docs/
│   └── Annual-Report-2024-25.pdf  # Sample document
├── main.jsx                    # Original prototype
└── task.md                     # Project specification
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- Ollama (for local LLM)

### 1. Install Ollama

```bash
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama service
ollama serve

# Pull models (in another terminal)
ollama pull llama3.2
ollama pull nomic-embed-text
```

### 2. Setup Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start server
python main.py
```

Backend will be available at `http://localhost:8000`

### 3. Setup Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend will be available at `http://localhost:3000`

### 4. Ingest Documents

```bash
# Trigger document ingestion
curl -X POST http://localhost:8000/api/ingest/documents \
  -H "x-iam-role: CHIEF_STRATEGY_OFFICER"
```

## 🎭 IAM Personas

### Chief Strategy Officer (Eleanor Vance)
- **Permissions**: Financial reports, strategy documents, aggregate HR data
- **Actions**: Schedule meetings, view analytics
- **Denied**: Source code access, employee PII

### HR Director (Marcus Thorne)
- **Permissions**: Employee data, HR policies, PII
- **Actions**: Draft policies, schedule interviews
- **Denied**: Source code, detailed financials

### DevOps Engineer (Sarah Chen)
- **Permissions**: Codebase, logs, technical documentation
- **Actions**: Create Jira tickets, search code, restart services
- **Denied**: Employee PII, salary data

## 🧪 Testing IAM Enforcement

### Allowed: C-Suite Financial Query
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "x-iam-role: CHIEF_STRATEGY_OFFICER" \
  -d '{"query": "Summarize Q3 revenue from the annual report"}'
```

### Denied: C-Suite Code Query
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "x-iam-role: CHIEF_STRATEGY_OFFICER" \
  -d '{"query": "Show me the authentication function code"}'
```

### Allowed: DevOps Code Query
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "x-iam-role: SR_DEVOPS_ENGINEER" \
  -d '{"query": "Find the auth middleware function"}'
```

## 🔑 Key Features

### 1. IAM-First Architecture
- Pre-computation capability checks before LLM invocation
- Deterministic security layer prevents unauthorized access
- Role-based metadata filtering for document retrieval

### 2. Advanced RAG
- PDF ingestion with metadata extraction
- Page-level citations in responses
- Sensitivity-based filtering
- Hybrid search (semantic + keyword)

### 3. Code Intelligence
- AST-based code indexing
- Function/class extraction with signatures
- Semantic code search
- Supports Python codebases (extensible)

### 4. Action Execution
- JSON schema validation for all actions
- Create Jira tickets, schedule meetings, draft documents
- Dry-run validation before execution
- Audit trail for all actions

### 5. Audit Logging
- Immutable log format
- Real-time WebSocket streaming
- Trace ID for debugging
- Query-level authorization tracking

## 📊 API Endpoints

### Core
- `POST /api/chat` - Main chat interface
- `GET /api/personas` - Available personas
- `GET /api/audit/logs` - Audit logs
- `WS /ws/audit` - Real-time audit stream

### Admin
- `POST /api/ingest/documents` - Ingest PDFs
- `POST /api/ingest/codebase` - Index codebase
- `GET /api/health` - Service health

## 🛠️ Technology Stack

### Backend
- **FastAPI** - Modern Python web framework
- **ChromaDB** - Vector database for embeddings
- **Ollama** - Local LLM inference
- **PyPDF2** - PDF text extraction
- **Sentence Transformers** - Text embeddings

### Frontend
- **React 18** - UI framework
- **Vite** - Build tool
- **Tailwind CSS** - Styling
- **Axios** - HTTP client
- **Lucide React** - Icons

## 🎨 UI Features

- Persona switcher with visual feedback
- Real-time typing indicators
- Rich attachment rendering (tickets, code, charts)
- Live audit log panel
- Dark mode support
- Responsive design

## 📝 Development

### Run Tests
```bash
# Backend
cd backend
pytest

# Frontend
cd frontend
npm test
```

### Format Code
```bash
# Backend
black backend/
isort backend/

# Frontend
npm run lint
```

## 🚢 Production Deployment

### Backend
1. Replace in-memory storage with PostgreSQL/MongoDB
2. Use hosted vector DB (Pinecone/Weaviate)
3. Add JWT authentication
4. Enable HTTPS with proper certificates
5. Implement rate limiting

### Frontend
1. Build optimized bundle: `npm run build`
2. Serve via CDN or Nginx
3. Configure production API URL
4. Add error tracking (Sentry)
5. Enable analytics

## 🐛 Troubleshooting

### Ollama Not Running
```bash
# Check status
curl http://localhost:11434/api/tags

# Restart
ollama serve
```

### ChromaDB Issues
```bash
# Delete and recreate
rm -rf backend/chroma_db/
# Restart backend
```

### Frontend Build Fails
```bash
# Clear cache
rm -rf node_modules package-lock.json
npm install
```

## 📚 Documentation

- [Backend README](backend/README.md) - Detailed backend documentation
- [Frontend README](frontend/README.md) - Frontend architecture
- [Task Specification](task.md) - Original project requirements

## 🤝 Contributing

This is a challenge project. For questions or issues:
1. Check existing documentation
2. Review API health endpoint
3. Check audit logs for errors

## 📄 License

This project is for evaluation purposes.

## 🎯 Demonstration Checklist

- [ ] PDF Chat with page citations
- [ ] Code intelligence search
- [ ] IAM enforcement (deny HR from accessing code)
- [ ] Action execution (create Jira ticket)
- [ ] Live audit log streaming
- [ ] Persona switching
- [ ] Error handling and recovery

---

Built with ❤️ for HCLTech NLP Challenge
