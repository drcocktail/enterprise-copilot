"""
Code Intelligence Service
AST-based code indexing and semantic search for legacy codebases
"""

import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path
import ast
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions


class CodeIntelligence:
    """
    Code Intelligence Service for legacy codebase analysis
    - AST-based parsing
    - Function/class extraction
    - Semantic code search
    """
    
    def __init__(
        self,
        collection_name: str = "codebase_index",
        persist_directory: str = "./chroma_db"
    ):
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # Embedding function
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        
        # Get or create collection
        try:
            self.collection = self.client.get_collection(
                name=collection_name,
                embedding_function=self.embedding_function
            )
            print(f"💻 Loaded existing code collection: {collection_name}")
        except:
            self.collection = self.client.create_collection(
                name=collection_name,
                embedding_function=self.embedding_function,
                metadata={"description": "Code intelligence index"}
            )
            print(f"💻 Created new code collection: {collection_name}")
    
    async def index_codebase(self, path: str) -> Dict[str, Any]:
        """
        Index a Python codebase
        Extracts functions, classes, and their metadata
        """
        print(f"🔍 Indexing codebase at: {path}")
        
        codebase_path = Path(path)
        if not codebase_path.exists():
            return {"status": "error", "message": f"Path not found: {path}"}
        
        # Find all Python files
        python_files = list(codebase_path.rglob("*.py"))
        
        total_functions = 0
        total_classes = 0
        
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    source_code = f.read()
                
                # Parse AST
                tree = ast.parse(source_code)
                
                # Extract code entities
                entities = self._extract_code_entities(
                    tree,
                    str(py_file.relative_to(codebase_path)),
                    source_code
                )
                
                if entities:
                    # Add to collection
                    self.collection.add(
                        documents=[e["description"] for e in entities],
                        metadatas=[e["metadata"] for e in entities],
                        ids=[e["id"] for e in entities]
                    )
                    
                    total_functions += sum(1 for e in entities if e["metadata"]["type"] == "function")
                    total_classes += sum(1 for e in entities if e["metadata"]["type"] == "class")
            
            except Exception as e:
                print(f"  ⚠️  Error parsing {py_file.name}: {e}")
        
        print(f"✅ Indexed {total_functions} functions and {total_classes} classes from {len(python_files)} files")
        
        return {
            "status": "success",
            "files_processed": len(python_files),
            "functions_indexed": total_functions,
            "classes_indexed": total_classes
        }
    
    def _extract_code_entities(
        self,
        tree: ast.AST,
        file_path: str,
        source_code: str
    ) -> List[Dict[str, Any]]:
        """
        Extract functions and classes from AST
        """
        entities = []
        source_lines = source_code.split('\n')
        
        for node in ast.walk(tree):
            # Extract functions
            if isinstance(node, ast.FunctionDef):
                # Get function signature
                args = [arg.arg for arg in node.args.args]
                signature = f"{node.name}({', '.join(args)})"
                
                # Get docstring
                docstring = ast.get_docstring(node) or "No documentation"
                
                # Get source code snippet
                if hasattr(node, 'lineno') and hasattr(node, 'end_lineno'):
                    snippet = '\n'.join(source_lines[node.lineno-1:node.end_lineno])
                else:
                    snippet = ""
                
                # Create searchable description
                description = f"Function: {signature}\n{docstring}\nFile: {file_path}"
                
                entity_id = f"{file_path}::{node.name}::L{node.lineno}"
                
                entities.append({
                    "id": entity_id,
                    "description": description,
                    "metadata": {
                        "type": "function",
                        "name": node.name,
                        "signature": signature,
                        "file_path": file_path,
                        "line_start": node.lineno if hasattr(node, 'lineno') else 0,
                        "line_end": node.end_lineno if hasattr(node, 'end_lineno') else 0,
                        "docstring": docstring,
                        "snippet": snippet[:500]  # Limit snippet size
                    }
                })
            
            # Extract classes
            elif isinstance(node, ast.ClassDef):
                # Get class info
                bases = [base.id if isinstance(base, ast.Name) else str(base) for base in node.bases]
                docstring = ast.get_docstring(node) or "No documentation"
                
                # Get methods
                methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                
                description = f"Class: {node.name}\nInherits: {', '.join(bases) if bases else 'None'}\nMethods: {', '.join(methods)}\n{docstring}\nFile: {file_path}"
                
                entity_id = f"{file_path}::{node.name}::CLASS::L{node.lineno}"
                
                entities.append({
                    "id": entity_id,
                    "description": description,
                    "metadata": {
                        "type": "class",
                        "name": node.name,
                        "bases": bases,
                        "methods": methods,
                        "file_path": file_path,
                        "line_start": node.lineno if hasattr(node, 'lineno') else 0,
                        "docstring": docstring
                    }
                })
        
        return entities
    
    async def search(
        self,
        query: str,
        role: str,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 3
    ) -> Dict[str, Any]:
        """
        Search for code entities based on query
        """
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k,
                where=filters if filters else {}
            )
            
            chunks = []
            sources = []
            
            if results["documents"] and results["documents"][0]:
                for i in range(len(results["documents"][0])):
                    metadata = results["metadatas"][0][i]
                    
                    chunks.append({
                        "text": f"```python\n{metadata.get('snippet', 'No code available')}\n```\n\nLocation: {metadata.get('file_path')} (Lines {metadata.get('line_start')}-{metadata.get('line_end')})\n\n{results['documents'][0][i]}",
                        "metadata": metadata
                    })
                    
                    sources.append({
                        "type": "code",
                        "file": metadata.get("file_path", "Unknown"),
                        "entity": metadata.get("name", "Unknown"),
                        "entity_type": metadata.get("type", "code"),
                        "line_start": metadata.get("line_start", 0)
                    })
            
            return {
                "chunks": chunks,
                "sources": sources,
                "total_found": len(chunks)
            }
        
        except Exception as e:
            print(f"Error searching code: {e}")
            return {"chunks": [], "sources": [], "total_found": 0}
