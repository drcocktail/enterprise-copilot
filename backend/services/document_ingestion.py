"""
Document Ingestion Service
Handles PDF extraction, chunking, and Knowledge Graph construction (Concepts + Sequential).
"""

import os
import uuid
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import re
from collections import Counter
import math

# PDF Processing
import PyPDF2

# Graph
import networkx as nx

# Embeddings (using the same model as code for consistency, or text model)
# We'll assume the same embedding service or key is used.

class DocumentIngestionService:
    """
    Ingests documents into a Knowledge Graph.
    Nodes: Chunks (text) and Concepts (keywords).
    Edges: NEXT (chunk->chunk), MENTIONS (chunk->concept).
    """

    def __init__(self, upload_dir: Optional[str] = None):
        if upload_dir is None:
            self.upload_dir = Path(__file__).parent.parent / "uploads"
        else:
            self.upload_dir = Path(upload_dir)
        
        self.upload_dir.mkdir(exist_ok=True)
        self.graph = nx.DiGraph()
        
        # Concept extraction settings
        self.min_concept_freq = 2
        self.stop_words = set([
            "the", "and", "or", "of", "to", "a", "in", "is", "that", "for", "it", "as", "was", "with", "on",
            "at", "by", "be", "this", "which", "from", "but", "not", "are", "can", "an", "if", "we", "you",
            "all", "has", "have", "they", "their", "one", "more", "when", "document", "file", "page", "section"
        ])

    async def ingest_document(self, file_path: str, user_id: str, original_filename: str) -> Dict[str, Any]:
        """
        Process a document: Extract -> Chunk -> Build Graph.
        Returns stats about the ingestion.
        """
        try:
            print(f"📄 Processing {original_filename}...")
            
            # 1. Extract Text
            content = await self._extract_text(file_path)
            if not content:
                raise ValueError("No text extracted/empty file")

            # 2. Chunking (Paragraph/Recursive)
            chunks = self._chunk_text(content, original_filename, user_id)
            print(f"🧩 Created {len(chunks)} chunks")

            # 3. Concept Extraction (Heuristic TF-IDF style on this doc)
            concepts = self._extract_concepts(chunks)
            print(f"🧠 Extracted {len(concepts)} key concepts")

            # 4. Build Graph
            node_count, edge_count = await self._build_document_graph(chunks, concepts, original_filename)

            return {
                "status": "success",
                "file_path": file_path,
                "chunk_count": len(chunks),
                "concept_count": len(concepts),
                "graph_nodes": node_count,
                "graph_edges": edge_count
            }
        
        except Exception as e:
            print(f"❌ Document ingestion error: {e}")
            return {"status": "error", "error": str(e)}

    async def _extract_text(self, file_path: str) -> str:
        """Extract text from PDF or Text file."""
        path = Path(file_path)
        content = ""
        
        if path.suffix.lower() == '.pdf':
            def read_pdf():
                text = ""
                with open(path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    for page in reader.pages:
                        text += page.extract_text() + "\n\n"
                return text
            
            loop = asyncio.get_event_loop()
            content = await loop.run_in_executor(None, read_pdf)
        else:
            # Assume text/md
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        
        return content

    def _chunk_text(self, text: str, filename: str, user_id: str, chunk_size: int = 1000, overlap: int = 100) -> List[Dict[str, Any]]:
        """
        Split text into chunks. 
        Uses double newline (paragraphs) as primary split, then length.
        """
        # Simple recursive-like split on paragraphs
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = ""
        
        chunk_id_counter = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
                
            if len(current_chunk) + len(para) > chunk_size:
                # Flush current chunk
                if current_chunk:
                    chunks.append(self._create_chunk_obj(current_chunk, filename, user_id, chunk_id_counter))
                    chunk_id_counter += 1
                    # Start new chunk with overlap (last few words of prev)
                    overlap_text = " ".join(current_chunk.split()[-20:]) 
                    current_chunk = overlap_text + "\n\n" + para
                else:
                    # Para is massive, force split it
                    # (Simplified: just take it as is for now, or could split by chars)
                    chunks.append(self._create_chunk_obj(para, filename, user_id, chunk_id_counter))
                    chunk_id_counter += 1
                    current_chunk = ""
            else:
                if current_chunk:
                    current_chunk += "\n\n"
                current_chunk += para
        
        if current_chunk:
             chunks.append(self._create_chunk_obj(current_chunk, filename, user_id, chunk_id_counter))
             
        return chunks

    def _create_chunk_obj(self, text: str, filename: str, user_id: str, index: int) -> Dict[str, Any]:
        return {
            "id": f"{filename}_chunk_{index}_{uuid.uuid4().hex[:6]}",
            "text": text,
            "metadata": {
                "type": "document_chunk",
                "filename": filename,
                "user_id": user_id,
                "chunk_index": index,
                "created_at": datetime.now().isoformat()
            }
        }

    def _extract_concepts(self, chunks: List[Dict[str, Any]]) -> List[str]:
        """
        Extract key concepts based on frequency and capitalization (heuristic).
        Finds Proper Nouns or frequent technical terms.
        """
        all_text = " ".join([c["text"] for c in chunks])
        words = re.findall(r'\b[A-Za-z][a-zA-Z0-9_-]+\b', all_text)
        
        # Filter stopwords and short words
        filtered = [w for w in words if w.lower() not in self.stop_words and len(w) > 2]
        
        # Count freq
        counts = Counter(filtered)
        
        # Calculate dynamic threshold (e.g., top 10% or min_freq)
        concepts = [word for word, count in counts.items() if count >= self.min_concept_freq]
        
        # Limit to top 20 concepts per doc to keep graph clean
        top_concepts = sorted(concepts, key=lambda x: counts[x], reverse=True)[:20]
        return top_concepts

    async def _build_document_graph(self, chunks: List[Dict[str, Any]], concepts: List[str], filename: str):
        """Build NetworkX graph for the document."""
        
        # 1. Add Chunk Nodes and NEXT edges
        prev_chunk_id = None
        for chunk in chunks:
            chunk_id = chunk["id"]
            self.graph.add_node(chunk_id, type="chunk", text=chunk["text"][:100]+"...", full_text=chunk["text"], **chunk["metadata"])
            
            if prev_chunk_id:
                self.graph.add_edge(prev_chunk_id, chunk_id, type="NEXT")
            
            prev_chunk_id = chunk_id

        # 2. Add Concept Nodes and MENTIONS edges
        # Normalize concepts for matching
        concept_set = set(concepts)
        
        for concept in concepts:
            concept_id = f"concept::{concept.lower()}"
            self.graph.add_node(concept_id, type="concept", name=concept, filename=filename)
        
        for chunk in chunks:
            chunk_id = chunk["id"]
            chunk_text_lower = chunk["text"].lower()
            
            for concept in concepts:
                if concept.lower() in chunk_text_lower:
                    concept_id = f"concept::{concept.lower()}"
                    # MENTIONS edge
                    self.graph.add_edge(chunk_id, concept_id, type="MENTIONS")
        
        return self.graph.number_of_nodes(), self.graph.number_of_edges()

    async def get_context_for_query(self, query: str) -> str:
        """
        Retrieve context using graph traversal.
        1. Find matching Concept nodes.
        2. Retrieve linked Chunk nodes (MENTIONS).
        3. Return text of top chunks.
        """
        if not self.graph.nodes():
            return "No documents ingested properly."
            
        params = query.lower().split()
        relevant_chunks = []
        
        # 1. Find matched concepts
        matched_concepts = []
        for node, data in self.graph.nodes(data=True):
            if data.get("type") == "concept":
                if data["name"].lower() in params or any(p in data["name"].lower() for p in params):
                    matched_concepts.append(node)
        
        # 2. Get adjacent chunks
        for concept_node in matched_concepts:
            neighbors = self.graph.neighbors(concept_node)
            for neighbor in neighbors: # Since edges are directed, check direction? 
                # MENTIONS is Chunk -> Concept. So we need predecessors of concept.
                pass
            
            # Using predecessors for Chunk -> Concept
            predecessors = self.graph.predecessors(concept_node)
            for pred in predecessors:
                node_data = self.graph.nodes[pred]
                if node_data.get("type") == "chunk":
                    relevant_chunks.append(node_data["text"])

        # Fallback: Simple text match on chunks if no concepts found or just to boost
        for node, data in self.graph.nodes(data=True):
            if data.get("type") == "chunk":
                if any(p in data["text"].lower() for p in params):
                    relevant_chunks.append(data["text"])

        if not relevant_chunks:
            return "No relevant information found in documents."
            
        # Deduplicate and format
        unique_chunks = list(set(relevant_chunks))
        return "\n---\n".join(unique_chunks[:5]) 
