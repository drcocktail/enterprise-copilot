"""
Agentic Enterprise Copilot - FastAPI Backend
IAM-First Architecture with RAG, Code Intelligence, and Action Execution
"""

from fastapi import FastAPI, HTTPException, Header, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
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

from config.iam_config import IAMConfig, resolve_capabilities
from services.audit_logger import AuditLogger
from services.rag_service import RAGService
from services.code_intelligence import CodeIntelligence
from services.action_executor import ActionExecutor
from services.llm_service import LLMService
from services.db_service import DatabaseService
from services.agentic_rag import AgenticRAG

# Global state
audit_logger = AuditLogger()
iam_config = IAMConfig()
rag_service: Optional[RAGService] = None
code_intelligence: Optional[CodeIntelligence] = None
action_executor: Optional[ActionExecutor] = None
llm_service: Optional[LLMService] = None
db_service: Optional[DatabaseService] = None
agentic_rag: Optional[AgenticRAG] = None

# Upload directory
UPLOAD_DIR = Path(__file__).parent / "uploads"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup"""
    global rag_service, code_intelligence, action_executor, llm_service, db_service, agentic_rag
    
    print("🚀 Initializing Agentic Enterprise Copilot V2...")
    
    # Create upload directory
    UPLOAD_DIR.mkdir(exist_ok=True)
    
    # Initialize services
    db_service = DatabaseService()
    llm_service = LLMService()
    rag_service = RAGService()
    code_intelligence = CodeIntelligence()
    action_executor = ActionExecutor()
    agentic_rag = AgenticRAG(rag_service=rag_service)
    
    # Load IAM configuration
    await iam_config.load()
    
    print("✅ All services initialized successfully")
    yield
    
    # Cleanup
    print("🛑 Shutting down services...")


app = FastAPI(
    title="Enterprise Copilot API",
    description="IAM-First Agentic Assistant with RAG & Code Intelligence",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://localhost:3003",
        "http://localhost:3004",
        "http://localhost:3005",
        "http://localhost:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== MODELS ====================

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    context: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None


class ActionData(BaseModel):
    type: str
    data: Dict[str, Any]


class AgentResponse(BaseModel):
    content: str
    attachment: Optional[ActionData] = None
    iam_role: str
    trace_id: str
    timestamp: datetime
    sources: Optional[List[Dict[str, Any]]] = None


class AuditLog(BaseModel):
    id: str
    timestamp: datetime
    actor: str
    iam_role: str
    action: str
    status: Literal["ALLOWED", "DENIED", "ERROR"]
    details: str
    trace_id: str
    metadata: Optional[Dict[str, Any]] = None


class PersonaInfo(BaseModel):
    id: str
    role: str
    name: str
    permissions: List[str]
    description: str


# ==================== ENDPOINTS ====================

@app.get("/")
async def root():
    """Health check"""
    return {
        "status": "online",
        "service": "Enterprise Copilot API",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/personas", response_model=List[PersonaInfo])
async def get_personas():
    """Get available personas and their permissions"""
    return iam_config.get_all_personas()


@app.post("/api/chat", response_model=AgentResponse)
async def chat(
    request: QueryRequest,
    x_iam_role: str = Header(..., description="IAM Role of the requester")
):
    """
    Main chat endpoint with IAM enforcement
    """
    trace_id = str(uuid.uuid4())
    
    try:
        # Step 1: Resolve capabilities based on IAM role
        capabilities = await resolve_capabilities(
            iam_config,
            x_iam_role,
            request.query
        )
        
        if not capabilities.allowed:
            # Log denied access
            await audit_logger.log(
                actor=capabilities.actor_name,
                iam_role=x_iam_role,
                action="QUERY_DENIED",
                status="DENIED",
                details=f"Access denied for query: {request.query[:50]}...",
                trace_id=trace_id,
                metadata={"reason": capabilities.denial_reason}
            )
            
            raise HTTPException(
                status_code=403,
                detail=f"Access Denied: {capabilities.denial_reason}"
            )
        
        # Log allowed action
        await audit_logger.log(
            actor=capabilities.actor_name,
            iam_role=x_iam_role,
            action="QUERY_PROCESSING",
            status="ALLOWED",
            details=f"Processing query: {request.query[:50]}...",
            trace_id=trace_id
        )
        
        # Step 2: Determine query intent and route accordingly
        intent = await llm_service.classify_intent(request.query, capabilities)
        
        # Step 3: Retrieve context based on intent
        context_chunks = []
        sources = []
        
        if intent.requires_rag:
            # RAG retrieval with IAM filtering
            rag_results = await rag_service.retrieve(
                query=request.query,
                role=x_iam_role,
                top_k=5,
                filters=capabilities.metadata_filters
            )
            context_chunks.extend(rag_results["chunks"])
            sources.extend(rag_results["sources"])
        
        if intent.requires_code_search:
            # Code intelligence search
            code_results = await code_intelligence.search(
                query=request.query,
                role=x_iam_role,
                filters=capabilities.code_filters
            )
            context_chunks.extend(code_results["chunks"])
            sources.extend(code_results["sources"])
        
        # Step 4: Generate response with LLM
        llm_response = await llm_service.generate_response(
            query=request.query,
            context=context_chunks,
            role=x_iam_role,
            capabilities=capabilities,
            intent=intent
        )
        
        # Step 5: Execute actions if needed
        attachment = None
        if intent.requires_action:
            action_result = await action_executor.execute(
                action_type=intent.action_type,
                parameters=llm_response.get("action_parameters", {}),
                role=x_iam_role
            )
            attachment = ActionData(
                type=action_result["type"],
                data=action_result["data"]
            )
            
            # Log action execution
            await audit_logger.log(
                actor=capabilities.actor_name,
                iam_role=x_iam_role,
                action=f"ACTION_EXECUTED_{intent.action_type}",
                status="ALLOWED",
                details=f"Executed {intent.action_type}",
                trace_id=trace_id,
                metadata=action_result
            )
        
        return AgentResponse(
            content=llm_response["content"],
            attachment=attachment,
            iam_role=x_iam_role,
            trace_id=trace_id,
            timestamp=datetime.now(),
            sources=sources if llm_response.get("show_sources", False) and sources else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await audit_logger.log(
            actor="SYSTEM",
            iam_role=x_iam_role,
            action="ERROR",
            status="ERROR",
            details=f"Error processing query: {str(e)}",
            trace_id=trace_id
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/audit/logs", response_model=List[AuditLog])
async def get_audit_logs(
    limit: int = 50,
    x_iam_role: str = Header(..., description="IAM Role of the requester")
):
    """Get recent audit logs (admin only)"""
    # Check if role has audit access
    if not iam_config.has_permission(x_iam_role, "READ_AUDIT_LOGS"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    return await audit_logger.get_recent_logs(limit=limit)


@app.websocket("/ws/audit")
async def websocket_audit_stream(websocket: WebSocket):
    """WebSocket endpoint for real-time audit log streaming"""
    await websocket.accept()
    
    try:
        # Subscribe to audit log updates
        async for log in audit_logger.stream():
            await websocket.send_json(log.dict())
    except WebSocketDisconnect:
        print("Client disconnected from audit stream")


@app.post("/api/ingest/documents")
async def ingest_documents(
    x_iam_role: str = Header(..., description="IAM Role of the requester")
):
    """Trigger document ingestion (admin only)"""
    if not iam_config.has_permission(x_iam_role, "ADMIN"):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await rag_service.ingest_documents()
    return {"status": "success", "result": result}


@app.post("/api/ingest/codebase")
async def ingest_codebase(
    path: str,
    x_iam_role: str = Header(..., description="IAM Role of the requester")
):
    """Index a codebase for code intelligence (admin only)"""
    if not iam_config.has_permission(x_iam_role, "ADMIN"):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await code_intelligence.index_codebase(path)
    return {"status": "success", "result": result}


@app.get("/api/health")
async def health_check():
    """Detailed health check for all services"""
    return {
        "status": "healthy",
        "services": {
            "iam": "online",
            "rag": "online" if rag_service else "offline",
            "code_intelligence": "online" if code_intelligence else "offline",
            "llm": "online" if llm_service else "offline",
            "database": "online" if db_service else "offline",
            "agentic_rag": "online" if agentic_rag else "offline",
            "audit": "online"
        },
        "timestamp": datetime.now().isoformat()
    }


# ==================== CONVERSATION MANAGEMENT ====================

class CreateConversationRequest(BaseModel):
    title: Optional[str] = None


class AddMessageRequest(BaseModel):
    role: str = "user"
    content: str
    metadata: Optional[Dict[str, Any]] = None


@app.get("/api/conversations")
async def list_conversations(
    x_iam_role: str = Header(..., description="IAM Role of the requester")
):
    """List user's conversations"""
    # Use role as user_id for now (in production, would use actual user ID)
    conversations = await db_service.get_conversations(user_id=x_iam_role)
    return {"conversations": conversations}


