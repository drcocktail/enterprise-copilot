"""
Build Tree-sitter Languages
Clones language grammars and builds the shared library.
"""

from tree_sitter import Language
import os
import shutil
import subprocess
from pathlib import Path

BUILD_DIR = Path(__file__).parent / "build"
VENDORS_DIR = BUILD_DIR / "vendors"

LANGUAGES = {
    "python": "https://github.com/tree-sitter/tree-sitter-python",
    "javascript": "https://github.com/tree-sitter/tree-sitter-javascript",
    "typescript": "https://github.com/tree-sitter/tree-sitter-typescript",
    "go": "https://github.com/tree-sitter/tree-sitter-go",
    "java": "https://github.com/tree-sitter/tree-sitter-java",
}

def build():
    BUILD_DIR.mkdir(exist_ok=True)
    VENDORS_DIR.mkdir(exist_ok=True)
    
    repo_paths = []
    
    print("📦 Cloning tree-sitter grammars...")
    for lang, url in LANGUAGES.items():
        repo_path = VENDORS_DIR / f"tree-sitter-{lang}"
        if not repo_path.exists():
            print(f"  - Cloning {lang}...")
            subprocess.run(["git", "clone", "--depth", "1", url, str(repo_path)], check=True)
        
        if lang == "typescript":
            # Typescript repo has two directories: typescript and tsx
            repo_paths.append(str(repo_path / "typescript"))
            repo_paths.append(str(repo_path / "tsx"))
        else:
            repo_paths.append(str(repo_path))
            
    output_lib = BUILD_DIR / "my-languages.so"
    
    print(f"🔨 Building {output_lib}...")
    Language.build_library(
        str(output_lib),
        repo_paths
    )
    print("✅ Build complete!")

if __name__ == "__main__":
    build()
