"""
Document Service (Microservice)
Handles Document Ingestion Workflow:
1. Parse (PyMuPDF)
2. Chunk
3. Embed & Persist (via RagService)
4. Update DB Status
"""

import fitz  # PyMuPDF
import uuid
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from services.rag_service import RagService
from services.db_service import DatabaseService

class DocumentService:
    def __init__(self, rag_service: RagService, db_service: DatabaseService):
        self.rag_service = rag_service
        self.db_service = db_service
        
    async def process_document(self, doc_id: str, file_path: str, user_id: str, original_filename: str):
        """
        Background task to process a document.
        Does NOT block the API response.
        """
        try:
            print(f"⚙️ [DocumentService] Starting processing for {original_filename} ({doc_id})")
            
            # 1. Update Status to Processing (double check)
            await self.db_service.update_document_status(doc_id, "processing", 0)
            
            # 2. Extract Text (PyMuPDF)
            text = self._extract_text(file_path)
            if not text:
                raise ValueError("Empty text extracted")
                
            # 3. Chunking
            chunks = self._chunk_text(text, original_filename, user_id, doc_id)
            
            # 4. Embed & Persist
            # Run in thread pool to avoid blocking async loop with heavy CPU work
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.rag_service.add_documents, chunks)
            
            # 5. Update DB Status to Success
            await self.db_service.update_document_status(
                doc_id=doc_id, 
                status="Indexed", 
                chunk_count=len(chunks)
            )
            
            print(f"✅ [DocumentService] Successfully indexed {original_filename}")
            
        except Exception as e:
            print(f"❌ [DocumentService] Error processing {original_filename}: {e}")
            await self.db_service.update_document_status(
                doc_id=doc_id, 
                status="Error", 
                error_message=str(e)
            )

    def _extract_text(self, file_path: str) -> str:
        """Fast extraction using PyMuPDF"""
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text() + "\n"
        return text

    def _chunk_text(self, text: str, filename: str, user_id: str, doc_id: str, chunk_size: int = 1000) -> List[Dict[str, Any]]:
        """Recursive character splitting"""
        # Simple implementation for now
        # Ideally use langchain's splitter, but keeping deps minimal if needed
        # We'll use the same logic as before but better structured
        
        chunks = []
        start = 0
        text_len = len(text)
        
        index = 0
        while start < text_len:
            end = start + chunk_size
            if end >= text_len:
                end = text_len
            else:
                # Find last space/newline to avoid splitting words
                last_space = text.rfind(' ', start, end)
                if last_space != -1 and last_space > start:
                    end = last_space
            
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append({
                    "id": f"{doc_id}_chunk_{index}",
                    "text": chunk_text,
                    "metadata": {
                        "doc_id": doc_id,
                        "filename": filename,
                        "user_id": user_id,
                        "chunk_index": index,
                        "type": "document"
                    }
                })
                index += 1
            
            start = end
            
        return chunks
