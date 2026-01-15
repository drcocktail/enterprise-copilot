"""
IAM Configuration and Capability Resolution
Defines persona permissions and enforces role-based access control
"""

import json
from typing import Dict, List, Optional, Any
from pathlib import Path
from pydantic import BaseModel


class CapabilityEnvelope(BaseModel):
    """Result of capability resolution for a query"""
    allowed: bool
    actor_name: str
    permissions: List[str]
    metadata_filters: Dict[str, Any]
    code_filters: Dict[str, Any]
    denial_reason: Optional[str] = None


class PersonaConfig(BaseModel):
    """Configuration for a single persona"""
    id: str
    role: str
    name: str
    permissions: List[str]
    description: str
    scopes: List[str]
    max_sensitivity_level: int  # 1=Public, 2=Internal, 3=Confidential, 4=Restricted


# Predefined IAM Configuration
IAM_PERSONAS = {
    "CHIEF_STRATEGY_OFFICER": PersonaConfig(
        id="c_suite_01",
        role="CHIEF_STRATEGY_OFFICER",
        name="Eleanor Vance",
        description="Strategic Overview & Financial Analysis",
        permissions=[
            "READ_FINANCIALS",
            "READ_HR_AGGREGATE",
            "WRITE_STRATEGY",
            "CALENDAR_WRITE",
            "READ_STRATEGY_DOCS",
            "ADMIN"
        ],
        scopes=[
            "scope:financials:read",
            "scope:strategy:read",
            "scope:strategy:write",
            "scope:calendar:write"
        ],
        max_sensitivity_level=3  # Can access confidential
    ),
    "HR_DIRECTOR": PersonaConfig(
        id="hr_lead_04",
        role="HR_DIRECTOR",
        name="Marcus Thorne",
        description="People & Culture Management",
        permissions=[
            "READ_EMPLOYEE_PII",
            "READ_EMPLOYEE_DATA",
            "WRITE_POLICY",
            "CALENDAR_WRITE",
            "SLACK_BROADCAST",
            "READ_HR_DOCS"
        ],
        scopes=[
            "scope:employee:read",
            "scope:employee:pii:read",
            "scope:policy:write",
            "scope:calendar:write",
            "scope:slack:write"
        ],
        max_sensitivity_level=4  # Can access restricted (PII)
    ),
    "SR_DEVOPS_ENGINEER": PersonaConfig(
        id="dev_ops_99",
        role="SR_DEVOPS_ENGINEER",
        name="Sarah Chen",
        description="Infrastructure & Code Operations",
        permissions=[
            "READ_CODEBASE",
            "READ_LOGS",
            "WRITE_JIRA",
            "RESTART_SERVICES",
            "READ_TECHNICAL_DOCS"
        ],
        scopes=[
            "scope:code:read",
            "scope:logs:read",
            "scope:jira:write",
            "scope:infrastructure:write"
        ],
        max_sensitivity_level=3  # Can access confidential technical data
    )
}


# Restricted keywords by role
RESTRICTED_KEYWORDS = {
    "CHIEF_STRATEGY_OFFICER": [
        "employee salary",
        "source code",
        "api key",
        "password",
        "credentials"
    ],
    "HR_DIRECTOR": [
        "source code",
        "api key",
        "aws secret",
        "database password",
        "revenue detail"
    ],
    "SR_DEVOPS_ENGINEER": [
        "employee pii",
        "salary",
        "compensation",
        "personal information",
        "ssn"
    ]
}


class IAMConfig:
    """IAM Configuration Manager"""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path(__file__).parent / "iam_config.json"
        self.personas = IAM_PERSONAS
        
    async def load(self):
        """Load IAM configuration from file"""
        # For now, using hardcoded config
        # In production, load from JSON file
        print("📋 Loaded IAM configuration for", len(self.personas), "personas")
        
    def get_persona(self, role: str) -> Optional[PersonaConfig]:
        """Get persona configuration by role"""
        return self.personas.get(role)
    
    def get_all_personas(self) -> List[Dict[str, Any]]:
        """Get all available personas"""
        return [
            {
                "id": p.id,
                "role": p.role,
                "name": p.name,
                "permissions": p.permissions,
                "description": p.description
            }
            for p in self.personas.values()
        ]
    
    def has_permission(self, role: str, permission: str) -> bool:
        """Check if role has specific permission"""
        persona = self.get_persona(role)
        if not persona:
            return False
        return permission in persona.permissions
    
    def get_metadata_filters(self, role: str) -> Dict[str, Any]:
        """Get metadata filters for document retrieval based on role"""
        persona = self.get_persona(role)
        if not persona:
            return {"sensitivity_level": {"$lte": 1}}  # Public only
        
        return {
            "sensitivity_level": {"$lte": persona.max_sensitivity_level}
        }
    
    def get_code_filters(self, role: str) -> Dict[str, Any]:
        """Get filters for code intelligence based on role"""
        persona = self.get_persona(role)
        if not persona:
            return {"access": "none"}
        
        if "READ_CODEBASE" in persona.permissions:
            return {"type": "code"}
        
        return {"access": "none"}


async def resolve_capabilities(
    iam_config: IAMConfig,
    role: str,
    query: str
) -> CapabilityEnvelope:
    """
    Pre-computation capability check
    Determines if a query is allowed before invoking LLM
    This is the "Deterministic Security" layer
    """
    persona = iam_config.get_persona(role)
    
    if not persona:
        return CapabilityEnvelope(
            allowed=False,
            actor_name="Unknown",
            permissions=[],
            metadata_filters={},
            code_filters={},
            denial_reason=f"Invalid IAM role: {role}"
        )
    
    # Check for restricted keywords
    query_lower = query.lower()
    restricted_for_role = RESTRICTED_KEYWORDS.get(role, [])
    
    for keyword in restricted_for_role:
        if keyword in query_lower:
            return CapabilityEnvelope(
                allowed=False,
                actor_name=persona.name,
                permissions=persona.permissions,
                metadata_filters={},
                code_filters={},
                denial_reason=f"Query contains restricted content for your role: '{keyword}'"
            )
    
    # Intent-based permission check
    # Check if query requires code access
    if any(word in query_lower for word in ["code", "function", "class", "api", "grep", "codebase"]):
        if "READ_CODEBASE" not in persona.permissions:
            return CapabilityEnvelope(
                allowed=False,
                actor_name=persona.name,
                permissions=persona.permissions,
                metadata_filters={},
                code_filters={},
                denial_reason="Your role does not have code access permissions"
            )
    
    # Check if query requires financial data
    if any(word in query_lower for word in ["revenue", "financial", "earnings", "profit", "ebitda"]):
        if "READ_FINANCIALS" not in persona.permissions:
            return CapabilityEnvelope(
                allowed=False,
                actor_name=persona.name,
                permissions=persona.permissions,
                metadata_filters={},
                code_filters={},
                denial_reason="Your role does not have financial data access"
            )
    
    # Check if query requires PII
    if any(word in query_lower for word in ["employee", "salary", "compensation", "personal"]):
        if "READ_EMPLOYEE_PII" not in persona.permissions and role != "HR_DIRECTOR":
            return CapabilityEnvelope(
                allowed=False,
                actor_name=persona.name,
                permissions=persona.permissions,
                metadata_filters={},
                code_filters={},
                denial_reason="Your role does not have access to employee data"
            )
    
    # All checks passed
    return CapabilityEnvelope(
        allowed=True,
        actor_name=persona.name,
        permissions=persona.permissions,
        metadata_filters=iam_config.get_metadata_filters(role),
        code_filters=iam_config.get_code_filters(role)
    )
