"""
RAG Service
Microservice for handling Embeddings and Vector DB interactions for DOCUMENTS.
Distinct from Code Ingestion.
"""

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any
import os
from pathlib import Path

class RagService:
    def __init__(self, collection_name: str = "document_chunks"):
        print("🤖 Initializing RAG Service (Document Embeddings)...")
        
        # 1. Initialize Vector DB (Chroma)
        self.chroma_path = Path(__file__).parent.parent / "chroma_db"
        self.chroma_client = chromadb.PersistentClient(
            path=str(self.chroma_path),
            settings=Settings(anonymized_telemetry=False)
        )
        
        self.collection = self.chroma_client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        
        # 2. Initialize Text Embedding Model
        # Using a lightweight, high-performance model for docs
        # distinct from the code model (bge-code)
        try:
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            print("✅ Loaded embedding model: all-MiniLM-L6-v2")
        except Exception as e:
            print(f"⚠️ Failed to load embedding model: {e}")
            self.model = None

        # 3. Initialize Code Collection (for code chunks)
        self.code_collection = self.chroma_client.get_or_create_collection(
            name="code_chunks",
            metadata={"hnsw:space": "cosine"}
        )

    def embed_text(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of text chunks"""
        if not self.model:
            return []
        
        embeddings = self.model.encode(texts)
        return embeddings.tolist()

    def add_documents(self, chunks: List[Dict[str, Any]]):
        """Add chunks to ChromaDB"""
        if not chunks:
            return
            
        texts = [c["text"] for c in chunks]
        metadatas = [c["metadata"] for c in chunks]
        ids = [c["id"] for c in chunks]
        
        # Generate embeddings
        print(f"🧮 Generating embeddings for {len(texts)} chunks...")
        embeddings = self.embed_text(texts)
        
        if embeddings:
            self.collection.add(
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
            print(f"💾 Persisted {len(texts)} chunks to ChromaDB (documents)")

    async def add_code_chunks(self, chunks: List[Dict[str, Any]]):
        """Add code chunks to ChromaDB (code_chunks collection)"""
        if not chunks or not self.model:
            return
            
        texts = [c["text"] for c in chunks]
        metadatas = [c["metadata"] for c in chunks]
        ids = [c["id"] for c in chunks]
        
        # Generate embeddings
        print(f"🧮 Generating embeddings for {len(texts)} code chunks...")
        # Since this is async/blocking, we might want to run in executor but for now direct is fine
        embeddings = self.embed_text(texts)
        
        if embeddings:
            self.code_collection.add(
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
            print(f"💾 Persisted {len(texts)} chunks to ChromaDB (code_chunks)")

    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Semantic search for documents"""
        if not self.model:
            return []
            
        query_embedding = self.model.encode([query]).tolist()
        
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=limit
        )
        
        formatted_results = []
        if results["documents"]:
            for i in range(len(results["documents"][0])):
                formatted_results.append({
                    "text": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "score": results["distances"][0][i] if results["distances"] else 0
                })
                
        return formatted_results
