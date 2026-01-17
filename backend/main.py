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
from services.document_service import DocumentService
from services.rag_service import RagService
from services.hybrid_retriever import HybridRetriever
from services.agent_loop import AgentLoop

import chromadb
from chromadb.config import Settings


# Global state
iam_config = IAMConfig()
llm_service: Optional[LLMService] = None
db_service: Optional[DatabaseService] = None
code_ingestion: Optional[CodeIngestionService] = None
document_service: Optional[DocumentService] = None
rag_service: Optional[RagService] = None
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
    
    # Init Code Ingestion
    app.state.code_ingestion = CodeIngestionService()
    # Load persisted graphs
    try:
        app.state.code_ingestion.load_all_graphs()
    except Exception as e:
        print(f"⚠️ Failed to load code graphs: {e}")
    app.state.rag_service = RagService() # New Microservice
    app.state.document_service = DocumentService(app.state.rag_service, app.state.db_service) # New Microservice
    app.state.hybrid_retriever = HybridRetriever(collection=app.state.code_collection)
    
    # Update globals
    global llm_service, db_service, code_ingestion, hybrid_retriever, code_collection, document_service, rag_service
    llm_service = app.state.llm_service
    db_service = app.state.db_service
    code_ingestion = app.state.code_ingestion
    document_service = app.state.document_service
    rag_service = app.state.rag_service
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
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173"
    ],
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
        rag_service=rag_service,
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
    
    # 1. Ensure conversation exists (Persistence Fix)
    conversation_id = body.conversation_id
    if not conversation_id:
        conversation_id = str(uuid.uuid4())
    
    # Ensure DB record exists
    await request.app.state.db_service.ensure_conversation(
        conversation_id, 
        user_id=x_iam_role, 
        role=x_iam_role
    )
    
    # 2. Persist User Message & Get History
    conversation_history = []
    try:
        if body.conversation_id: # Only persist if ID was provided (or we decided to persist new ones)
             # Wait, if we generated a new ID, we should persist associated with that too.
             # But the frontend might not know the new ID unless we send it back.
             # We send it back via 'meta' event.
             pass
        
        await request.app.state.db_service.add_message(
            conversation_id,
            "user",
            body.query
        )
        
        messages = await request.app.state.db_service.get_recent_messages(
            conversation_id=conversation_id,
            limit=10 
        )
        
        # Filter out the current query from history (it's the last one we just added)
        if messages and messages[-1]["content"] == body.query:
            messages.pop()
            
        conversation_history = [
            {"role": m["role"], "content": m["content"]}
            for m in messages
        ]
    except Exception as e:
        print(f"Error fetching history: {e}")
            
    event_queue = asyncio.Queue()
    
    async def background_worker():
        """Runs the agent, pushes to queue, and saves to DB."""
        full_answer = ""
        thoughts = []
        actions = []
        
        try:
            # Notify client of the conversation ID
            await event_queue.put({
                "type": "meta",
                "conversation_id": conversation_id
            })

            # Initialize agent
            agent = AgentLoop(
                llm_service=request.app.state.llm_service,
                hybrid_retriever=request.app.state.hybrid_retriever,
                code_ingestion=request.app.state.code_ingestion,
                rag_service=request.app.state.rag_service
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
                    thoughts.append(event)
                elif event["type"] == "answer":
                    full_answer = event["content"]
                elif event["type"] == "action_result":
                    actions.append(event["data"])
            
            # 3. Persistence: Save the assistant's response to DB
            try:
                await request.app.state.db_service.add_message(
                    conversation_id,
                    "assistant",
                    full_answer,
                    metadata={"thoughts": thoughts, "actions": actions}
                )
                
                # 4. Summarization Trigger
                # If message count is multiple of 5, trigger summarization
                msgs = await request.app.state.db_service.get_messages(conversation_id, limit=100)
                if len(msgs) > 0 and len(msgs) % 5 == 0:
                     summary = await request.app.state.llm_service.summarize_conversation(msgs)
                     await request.app.state.db_service.update_conversation(conversation_id, title=summary)
                     await event_queue.put({
                         "type": "title",
                         "title": summary
                     })
                     
            except Exception as db_e:
                print(f"Failed to save message or summarize: {db_e}")
                    
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
                    yield f"data: {json.dumps({'type': 'error', 'content': event['error']})}\n\n"
                    break
                
                if event.get("type") == "meta":
                     yield f"data: {json.dumps(event)}\n\n"
                     continue
                     
                if event.get("type") == "title":
                     yield f"data: {json.dumps(event)}\n\n"
                     continue

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
                print(f"Stream cancelled by client for conversation {conversation_id}")
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
    
    # Extract repo name from URL
    repo_name = request.github_url.rstrip('/').split('/')[-1].replace('.git', '')
    
    # Create DB entry first (status: cloning)
    repo_record = await db_service.add_repository({
        "name": repo_name,
        "url": request.github_url,
        "language": "DETECTING",
        "status": "cloning",
        "user_id": x_iam_role
    })
    repo_id = repo_record["id"]
    
    try:
        # Update status to parsing
        await db_service.update_repository_status(repo_id, "parsing")
        
        # Ingest repository
        result = await code_ingestion.ingest_github_repo(
            github_url=request.github_url,
            user_id=x_iam_role
        )
        
        if result.get("status") == "error":
            await db_service.update_repository_status(repo_id, "error", error=result.get("error"))
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
        
        # Update DB with success status and stats
        await db_service.update_repository_status(
            repo_id, 
            "ready",
            stats={
                "graph_nodes": result.get("graph_nodes", 0),
                "file_count": result.get("file_count", 0)
            }
        )
        
        return {
            "status": "success",
            "repo_id": repo_id,
            "repo_name": result.get("repo_name"),
            "file_count": result.get("file_count"),
            "chunk_count": result.get("chunk_count"),
            "graph_nodes": result.get("graph_nodes"),
            "graph_edges": result.get("graph_edges")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db_service.update_repository_status(repo_id, "error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/github/repos")
async def list_repos(
    x_iam_role: str = Header(..., description="IAM Role of the requester")
):
    """List ingested repositories from database"""
    # Get repos from database first
    db_repos = await db_service.get_repositories(user_id=x_iam_role)
    
    if db_repos:
        # Return repos from database with full info
        return db_repos
    
    # Fallback: scan directory if no DB entries (legacy repos)
    repos = []
    if code_ingestion and code_ingestion.repos_dir.exists():
        for repo_dir in code_ingestion.repos_dir.iterdir():
            if repo_dir.is_dir() and not repo_dir.name.startswith("data_"):
                repos.append({
                    "id": repo_dir.name,
                    "name": repo_dir.name,
                    "url": "",
                    "language": "UNKNOWN",
                    "status": "ready",
                    "nodes_count": 0,
                    "file_count": 0,
                    "last_indexed_at": None,
                    "error_message": None
                })
    
    return repos


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
    
    file_size = os.path.getsize(file_path)
    
    # 1. Create DB record first (Processing)
    doc_record = await db_service.add_user_document(
        user_id=x_iam_role,
        filename=safe_filename,
        original_filename=file.filename,
        file_path=str(file_path),
        file_size=file_size
    )
    
    # 2. Trigger Background Task
    if document_service:
        asyncio.create_task(
            document_service.process_document(
                doc_id=doc_record["id"],
                file_path=str(file_path),
                user_id=x_iam_role,
                original_filename=file.filename
            )
        )
    
    return {
        "id": doc_record["id"],
        "filename": file.filename,
        "status": "processing",
        "message": "Ingestion started in background" 
    }


@app.get("/api/documents")
async def list_documents(
    x_iam_role: str = Header(..., description="IAM Role of the requester")
):
    """List user's documents"""
    documents = await db_service.get_user_documents(user_id=x_iam_role)
    return {"documents": documents}


@app.delete("/api/documents/{document_id}")
async def delete_document(
    document_id: str,
    x_iam_role: str = Header(..., description="IAM Role of the requester")
):
    """Delete a document and its chunks from the database and vector store"""
    try:
        # Get document to verify ownership
        doc = await db_service.get_document(document_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Delete from ChromaDB (vector store)
        if rag_service and rag_service.collection:
            try:
                # Get all chunks for this document
                result = rag_service.collection.get(
                    where={"doc_id": document_id},  # Match the metadata field name
                    include=[]
                )
                if result and result.get("ids"):
                    rag_service.collection.delete(ids=result["ids"])
                    print(f"Deleted {len(result['ids'])} chunks from vector store")
            except Exception as e:
                print(f"Warning: Could not delete from vector store: {e}")
        
        # Delete from database
        success = await db_service.delete_user_document(document_id)
        
        # Delete file from disk
        if doc.get("file_path") and os.path.exists(doc["file_path"]):
            os.remove(doc["file_path"])
            print(f"Deleted file: {doc['file_path']}")
        
        return {"success": success, "message": f"Document {document_id} deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/documents/{document_id}/chunks")
async def get_document_chunks(
    document_id: str,
    limit: int = 50,
    x_iam_role: str = Header(..., description="IAM Role of the requester")
):
    """Get chunks for a specific document"""
    chunks = []
    
    if rag_service and rag_service.collection:
        try:
            result = rag_service.collection.get(
                where={"doc_id": document_id},  # Match the metadata field name
                include=["documents", "metadatas"],
                limit=limit
            )
            
            if result and result.get("documents"):
                for i, doc in enumerate(result["documents"]):
                    meta = result["metadatas"][i] if result.get("metadatas") else {}
                    chunks.append({
                        "id": result["ids"][i] if result.get("ids") else i,
                        "content": doc,
                        "chunk_index": meta.get("chunk_index", i),
                        "page": meta.get("page", "?"),
                        "filename": meta.get("filename", "unknown")
                    })
        except Exception as e:
            print(f"Error fetching chunks: {e}")
    
    return {"chunks": chunks, "total": len(chunks)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
