"""
IAM Configuration for DevOps Copilot V3
Developer and IT-focused personas.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class RoleCapabilities:
    """Capabilities for a given IAM role."""
    permissions: List[str] = field(default_factory=list)
    scopes: List[str] = field(default_factory=list)
    data_access: str = "none"
    
    def can(self, action: str) -> bool:
        """Check if role has permission for action."""
        return action in self.permissions


# Developer and IT personas
PERSONA_DEFINITIONS = {
    "sde_ii": {
        "id": "sde_ii_01",
        "name": "Alex Rivera",
        "role": "sde_ii",
        "permissions": [
            "READ_CODEBASE",
            "WRITE_JIRA",
            "READ_DOCS",
            "SEARCH_CODE",
            "VIEW_ARCHITECTURE"
        ],
        "context": "Software Development",
        "description": "Senior Developer with full codebase access",
        "emoji": "👨‍💻",
        "color": "bg-blue-100 text-blue-700",
        "accent": "bg-blue-500",
        "suggested": [
            "How does the authentication flow work?",
            "Find all API endpoints",
            "Explain the database schema"
        ]
    },
    "principal_architect": {
        "id": "architect_01",
        "name": "Jordan Chen",
        "role": "principal_architect",
        "permissions": [
            "READ_CODEBASE",
            "READ_ARCHITECTURE",
            "WRITE_DESIGN",
            "SEARCH_CODE",
            "VIEW_ALL_SYSTEMS",
            "REVIEW_PATTERNS"
        ],
        "context": "Architecture & Design",
        "description": "Principal Architect with system-wide view",
        "emoji": "🏗️",
        "color": "bg-purple-100 text-purple-700",
        "accent": "bg-purple-500",
        "suggested": [
            "Analyze the system architecture",
            "Find dependency patterns",
            "Review service boundaries"
        ]
    },
    "it_analyst": {
        "id": "it_analyst_01",
        "name": "Morgan Kim",
        "role": "it_analyst",
        "permissions": [
            "RUN_HEALTHCHECKS",
            "READ_LOGS",
            "VIEW_METRICS",
            "CHECK_SERVICES",
            "READ_DOCS",
            "SCHEDULE_MEETING"
        ],
        "context": "IT Operations",
        "description": "IT Solutions Analyst with operations access",
        "emoji": "🔧",
        "color": "bg-emerald-100 text-emerald-700",
        "accent": "bg-emerald-500",
        "suggested": [
            "Check API health status",
            "Get recent error logs",
            "List running containers"
        ]
    }
}


class IAMConfig:
    """IAM configuration manager."""
    
    def __init__(self):
        self.personas = {}
        self.role_capabilities = {}
    
    async def load(self):
        """Load IAM configuration."""
        self.personas = PERSONA_DEFINITIONS.copy()
        
        for role_id, persona in self.personas.items():
            self.role_capabilities[role_id] = RoleCapabilities(
                permissions=persona["permissions"],
                scopes=[persona["context"]],
                data_access="full" if "READ_CODEBASE" in persona["permissions"] else "limited"
            )
        
        print(f"📋 Loaded IAM configuration for {len(self.personas)} personas")
    
    def get_capabilities(self, role: str) -> RoleCapabilities:
        """Get capabilities for a role."""
        return self.role_capabilities.get(
            role.lower(), 
            RoleCapabilities(permissions=["READ_DOCS"])
        )
    
    def has_permission(self, role: str, permission: str) -> bool:
        """Check if role has a specific permission."""
        caps = self.get_capabilities(role.lower())
        return permission in caps.permissions
    
    def get_personas(self) -> List[Dict[str, Any]]:
        """Get all personas."""
        return list(self.personas.values())


def resolve_capabilities(role: str) -> RoleCapabilities:
    """Resolve capabilities for a given role."""
    role_lower = role.lower()
    
    if role_lower in PERSONA_DEFINITIONS:
        persona = PERSONA_DEFINITIONS[role_lower]
        return RoleCapabilities(
            permissions=persona["permissions"],
            scopes=[persona["context"]],
            data_access="full" if "READ_CODEBASE" in persona["permissions"] else "limited"
        )
    
    # Default minimal permissions
    return RoleCapabilities(permissions=["READ_DOCS"])
