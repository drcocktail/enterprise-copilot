"""
Hybrid Retriever Service
Implements Semantic + BM25 + RRF (Reciprocal Rank Fusion) for code retrieval.
"""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
import numpy as np

# BM25 for keyword search
from rank_bm25 import BM25Okapi

# Cross-encoder reranking
try:
    from sentence_transformers import CrossEncoder
    RERANKER_AVAILABLE = True
except ImportError:
    RERANKER_AVAILABLE = False


class HybridRetriever:
    """
    Hybrid retrieval combining:
    1. Semantic search (vector similarity)
    2. BM25 keyword search
    3. Graph-based expansion
    4. RRF fusion
    5. Cross-encoder reranking
    """
    
    def __init__(
        self,
        collection,  # ChromaDB collection
        graph=None,  # NetworkX graph (optional)
        reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    ):
        self.collection = collection
        self.graph = graph
        
        # BM25 index (built lazily)
        self.bm25 = None
        self.bm25_corpus = []
        self.bm25_ids = []
        
        # Cross-encoder reranker
        self.reranker = None
        if RERANKER_AVAILABLE:
            try:
                self.reranker = CrossEncoder(reranker_model)
                print("✅ Cross-encoder reranker initialized")
            except Exception as e:
                print(f"⚠️ Could not load reranker: {e}")
    
    def build_bm25_index(self, documents: List[Dict[str, Any]]) -> None:
        """Build BM25 index from documents."""
        self.bm25_corpus = []
        self.bm25_ids = []
        
        for doc in documents:
            text = doc.get("text", "")
            doc_id = doc.get("id", "")
            
            # Tokenize for BM25
            tokens = self._tokenize(text)
            self.bm25_corpus.append(tokens)
            self.bm25_ids.append(doc_id)
        
        if self.bm25_corpus:
            self.bm25 = BM25Okapi(self.bm25_corpus)
            print(f"📚 BM25 index built with {len(self.bm25_corpus)} documents")
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization for BM25."""
        import re
        # Convert camelCase and snake_case
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
        text = text.replace('_', ' ')
        # Lowercase and split
        tokens = text.lower().split()
        # Remove very short tokens
        tokens = [t for t in tokens if len(t) > 2]
        return tokens
    
    async def hybrid_search(
        self,
        query: str,
        top_k: int = 10,
        semantic_weight: float = 0.5,
        bm25_weight: float = 0.3,
        graph_weight: float = 0.2,
        rerank: bool = True,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search with RRF fusion.
        """
        all_results = {}
        
        # 1. Semantic search (ChromaDB)
        semantic_results = await self._semantic_search(query, top_k * 3, filters)
        self._add_to_results(all_results, semantic_results, "semantic", semantic_weight)
        
        # 2. BM25 keyword search
        if self.bm25 is not None:
            bm25_results = await self._bm25_search(query, top_k * 3)
            self._add_to_results(all_results, bm25_results, "bm25", bm25_weight)
        
        # 3. Graph expansion (if available)
        if self.graph is not None and semantic_results:
            graph_results = await self._graph_expansion(semantic_results[:3])
            self._add_to_results(all_results, graph_results, "graph", graph_weight)
        
        # 4. RRF fusion
        fused_results = self._rrf_fusion(all_results)
        
        # 5. Get top candidates
        top_candidates = sorted(fused_results.items(), key=lambda x: x[1], reverse=True)[:top_k * 2]
        
        # 6. Enrich with full documents
        enriched = await self._enrich_results([doc_id for doc_id, _ in top_candidates])
        
        # 7. Rerank with cross-encoder
        if rerank and self.reranker and len(enriched) > 0:
            enriched = await self._rerank(query, enriched, top_k)
        else:
            enriched = enriched[:top_k]
        
        return enriched
    
    async def _semantic_search(
        self,
        query: str,
        top_k: int,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[str, float]]:
        """Semantic search using ChromaDB."""
        try:
            where = filters if filters else None
            
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k,
                where=where
            )
            
            # Return (id, score) tuples
            ids = results.get("ids", [[]])[0]
            distances = results.get("distances", [[]])[0]
            
            # Convert distances to similarity scores
            scores = [1 / (1 + d) for d in distances]
            
            return list(zip(ids, scores))
            
        except Exception as e:
            print(f"Semantic search error: {e}")
            return []
    
    async def _bm25_search(
        self,
        query: str,
        top_k: int
    ) -> List[Tuple[str, float]]:
        """BM25 keyword search."""
        if self.bm25 is None:
            return []
        
        tokens = self._tokenize(query)
        scores = self.bm25.get_scores(tokens)
        
        # Get top k indices
        top_indices = np.argsort(scores)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            if scores[idx] > 0:
                results.append((self.bm25_ids[idx], float(scores[idx])))
        
        # Normalize scores
        if results:
            max_score = max(r[1] for r in results)
            if max_score > 0:
                results = [(doc_id, score / max_score) for doc_id, score in results]
        
        return results
    
    async def _graph_expansion(
        self,
        seed_results: List[Tuple[str, float]]
    ) -> List[Tuple[str, float]]:
        """Expand results using code graph."""
        if self.graph is None:
            return []
        
        expanded = []
        
        for doc_id, score in seed_results:
            # Try to find node by matching file path
            for node in self.graph.nodes():
                if doc_id in node or node in doc_id:
                    # Get neighbors
                    neighbors = list(self.graph.neighbors(node))
                    for neighbor in neighbors[:5]:
                        # Give neighbors a reduced score
                        expanded.append((neighbor, score * 0.5))
                    break
        
        return expanded
    
    def _add_to_results(
        self,
        all_results: Dict[str, List[Tuple[int, str]]],
        new_results: List[Tuple[str, float]],
        source: str,
        weight: float
    ) -> None:
        """Add results with their ranks for RRF."""
        for rank, (doc_id, score) in enumerate(new_results):
            if doc_id not in all_results:
                all_results[doc_id] = []
            all_results[doc_id].append((rank + 1, source, weight))
    
    def _rrf_fusion(
        self,
        all_results: Dict[str, List[Tuple[int, str, float]]],
        k: int = 60
    ) -> Dict[str, float]:
        """
        Reciprocal Rank Fusion.
        RRF(d) = Σ 1 / (k + rank(d))
        """
        fused = {}
        
        for doc_id, ranks in all_results.items():
            score = 0
            for rank, source, weight in ranks:
                score += weight * (1 / (k + rank))
            fused[doc_id] = score
        
        return fused
    
    async def _enrich_results(
        self,
        doc_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """Fetch full documents from ChromaDB."""
        if not doc_ids:
            return []
        
        try:
            results = self.collection.get(
                ids=doc_ids,
                include=["documents", "metadatas"]
            )
            
            enriched = []
            for i, doc_id in enumerate(results.get("ids", [])):
                enriched.append({
                    "id": doc_id,
                    "text": results["documents"][i] if results.get("documents") else "",
                    "metadata": results["metadatas"][i] if results.get("metadatas") else {}
                })
            
            return enriched
            
        except Exception as e:
            print(f"Enrichment error: {e}")
            return []
    
    async def _rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """Rerank documents using cross-encoder."""
        if not self.reranker or not documents:
            return documents[:top_k]
        
        try:
            # Create query-document pairs
            pairs = [[query, doc.get("text", "")[:1000]] for doc in documents]
            
            # Get scores
            scores = self.reranker.predict(pairs)
            
            # Sort by score
            scored_docs = list(zip(documents, scores))
            scored_docs.sort(key=lambda x: x[1], reverse=True)
            
            # Add rerank score to metadata
            reranked = []
            for doc, score in scored_docs[:top_k]:
                doc_copy = doc.copy()
                doc_copy["rerank_score"] = float(score)
                reranked.append(doc_copy)
            
            return reranked
            
        except Exception as e:
            print(f"Reranking error: {e}")
            return documents[:top_k]
    
    def format_for_context(
        self,
        results: List[Dict[str, Any]],
        max_chars: int = 8000
    ) -> str:
        """Format results for LLM context."""
        context_parts = []
        total_chars = 0
        
        for doc in results:
            meta = doc.get("metadata", {})
            text = doc.get("text", "")
            
            file_path = meta.get("file_path", "unknown")
            start_line = meta.get("start_line", "?")
            end_line = meta.get("end_line", "?")
            language = meta.get("language", "")
            name = meta.get("name", "")
            
            header = f"📁 {file_path}:{start_line}-{end_line}"
            if name:
                header += f" ({name})"
            
            code_block = f"\n{header}\n```{language}\n{text}\n```\n"
            
            if total_chars + len(code_block) > max_chars:
                break
            
            context_parts.append(code_block)
            total_chars += len(code_block)
        
        return "\n".join(context_parts)
