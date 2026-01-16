"""
DevOps Copilot V3 - FastAPI Backend
Developer and IT-focused Agentic Assistant with Code Intelligence.
"""

from fastapi import FastAPI, HTTPException, Header, UploadFile, File, Request
from fastapi.responses import StreamingResponse
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
from services.document_ingestion import DocumentIngestionService
from services.hybrid_retriever import HybridRetriever
from services.agent_loop import AgentLoop

import chromadb
from chromadb.config import Settings


# Global state
iam_config = IAMConfig()
llm_service: Optional[LLMService] = None
db_service: Optional[DatabaseService] = None
code_ingestion: Optional[CodeIngestionService] = None
document_ingestion: Optional[DocumentIngestionService] = None
hybrid_retriever: Optional[HybridRetriever] = None
chroma_client = None
code_collection = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup"""
    print("🚀 Initializing DevOps Copilot V3...")
    
    # Initialize ChromaDB
    chroma_path = Path(__file__).parent / "chroma_db"
    app.state.chroma_client = chromadb.PersistentClient(
        path=str(chroma_path),
        settings=Settings(anonymized_telemetry=False)
    )
    
    # Get or create code collection
    app.state.code_collection = app.state.chroma_client.get_or_create_collection(
        name="code_chunks",
        metadata={"hnsw:space": "cosine"}
    )
    
    # Initialize services
    app.state.db_service = DatabaseService()
    app.state.llm_service = LLMService()
    app.state.code_ingestion = CodeIngestionService()
    app.state.document_ingestion = DocumentIngestionService()
    app.state.hybrid_retriever = HybridRetriever(collection=app.state.code_collection)
    
    # Update globals
    global llm_service, db_service, code_ingestion, hybrid_retriever, code_collection, document_ingestion
    llm_service = app.state.llm_service
    db_service = app.state.db_service
    code_ingestion = app.state.code_ingestion
    document_ingestion = app.state.document_ingestion
    hybrid_retriever = app.state.hybrid_retriever
    code_collection = app.state.code_collection
    app.state.iam_config = IAMConfig()
    
    # Load IAM configuration
    await app.state.iam_config.load()
    
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
    trace: Optional[List[Dict[str, Any]]] = None  # Reasoning steps
    actions: Optional[List[Dict[str, Any]]] = None  # Tool outputs


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


@app.post("/api/chat/agent", response_model=AgentResponse)
async def chat_agent(
    request: QueryRequest,
    x_iam_role: str = Header(..., description="IAM Role of the requester")
):
    """Main chat endpoint with agentic reasoning loop"""
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
    
    # Create agent and run
    agent = AgentLoop(
        llm_service=llm_service,
        hybrid_retriever=hybrid_retriever,
        code_ingestion=code_ingestion,
        document_ingestion=document_ingestion,
        max_steps=5
    )
    
    result = await agent.run(
        query=request.query,
        role=x_iam_role,
        capabilities=capabilities,
        conversation_history=conversation_history
    )
    
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
                content=result.answer,
                metadata={"trace": result.trace, "actions": result.actions}
            )
        except:
            pass
    
    return AgentResponse(
        content=result.answer,
        attachment=result.actions[0] if result.actions else None,
        iam_role=x_iam_role,
        trace_id=trace_id,
        timestamp=datetime.now(),
        trace=result.trace,
        actions=result.actions
    )


@app.post("/api/chat/stream")
async def chat_stream(
    body: QueryRequest,
    request: Request,
    x_iam_role: str = Header(..., description="IAM Role of the requester")
):
    """Streaming chat endpoint using Server-Sent Events"""
    
    # Resolve capabilities
    capabilities = resolve_capabilities(x_iam_role)
    
    # Get conversation history
    conversation_history = []
    if body.conversation_id:
        try:
            # Use request.app.state.db_service
            messages = await request.app.state.db_service.get_recent_messages(body.conversation_id, limit=6)
            conversation_history = [{"role": m["role"], "content": m["content"]} for m in messages]
        except:
            pass
    
    # Create a Queue for the stream
    event_queue = asyncio.Queue()
    
    async def background_worker():
        """Runs the agent, pushes to queue, and saves to DB."""
        full_answer = ""
        thoughts = []
        actions = []
        
        try:
            # Initialize agent
            agent = AgentLoop(
                llm_service=request.app.state.llm_service,
                hybrid_retriever=request.app.state.hybrid_retriever,
                code_ingestion=request.app.state.code_ingestion,
                document_ingestion=request.app.state.document_ingestion
            )
            
            async for event in agent.run_stream(
                query=body.query,
                role=x_iam_role,
                capabilities=capabilities,
                conversation_history=conversation_history
            ):
                # 1. Push to queue for the live client
                await event_queue.put(event)
                
                # 2. Accumulate state for persistence
                if event["type"] == "step":
                    thoughts.append(event) # {"type": "step", "text": "...", "state": "done"}
                elif event["type"] == "answer":
                    full_answer = event["content"]
                elif event["type"] == "action_result":
                    actions.append(event["data"])
            
            # 3. Persistence: Save the assistant's response to DB
            if body.conversation_id:
                try:
                    # Construct the complex message content if needed, but DB currently takes 'content'.
                    # We might want to save the trace in a separate field if DB supports it.
                    # As a fallback, we append the trace to the content or just save the answer.
                    # Ideally, db_service.add_message supports `metadata` or `trace`.
                    # Let's stick to simple content for now to ensure compatibility.
                    
                    # For a "true agent", the answer is the answer. The trace is metadata.
                    # We assume db_service.add_message(conversation_id, role, content)
                    await request.app.state.db_service.add_message(
                        body.conversation_id,
                        "assistant",
                        full_answer
                    )
                    # TODO: If DB has a `trace` column, save `thoughts` and `actions` there.
                except Exception as db_e:
                    print(f"Failed to save message to DB: {db_e}")
                    
        except Exception as e:
            print(f"Background worker error: {e}")
            await event_queue.put({"type": "error", "error": str(e)})
        finally:
            await event_queue.put(None) # Sentinel

    # Start background task
    asyncio.create_task(background_worker())

    async def stream_generator():
        while True:
            try:
                # Wait for next event
                event = await event_queue.get()
                
                if event is None: # Done
                    break
                
                if event.get("type") == "error":
                    # Optionally verify if we should signal error to stream
                    break
                    
                # Yield SSE format
                if event["type"] == "step":
                    yield f"data: {json.dumps({'type': 'step', 'text': event['text'], 'state': event['state']})}\n\n"
                elif event["type"] == "action_result":
                    yield f"data: {json.dumps({'type': 'action', 'data': event['data']})}\n\n"
                elif event["type"] == "answer":
                    yield f"data: {json.dumps({'type': 'done', 'content': event['content']})}\n\n"
                elif event["type"] == "step_start":
                    pass

            except asyncio.CancelledError:
                # Client disconnected.
                # We stop yielding, but the background_worker continues running!
                print(f"Stream cancelled by client for conversation {body.conversation_id}")
                raise

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
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


@app.get("/api/repos/{repo_id}/graph")
async def get_repo_graph(
    repo_id: str,
    x_iam_role: str = Header(..., description="IAM Role of the requester")
):
    """Get AST graph for a repository"""
    nodes = []
    edges = []
    
    if code_ingestion and code_ingestion.graph:
        # Get nodes and edges from NetworkX graph
        for node_id, data in code_ingestion.graph.nodes(data=True):
            # Filter by repo if needed
            nodes.append({
                "id": node_id,
                "type": data.get("type", "unknown"),
                "label": data.get("name", node_id),
                "file": data.get("file", ""),
                "line": data.get("line", 0)
            })
        
        for source, target, data in code_ingestion.graph.edges(data=True):
            edges.append({
                "source": source,
                "target": target,
                "type": data.get("type", "RELATED")
            })
    
    return {"nodes": nodes, "edges": edges}


@app.get("/api/repos/{repo_id}/chunks")
async def get_repo_chunks(
    repo_id: str,
    x_iam_role: str = Header(..., description="IAM Role of the requester")
):
    """Get vector chunks for a repository"""
    chunks = []
    
    if code_collection:
        try:
            # Query all chunks (limit for performance)
            result = code_collection.get(
                limit=50,
                include=["documents", "metadatas"]
            )
            
            if result and result.get("documents"):
                for i, doc in enumerate(result["documents"]):
                    meta = result["metadatas"][i] if result.get("metadatas") else {}
                    chunks.append({
                        "id": result["ids"][i] if result.get("ids") else i,
                        "content": doc[:500] + "..." if len(doc) > 500 else doc,
                        "file": meta.get("file_path", "unknown"),
                        "lines": f"{meta.get('start_line', 0)}-{meta.get('end_line', 0)}"
                    })
        except Exception as e:
            print(f"Error fetching chunks: {e}")
    
    return {"chunks": chunks}


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
    
    # Trigger background ingestion
    # In a real app, this should be a background task, but we'll await it for now to return stats
    # or use asyncio.create_task if we want fire-and-forget
    
    ingest_stats = {}
    if document_ingestion:
        try:
            # We treat this as fire-and-forget for speed, or await for immediate feedback?
            # User wants "Ingesting..." progress. 
            # Let's await it so we can return the node count immediately for the UI to show.
            ingest_stats = await document_ingestion.ingest_document(
                file_path=str(file_path),
                user_id=x_iam_role,
                original_filename=file.filename
            )
        except Exception as e:
            print(f"Ingestion failed: {e}")
            ingest_stats = {"error": str(e)}

    doc_record = await db_service.add_user_document(
        user_id=x_iam_role,
        filename=safe_filename,
        original_filename=file.filename,
        file_path=str(file_path),
        file_size=file_size,
        chunk_count=ingest_stats.get("chunk_count", 0)
    )
    
    return {
        "id": doc_record["id"],
        "filename": file.filename,
        "status": "uploaded",
        "ingestion": ingest_stats
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
