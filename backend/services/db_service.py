"""
Database Service V2
SQLite implementation for:
- Tickets, Meetings, Audit Logs (existing)
- Conversations & Messages (NEW)
- User Documents (NEW)
"""

import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid


class DatabaseService:
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            self.db_path = str(Path(__file__).parent.parent / "db.sqlite")
        else:
            self.db_path = db_path
        
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initialize all database tables"""
        conn = self._get_connection()
        conn.execute("PRAGMA journal_mode=WAL;")  # Enable Write-Ahead Logging for concurrency
        cursor = conn.cursor()
        
        # ==================== EXISTING TABLES ====================
        
        # Tickets Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                priority TEXT,
                assignee TEXT,
                status TEXT,
                created_at TEXT
            )
        """)

        # Meetings Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS meetings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                participants TEXT,
                duration INTEGER,
                scheduled_time TEXT,
                status TEXT
            )
        """)

        # Audit Logs Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                actor TEXT NOT NULL,
                action_type TEXT NOT NULL,
                status TEXT NOT NULL,
                details TEXT,
                trace_id TEXT
            )
        """)
        
        # ==================== NEW V2 TABLES ====================
        
        # Conversations Table (chat sessions)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL,
                title TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Messages Table (messages within conversations)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            )
        """)
        
        # User Documents Table (per-user document library)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_documents (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                original_filename TEXT,
                file_path TEXT,
                file_size INTEGER,
                category TEXT,
                sensitivity_level INTEGER DEFAULT 2,
                chunk_count INTEGER DEFAULT 0,
                uploaded_at TEXT NOT NULL,
                status TEXT DEFAULT 'processing',
                error_message TEXT
            )
        """)
        
        # Create indexes for common queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_conversations_user 
            ON conversations(user_id, updated_at DESC)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_conversation 
            ON messages(conversation_id, created_at ASC)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_documents_user 
            ON user_documents(user_id, uploaded_at DESC)
        """)
        
        # Repositories Table (codebases)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS repositories (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                url TEXT NOT NULL,
                language TEXT,
                branch TEXT DEFAULT 'main',
                status TEXT DEFAULT 'pending', -- pending, cloning, parsing, ready, error
                nodes_count INTEGER DEFAULT 0,
                file_count INTEGER DEFAULT 0,
                last_indexed_at TEXT,
                error_message TEXT,
                user_id TEXT
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_repos_user 
            ON repositories(user_id, last_indexed_at DESC)
        """)
        
        conn.commit()
        conn.close()

    # ==================== TICKETS ====================
    
    async def create_ticket(self, ticket_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new Jira ticket"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        ticket_id = ticket_data["ticket_id"]
        
        cursor.execute(
            "INSERT INTO tickets (id, title, description, priority, assignee, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                ticket_id,
                ticket_data["title"],
                ticket_data.get("description", ""),
                ticket_data.get("priority", "Medium"),
                ticket_data.get("assignee", "Unassigned"),
                ticket_data.get("status", "TO DO"),
                ticket_data.get("created_at", datetime.now().isoformat())
            )
        )
        conn.commit()
        conn.close()
        return ticket_data

    async def get_tickets(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent tickets"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM tickets ORDER BY created_at DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]

    # ==================== MEETINGS ====================
    
    async def create_meeting(self, meeting_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new meeting"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        participants_json = json.dumps(meeting_data.get("participants", []))
        
        cursor.execute(
            "INSERT INTO meetings (title, participants, duration, scheduled_time, status) VALUES (?, ?, ?, ?, ?)",
            (
                meeting_data["title"],
                participants_json,
                meeting_data.get("duration", 30),
                meeting_data.get("scheduled_time", ""),
                meeting_data.get("status", "SCHEDULED")
            )
        )
        meeting_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        meeting_data["id"] = meeting_id
        return meeting_data

    # ==================== AUDIT LOGS ====================
    
    async def log_event(self, log_entry: Dict[str, Any]):
        """Log an audit event"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        details_json = json.dumps(log_entry.get("details", {})) if isinstance(log_entry.get("details"), dict) else log_entry.get("details", "")
        
        cursor.execute(
            "INSERT INTO audit_logs (id, timestamp, actor, action_type, status, details, trace_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                log_entry["id"],
                log_entry["timestamp"],
                log_entry["actor"],
                log_entry["action_type"],
                log_entry["status"],
                details_json,
                log_entry.get("trace_id", "")
            )
        )
        conn.commit()
        conn.close()

    async def get_audit_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent audit logs"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        conn.close()
        
        logs = []
        for row in rows:
            log_dict = dict(row)
            if log_dict["details"]:
                try:
                    log_dict["details"] = json.loads(log_dict["details"])
                except:
                    pass
            logs.append(log_dict)
        return logs

    # ==================== CONVERSATIONS (NEW) ====================
    
    async def ensure_conversation(self, conversation_id: str, user_id: str, role: str) -> bool:
        """Ensure a conversation exists, create if not"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT 1 FROM conversations WHERE id = ?", (conversation_id,))
        exists = cursor.fetchone()
        
        if not exists:
            now = datetime.now().isoformat()
            cursor.execute(
                "INSERT INTO conversations (id, user_id, role, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (conversation_id, user_id, role, "New Chat", now, now)
            )
            conn.commit()
            print(f"Created missing conversation {conversation_id}")
            return True
            
        return False

    async def create_conversation(
        self,
        user_id: str,
        role: str,
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new conversation session"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        conversation_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        cursor.execute(
            "INSERT INTO conversations (id, user_id, role, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (conversation_id, user_id, role, title or "New Chat", now, now)
        )
        conn.commit()
        conn.close()
        
        return {
            "id": conversation_id,
            "user_id": user_id,
            "role": role,
            "title": title or "New Chat",
            "created_at": now,
            "updated_at": now
        }
    
    async def get_conversations(
        self,
        user_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get user's conversations, most recent first"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM conversations ORDER BY updated_at DESC LIMIT ?",
            (limit,)
        )
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    async def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get a single conversation by ID"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,))
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else None
    
    async def update_conversation(
        self,
        conversation_id: str,
        title: Optional[str] = None
    ) -> bool:
        """Update conversation (e.g., auto-generate title from first message)"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        if title:
            cursor.execute(
                "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?",
                (title, now, conversation_id)
            )
        else:
            cursor.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (now, conversation_id)
            )
        
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        
        return success
    
    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation and all its messages"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Delete messages first (or rely on CASCADE)
        cursor.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
        cursor.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
        
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        
        return success

    # ==================== MESSAGES (NEW) ====================
    
    async def add_message(
        self,
        conversation_id: str,
        role: str,  # 'user' or 'assistant'
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Add a message to a conversation"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        metadata_json = json.dumps(metadata) if metadata else None
        
        cursor.execute(
            "INSERT INTO messages (conversation_id, role, content, metadata, created_at) VALUES (?, ?, ?, ?, ?)",
            (conversation_id, role, content, metadata_json, now)
        )
        message_id = cursor.lastrowid
        
        # Update conversation's updated_at
        cursor.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (now, conversation_id)
        )
        
        conn.commit()
        conn.close()
        
        return {
            "id": message_id,
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "metadata": metadata,
            "created_at": now
        }
    
    async def get_messages(
        self,
        conversation_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get messages for a conversation, oldest first"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC LIMIT ?",
            (conversation_id, limit)
        )
        rows = cursor.fetchall()
        conn.close()
        
        messages = []
        for row in rows:
            msg = dict(row)
            if msg["metadata"]:
                try:
                    msg["metadata"] = json.loads(msg["metadata"])
                except:
                    pass
            messages.append(msg)
        
        return messages
    
    async def get_recent_messages(
        self,
        conversation_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get the most recent N messages (for context window)"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Get last N messages, but return in chronological order
        cursor.execute(
            """
            SELECT * FROM (
                SELECT * FROM messages 
                WHERE conversation_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?
            ) ORDER BY created_at ASC
            """,
            (conversation_id, limit)
        )
        rows = cursor.fetchall()
        conn.close()
        
        messages = []
        for row in rows:
            msg = dict(row)
            if msg["metadata"]:
                try:
                    msg["metadata"] = json.loads(msg["metadata"])
                except:
                    pass
            messages.append(msg)
        
        return messages

    # ==================== USER DOCUMENTS (NEW) ====================
    
    async def add_user_document(
        self,
        user_id: str,
        filename: str,
        original_filename: str,
        file_path: str,
        file_size: int,
        category: str = "General Document",
        sensitivity_level: int = 2
    ) -> Dict[str, Any]:
        """Add a document to user's library"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        doc_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        cursor.execute(
            """
            INSERT INTO user_documents 
            (id, user_id, filename, original_filename, file_path, file_size, 
             category, sensitivity_level, uploaded_at, status) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'processing')
            """,
            (doc_id, user_id, filename, original_filename, file_path, 
             file_size, category, sensitivity_level, now)
        )
        conn.commit()
        conn.close()
        
        return {
            "id": doc_id,
            "user_id": user_id,
            "filename": filename,
            "original_filename": original_filename,
            "file_path": file_path,
            "file_size": file_size,
            "category": category,
            "sensitivity_level": sensitivity_level,
            "chunk_count": 0,
            "uploaded_at": now,
            "status": "processing"
        }
    
    async def update_document_status(
        self,
        doc_id: str,
        status: str,
        chunk_count: int = 0,
        error_message: Optional[str] = None
    ) -> bool:
        """Update document processing status"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE user_documents SET status = ?, chunk_count = ?, error_message = ? WHERE id = ?",
            (status, chunk_count, error_message, doc_id)
        )
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        
        return success
    
    async def get_user_documents(
        self,
        user_id: str,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get documents for a user"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if status:
            cursor.execute(
                "SELECT * FROM user_documents WHERE user_id = ? AND status = ? ORDER BY uploaded_at DESC",
                (user_id, status)
            )
        else:
            cursor.execute(
                "SELECT * FROM user_documents ORDER BY uploaded_at DESC"
            )
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    async def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get a single document by ID"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM user_documents WHERE id = ?", (doc_id,))
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else None
    
    async def delete_user_document(self, doc_id: str) -> bool:
        """Delete a document (also need to clean up ChromaDB)"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM user_documents WHERE id = ?", (doc_id,))
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        
        return success

    # ==================== REPOSITORIES (NEW) ====================
    
    async def add_repository(
        self,
        repo_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Add a repository to tracking"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        repo_id = repo_data.get("id", str(uuid.uuid4())[:8])
        now = datetime.now().isoformat()
        
        cursor.execute(
            """
            INSERT INTO repositories 
            (id, name, url, language, status, last_indexed_at, user_id) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                repo_id,
                repo_data["name"],
                repo_data["url"],
                repo_data.get("language", "UNKNOWN"),
                repo_data.get("status", "pending"),
                now,
                repo_data.get("user_id")
            )
        )
        conn.commit()
        conn.close()
        
        repo_data["id"] = repo_id
        repo_data["last_indexed_at"] = now
        return repo_data
        
    async def update_repository_status(
        self,
        repo_id: str,
        status: str,
        stats: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ):
        """Update repository status and stats"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        if stats:
            cursor.execute(
                """
                UPDATE repositories 
                SET status = ?, nodes_count = ?, file_count = ?, last_indexed_at = ?, error_message = ? 
                WHERE id = ?
                """,
                (
                    status, 
                    stats.get("graph_nodes", 0), 
                    stats.get("file_count", 0), 
                    now, 
                    error, 
                    repo_id
                )
            )
        else:
            cursor.execute(
                "UPDATE repositories SET status = ?, error_message = ? WHERE id = ?",
                (status, error, repo_id)
            )
            
        conn.commit()
        conn.close()
        
    async def get_repositories(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all repositories for user"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM repositories ORDER BY last_indexed_at DESC")
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
