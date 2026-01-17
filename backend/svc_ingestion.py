"""
Ingestion Service
Port: 8001
Handles:
- /api/documents/upload (PDFs)
- /api/repos/* (GitHub cloning, embedding)
"""
from fastapi import FastAPI, HTTPException, UploadFile, File, Header, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uvicorn
import shutil
import os
import uuid
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager

# Services
from services.db_service import DatabaseService
from services.code_ingestion import CodeIngestionService
from services.document_service import DocumentService
from services.rag_service import RagService 
# Note: RagService here is for WRITE access (embedding). Chat uses it for READ.

# Globals
db_service: Optional[DatabaseService] = None
code_ingestion: Optional[CodeIngestionService] = None
document_service: Optional[DocumentService] = None
rag_service: Optional[RagService] = None

UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_service, code_ingestion, document_service, rag_service
    print("🚀 Starting Ingestion Service...")
    db_service = DatabaseService()
    rag_service = RagService() # Embeddings
    code_ingestion = CodeIngestionService()
    document_service = DocumentService(rag_service, db_service)
    print("✅ Ingestion Service Ready")
    yield

app = FastAPI(title="Ingestion Service", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class RepoRequest(BaseModel):
    url: str

class ProcessRequest(BaseModel):
    repo_name: str

# ROUTES

@app.post("/api/documents/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    x_iam_role: str = Header(..., description="IAM Role")
):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    file_id = str(uuid.uuid4())
    safe_filename = f"{file_id}_{file.filename}"
    file_path = UPLOAD_DIR / safe_filename
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    file_size = os.path.getsize(file_path)
    
    # 1. Create DB record
    doc_record = await db_service.add_user_document(
        user_id=x_iam_role,
        filename=safe_filename,
        original_filename=file.filename,
        file_path=str(file_path),
        file_size=file_size
    )
    
    # 2. Trigger Background Task
    # Note: background_tasks.add_task expects a synchronous callable or coroutine?
    # It supports async defs.
    background_tasks.add_task(
        document_service.process_document,
        doc_id=doc_record["id"],
        file_path=str(file_path),
        user_id=x_iam_role,
        original_filename=file.filename
    )

    return {
        "id": doc_record["id"],
        "filename": file.filename,
        "status": "processing",
        "message": "Ingestion started in background"
    }

@app.post("/api/repos/ingest")
async def ingest_repo(
    request: RepoRequest, 
    background_tasks: BackgroundTasks,
    x_iam_role: str = Header(...)
):
    """Clone and Ingest a GitHub Repository asynchronously"""
    
    # 0. Sanitize URL
    clean_url = request.url.strip()
    
    # 1. Extract name immediately for DB
    repo_name = clean_url.rstrip('/').split('/')[-1].replace('.git', '')
    repo_id = str(uuid.uuid4())[:8]

    # 2. Add 'pending' record to DB
    await db_service.add_repository({
        "id": repo_id,
        "name": repo_name,
        "url": clean_url,
        "language": "UNKNOWN",
        "status": "pending",
        "user_id": x_iam_role
    })

    # 3. Trigger Background Task
    background_tasks.add_task(
        code_ingestion.ingest_github_repo,
        github_url=clean_url,
        user_id=x_iam_role,
        repo_id=repo_id,  # Pass pre-generated ID
        db_service=db_service, # Pass DB service to update status
        rag_service=rag_service # Pass RAG service to embed chunks
    )

    return {
        "status": "accepted", 
        "message": "Repository ingestion started",
        "repo_id": repo_id,
        "repo_name": repo_name
    }

@app.get("/api/documents")
async def list_documents(x_iam_role: str = Header(...)):
    """List User Documents"""
    docs = await db_service.get_user_documents(x_iam_role)
    return {"documents": docs}

@app.get("/api/repos")
async def list_repos(x_iam_role: str = Header(...)):
    """List User Repositories from DB"""
    return await db_service.get_repositories(x_iam_role)

@app.get("/api/repos/{repo_id}/graph")
async def get_repo_graph(repo_id: str, x_iam_role: str = Header(...)):
    """Get AST Graph for Repository"""
    graph_data = code_ingestion.get_repo_graph(repo_id)
    # Ensure it matches frontend expectations usually {nodes: [], edges: []}
    # nx.node_link_data returns {nodes: [...], links: [...], directed: True, ...}
    # Frontend expects 'edges' key? Let's check or map it.
    if "links" in graph_data:
        graph_data["edges"] = graph_data.pop("links")
        
    return graph_data

@app.get("/api/repos/{repo_id}/chunks")
async def get_repo_chunks(repo_id: str, x_iam_role: str = Header(...)):
    """Get Code Chunks for Repository"""
    chunks = code_ingestion.get_repo_chunks(repo_id)
    # Simplify for frontend if needed
    cleaned_chunks = []
    for c in chunks:
        meta = c.get("metadata", {})
        cleaned_chunks.append({
            "id": c.get("id"),
            "content": c.get("text"),
            "file": meta.get("file_path"),
            "lines": f"{meta.get('start_line', 0)}-{meta.get('end_line', 0)}",
            "type": meta.get("chunk_type")
        })
    return {"chunks": cleaned_chunks}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
