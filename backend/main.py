"""
DevOps Copilot V3 - FastAPI Backend
Developer and IT-focused Agentic Assistant with Code Intelligence.
"""

from fastapi import FastAPI, HTTPException, Header, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
import json
import uuid
import asyncio
import os
import shutil
from pathlib import Path
from contextlib import asynccontextmanager

from config.iam_config import IAMConfig, resolve_capabilities, PERSONA_DEFINITIONS
from services.llm_service import LLMService
from services.db_service import DatabaseService
from services.code_ingestion import CodeIngestionService
from services.hybrid_retriever import HybridRetriever

import chromadb
from chromadb.config import Settings


# Global state
iam_config = IAMConfig()
llm_service: Optional[LLMService] = None
db_service: Optional[DatabaseService] = None
code_ingestion: Optional[CodeIngestionService] = None
hybrid_retriever: Optional[HybridRetriever] = None
chroma_client = None
code_collection = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup"""
    global llm_service, db_service, code_ingestion, hybrid_retriever
    global chroma_client, code_collection
    
    print("🚀 Initializing DevOps Copilot V3...")
    
    # Initialize ChromaDB
    chroma_path = Path(__file__).parent / "chroma_db"
    chroma_client = chromadb.PersistentClient(
        path=str(chroma_path),
        settings=Settings(anonymized_telemetry=False)
    )
    
    # Get or create code collection
    code_collection = chroma_client.get_or_create_collection(
        name="code_chunks",
        metadata={"hnsw:space": "cosine"}
    )
    
    # Initialize services
    db_service = DatabaseService()
    llm_service = LLMService()
    code_ingestion = CodeIngestionService()
    hybrid_retriever = HybridRetriever(collection=code_collection)
    
    # Load IAM configuration
    await iam_config.load()
    
    print("✅ DevOps Copilot V3 ready!")
    print("   - LLM: qwen2.5-coder:7b")
    print("   - Hybrid retrieval: Semantic + BM25 + RRF")
    print("   - Personas: SDE-II, Principal Architect, IT Analyst")
    
    yield
    
    # Cleanup
    print("🛑 Shutting down...")


app = FastAPI(
    title="DevOps Copilot API",
    description="Developer and IT-focused Agentic Assistant with Code Intelligence",
    version="3.0.0",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== MODELS ====================

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=5000)
    conversation_id: Optional[str] = None


class GitHubIngestRequest(BaseModel):
    github_url: str = Field(..., min_length=10)


class AgentResponse(BaseModel):
    content: str
    attachment: Optional[Dict[str, Any]] = None
    iam_role: str
    trace_id: str
    timestamp: datetime
    sources: Optional[List[Dict[str, Any]]] = None


class PersonaInfo(BaseModel):
    id: str
    role: str
    name: str
    permissions: List[str]
    description: str
    context: str
    emoji: str
    suggested: List[str]


# ==================== ENDPOINTS ====================

@app.get("/")
async def root():
    """Health check"""
    return {
        "status": "online",
        "service": "DevOps Copilot V3",
        "version": "3.0.0"
    }


@app.get("/api/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "services": {
            "llm": "online" if llm_service else "offline",
            "database": "online" if db_service else "offline",
            "code_ingestion": "online" if code_ingestion else "offline",
            "hybrid_retriever": "online" if hybrid_retriever else "offline",
            "chromadb": "online" if code_collection else "offline"
        },
        "llm_model": "qwen2.5-coder:7b",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/personas", response_model=List[PersonaInfo])
async def get_personas():
    """Get available personas"""
    personas = []
    for persona in PERSONA_DEFINITIONS.values():
        personas.append(PersonaInfo(
            id=persona["id"],
            role=persona["role"],
            name=persona["name"],
            permissions=persona["permissions"],
            description=persona["description"],
            context=persona["context"],
            emoji=persona["emoji"],
            suggested=persona["suggested"]
        ))
    return personas


@app.post("/api/chat", response_model=AgentResponse)
async def chat(
    request: QueryRequest,
    x_iam_role: str = Header(..., description="IAM Role of the requester")
):
    """Main chat endpoint"""
    trace_id = str(uuid.uuid4())[:8]
    
    # Resolve capabilities
    capabilities = resolve_capabilities(x_iam_role)
    
    # Get conversation history if provided
    conversation_history = []
    if request.conversation_id:
        try:
            messages = await db_service.get_recent_messages(
                request.conversation_id,
                limit=6
            )
            conversation_history = [
                {"role": m["role"], "content": m["content"]}
                for m in messages
            ]
        except:
            pass
    
    # Classify intent
    intent = await llm_service.classify_intent(request.query, capabilities)
    
    # Get context based on intent
    context = []
    sources = []
    
    if intent.requires_code_search and code_collection.count() > 0:
        # Use hybrid retrieval for code
        filters = None  # Could filter by user's repos
        results = await hybrid_retriever.hybrid_search(
            query=request.query,
            top_k=5,
            filters=filters
        )
        context = results
        sources = [
            {
                "file": r.get("metadata", {}).get("file_path", "unknown"),
                "name": r.get("metadata", {}).get("name", ""),
                "lines": f"{r.get('metadata', {}).get('start_line', '?')}-{r.get('metadata', {}).get('end_line', '?')}",
                "language": r.get("metadata", {}).get("language", "")
            }
            for r in results
        ]
    
    # Generate response
    llm_response = await llm_service.generate_response(
        query=request.query,
        context=context,
        role=x_iam_role,
        capabilities=capabilities,
        intent=intent,
        conversation_history=conversation_history
    )
    
    # Build attachment if IT action
    attachment = None
    if llm_response.get("attachment"):
        attachment = llm_response["attachment"]
    
    # Save messages if conversation exists
    if request.conversation_id:
        try:
            await db_service.add_message(
                request.conversation_id,
                role="user",
                content=request.query
            )
            await db_service.add_message(
                request.conversation_id,
                role="assistant",
                content=llm_response["content"],
                metadata={"sources": sources} if sources else None
            )
        except:
            pass
    
    return AgentResponse(
        content=llm_response["content"],
        attachment=attachment,
        iam_role=x_iam_role,
        trace_id=trace_id,
        timestamp=datetime.now(),
        sources=sources if llm_response.get("show_sources") else None
    )


# ==================== GITHUB INGESTION ====================

@app.post("/api/github/ingest")
async def ingest_github_repo(
    request: GitHubIngestRequest,
    x_iam_role: str = Header(..., description="IAM Role of the requester")
):
    """Ingest a GitHub repository"""
    capabilities = resolve_capabilities(x_iam_role)
    
    if "READ_CODEBASE" not in capabilities.permissions:
        raise HTTPException(status_code=403, detail="Code access not permitted")
    
    # Ingest repository
    result = await code_ingestion.ingest_github_repo(
        github_url=request.github_url,
        user_id=x_iam_role
    )
    
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    # Add chunks to ChromaDB
    chunks = result.get("chunks", [])
    if chunks:
        code_collection.add(
            documents=[c["text"] for c in chunks],
            metadatas=[c["metadata"] for c in chunks],
            ids=[c["id"] for c in chunks]
        )
        
        # Build BM25 index
        hybrid_retriever.build_bm25_index(chunks)
        
        # Update graph reference
        hybrid_retriever.graph = code_ingestion.graph
    
    return {
        "status": "success",
        "repo_name": result.get("repo_name"),
        "file_count": result.get("file_count"),
        "chunk_count": result.get("chunk_count"),
        "graph_nodes": result.get("graph_nodes"),
        "graph_edges": result.get("graph_edges")
    }


@app.get("/api/github/repos")
async def list_repos(
    x_iam_role: str = Header(..., description="IAM Role of the requester")
):
    """List ingested repositories"""
    repos = []
    
    if code_ingestion and code_ingestion.repos_dir.exists():
        for repo_dir in code_ingestion.repos_dir.iterdir():
            if repo_dir.is_dir():
                repos.append({
                    "name": repo_dir.name,
                    "path": str(repo_dir)
                })
    
    return {"repos": repos}


# ==================== CONVERSATIONS ====================

@app.get("/api/conversations")
async def list_conversations(
    x_iam_role: str = Header(..., description="IAM Role of the requester")
):
    """List user's conversations"""
    conversations = await db_service.get_conversations(user_id=x_iam_role)
    return {"conversations": conversations}


