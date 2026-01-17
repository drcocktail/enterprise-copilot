"""
Core Service
Port: 8003
Handles:
- IAM (Roles, Permissions)
- DB CRUD (Conversations, Tickets, Audit, System Health)
- Document Lists (Read-only view)
"""
from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uvicorn
import asyncio
from contextlib import asynccontextmanager
from config.iam_config import IAMConfig
from services.db_service import DatabaseService

# Globals
db_service: Optional[DatabaseService] = None
iam_config: Optional[IAMConfig] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_service, iam_config
    print("🛠️ Starting Core Service...")
    db_service = DatabaseService()
    iam_config = IAMConfig()
    await iam_config.load()
    print("✅ Core Service Ready")
    yield

app = FastAPI(title="Core/Management Service", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class Conversation(BaseModel):
    id: str
    title: str

class Ticket(BaseModel):
    title: str
    description: str = ""
    priority: str = "Medium"

# ROUTES

# --- IAM ---
@app.get("/api/iam/roles")
async def get_roles():
    return iam_config.roles

@app.get("/api/iam/policy")
async def get_policy():
    return iam_config.policy_matrix

# --- Conversations ---
@app.get("/api/conversations")
async def get_conversations(x_iam_role: str = Header(...)):
    return await db_service.get_conversations(x_iam_role)

@app.get("/api/conversations/{conv_id}")
async def get_conversation(conv_id: str):
    conv = await db_service.get_conversation(conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Not found")
    messages = await db_service.get_messages(conv_id)
    return {"conversation": conv, "messages": messages}

@app.get("/api/conversations/{conversation_id}/messages")
async def get_conversation_messages(conversation_id: str, limit: int = 100):
    """Get messages for a conversation"""
    messages = await db_service.get_messages(conversation_id, limit)
    return {"messages": messages}

@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation"""
    success = await db_service.delete_conversation(conversation_id)
    return {"success": success}

# --- Tickets ---
@app.get("/api/tickets")
async def get_tickets():
    return await db_service.get_tickets()

@app.post("/api/tickets")
async def create_ticket(ticket: Ticket):
    import uuid
    t_id = f"TICK-{uuid.uuid4().hex[:4].upper()}"
    data = ticket.dict()
    data["ticket_id"] = t_id
    return await db_service.create_ticket(data)

# --- Audit ---
@app.get("/api/audit")
async def get_audit_logs():
    return await db_service.get_audit_logs()

# --- System ---
@app.get("/api/system/health")
async def health():
    return {"status": "ok", "service": "core"}

# --- Documents List (Read Only) ---
# Ingestion handles upload, Core handles listing? 
# Or gateway routes /api/documents/upload to Ingestion, and /api/documents (GET) to Core?
# In svc_gateway.py I routed /api/documents/* to Ingestion. 
# So Ingestion Service should handle listing too.
# Let's add listing to Ingestion Service or move routing in Gateway.
# User wants "processes... built on different microservices".
# Listing documents is "Management". Uploading is "Ingestion".
# BUT simpler to keep all document endpoints in Ingestion Service for now to avoid split brain on endpoints.
# So Core handles Users/IAM/Conversations/Tickets.

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)
