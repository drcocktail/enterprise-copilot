"""
API Gateway
Forward requests to appropriate microservices.
Port: 8000
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
import httpx
from starlette.middleware.cors import CORSMiddleware
import uvicorn
import asyncio
from contextlib import asynccontextmanager

# Global client (initialized in lifespan)
client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global client
    client = httpx.AsyncClient(timeout=60.0)
    yield
    await client.aclose()

app = FastAPI(title="Nexus Gateway", lifespan=lifespan)

# CORS (Allow Frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service Map
SERVICES = {
    "ingestion": "http://localhost:8001",
    "chat": "http://localhost:8002",
    "core": "http://localhost:8003"
}

async def forward_request(service_url: str, request: Request, path: str):
    url = f"{service_url}{path}"
    
    # Forward headers (excluding host to avoid confusion)
    headers = dict(request.headers)
    headers.pop("host", None)
    headers.pop("content-length", None) # Let httpx handle this
    
    try:
        # Check if client is initialized
        if client is None:
            print("ERROR: httpx client is None!")
            return JSONResponse({"error": "Gateway not initialized"}, status_code=503)
            
        # Read body
        body = await request.body()
        
        print(f"Gateway forwarding {request.method} to {url}")
        
        req = client.build_request(
            request.method,
            url,
            headers=headers,
            content=body,
            params=request.query_params
        )
        
        r = await client.send(req, stream=True)
        
        return StreamingResponse(
            r.aiter_raw(),
            status_code=r.status_code,
            headers=dict(r.headers),
            background=None
        )
    except Exception as e:
        print(f"Gateway Error for {url}: {type(e).__name__}: {e}")
        return JSONResponse({"error": f"Gateway Error: {str(e)}"}, status_code=502)

# ========== ROUTES ==========

# 1. Ingestion Service
@app.api_route("/api/documents/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def ingestion_docs(request: Request, path: str):
    return await forward_request(SERVICES["ingestion"], request, f"/api/documents/{path}")

@app.api_route("/api/repos/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def ingestion_repos(request: Request, path: str):
    return await forward_request(SERVICES["ingestion"], request, f"/api/repos/{path}")

# 2. Chat Service
@app.api_route("/api/chat/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def chat_proxy(request: Request, path: str):
    return await forward_request(SERVICES["chat"], request, f"/api/chat/{path}")

# 3. Core Service (IAM, System, Lists)
@app.api_route("/api/iam/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def core_iam(request: Request, path: str):
    return await forward_request(SERVICES["core"], request, f"/api/iam/{path}")

@app.api_route("/api/conversations", methods=["GET", "POST"])
async def core_conversations(request: Request):
    return await forward_request(SERVICES["core"], request, "/api/conversations")

@app.api_route("/api/conversations/{path:path}", methods=["GET", "POST", "DELETE", "PUT"])
async def core_conversations_sub(request: Request, path: str):
    return await forward_request(SERVICES["core"], request, f"/api/conversations/{path}")

@app.api_route("/api/tickets", methods=["GET", "POST"])
async def core_tickets(request: Request):
    return await forward_request(SERVICES["core"], request, "/api/tickets")

@app.api_route("/api/audit", methods=["GET"])
async def core_audit(request: Request):
    return await forward_request(SERVICES["core"], request, "/api/audit")

@app.api_route("/api/system/health", methods=["GET"])
async def health_check(request: Request):
    # Gateway health + check others?
    try:
        # Simple check
        return {"status": "ok", "service": "gateway", "services": SERVICES}
    except:
        return {"status": "error"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
