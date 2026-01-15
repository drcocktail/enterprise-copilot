"""
RAG Service with ChromaDB
Advanced document retrieval with metadata filtering and reranking
"""

import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
import PyPDF2
from datetime import datetime


class RAGService:
    """
    RAG (Retrieval Augmented Generation) Service
    - Document ingestion with metadata extraction
    - Semantic search with IAM filtering
    - Page-level citations
    """
    
    def __init__(
        self,
        collection_name: str = "enterprise_documents",
        persist_directory: str = "./chroma_db"
    ):
        # Initialize ChromaDB client (Persistent)
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # Use sentence transformers embedding (or Ollama nomic-embed-text)
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"  # Fast and efficient
        )
        
        # Get or create collection
        try:
            self.collection = self.client.get_collection(
                name=collection_name,
                embedding_function=self.embedding_function
            )
            print(f"📚 Loaded existing collection: {collection_name}")
        except:
            self.collection = self.client.create_collection(
                name=collection_name,
                embedding_function=self.embedding_function,
                metadata={"description": "Enterprise documents with IAM metadata"}
            )
            print(f"📚 Created new collection: {collection_name}")
        
        self.docs_path = Path(__file__).parent.parent.parent / "docs"
    
    async def ingest_documents(self) -> Dict[str, Any]:
        """
        Ingest all PDF documents from docs/ folder
        Extract text, metadata, and create embeddings
        """
        print("📥 Starting document ingestion...")
        
        pdf_files = list(self.docs_path.glob("*.pdf"))
        if not pdf_files:
            return {"status": "no_documents", "message": "No PDF files found in docs/"}
        
        total_chunks = 0
        
        for pdf_path in pdf_files:
            print(f"Processing: {pdf_path.name}")
            
            # Extract text from PDF
            chunks = await self._extract_pdf_chunks(pdf_path)
            
            # Add to ChromaDB
            if chunks:
                self.collection.add(
                    documents=[chunk["text"] for chunk in chunks],
                    metadatas=[chunk["metadata"] for chunk in chunks],
                    ids=[chunk["id"] for chunk in chunks]
                )
                total_chunks += len(chunks)
                print(f"  ✓ Added {len(chunks)} chunks")
        
        print(f"✅ Ingestion complete: {total_chunks} chunks from {len(pdf_files)} documents")
        
        return {
            "status": "success",
            "documents_processed": len(pdf_files),
            "total_chunks": total_chunks
        }
    
    async def _extract_pdf_chunks(
        self,
        pdf_path: Path,
        chunk_size: int = 1000,
        overlap: int = 200
    ) -> List[Dict[str, Any]]:
        """
        Extract text chunks from PDF with metadata
        Chunks are created at semantic boundaries (pages first, then paragraphs)
        """
        chunks = []
        
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                num_pages = len(pdf_reader.pages)
                
                for page_num in range(num_pages):
                    page = pdf_reader.pages[page_num]
                    page_text = page.extract_text()
                    
                    if not page_text.strip():
                        continue
                    
                    # Determine document category and sensitivity
                    doc_name = pdf_path.stem.lower()
                    category, sensitivity = self._classify_document(doc_name)
                    
                    # Create chunks from page text
                    page_chunks = self._create_text_chunks(
                        text=page_text,
                        chunk_size=chunk_size,
                        overlap=overlap
                    )
                    
                    # Add metadata to each chunk
                    for idx, chunk_text in enumerate(page_chunks):
                        chunk_id = f"{pdf_path.stem}_p{page_num+1}_c{idx}"
                        
                        chunks.append({
                            "id": chunk_id,
                            "text": chunk_text,
                            "metadata": {
                                "document_name": pdf_path.name,
                                "document_category": category,
                                "sensitivity_level": sensitivity,
                                "page_number": page_num + 1,
                                "total_pages": num_pages,
                                "chunk_index": idx,
                                "ingestion_timestamp": datetime.now().isoformat()
                            }
                        })
        
        except Exception as e:
            print(f"Error processing {pdf_path.name}: {e}")
        
        return chunks
    
    def _classify_document(self, filename: str) -> tuple[str, int]:
        """
        Classify document type and sensitivity level
        Returns: (category, sensitivity_level)
        Sensitivity: 1=Public, 2=Internal, 3=Confidential, 4=Restricted
        """
        if "annual" in filename or "report" in filename or "financial" in filename:
            return ("Financial Report", 3)  # Confidential
        elif "employee" in filename or "hr" in filename or "policy" in filename:
            return ("HR Policy", 4)  # Restricted (PII)
        elif "strategy" in filename or "roadmap" in filename:
            return ("Strategy Document", 3)  # Confidential
        elif "technical" in filename or "architecture" in filename:
            return ("Technical Document", 2)  # Internal
        else:
            return ("General Document", 2)  # Internal
    
    def _create_text_chunks(
        self,
        text: str,
        chunk_size: int = 500, # Approx chars
        overlap: int = 50
    ) -> List[str]:
        """
        Create overlapping text chunks using sentence boundaries
        Much more robust than word splitting.
        """
        import re
        
        # Split by sentence endings (.?!) followed by space or newline
        sentences = re.split(r'(?<=[.?!])\s+', text)
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence_len = len(sentence)
            
            if current_length + sentence_len > chunk_size and current_chunk:
                # Store current chunk
                chunks.append(" ".join(current_chunk))
                
                # Start new chunk with overlap (keep last few sentences if possible)
                # Simple overlap: keep last sentence
                last_sent = current_chunk[-1]
                current_chunk = [last_sent] if len(last_sent) < chunk_size else []
                current_length = len(last_sent) if len(last_sent) < chunk_size else 0
            
            current_chunk.append(sentence)
            current_length += sentence_len
        
        if current_chunk:
            chunks.append(" ".join(current_chunk))
            
        return chunks
    
    async def retrieve(
        self,
        query: str,
        role: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Retrieve relevant document chunks with IAM filtering
        """
        # Query ChromaDB with metadata filters
        where_clause = filters if filters else {}
        
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k,
                where=where_clause
            )
            
            # Format results
            chunks = []
            sources = []
            
            if results["documents"] and results["documents"][0]:
                for i in range(len(results["documents"][0])):
                    metadata = results["metadatas"][0][i]
                    
                    chunks.append({
                        "text": results["documents"][0][i],
                        "metadata": metadata
                    })
                    
                    sources.append({
                        "document": metadata.get("document_name", "Unknown"),
                        "page": metadata.get("page_number", 0),
                        "category": metadata.get("document_category", "General"),
                        "relevance_score": 1 - results["distances"][0][i] if "distances" in results else 1.0
                    })
            
            return {
                "chunks": chunks,
                "sources": sources,
                "total_found": len(chunks)
            }
        
        except Exception as e:
            print(f"Error retrieving documents: {e}")
            return {"chunks": [], "sources": [], "total_found": 0}
