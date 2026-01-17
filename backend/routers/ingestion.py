from fastapi import APIRouter, HTTPException, UploadFile, File, Header, BackgroundTasks, Request
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import shutil
import os
import uuid
from pathlib import Path

router = APIRouter()

UPLOAD_DIR = Path("backend/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

class RepoRequest(BaseModel):
    url: str

@router.post("/documents/upload")
async def upload_document(
    request: Request,
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
    
    db_service = request.app.state.db_service
    document_service = request.app.state.document_service
    
    # 1. Create DB record
    doc_record = await db_service.add_user_document(
        user_id=x_iam_role,
        filename=safe_filename,
        original_filename=file.filename,
        file_path=str(file_path),
        file_size=file_size
    )
    
    # 2. Trigger Background Task
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

@router.delete("/documents/{doc_id}")
async def delete_document(request: Request, doc_id: str, x_iam_role: str = Header(...)):
    """Delete User Document"""
    success = await request.app.state.db_service.delete_user_document(doc_id)
    if not success:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"status": "deleted", "id": doc_id}

@router.get("/documents")
async def list_documents(request: Request, x_iam_role: str = Header(...)):
    """List User Documents"""
    docs = await request.app.state.db_service.get_user_documents(x_iam_role)
    return {"documents": docs}

@router.get("/documents/{doc_id}/chunks")
async def get_document_chunks(request: Request, doc_id: str, limit: int = 100, x_iam_role: str = Header(...)):
    """Get Chunks for a Document"""
    chunks = request.app.state.rag_service.get_chunks_by_metadata("doc_id", doc_id, limit=limit)
    return {"chunks": chunks}

# --- Repository Routes ---

@router.post("/github/ingest")
@router.post("/repos/ingest")
async def ingest_repo(
    request: Request,
    body: RepoRequest, 
    background_tasks: BackgroundTasks,
    x_iam_role: str = Header(...)
):
    """Clone and Ingest a GitHub Repository asynchronously"""
    clean_url = body.url.strip()
    repo_name = clean_url.rstrip('/').split('/')[-1].replace('.git', '')
    repo_id = str(uuid.uuid4())[:8]

    db_service = request.app.state.db_service
    
    # Add 'pending' record
    await db_service.add_repository({
        "id": repo_id,
        "name": repo_name,
        "url": clean_url,
        "language": "UNKNOWN",
        "status": "pending",
        "user_id": x_iam_role
    })

    # Trigger Background Task
    background_tasks.add_task(
        request.app.state.code_ingestion.ingest_github_repo,
        github_url=clean_url,
        user_id=x_iam_role,
        repo_id=repo_id,
        db_service=db_service,
        rag_service=request.app.state.rag_service
    )

    return {
        "status": "accepted", 
        "message": "Repository ingestion started",
        "repo_id": repo_id,
        "repo_name": repo_name
    }

@router.get("/repos")
@router.get("/github/repos")
async def list_repos(request: Request, x_iam_role: str = Header(...)):
    """List User Repositories"""
    return await request.app.state.db_service.get_repositories(x_iam_role)

@router.delete("/repos/{repo_id}")
async def delete_repo(request: Request, repo_id: str, x_iam_role: str = Header(...)):
    """Delete a repository"""
    success = await request.app.state.db_service.delete_repository(repo_id)
    if not success:
        raise HTTPException(status_code=404, detail="Repository not found")
    return {"status": "deleted", "id": repo_id}

@router.get("/repos/{repo_id}/graph")
async def get_repo_graph(request: Request, repo_id: str, x_iam_role: str = Header(...)):
    """Get AST Graph for Repository"""
    graph_data = request.app.state.code_ingestion.get_repo_graph(repo_id)
    
    # Fix mapping for frontend (networkx node_link_data gives 'links', frontend expects 'edges')
    if "links" in graph_data:
        graph_data["edges"] = graph_data.pop("links")
        
    return graph_data

@router.get("/repos/{repo_id}/chunks")
async def get_repo_chunks(request: Request, repo_id: str, x_iam_role: str = Header(...)):
    """Get Code Chunks for Repository"""
    chunks = request.app.state.code_ingestion.get_repo_chunks(repo_id)
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