@app.post("/api/conversations")
async def create_conversation(
    x_iam_role: str = Header(..., description="IAM Role of the requester")
):
    """Create a new conversation"""
    conversation = await db_service.create_conversation(
        user_id=x_iam_role,
        role=x_iam_role,
        title="New Chat"
    )
    return conversation


@app.get("/api/conversations/{conversation_id}/messages")
async def get_messages(
    conversation_id: str,
    x_iam_role: str = Header(..., description="IAM Role of the requester")
):
    """Get messages for a conversation"""
    messages = await db_service.get_messages(conversation_id)
    return {"messages": messages}


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    x_iam_role: str = Header(..., description="IAM Role of the requester")
):
    """Delete a conversation"""
    success = await db_service.delete_conversation(conversation_id)
    return {"success": success}


# ==================== DOCUMENT UPLOAD ====================

UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


@app.post("/api/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    x_iam_role: str = Header(..., description="IAM Role of the requester")
):
    """Upload a document (PDF)"""
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    file_id = str(uuid.uuid4())
    safe_filename = f"{file_id}_{file.filename}"
    file_path = UPLOAD_DIR / safe_filename
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    file_size = os.path.getsize(file_path)
    
    doc_record = await db_service.add_user_document(
        user_id=x_iam_role,
        filename=safe_filename,
        original_filename=file.filename,
        file_path=str(file_path),
        file_size=file_size
    )
    
    return {
        "id": doc_record["id"],
        "filename": file.filename,
        "status": "uploaded"
    }


@app.get("/api/documents")
async def list_documents(
    x_iam_role: str = Header(..., description="IAM Role of the requester")
):
    """List user's documents"""
    documents = await db_service.get_user_documents(user_id=x_iam_role)
    return {"documents": documents}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
