"""
Agentic RAG Service
Multi-hop retrieval with LLM-driven self-reflection and cross-encoder reranking.
"""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
import httpx


class AgenticRAG:
    """
    Agentic RAG with:
    1. Initial retrieval
    2. LLM reflection on information sufficiency
    3. Follow-up queries if needed (multi-hop)
    4. Cross-encoder reranking of final results
    """
    
    def __init__(
        self,
        rag_service,
        llm_base_url: str = "http://localhost:11434",
        llm_model: str = "qwen2.5-coder:7b",
        max_hops: int = 3
    ):
        self.rag_service = rag_service
        self.llm_base_url = llm_base_url
        self.llm_model = llm_model
        self.max_hops = max_hops
        self.client = httpx.AsyncClient(timeout=60.0)
        
        # Initialize reranker (lazy load to avoid import errors if not installed)
        self.reranker = None
        self._init_reranker()
    
    def _init_reranker(self):
        """Initialize cross-encoder reranker"""
        try:
            from sentence_transformers import CrossEncoder
            self.reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
            print("✅ Cross-encoder reranker initialized")
        except ImportError:
            print("⚠️ sentence-transformers not installed. Reranking disabled.")
            self.reranker = None
        except Exception as e:
            print(f"⚠️ Failed to load reranker: {e}")
            self.reranker = None
    
    async def retrieve_with_reflection(
        self,
        query: str,
        role: str,
        conversation_history: List[Dict[str, Any]] = None,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Multi-hop retrieval with LLM-driven reflection.
        
        Flow:
        1. Retrieve initial documents
        2. Ask LLM if information is sufficient
        3. If not, generate follow-up query and repeat
        4. Rerank all collected chunks
        """
        all_chunks = []
        all_sources = []
        queries_made = [query]
        current_query = query
        
        for hop in range(self.max_hops):
            # Step 1: Retrieve documents
            results = await self.rag_service.retrieve(
                query=current_query,
                role=role,
                top_k=top_k,
                filters=filters
            )
            
            # Add new chunks (avoid duplicates)
            new_chunks = results.get("chunks", [])
            for chunk in new_chunks:
                chunk_text = chunk.get("text", "")
                if not any(c.get("text") == chunk_text for c in all_chunks):
                    all_chunks.append(chunk)
            
            all_sources.extend(results.get("sources", []))
            
            # Step 2: Check if we have enough information
            if hop < self.max_hops - 1:  # Don't reflect on last hop
                is_sufficient, follow_up = await self._reflect_on_results(
                    original_query=query,
                    retrieved_chunks=all_chunks,
                    conversation_history=conversation_history
                )
                
                if is_sufficient:
                    break
                
                # Step 3: Use follow-up query for next hop
                # Deduplication check
                if follow_up in queries_made:
                    print(f"Skipping duplicate query: {follow_up}")
                    break
                    
                current_query = follow_up
                queries_made.append(follow_up)
        
        # Step 4: Rerank all collected chunks
        reranked_chunks = await self._rerank_chunks(query, all_chunks, top_k)
        
        # Deduplicate sources
        unique_sources = self._deduplicate_sources(all_sources)
        
        return {
            "chunks": reranked_chunks,
            "sources": unique_sources[:top_k],
            "hops_taken": len(queries_made),
            "queries_made": queries_made,
            "total_found": len(reranked_chunks)
        }
    
    async def _reflect_on_results(
        self,
        original_query: str,
        retrieved_chunks: List[Dict[str, Any]],
        conversation_history: List[Dict[str, Any]] = None
    ) -> Tuple[bool, str]:
        """
        Ask LLM if the retrieved information is sufficient.
        Returns: (is_sufficient, follow_up_query_if_needed)
        """
        # Format chunks for the prompt
        chunks_text = "\n\n".join([
            f"[Chunk {i+1}]: {chunk.get('text', '')[:500]}..."
            for i, chunk in enumerate(retrieved_chunks[:5])
        ])
        
        # Format conversation history if available
        history_context = ""
        if conversation_history:
            recent = conversation_history[-3:]  # Last 3 exchanges
            history_context = "\n".join([
                f"{msg.get('role', 'user').capitalize()}: {msg.get('content', '')[:200]}"
                for msg in recent
            ])
            history_context = f"\nRecent conversation:\n{history_context}\n"
        
        reflection_prompt = f"""You are evaluating whether retrieved information is sufficient to answer a user's question.

User Question: {original_query}
{history_context}
Retrieved Information:
{chunks_text}

Task: Determine if this information is sufficient to fully and accurately answer the user's question.

If the information IS SUFFICIENT, respond with exactly:
SUFFICIENT

If the information is NOT SUFFICIENT, respond with:
NEED_MORE: <specific follow-up search query to find the missing information>

For example:
- If asked about Q3 revenue but only Q2 is found: "NEED_MORE: Q3 2024 revenue financial results"
- If asked about a policy but only general info is found: "NEED_MORE: specific hiring policy guidelines"

Be concise. Only say NEED_MORE if critical information is truly missing."""

        try:
            response = await self.client.post(
                f"{self.llm_base_url}/api/generate",
                json={
                    "model": self.llm_model,
                    "prompt": reflection_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,  # Low temperature for deterministic response
                        "num_predict": 100   # Short response
                    }
                }
            )
            
            if response.status_code == 200:
                result = response.json().get("response", "").strip()
                
                if result.upper().startswith("SUFFICIENT"):
                    return True, ""
                elif result.upper().startswith("NEED_MORE:"):
                    follow_up = result[10:].strip()
                    return False, follow_up
                else:
                    # Default to sufficient if unclear
                    return True, ""
            
            return True, ""
            
        except Exception as e:
            print(f"Reflection error: {e}")
            return True, ""  # Default to sufficient on error
    
    async def _rerank_chunks(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Rerank chunks using cross-encoder for better relevance.
        Falls back to original order if reranker not available.
        """
        if not chunks:
            return []
        
        if not self.reranker:
            # No reranker available, return as-is (limited to top_k)
            return chunks[:top_k]
        
        try:
            # Create query-document pairs for scoring
            pairs = [[query, chunk.get("text", "")] for chunk in chunks]
            
            # Get relevance scores
            scores = self.reranker.predict(pairs)
            
            # Sort by score (descending)
            scored_chunks = list(zip(chunks, scores))
            scored_chunks.sort(key=lambda x: x[1], reverse=True)
            
            # Return top_k with scores added to metadata
            reranked = []
            for chunk, score in scored_chunks[:top_k]:
                chunk_copy = chunk.copy()
                if "metadata" not in chunk_copy:
                    chunk_copy["metadata"] = {}
                chunk_copy["metadata"]["rerank_score"] = float(score)
                reranked.append(chunk_copy)
            
            return reranked
            
        except Exception as e:
            print(f"Reranking error: {e}")
            return chunks[:top_k]
    
    def _deduplicate_sources(
        self,
        sources: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Remove duplicate sources based on document + page"""
        seen = set()
        unique = []
        
        for source in sources:
            key = f"{source.get('document', '')}_p{source.get('page', 0)}"
            if key not in seen:
                seen.add(key)
                unique.append(source)
        
        # Sort by relevance score
        unique.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        
        return unique
    
    async def add_code_chunks(self, chunks: List[Dict[str, Any]]):
        """Delegate code chunk addition to underlying RAG service"""
        if hasattr(self.rag_service, "add_code_chunks"):
            await self.rag_service.add_code_chunks(chunks)
        else:
            # Fallback for now if not implemented in base RAG
            print("⚠️ underlying RAG service missing add_code_chunks")

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
