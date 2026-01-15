"""
Action Executor Service
Executes validated actions with JSON schema enforcement
"""

import asyncio
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, ValidationError
from datetime import datetime, timedelta
import json


# ==================== ACTION SCHEMAS ====================

class JiraTicketSchema(BaseModel):
    """Schema for JIRA ticket creation"""
    title: str = Field(..., min_length=5, max_length=200)
    description: str = Field(..., min_length=10)
    priority: str = Field(default="Medium", pattern="^(Low|Medium|High|Critical)$")
    assignee: str
    labels: list[str] = Field(default_factory=list)


class MeetingSchema(BaseModel):
    """Schema for meeting scheduling"""
    title: str = Field(..., min_length=3, max_length=100)
    participants: list[str] = Field(..., min_items=1)
    duration: int = Field(default=60, ge=15, le=480)  # minutes
    suggested_times: list[str] = Field(..., min_items=1)


class DocumentDraftSchema(BaseModel):
    """Schema for document drafting"""
    title: str
    content: str
    document_type: str = Field(default="memo", pattern="^(memo|policy|report|email)$")


# ==================== ACTION EXECUTOR ====================

# ==================== ACTION EXECUTOR ====================

from .db_service import DatabaseService

class ActionExecutor:
    """
    Executes validated actions with JSON schema enforcement
    - Validates action parameters
    - Persists actions to local SQLite database
    - Returns structured results for frontend rendering
    """
    
    def __init__(self):
        self.action_schemas = {
            "CREATE_JIRA_TICKET": JiraTicketSchema,
            "SCHEDULE_MEETING": MeetingSchema,
            "DRAFT_DOCUMENT": DocumentDraftSchema
        }
        self.db = DatabaseService()
    
    async def execute(
        self,
        action_type: str,
        parameters: Dict[str, Any],
        role: str
    ) -> Dict[str, Any]:
        """
        Execute action with validation
        """
        
        # Validate action type
        if action_type not in self.action_schemas:
            return {
                "type": "ERROR",
                "data": {"message": f"Unknown action type: {action_type}"}
            }
        
        # Validate parameters against schema
        try:
            schema_class = self.action_schemas[action_type]
            validated_params = schema_class(**parameters)
            
            # Route to specific executor
            if action_type == "CREATE_JIRA_TICKET":
                return await self._create_jira_ticket(validated_params)
            elif action_type == "SCHEDULE_MEETING":
                return await self._schedule_meeting(validated_params)
            elif action_type == "DRAFT_DOCUMENT":
                return await self._draft_document(validated_params)
        
        except ValidationError as e:
            # Return validation errors
            return {
                "type": "VALIDATION_ERROR",
                "data": {
                    "message": "Invalid action parameters",
                    "errors": json.loads(e.json())
                }
            }
        except Exception as e:
            return {
                "type": "ERROR",
                "data": {"message": str(e)}
            }
    
    async def _create_jira_ticket(self, params: JiraTicketSchema) -> Dict[str, Any]:
        """
        Create JIRA ticket and persist to DB
        """
        
        # Generate ticket ID
        ticket_id = f"JIRA-{hash(params.title) % 10000}"
        if ticket_id.startswith("JIRA--"): # Handle negative hash
             ticket_id = ticket_id.replace("JIRA--", "JIRA-")
        
        ticket_data = {
            "ticket_id": ticket_id,
            "title": params.title,
            "description": params.description,
            "priority": params.priority,
            "assignee": params.assignee,
            "status": "TO DO",
            "url": f"https://jira.company.com/browse/{ticket_id}",
            "created_at": datetime.now().isoformat()
        }
        
        # Persist to DB
        await self.db.create_ticket(ticket_data)
        
        return {
            "type": "TICKET",
            "data": ticket_data
        }
    
    async def _schedule_meeting(self, params: MeetingSchema) -> Dict[str, Any]:
        """
        Schedule meeting and persist to DB
        """
        
        meeting_data = {
            "title": params.title,
            "participants": params.participants,
            "duration": params.duration,
            "scheduled_time": params.suggested_times[0],  # Pick first slot for now
            "status": "SCHEDULED"
        }
        
        # Persist to DB
        saved_meeting = await self.db.create_meeting(meeting_data)
        
        return {
            "type": "CALENDAR",
            "data": {
                "id": saved_meeting["id"],
                "title": params.title,
                "participants": params.participants,
                "duration_minutes": params.duration,
                "confirmed_time": params.suggested_times[0],
                "calendar_link": "https://calendar.company.com/event/new",
                "status": "CONFIRMED"
            }
        }
    
    async def _draft_document(self, params: DocumentDraftSchema) -> Dict[str, Any]:
        """
        Draft document (Mock only, no persistence needed yet)
        """
        
        await asyncio.sleep(0.3)
        
        return {
            "type": "DOCUMENT",
            "data": {
                "title": params.title,
                "content_preview": params.content[:200] + "...",
                "document_type": params.document_type,
                "word_count": len(params.content.split()),
                "status": "DRAFT",
                "edit_url": "https://docs.company.com/document/new"
            }
        }
    
    async def validate_schema(self, action_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate parameters without executing
        Useful for pre-flight checks
        """
        
        if action_type not in self.action_schemas:
            return {
                "valid": False,
                "errors": [f"Unknown action type: {action_type}"]
            }
        
        try:
            schema_class = self.action_schemas[action_type]
            schema_class(**parameters)
            return {"valid": True, "errors": []}
        
        except ValidationError as e:
            return {
                "valid": False,
                "errors": [err["msg"] for err in e.errors()]
            }
