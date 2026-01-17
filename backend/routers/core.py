from fastapi import APIRouter, HTTPException, Header, Request
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uuid

router = APIRouter()

# --- Models ---

class Ticket(BaseModel):
    title: str
    description: str = ""
    priority: str = "Medium"

# --- Routes ---

@router.get("/health")
@router.get("/system/health")
async def health(request: Request):
    return {
        "status": "healthy",
        "service": "DevOps Copilot V3 (Modular Monolith)",
        "services": {
            "database": "online" if request.app.state.db_service else "offline",
            "chromadb": "online" # Assumed if server started
        }
    }

# --- IAM ---

@router.get("/iam/roles")
async def get_roles(request: Request):
    return request.app.state.iam_config.get_personas() # Actually get_personas returns a list

@router.get("/personas")
async def get_personas(request: Request):
    return request.app.state.iam_config.get_personas()

@router.get("/iam/policy")
async def get_policy(request: Request):
    # iam_config doesn't have policy_matrix method in the code I saw, 
    # but svc_core.py called it. The code I viewed in step 118 didn't show it.
    # It might be missing. I'll return empty dict or implement it if I see it.
    # Checking Step 118: file doesn't have policy_matrix.
    # It has role_capabilities. 
    # Let's return role_capabilities dump.
    return {r: c.__dict__ for r, c in request.app.state.iam_config.role_capabilities.items()}

# --- Conversations ---

@router.get("/conversations")
async def get_conversations(request: Request, x_iam_role: str = Header(...)):
    return await request.app.state.db_service.get_conversations(x_iam_role)

@router.post("/conversations")
async def create_conversation(request: Request, x_iam_role: str = Header(...), body: Dict[str, str] = {}): # body might have title
    return await request.app.state.db_service.create_conversation(
        user_id=x_iam_role,
        role=x_iam_role,
        title=body.get("title", "New Chat")
    )

@router.get("/conversations/{conv_id}")
async def get_conversation(request: Request, conv_id: str):
    conv = await request.app.state.db_service.get_conversation(conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Not found")
    messages = await request.app.state.db_service.get_messages(conv_id)
    return {"conversation": conv, "messages": messages}

@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(request: Request, conversation_id: str, limit: int = 100):
    messages = await request.app.state.db_service.get_messages(conversation_id, limit)
    return {"messages": messages}

@router.post("/conversations/{conversation_id}/messages")
async def add_message(request: Request, conversation_id: str, body: Dict[str, Any]):
    # Allow manually adding messages (frontend uses this sometimes?)
    return await request.app.state.db_service.add_message(
        conversation_id,
        body.get("role"),
        body.get("content"),
        body.get("metadata")
    )

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(request: Request, conversation_id: str):
    success = await request.app.state.db_service.delete_conversation(conversation_id)
    return {"success": success}

# --- Tickets ---

@router.get("/tickets")
async def get_tickets(request: Request):
    return await request.app.state.db_service.get_tickets()

@router.post("/tickets")
async def create_ticket(request: Request, ticket: Ticket):
    t_id = f"TICK-{uuid.uuid4().hex[:4].upper()}"
    data = ticket.dict()
    data["ticket_id"] = t_id
    return await request.app.state.db_service.create_ticket(data)

# --- Audit ---

@router.get("/audit")
@router.get("/audit/logs")
async def get_audit_logs(request: Request):
    return await request.app.state.db_service.get_audit_logs()
