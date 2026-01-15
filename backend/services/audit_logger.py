"""
Audit Logging System
Immutable log format with real-time streaming capability
"""

import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional, AsyncIterator
from dataclasses import dataclass, asdict
from collections import deque
import json
from .db_service import DatabaseService


@dataclass
class LogEntry:
    """Immutable audit log entry"""
    id: str
    timestamp: datetime
    actor: str
    iam_role: str
    action: str
    status: str  # ALLOWED, DENIED, ERROR
    details: str
    trace_id: str
    metadata: Optional[Dict[str, Any]] = None
    
    def dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            **asdict(self),
            "timestamp": self.timestamp.isoformat()
        }


class AuditLogger:
    """
    Audit logging system with:
    - Immutable logs persisted to SQLite
    - Real-time streaming via in-memory queues
    """
    
    def __init__(self, max_logs: int = 1000):
        self.subscribers: List[asyncio.Queue] = []
        self._log_counter = 0
        self.db = DatabaseService()
        
    async def log(
        self,
        actor: str,
        iam_role: str,
        action: str,
        status: str,
        details: str,
        trace_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Create a log entry, persist it, and stream it"""
        self._log_counter += 1
        
        entry = LogEntry(
            id=f"log_{int(datetime.now().timestamp())}_{self._log_counter:04d}",
            timestamp=datetime.now(),
            actor=actor,
            iam_role=iam_role,
            action=action,
            status=status,
            details=details,
            trace_id=trace_id,
            metadata=metadata
        )
        
        # 1. Persist to DB
        log_data = entry.dict()
        log_data["action_type"] = log_data.pop("action") # Remap for DB schema
        await self.db.log_event(log_data)
        
        # 2. Notify subscribers (Real-time stream)
        for queue in self.subscribers:
            try:
                queue.put_nowait(entry)
            except asyncio.QueueFull:
                pass
        
        # Console output
        status_emoji = "✅" if status == "ALLOWED" else "🚫" if status == "DENIED" else "❌"
        print(f"{status_emoji} [{entry.timestamp.strftime('%H:%M:%S')}] {actor} ({iam_role}) -> {action}: {status}")
        
    async def get_recent_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent logs from DB"""
        logs = await self.db.get_audit_logs(limit=limit)
        # Map back DB schema to API schema if needed
        # DB: action_type, API: action. 
        # But wait, I can just adjust the return or the DB service.
        # DB Service returns dicts.
        mapped_logs = []
        for log in logs:
            log["action"] = log.pop("action_type", log.get("action"))
            mapped_logs.append(log)
        return mapped_logs
    
    async def stream(self) -> AsyncIterator[LogEntry]:
        """Stream logs in real-time via async generator"""
        queue = asyncio.Queue(maxsize=100)
        self.subscribers.append(queue)
        
        try:
            while True:
                log = await queue.get()
                yield log
        finally:
            self.subscribers.remove(queue)
    
    # get_by_trace_id and get_denied_logs would also need DB impl, 
    # but for now I'll just remove them or impl them if needed.
    # The interface only uses get_recent_logs and stream.