@app.post("/api/conversations")
async def create_conversation(
    request: CreateConversationRequest,
    x_iam_role: str = Header(..., description="IAM Role of the requester")
):
    """Create a new conversation"""
    conversation = await db_service.create_conversation(
        user_id=x_iam_role,
        role=x_iam_role,
        title=request.title
    )
    return conversation


@app.get("/api/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    x_iam_role: str = Header(..., description="IAM Role of the requester")
):
    """Get a conversation with its messages"""
    conversation = await db_service.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Check access
    if conversation["user_id"] != x_iam_role:
        raise HTTPException(status_code=403, detail="Access denied")
    
    messages = await db_service.get_messages(conversation_id)
    
    return {
        "conversation": conversation,
        "messages": messages
    }


@app.get("/api/conversations/{conversation_id}/messages")
async def get_messages(
    conversation_id: str,
    limit: int = 100,
    x_iam_role: str = Header(..., description="IAM Role of the requester")
):
    """Get messages for a conversation"""
    conversation = await db_service.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    if conversation["user_id"] != x_iam_role:
        raise HTTPException(status_code=403, detail="Access denied")
    
    messages = await db_service.get_messages(conversation_id, limit=limit)
    return {"messages": messages}


@app.post("/api/conversations/{conversation_id}/messages")
async def add_message(
    conversation_id: str,
    request: AddMessageRequest,
    x_iam_role: str = Header(..., description="IAM Role of the requester")
):
    """Add a message to a conversation"""
    conversation = await db_service.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    if conversation["user_id"] != x_iam_role:
        raise HTTPException(status_code=403, detail="Access denied")
    
    message = await db_service.add_message(
        conversation_id=conversation_id,
        role=request.role,
        content=request.content,
        metadata=request.metadata
    )
    return message


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    x_iam_role: str = Header(..., description="IAM Role of the requester")
):
    """Delete a conversation"""
    conversation = await db_service.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    if conversation["user_id"] != x_iam_role:
        raise HTTPException(status_code=403, detail="Access denied")
    
    success = await db_service.delete_conversation(conversation_id)
    return {"success": success}


