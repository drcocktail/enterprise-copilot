"""
Database Service
SQLite implementation for persistent storage of Tickets, Meetings, and Audit Logs.
"""

import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

class DatabaseService:
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            # Default to backend/db.sqlite
            self.db_path = str(Path(__file__).parent.parent / "db.sqlite")
        else:
            self.db_path = db_path
        
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        """Initialize database tables"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
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
                participants TEXT,  -- JSON list
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
                details TEXT,  -- JSON object
                trace_id TEXT
            )
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
        conn.row_factory = sqlite3.Row
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
        
        details_json = json.dumps(log_entry.get("details", {}))
        
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
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        conn.close()
        
        logs = []
        for row in rows:
            role_dict = dict(row)
            if role_dict["details"]:
                try:
                    role_dict["details"] = json.loads(role_dict["details"])
                except:
                    pass
            logs.append(role_dict)
        return logs
