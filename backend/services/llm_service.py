"""
LLM Service with Ollama Integration
Implements proper agentic architecture with:
1. Intent classification (first LLM call)
2. Context-aware response generation (second LLM call)
3. Human-like conversational style
"""

import asyncio
import httpx
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import json


class QueryIntent(BaseModel):
    """Classified intent of user query"""
    intent_type: str = "GENERAL"  # GENERAL, DOCUMENT_QUERY, CODE_SEARCH, ACTION
    requires_rag: bool = False
    requires_code_search: bool = False
    requires_action: bool = False
    action_type: Optional[str] = None
    confidence: float = 0.0
    is_greeting: bool = False


class LLMService:
    """
    LLM Service using Ollama with proper agentic flow:
    1. Classify intent first
    2. Route to appropriate handler
    3. Generate human-like response
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.2"
    ):
        self.base_url = base_url
        self.model = model
        self.client = httpx.AsyncClient(timeout=120.0)
    
    async def classify_intent(
        self,
        query: str,
        capabilities
    ) -> QueryIntent:
        """
        Step 1: Classify query intent to determine required services
        Uses hierarchical classification for accuracy
        """
        
        query_lower = query.lower().strip()
        intent = QueryIntent()
        
        # === LEVEL 1: Detect greetings and simple chat ===
        greeting_patterns = [
            "hello", "hi", "hey", "good morning", "good afternoon", 
            "good evening", "how are you", "what's up", "sup", "yo"
        ]
        if any(query_lower.startswith(g) or query_lower == g for g in greeting_patterns):
            intent.intent_type = "GENERAL"
            intent.is_greeting = True
            intent.confidence = 0.95
            return intent
        
        # === LEVEL 2: Detect ACTION intent (highest priority) ===
        action_keywords = {
            "CREATE_JIRA_TICKET": ["create", "make", "open", "file", "submit"],
            "SCHEDULE_MEETING": ["schedule", "book", "set up", "arrange", "find time"],
            "DRAFT_DOCUMENT": ["draft", "write", "compose", "prepare"]
        }
        
        # Check if it's an action request
        if any(k in query_lower for k in ["jira", "ticket", "bug", "issue"]):
            if any(w in query_lower for w in action_keywords["CREATE_JIRA_TICKET"]):
                intent.intent_type = "ACTION"
                intent.requires_action = True
                intent.action_type = "CREATE_JIRA_TICKET"
                intent.confidence = 0.95
                return intent
        
        if any(k in query_lower for k in ["meeting", "calendar", "interview", "sync", "call"]):
            if any(w in query_lower for w in action_keywords["SCHEDULE_MEETING"]):
                intent.intent_type = "ACTION"
                intent.requires_action = True
                intent.action_type = "SCHEDULE_MEETING"
                intent.confidence = 0.95
                return intent
        
        # === LEVEL 3: Detect DOCUMENT_QUERY intent ===
        # These are explicit document-related queries
        doc_triggers = [
            "according to", "what does the", "in the report", "in the document",
            "policy says", "handbook", "annual report", "quarterly report",
            "what is our", "summarize the", "from the pdf", "page", "section",
            "compliance", "regulation", "procedure", "guideline"
        ]
        
        if any(trigger in query_lower for trigger in doc_triggers):
            intent.intent_type = "DOCUMENT_QUERY"
            intent.requires_rag = True
            intent.confidence = 0.9
            return intent
        
        # Check for explicit financial/strategy document queries
        financial_doc_queries = [
            "revenue", "earnings", "profit", "financial", "q1", "q2", "q3", "q4",
            "ebitda", "margin", "forecast", "budget"
        ]
        
        if any(f in query_lower for f in financial_doc_queries):
            # Only trigger RAG if it sounds like a document query
            if any(q in query_lower for q in ["what", "how much", "show", "tell me", "summarize"]):
                intent.intent_type = "DOCUMENT_QUERY"
                intent.requires_rag = True
                intent.confidence = 0.85
                return intent
        
        # === LEVEL 4: Detect CODE_SEARCH intent ===
        code_patterns = [
            "grep", "where is the", "find the function", "find the code",
            "authentication", "auth module", "source code", "implementation",
            "how does the", "show me the code", "api endpoint", "service code"
        ]
        
        if any(pattern in query_lower for pattern in code_patterns):
            if "READ_CODEBASE" in capabilities.permissions:
                intent.intent_type = "CODE_SEARCH"
                intent.requires_code_search = True
                intent.confidence = 0.9
                return intent
        
        # === DEFAULT: General conversation ===
        intent.intent_type = "GENERAL"
        intent.confidence = 0.7
        return intent
    
    async def generate_response(
        self,
        query: str,
        context: List[Dict[str, Any]],
        role: str,
        capabilities,
        intent: QueryIntent,
        conversation_history: List[Dict[str, Any]] = None  # NEW: Chat history
    ) -> Dict[str, Any]:
        """
        Step 2: Generate response based on classified intent
        Uses different prompt strategies for different intents
        Now includes conversation history for context
        """
        
        # Build appropriate system prompt based on intent
        system_prompt = self._build_system_prompt(role, capabilities, intent)
        
        # Build conversation history string
        history_str = self._format_conversation_history(conversation_history)
        
        # Build user prompt (context only for document/code queries)
        user_prompt = self._build_user_prompt(query, context, intent)
        
        # Combine all parts
        full_prompt = system_prompt
        if history_str:
            full_prompt += f"\n\n{history_str}"
        full_prompt += f"\n\n{user_prompt}"
        
        try:
            response = await self.client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7 if intent.intent_type == "GENERAL" else 0.4,
                        "top_p": 0.9
                    }
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result.get("response", "I apologize, but I couldn't generate a response.")
                
                # Extract action parameters if needed
                action_parameters = {}
                if intent.requires_action:
                    action_parameters = await self._extract_action_parameters(
                        query,
                        content,
                        intent.action_type
                    )
                
                return {
                    "content": content,
                    "action_parameters": action_parameters,
                    "show_sources": intent.requires_rag  # Only show sources for RAG queries
                }
            else:
                return {
                    "content": "I'm having trouble connecting right now. Please try again.",
                    "action_parameters": {},
                    "show_sources": False
                }
        
        except Exception as e:
            print(f"LLM Error: {e}")
            return {
                "content": self._generate_fallback_response(query, context, role, intent),
                "action_parameters": {},
                "show_sources": False
            }
    
    def _build_system_prompt(self, role: str, capabilities, intent: QueryIntent) -> str:
        """Build human-like, intent-specific system prompt"""
        
        role_name = role.replace("_", " ").title()
        
        # Base persona (friendly and professional)
        base = f"""You are a helpful enterprise AI assistant. You're speaking with someone in the {role_name} role.