# ==================== DOCUMENT MANAGEMENT ====================

@app.get("/api/documents")
async def list_documents(
    x_iam_role: str = Header(..., description="IAM Role of the requester")
):
    """List user's documents"""
    documents = await db_service.get_user_documents(user_id=x_iam_role)
    return {"documents": documents}


@app.post("/api/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    x_iam_role: str = Header(..., description="IAM Role of the requester")
):
    """Upload and ingest a document"""
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Generate unique filename
    file_id = str(uuid.uuid4())
    safe_filename = f"{file_id}_{file.filename}"
    file_path = UPLOAD_DIR / safe_filename
    
    try:
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Get file size
        file_size = os.path.getsize(file_path)
        
        # Add to database
        doc_record = await db_service.add_user_document(
            user_id=x_iam_role,
            filename=safe_filename,
            original_filename=file.filename,
            file_path=str(file_path),
            file_size=file_size
        )
        
        # Ingest into RAG (async task in real production)
        try:
            chunks = await rag_service._extract_pdf_chunks(file_path)
            if chunks:
                # Add user_id to metadata for filtering
                for chunk in chunks:
                    chunk["metadata"]["user_id"] = x_iam_role
                    chunk["metadata"]["doc_id"] = doc_record["id"]
                
                rag_service.collection.add(
                    documents=[chunk["text"] for chunk in chunks],
                    metadatas=[chunk["metadata"] for chunk in chunks],
                    ids=[chunk["id"] for chunk in chunks]
                )
                
                # Update status
                await db_service.update_document_status(
                    doc_id=doc_record["id"],
                    status="ready",
                    chunk_count=len(chunks)
                )
            else:
                await db_service.update_document_status(
                    doc_id=doc_record["id"],
                    status="error",
                    error_message="No text content found in PDF"
                )
        except Exception as e:
            await db_service.update_document_status(
                doc_id=doc_record["id"],
                status="error",
                error_message=str(e)
            )
        
        return {
            "id": doc_record["id"],
            "filename": file.filename,
            "status": "processing",
            "message": "Document uploaded and being processed"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.delete("/api/documents/{doc_id}")
async def delete_document(
    doc_id: str,
    x_iam_role: str = Header(..., description="IAM Role of the requester")
):
    """Delete a document"""
    doc = await db_service.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if doc["user_id"] != x_iam_role:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Delete from ChromaDB
    try:
        # Find and delete chunks by doc_id metadata
        rag_service.collection.delete(
            where={"doc_id": doc_id}
        )
    except Exception as e:
        print(f"Warning: Could not delete chunks from ChromaDB: {e}")
    
    # Delete file
    try:
        if doc["file_path"]:
            os.remove(doc["file_path"])
    except:
        pass
    
    # Delete from database
    success = await db_service.delete_user_document(doc_id)
    
    return {"success": success}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
