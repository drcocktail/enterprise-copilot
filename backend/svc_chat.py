"""
Chat Service
Port: 8002
Handles:
- /api/chat/stream (Agent Loop)
"""
from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uvicorn
import asyncio
import json
from contextlib import asynccontextmanager

# Services
from services.llm_service import LLMService
from services.rag_service import RagService
from services.hybrid_retriever import HybridRetriever
from services.agent_loop import AgentLoop
from config.iam_config import resolve_capabilities
from services.code_ingestion import CodeIngestionService # Needed for search_code tool? 
# Wait, search_code uses HybridRetriever which uses ChromaDB. We just need access to the DB.
# CodeIngestionService isn't needed for search, but AgentLoop might want it?
# The AgentLoop tools: search_code (Retriever), search_docs (RagService).
# So we don't strictly need CodeIngestionService instance if Retriever handles the search.
# BUT HybridRetriever takes `collection` which comes from chroma.

# Globals
llm_service: Optional[LLMService] = None
rag_service: Optional[RagService] = None
hybrid_retriever: Optional[HybridRetriever] = None
agent_loop: Optional[AgentLoop] = None # We instantiate per request usually, or reusing?

@asynccontextmanager
async def lifespan(app: FastAPI):
    global llm_service, rag_service, hybrid_retriever, db_service
    print("💬 Starting Chat Service...")
    
    # Initialize Core Services
    llm_service = LLMService()
    rag_service = RagService() 
    
    # Initialize DB Service for Persistence
    from services.db_service import DatabaseService
    db_service = DatabaseService()
    
    # Vector DB for code (Chroma)
    import chromadb
    from chromadb.config import Settings
    from pathlib import Path
    
    chroma_path = Path(__file__).parent / "chroma_db"
    chroma_client = chromadb.PersistentClient(
            path=str(chroma_path),
            settings=Settings(anonymized_telemetry=False)
    )
    code_collection = chroma_client.get_or_create_collection(name="code_chunks")
    
    hybrid_retriever = HybridRetriever(collection=code_collection)
    print("✅ Chat Service Ready")
    yield

app = FastAPI(title="Chat Service", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    history: List[Dict[str, str]] = []

@app.post("/api/chat/stream")
async def chat_stream(request: Request, x_iam_role: str = Header(...)):
    """Stream chat response with persistence"""
    body = await request.json()
    # Accept both 'message' and 'query' for compatibility
    message = body.get("message") or body.get("query")
    conversation_id = body.get("conversation_id")
    
    if not message:
        raise HTTPException(status_code=400, detail="Message required")

    # 1. Handle Conversation ID & Persistence
    if not conversation_id:
        # Create new conversation
        conv = await db_service.create_conversation(
            user_id="user", # TODO: Get from auth token if available
            role=x_iam_role,
            title=message[:30] + "..."
        )
        conversation_id = conv["id"]
    else:
        # Verify exists
        conv = await db_service.get_conversation(conversation_id)
        if not conv:
            # Fallback if ID provided but not found
            conv = await db_service.create_conversation(
                user_id="user", 
                role=x_iam_role,
                title=message[:30] + "..."
            )
            conversation_id = conv["id"]

    # 2. Save User Message
    await db_service.add_message(
        conversation_id=conversation_id,
        role="user",
        content=message
    )
    
    # 3. Load Persistent History for Context
    # We fetch more history from DB than what frontend sends, for better context
    db_messages = await db_service.get_recent_messages(conversation_id, limit=20)
    agent_history = [{"role": m["role"], "content": m["content"]} for m in db_messages]
        
    # Instantiate Agent per request to keep state fresh or separate
    # AgentLoop uses the services we initialized
    agent = AgentLoop(
        llm_service=llm_service,
        hybrid_retriever=hybrid_retriever,
        code_ingestion=None, # Only needed if we use ingestion tools? search_code uses retriever.
        rag_service=rag_service,
        max_steps=5
    )
    
    # Resolve capabilities for the role
    capabilities = resolve_capabilities(x_iam_role)
    
    async def event_generator():
        full_response = ""
        try:
            # Yield conversation_id first so frontend knows it
            yield f"data: {json.dumps({'type': 'meta', 'conversation_id': conversation_id})}\n\n"

            async for event in agent.run_stream(message, x_iam_role, capabilities, agent_history):
                # Accumulate answer for persistence
                if event["type"] == "answer":
                    full_response += event.get("content", "")

                # SSE format: "data: {...}\n\n" (frontend expects this)
                yield f"data: {json.dumps(event)}\n\n"
            
            # 4. Save Assistant Response to DB
            if full_response:
                print(f"💾 Saving assistant response for {conversation_id} (len: {len(full_response)})")
                await db_service.add_message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=full_response
                )
                
                # 5. Auto-Summarize Title (Fire & Forget)
                if len(agent_history) == 0: # Only for new conversations (or empty history + current turns)
                     print(f"📝 Triggering title summarization for {conversation_id}")
                     asyncio.create_task(summarize_conversation(conversation_id, message, full_response))

        except Exception as e:
            print(f"Chat Error: {e}")
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

async def summarize_conversation(conversation_id: str, user_query: str, assistant_response: str):
    """Generate a short title using LLM"""
    try:
        prompt = f"Summarize this conversation into a short, 3-5 word title.\\nUser: {user_query}\\nAssistant: {assistant_response}\\nTitle:"
        title = await llm_service._call_ollama(prompt, system="You are a summarization engine. Output ONLY the title. Do not wrap in quotes.")
        title = title.strip().replace('"', '').replace("Title:", "").strip()
        if title:
             await db_service.update_conversation(conversation_id, title=title)
             print(f"✅ Updated title for {conversation_id}: {title}")
    except Exception as e:
         print(f"⚠️ Title summarization failed: {e}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