Your personality:
- Friendly, professional, and conversational
- You give clear, actionable answers
- You're efficient - no unnecessary fluff
- You sound like a helpful colleague, not a robot"""

        # Intent-specific additions
        if intent.is_greeting:
            return f"""{base}

The user is greeting you. Respond warmly and briefly, then ask how you can help them today. Keep it natural and short (1-2 sentences max)."""

        elif intent.intent_type == "ACTION":
            action_name = intent.action_type.replace("_", " ").lower() if intent.action_type else "action"
            return f"""{base}

The user wants to {action_name}. Your job:
1. Acknowledge their request briefly
2. Confirm what you're doing (e.g., "I'll create that ticket for you")
3. Let them know it's done

Keep it conversational and brief. Don't mention technical details like IAM, permissions, or system internals."""

        elif intent.intent_type == "DOCUMENT_QUERY":
            return f"""{base}

The user is asking about information from documents. Use the provided context to answer.
- When referencing specific information, cite the source naturally (e.g., "According to page 42 of the annual report...")
- If the context doesn't contain the answer, say so honestly
- Summarize key points clearly"""

        elif intent.intent_type == "CODE_SEARCH":
            return f"""{base}

The user is asking about code. Use the provided code context to answer.
- Reference file paths when helpful
- Explain the code in plain terms
- Be technical but accessible"""

        else:
            # General conversation
            return f"""{base}

Have a natural conversation. Answer questions helpfully and concisely.
Don't mention internal systems, IAM, permissions, or technical infrastructure unless specifically asked."""

    def _build_user_prompt(self, query: str, context: List[Dict[str, Any]], intent: QueryIntent) -> str:
        """Build user prompt - only include context when relevant"""
        
        # For greetings and general chat, no context needed
        if intent.is_greeting or intent.intent_type == "GENERAL":
            return f"User: {query}"
        
        # For actions, minimal context
        if intent.intent_type == "ACTION":
            return f"User request: {query}\n\nProcess this request and confirm the action."
        
        # For document/code queries, include context
        if context:
            context_str = self._format_context(context, intent)
            return f"""User question: {query}

{context_str}

Answer the user's question based on the above context. Be conversational and cite sources naturally when using specific facts."""
        
        return f"User: {query}"
    
    def _format_context(self, context: List[Dict[str, Any]], intent: QueryIntent) -> str:
        """Format context for the prompt"""
        if not context:
            return "No relevant documents found."
        
        parts = ["Relevant context:"]
        
        for i, chunk in enumerate(context[:3], 1):  # Limit to top 3 chunks
            metadata = chunk.get("metadata", {})
            text = chunk.get("text", "")
            
            if metadata.get("type") == "code":
                file_path = metadata.get("file_path", "unknown")
                parts.append(f"\n[Code from {file_path}]\n{text}")
            else:
                page = metadata.get("page_number", "?")
                doc = metadata.get("document_name", "document")
                parts.append(f"\n[From {doc}, Page {page}]\n{text}")
        
        return "\n".join(parts)
    
    def _format_conversation_history(
        self,
        history: List[Dict[str, Any]] = None,
        max_messages: int = 10
    ) -> str:
        """Format conversation history for inclusion in prompt"""
        if not history:
            return ""
        
        # Take last N messages
        recent = history[-max_messages:] if len(history) > max_messages else history
        
        if not recent:
            return ""
        
        lines = ["Previous conversation:"]
        for msg in recent:
            role = msg.get("role", "user").capitalize()
            content = msg.get("content", "")
            
            # Truncate long messages
            if len(content) > 300:
                content = content[:297] + "..."
            
            lines.append(f"{role}: {content}")
        
        return "\n".join(lines)
    
    async def _extract_action_parameters(
        self,
        query: str,
        response: str,
        action_type: Optional[str]
    ) -> Dict[str, Any]:
        """Extract structured parameters for actions"""
        
        parameters = {}
        
        if action_type == "CREATE_JIRA_TICKET":
            # Extract title from query
            title = query
            for prefix in ["create a jira ticket for", "create jira ticket for", 
                          "create a ticket for", "make a ticket for", "file a ticket for"]:
                if query.lower().startswith(prefix):
                    title = query[len(prefix):].strip()
                    break
            
            parameters = {
                "title": title[:100] if len(title) > 100 else title,
                "priority": "Medium",
                "assignee": "Auto-assigned",
                "description": f"Created via Enterprise Copilot: {query}"
            }
            
        elif action_type == "SCHEDULE_MEETING":
            parameters = {
                "title": "Meeting",
                "participants": ["Auto-detect from query"],
                "duration": 60,
                "suggested_times": ["Tomorrow 10:00 AM", "Tomorrow 2:00 PM", "Friday 11:00 AM"]
            }
        
        return parameters
    
    def _generate_fallback_response(
        self,
        query: str,
        context: List[Dict[str, Any]],
        role: str,
        intent: QueryIntent
    ) -> str:
        """Generate fallback response when LLM is unavailable"""
        
        if intent.is_greeting:
            return "Hello! How can I help you today?"
        
        if intent.requires_action:
            return "I've received your request and I'm processing it now."
        
        if context:
            return f"I found {len(context)} relevant documents. However, I'm having trouble summarizing them right now. Please try again in a moment."
        
        return "I'm here to help! Could you tell me more about what you need?"
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
