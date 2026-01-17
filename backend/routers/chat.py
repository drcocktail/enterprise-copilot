from fastapi import APIRouter, HTTPException, Header, Request, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
import json
import uuid
import asyncio

from config.iam_config import resolve_capabilities
from services.agent_loop import AgentLoop

router = APIRouter()

# --- Models ---

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=5000)
    conversation_id: Optional[str] = None

class AgentResponse(BaseModel):
    content: str
    attachment: Optional[Dict[str, Any]] = None
    iam_role: str
    trace_id: str
    timestamp: datetime
    sources: Optional[List[Dict[str, Any]]] = None
    trace: Optional[List[Dict[str, Any]]] = None
    actions: Optional[List[Dict[str, Any]]] = None

# --- Endpoints ---

@router.post("/chat", response_model=AgentResponse)
async def chat(
    request: Request,
    body: QueryRequest,
    x_iam_role: str = Header(..., description="IAM Role of the requester")
):
    """Main chat endpoint (Legacy/Standard)"""
    trace_id = str(uuid.uuid4())[:8]
    
    # Resolve capabilities
    capabilities = resolve_capabilities(x_iam_role)
    
    # Access services from app state
    db_service = request.app.state.db_service
    llm_service = request.app.state.llm_service
    hybrid_retriever = request.app.state.hybrid_retriever
    
    # Get conversation history if provided
    conversation_history = []
    if body.conversation_id:
        try:
            messages = await db_service.get_recent_messages(body.conversation_id, limit=6)
            conversation_history = [{"role": m["role"], "content": m["content"]} for m in messages]
        except:
            pass
    
    # Classify intent
    intent = await llm_service.classify_intent(body.query, capabilities)
    
    # Get context based on intent
    context = []
    sources = []
    
    if intent.requires_code_search and request.app.state.code_collection.count() > 0:
        results = await hybrid_retriever.hybrid_search(query=body.query, top_k=5)
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
        query=body.query,
        context=context,
        role=x_iam_role,
        capabilities=capabilities,
        intent=intent,
        conversation_history=conversation_history
    )
    
    # Save messages
    if body.conversation_id:
        try:
            await db_service.add_message(body.conversation_id, role="user", content=body.query)
            await db_service.add_message(
                body.conversation_id, 
                role="assistant", 
                content=llm_response["content"], 
                metadata={"sources": sources} if sources else None
            )
        except:
            pass
    
    return AgentResponse(
        content=llm_response["content"],
        attachment=llm_response.get("attachment"),
        iam_role=x_iam_role,
        trace_id=trace_id,
        timestamp=datetime.now(),
        sources=sources if llm_response.get("show_sources") else None
    )

@router.post("/chat/agent", response_model=AgentResponse)
async def chat_agent(
    request: Request,
    body: QueryRequest,
    x_iam_role: str = Header(..., description="IAM Role")
):
    """Agentic reasoning loop endpoint"""
    trace_id = str(uuid.uuid4())[:8]
    capabilities = resolve_capabilities(x_iam_role)
    db_service = request.app.state.db_service
    
    conversation_history = []
    if body.conversation_id:
        try:
            messages = await db_service.get_recent_messages(body.conversation_id, limit=6)
            conversation_history = [{"role": m["role"], "content": m["content"]} for m in messages]
        except:
            pass
            
    # Create agent
    agent = AgentLoop(
        llm_service=request.app.state.llm_service,
        hybrid_retriever=request.app.state.hybrid_retriever,
        code_ingestion=request.app.state.code_ingestion, # FIXED: Passed correctly
        rag_service=request.app.state.rag_service,
        max_steps=5
    )
    
    result = await agent.run(
        query=body.query,
        role=x_iam_role,
        capabilities=capabilities,
        conversation_history=conversation_history
    )
    
    if body.conversation_id:
        try:
            await db_service.add_message(body.conversation_id, role="user", content=body.query)
            await db_service.add_message(
                body.conversation_id, 
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

@router.post("/chat/stream")
async def chat_stream(
    request: Request,
    body: QueryRequest,
    x_iam_role: str = Header(..., description="IAM Role")
):
    """Streaming chat endpoint using SSE"""
    capabilities = resolve_capabilities(x_iam_role)
    db_service = request.app.state.db_service
    
    conversation_id = body.conversation_id or str(uuid.uuid4())
    
    # Ensure DB record exists
    await db_service.ensure_conversation(conversation_id, user_id=x_iam_role, role=x_iam_role)
    
    # Add user message
    await db_service.add_message(conversation_id, "user", body.query)
    
    # Get history
    messages = await db_service.get_recent_messages(conversation_id, limit=10)
    # Exclude the message we just added
    if messages and messages[-1]["content"] == body.query:
        messages.pop()
    conversation_history = [{"role": m["role"], "content": m["content"]} for m in messages]
    
    event_queue = asyncio.Queue()
    
    async def background_worker():
        full_answer = ""
        thoughts = []
        actions = []
        try:
            await event_queue.put({"type": "meta", "conversation_id": conversation_id})
            
            agent = AgentLoop(
                llm_service=request.app.state.llm_service,
                hybrid_retriever=request.app.state.hybrid_retriever,
                code_ingestion=request.app.state.code_ingestion,
                rag_service=request.app.state.rag_service
            )
            
            async for event in agent.run_stream(body.query, x_iam_role, capabilities, conversation_history):
                await event_queue.put(event)
                if event["type"] == "step":
                    thoughts.append(event)
                elif event["type"] == "answer":
                    full_answer = event["content"]
                elif event["type"] == "action_result":
                    actions.append(event["data"])
            
            # Save assistant message
            await db_service.add_message(
                conversation_id,
                "assistant",
                full_answer,
                metadata={"thoughts": thoughts, "actions": actions}
            )
            
            # Summarize
            msgs = await db_service.get_messages(conversation_id, limit=100)
            if len(msgs) > 0 and len(msgs) % 5 == 0:
                summary = await request.app.state.llm_service.summarize_conversation(msgs)
                await db_service.update_conversation(conversation_id, title=summary)
                await event_queue.put({"type": "title", "title": summary})
                
        except Exception as e:
            print(f"Stream Error: {e}")
            await event_queue.put({"type": "error", "error": str(e)})
        finally:
            await event_queue.put(None)

    asyncio.create_task(background_worker())

    async def stream_generator():
        while True:
            try:
                event = await event_queue.get()
                if event is None: break
                
                if event.get("type") == "error":
                    yield f"data: {json.dumps({'type': 'error', 'content': event['error']})}\\n\\n"
                    break
                
                if event.get("type") in ["meta", "title"]:
                    yield f"data: {json.dumps(event)}\\n\\n"
                    continue
                
                # Standardize events
                if event["type"] == "step":
                    payload = {'type': 'step', 'text': event['text'], 'state': event['state']}
                elif event["type"] == "action_result":
                    payload = {'type': 'action', 'data': event['data']}
                elif event["type"] == "answer":
                    payload = {'type': 'done', 'content': event['content']}
                elif event["type"] == "step_start":
                    continue
                else:
                    payload = event
                    
                yield f"data: {json.dumps(payload)}\\n\\n"
                
            except asyncio.CancelledError:
                break

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )
