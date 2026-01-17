from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pathlib import Path
import uvicorn
import chromadb
from chromadb.config import Settings

# Import Services
from services.db_service import DatabaseService
from services.rag_service import RagService
from services.code_ingestion import CodeIngestionService
from services.llm_service import LLMService
from services.document_service import DocumentService
from services.hybrid_retriever import HybridRetriever
from config.iam_config import IAMConfig

# Import Routers
from routers import chat, ingestion, core

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Initializing DevOps Copilot V3 (Modular Monolith)...")

    # 1. Initialize Configuration
    app.state.iam_config = IAMConfig()
    await app.state.iam_config.load()

    # 2. Initialize Core Services
    app.state.db_service = DatabaseService()
    app.state.llm_service = LLMService()

    # 3. Initialize Vectors (SHARED CHROMA CLIENT)
    chroma_path = Path(__file__).parent / "chroma_db"
    print(f"🔹 Connecting to ChromaDB at {chroma_path}")
    app.state.chroma_client = chromadb.PersistentClient(
        path=str(chroma_path),
        settings=Settings(anonymized_telemetry=False)
    )
    
    # Create Collections
    app.state.code_collection = app.state.chroma_client.get_or_create_collection(
        name="code_chunks",
        metadata={"hnsw:space": "cosine"}
    )
    
    # 4. Initialize Rag & Retriever
    # RagService usually controls its own chroma client, but we want to SHARE it if possible
    # or ensure it points to same path safely. 
    # Current rag_service.py likely does its own init. 
    # For now, let's let RagService do its thing but strictly in THIS process.
    # ideally we pass the client to RagService.
    # Looking at rag_service.py (I haven't edited it), it likely inits its own.
    # Since we are single process now, it's safer.
    app.state.rag_service = RagService() 
    
    app.state.hybrid_retriever = HybridRetriever(collection=app.state.code_collection)

    # 5. Initialize Ingestion
    app.state.code_ingestion = CodeIngestionService()
    try:
        app.state.code_ingestion.load_all_graphs()
        # Sync graph to retriever
        app.state.hybrid_retriever.graph = app.state.code_ingestion.load_all_graphs()
    except Exception as e:
        print(f"⚠️ Failed to load code graphs: {e}")

    app.state.document_service = DocumentService(app.state.rag_service, app.state.db_service)
    
    print("✅ All Services Ready & Mounted to app.state")
    
    # Debug: Print Routes
    for route in app.routes:
        print(f"📍 Route: {route.path} [{route.name}]")

    yield
    
    print("🛑 Shutting down...")

app = FastAPI(
    title="DevOps Copilot API",
    version="3.0.0",
    description="Modular Monolith Architecture",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routers
# /api/chat...
app.include_router(chat.router, prefix="/api", tags=["Chat"])
# /api/repos..., /api/documents...
app.include_router(ingestion.router, prefix="/api", tags=["Ingestion"])
# /api/health, /api/iam...
app.include_router(core.router, prefix="/api", tags=["Core"])

@app.get("/")
async def root():
    return {"status": "online", "architecture": "Modular Monolith"}

if __name__ == "__main__":
    # Run on 8000 as typical for monoliths (Gateway was 8000)
    uvicorn.run(app, host="0.0.0.0", port=8000)
