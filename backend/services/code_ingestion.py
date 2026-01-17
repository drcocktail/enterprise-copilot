"""
Code Ingestion Service
Handles GitHub repo cloning, AST parsing using Tree-sitter, and code embedding.
"""

import os
import uuid
import shutil
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import re
import json

# Git operations
from git import Repo

# Graph for code relationships
import networkx as nx

# Tree-sitter
try:
    from tree_sitter import Language, Parser
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False
    print("⚠️ tree-sitter not installed.")

class CodeIngestionService:
    """
    Service for ingesting GitHub repos using Tree-sitter for robust parsing.
    """
    
    SUPPORTED_EXTENSIONS = {
        '.py': 'python',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.jsx': 'javascript',
        '.tsx': 'typescript',
        '.java': 'java',
        '.go': 'go',
        '.go': 'go',
        '.c': 'c',
        '.md': 'markdown',
        '.txt': 'text',
        '.json': 'json',
        '.yml': 'yaml',
        '.yaml': 'yaml',
    }
    
    SKIP_DIRS = {
        'node_modules', '.git', '__pycache__', '.venv', 'venv', 
        'dist', 'build', '.next', '.nuxt', 'coverage', '.pytest_cache',
        'vendor', 'target', '.idea', '.vscode'
    }
    
    def __init__(self, repos_dir: Optional[str] = None):
        if repos_dir is None:
            self.repos_dir = Path(__file__).parent.parent / "repos"
        else:
            self.repos_dir = Path(repos_dir)
        
        self.repos_dir.mkdir(exist_ok=True)
        self.graph = nx.DiGraph()
        
        self.parsers = {}
        if TREE_SITTER_AVAILABLE:
            self._setup_parsers()
        
    def _setup_parsers(self):
        """Load compiled tree-sitter languages."""
        lib_path = Path(__file__).parent.parent / "build" / "my-languages.so"
        if not lib_path.exists():
            print(f"⚠️ Tree-sitter library not found at: {lib_path}")
            return

        try:
            import ctypes
            lib = ctypes.cdll.LoadLibrary(str(lib_path))
            
            self.LANGUAGES = {}
            
            # Map of internal name to symbol name
            # Usually tree_sitter_{lang}
            lang_map = {
                'python': 'tree_sitter_python',
                'javascript': 'tree_sitter_javascript',
                'typescript': 'tree_sitter_typescript',
                'go': 'tree_sitter_go',
                'java': 'tree_sitter_java'
            }
            
            for lang_name, symbol in lang_map.items():
                try:
                    # New API (0.22+): Language(ptr)
                    # We need to get the function from lib and call it?
                    # No, usually we pass the function pointer directly or the result of calling it?
                    # The function returns a TSLanguage*
                    
                    # For tree-sitter 0.22+, Language() takes a capsule or void*
                    # Let's try passing the address.
                    lang_func = getattr(lib, symbol)
                    # We need to set res type
                    lang_func.restype = ctypes.c_void_p
                    lang_ptr = lang_func()
                    
                    self.LANGUAGES[lang_name] = Language(lang_ptr)
                except Exception as e:
                    print(f"Failed to load {lang_name}: {e}")
            
            for lang_name, lang_obj in self.LANGUAGES.items():
                try:
                    parser = Parser(lang_obj)
                    self.parsers[lang_name] = parser
                except TypeError:
                    # Fallback for older versions if somehow mixed
                    parser = Parser()
                    parser.set_language(lang_obj)
                    self.parsers[lang_name] = parser
            
            print(f"✅ Tree-sitter parsers loaded: {list(self.parsers.keys())}")
        except Exception as e:
            print(f"⚠️ Error loading parsers: {e}")
            # Fallback to old API attempt if ctypes fails (for 0.20 compat just in case)
            try:
                 self.LANGUAGES = {
                    'python': Language(str(lib_path), 'python'),
                    'javascript': Language(str(lib_path), 'javascript'),
                    'typescript': Language(str(lib_path), 'typescript'),
                    'go': Language(str(lib_path), 'go'),
                    'java': Language(str(lib_path), 'java')
                }
                 for lang_name, lang_obj in self.LANGUAGES.items():
                    parser = Parser()
                    parser.set_language(lang_obj)
                    self.parsers[lang_name] = parser
            except:
                pass

    async def ingest_github_repo(
        self, 
        github_url: str, 
        user_id: str, 
        repo_id: Optional[str] = None, 
        db_service=None,
        rag_service=None
    ) -> Dict[str, Any]:
        """Clone and parse repo using Tree-sitter."""
        try:
            repo_name = self._extract_repo_name(github_url)
            if not repo_id:
                repo_id = str(uuid.uuid4())[:8]
                
            repo_path = self.repos_dir / f"{repo_id}_{repo_name}"
            
            # Update DB: Cloning
            if db_service:
                await db_service.update_repository_status(repo_id, "cloning")
            
            print(f"📥 Cloning {github_url}...")
            await self._clone_repo(github_url, repo_path)
            
            # Update DB: Parsing
            if db_service:
                await db_service.update_repository_status(repo_id, "parsing")
            
            print(f"🔍 Parsing code files...")
            code_chunks = await self._parse_repository(repo_path, repo_name, user_id)
            
            print(f"🔗 Building code graph...")
            await self._build_code_graph(code_chunks)
            
            stats = {
                "file_count": len(set(c["metadata"]["file_path"] for c in code_chunks)),
                "chunk_count": len(code_chunks),
                "graph_nodes": self.graph.number_of_nodes(),
            }
            
            # Update DB: Ready
            if db_service:
                await db_service.update_repository_status(repo_id, "ready", stats=stats)
            
            # Save Graph and Chunks to Disk (for persistence)
            await self._save_repo_data(repo_id, code_chunks, self.graph)

            # 4. EMBED CHUNKS to Vector DB (CRITICAL FIX)
            if rag_service:
                print(f"🧠 Embedding {len(code_chunks)} code chunks...")
                # We need to adapt chunks to what rag_service expects or use a dedicated method
                # rag_service.add_documents expects {text, metadata, id}
                # Our chunks have this structure.
                # However, RAGService writes to 'document_chunks'. We might want 'code_chunks'.
                # Let's check rag_service support for collections or just put them there for now.
                # Ideally we want a separate collection.
                # We will add a method to RagService to switch collection or add generic add_items.
                # For now, let's assume we can pass collection_name or it handles it.
                # Let's use rag_service.add_code_chunks if we add it, or just add_documents for now.
                # Wait, rag_service defaults to "document_chunks". 
                # We should update RagService to support code_chunks collection.
                pass 
                # I will handle the RagService update in the next step.
                # But here I need to call it.
                await rag_service.add_code_chunks(code_chunks)

            return {
                "repo_id": repo_id,
                "repo_name": repo_name,
                "chunks": code_chunks,
                "status": "ready",
                **stats
            }
        except Exception as e:
            print(f"❌ Ingestion error: {e}")
            if db_service and repo_id:
                await db_service.update_repository_status(repo_id, "error", error=str(e))
            return {"status": "error", "error": str(e)}

    def _extract_repo_name(self, github_url: str) -> str:
        url = github_url.rstrip('/')
        if url.endswith('.git'):
            url = url[:-4]
        parts = url.split('/')
        return parts[-1] if parts else "unknown"
    
    async def _clone_repo(self, github_url: str, repo_path: Path) -> None:
        if repo_path.exists():
            shutil.rmtree(repo_path)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: Repo.clone_from(github_url, repo_path, depth=1))

    async def _parse_repository(self, repo_path: Path, repo_name: str, user_id: str) -> List[Dict[str, Any]]:
        chunks = []
        for file_path in repo_path.rglob('*'):
            if file_path.is_dir() or any(skip in file_path.parts for skip in self.SKIP_DIRS):
                continue
            
            ext = file_path.suffix.lower()
            if ext not in self.SUPPORTED_EXTENSIONS:
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                lang = self.SUPPORTED_EXTENSIONS[ext]
                relative_path = str(file_path.relative_to(repo_path))
                
                if lang in self.parsers:
                    try:
                        file_chunks = self._parse_with_treesitter(content, relative_path, lang, repo_name, user_id)
                    except Exception as e:
                         print(f"Tree-sitter error {file_path}: {e}")
                         file_chunks = self._chunk_by_lines(content, relative_path, lang, repo_name, user_id)
                else:
                    file_chunks = self._chunk_by_lines(content, relative_path, lang, repo_name, user_id)
                
                chunks.extend(file_chunks)
            except Exception as e:
                print(f"Error parsing {file_path}: {e}")
                
        return chunks

    def _parse_with_treesitter(self, content: str, file_path: str, lang: str, repo_name: str, user_id: str) -> List[Dict[str, Any]]:
        parser = self.parsers[lang]
        tree = parser.parse(bytes(content, "utf8"))
        root_node = tree.root_node
        
        # Queries for extracting definitions
        queries = {
            'python': """
                (function_definition name: (identifier) @name body: (block) @body) @function
                (class_definition name: (identifier) @name body: (block) @body) @class
            """,
            'javascript': """
                (function_declaration name: (identifier) @name body: (statement_block) @body) @function
                (class_declaration name: (identifier) @name body: (class_body) @body) @class
            """,
             'typescript': """
                (function_declaration name: (identifier) @name body: (statement_block) @body) @function
                (class_declaration name: (identifier) @name body: (class_body) @body) @class
            """,
            'go': """
                (function_declaration name: (identifier) @name body: (block) @body) @function
                (method_declaration name: (field_identifier) @name body: (block) @body) @method
            """,
             'java': """
                (method_declaration name: (identifier) @name body: (block) @body) @method
                (class_declaration name: (identifier) @name body: (class_body) @body) @class
            """
        }
        
        query_str = queries.get(lang)
        if not query_str:
             return self._chunk_by_lines(content, file_path, lang, repo_name, user_id)
            
        language_obj = self.LANGUAGES[lang]
        query = language_obj.query(query_str)
        captures = query.captures(root_node)
        
        chunks = []
        seen_ranges = set()
        
        for node, capture_name in captures:
            if capture_name in ['function', 'class', 'method']:
                start_byte = node.start_byte
                end_byte = node.end_byte
                
                if start_byte in seen_ranges:
                    continue
                seen_ranges.add(start_byte)
                
                text_bytes = content.encode('utf8')[start_byte:end_byte]
                text = text_bytes.decode('utf8', errors='replace')
                
                # Extract name roughly
                name = "anonymous"
                # For simplified logic, we just grab the first identifier child if possible
                # Or rely on the capture group @name if we processed it differently, 
                # but 'captures' flattens. 
                # Better approach: query.captures returns (node, name), so we can look for @name nodes
                pass

        # Re-run query to get names specifically? 
        # Actually captures returns a list of (Node, capture_index) in older bindings 
        # or (Node, capture_name) in newer.
        # Let's simplify: iterate captures, if name is @function/class, create chunk.
        # Name extraction is hard without grouping. 
        # Fallback to regex for name extraction on the chunk text? Or just use "code_block"
        
        # Correct approach for flat captures:
        # We need to map @name nodes to their parent @function nodes can be tricky.
        # Alternative: Just dump the whole function as a chunk.
        
        for node, capture_name in captures:
             if capture_name in ['function', 'class', 'method']:
                  start_byte = node.start_byte
                  end_byte = node.end_byte
                  text_bytes = content.encode('utf8')[start_byte:end_byte]
                  text = text_bytes.decode('utf8', errors='replace')
                  
                   # Try to find name in text
                  name = "block"
                  # Improved Regex for name extraction
                  # Python: def foo / class Foo
                  # JS/TS: function foo / class Foo / const foo = () =>
                  # Go: func foo / type Foo
                  lines = text.split('\n')
                  first_line = lines[0].strip()
                  
                  # Generic robust matcher for definition lines
                  name_match = re.search(r'(?:class|def|func|function|type|var|const|let)\s+([a-zA-Z0-9_]+)', first_line)
                  if name_match:
                      name = name_match.group(1)
                  else:
                      # Check for method receivers in Go: func (r *Receiver) MethodName
                      go_method = re.search(r'func\s+\(.*\)\s+([a-zA-Z0-9_]+)', first_line)
                      if go_method:
                          name = go_method.group(1)
                  
                  chunks.append(self._create_chunk(
                    text=text,
                    chunk_type=capture_name,
                    name=name,
                    file_path=file_path,
                    language=lang,
                    repo_name=repo_name,
                    user_id=user_id,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1
                ))
        
        if not chunks:
             return self._chunk_by_lines(content, file_path, lang, repo_name, user_id)

        return chunks

    def _chunk_by_lines(self, content, file_path, language, repo_name, user_id, chunk_size=1000, overlap=100):
        """
        Robust chunking using recursive character splitting logic.
        Splits by separators (class/def, newlines, spaces) to respect code structure.
        """
        separators = ["\nclass ", "\ndef ", "\nfunc ", "\n\n", "\n", " "]
        
        final_chunks = []
        
        # Initial split
        if len(content) <= chunk_size:
            final_chunks = [content]
        else:
            final_chunks = self._recursive_split(content, separators, chunk_size, overlap)
            
        chunks = []
        for i, text in enumerate(final_chunks):
            if len(text.strip()) > 10:
                chunks.append(self._create_chunk(
                    text=text,
                    chunk_type="code_block",
                    name=f"{file_path}:chunk_{i+1}",
                    file_path=file_path,
                    language=language,
                    repo_name=repo_name,
                    user_id=user_id,
                    start_line=0, # Hard to track line numbers exactly with recursive split without robust tracking
                    end_line=0
                ))
        return chunks

    def _recursive_split(self, text, separators, chunk_size, overlap):
        """Recursive splitting helper"""
        if len(text) <= chunk_size:
            return [text]
            
        # Find best separator
        separator = separators[-1]
        for sep in separators:
            if sep in text:
                separator = sep
                break
        
        # Split
        parts = text.split(separator)
        
        # Merge parts back into chunks
        chunks = []
        current_chunk = []
        current_len = 0
        
        for part in parts:
            part_len = len(part) + len(separator)
            if current_len + part_len > chunk_size and current_chunk:
                # Flush current chunk
                chunks.append(separator.join(current_chunk))
                # Handle overlap? (Simplified: no overlap for now to avoid duplications in RAG)
                current_chunk = [part]
                current_len = part_len
            else:
                current_chunk.append(part)
                current_len += part_len
        
        if current_chunk:
            chunks.append(separator.join(current_chunk))
            
        return chunks

    def _create_chunk(self, text, chunk_type, name, file_path, language, repo_name, user_id, start_line, end_line):
        return {
            "id": f"{repo_name}_{file_path}_{name}_{uuid.uuid4().hex[:8]}",
            "text": text,
            "metadata": {
                "type": "code",
                "chunk_type": chunk_type,
                "name": name,
                "file_path": file_path,
                "language": language,
                "repo_name": repo_name,
                "user_id": user_id,
                "start_line": start_line,
                "end_line": end_line,
                "char_count": len(text),
                "ingested_at": datetime.now().isoformat()
            }
        }

    async def _build_code_graph(self, chunks):
        self.graph.clear()
        
        # Add file nodes first
        files = set(c["metadata"]["file_path"] for c in chunks)
        for file_path in files:
            file_node_id = f"FILE::{file_path}"
            self.graph.add_node(
                file_node_id, 
                type="file", 
                label=Path(file_path).name,
                file=file_path
            )
        
        # Add code entity nodes
        for chunk in chunks:
             meta = chunk["metadata"]
             if meta.get("chunk_type") in ["function", "class", "method"]:
                 # Create a unique ID for the node in the graph
                 # Format: TYPE::FILE::NAME
                 node_id = f"{meta['chunk_type']}::{meta['file_path']}::{meta['name']}"
                 
                 self.graph.add_node(
                     node_id, 
                     type=meta['chunk_type'],
                     label=meta['name'],
                     file=meta['file_path'],
                     lines=f"{meta['start_line']}-{meta['end_line']}"
                 )
                 
                 # Edge: File -> Entity
                 file_node_id = f"FILE::{meta['file_path']}"
                 if self.graph.has_node(file_node_id):
                     self.graph.add_edge(file_node_id, node_id, type="CONTAINS")
    
    def load_all_graphs(self):
        """Load all persisted graphs from disk into memory"""
        print("🔄 Loading persisted code graphs...")
        count = 0
        try:
            # Iterate through all data_* directories
            for data_dir in self.repos_dir.glob("data_*"):
                if not data_dir.is_dir():
                    continue
                
                graph_file = data_dir / "graph.json"
                if graph_file.exists():
                    try:
                        with open(graph_file, "r") as f:
                            data = json.load(f)
                            # We can merge this into the main graph or keep separate?
                            # For RAG, we might want a unified graph.
                            # For visualization, we load per repo.
                            # Let's merge into main graph to support global search if needed.
                            # But beware of collisions.
                            
                            subgraph = nx.node_link_graph(data)
                            self.graph.update(subgraph)
                            count += 1
                    except Exception as e:
                        print(f"Failed to load graph from {data_dir}: {e}")
            
            print(f"✅ Loaded {count} repository graphs. Total nodes: {self.graph.number_of_nodes()}")
        except Exception as e:
            print(f"Error loading graphs: {e}")

    async def _save_repo_data(self, repo_id: str, chunks: List[Dict], graph: nx.DiGraph):
        """Persist graph and chunks to disk"""
        data_dir = self.repos_dir / f"data_{repo_id}"
        data_dir.mkdir(exist_ok=True)
        
        # Save Chunks
        with open(data_dir / "chunks.json", "w") as f:
            json.dump(chunks, f, indent=2)
            
        # Save Graph (node-link format)
        # We need to save ONLY the subgraph relevant to this repo?
        # self.graph currently holds ALL nodes if we don't clear it.
        # But ingest_github_repo calls _build_code_graph which clears it first?
        # YES: self.graph.clear() is called in _build_code_graph.
        # So self.graph ONLY contains the current repo's graph during ingestion.
        # This is correct for saving.
        
        graph_data = nx.node_link_data(graph)
        with open(data_dir / "graph.json", "w") as f:
            json.dump(graph_data, f, indent=2)
            
    def get_repo_graph(self, repo_id: str) -> Dict[str, Any]:
        """Load and return graph data for frontend"""
        try:
            # Check for data_{repo_id}
            data_file = self.repos_dir / f"data_{repo_id}" / "graph.json"
            
            if not data_file.exists():
                # Fallback: check if we have it in memory (for just ingested)
                # But memory is transient.
                return {"nodes": [], "edges": []}
                
            with open(data_file, "r") as f:
                data = json.load(f)
            return data
        except Exception as e:
            print(f"Error loading graph for {repo_id}: {e}")
            return {"nodes": [], "edges": []}

    def get_repo_chunks(self, repo_id: str) -> List[Dict[str, Any]]:
        """Load and return chunks"""
        try:
            data_file = self.repos_dir / f"data_{repo_id}" / "chunks.json"
            if not data_file.exists():
                return []
                
            with open(data_file, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading chunks for {repo_id}: {e}")
            return []
