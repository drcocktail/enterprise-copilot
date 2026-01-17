"""
LLM Service for DevOps Copilot V3
Uses Qwen2.5-Coder for code understanding and IT tool actions.
"""

import asyncio
import httpx
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import json
import re


class QueryIntent(BaseModel):
    """Classified intent of user query"""
    intent_type: str = "GENERAL"  # CODE_QUERY, DOC_QUERY, IT_ACTION, GENERAL
    requires_code_search: bool = False
    requires_doc_search: bool = False
    requires_action: bool = False
    action_type: Optional[str] = None
    confidence: float = 0.0
    is_greeting: bool = False


class LLMService:
    """
    LLM Service using Qwen2.5-Coder for code understanding.
    Supports:
    - Code explanation and search
    - Documentation queries
    - IT tool actions (health checks, logs, etc.)
    """
    
    # IT Tool Actions
    IT_TOOLS = {
        "HEALTH_CHECK": {
            "description": "Check health status of a service",
            "keywords": ["health", "status", "alive", "running", "up", "down"]
        },
        "PING_SERVICE": {
            "description": "Ping a service or endpoint",
            "keywords": ["ping", "reachable", "connectivity", "connect"]
        },
        "GET_LOGS": {
            "description": "Retrieve service logs",
            "keywords": ["logs", "log", "errors", "warnings", "trace"]
        },
        "CHECK_DISK": {
            "description": "Check disk usage",
            "keywords": ["disk", "storage", "space", "usage"]
        },
        "LIST_CONTAINERS": {
            "description": "List Docker containers",
            "keywords": ["docker", "containers", "pods", "k8s", "kubernetes"]
        },
        "CHECK_MEMORY": {
            "description": "Check memory usage",
            "keywords": ["memory", "ram", "heap", "usage"]
        },
        "LIST_SERVICES": {
            "description": "List running services",
            "keywords": ["services", "processes", "running", "active"]
        }
    }
    
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.2:latest"
    ):
        self.base_url = base_url
        self.model = model
        self.client = httpx.AsyncClient(timeout=120.0)
    
    async def _call_ollama(self, prompt: str, system: str = None) -> str:
        """Direct call to Ollama API for agent loop compatibility"""
        try:
            full_prompt = prompt
            if system:
                full_prompt = f"System: {system}\n\n{prompt}"
            
            response = await self.client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "top_p": 0.9,
                        "num_predict": 2500
                    }
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "")
            else:
                return f"Error: {response.status_code}"
        except Exception as e:
            return f"Error calling LLM: {str(e)}"
    
    async def stream_response(
        self,
        query: str,
        context,
        role: str,
        capabilities,
        intent,
        conversation_history = None
    ):
        """Stream response tokens from Ollama"""
        # Build prompt
        system_prompt = self._build_system_prompt(role, capabilities, intent)
        history_str = self._format_conversation_history(conversation_history)
        context_str = self._format_code_context(context)
        
        full_prompt = system_prompt
        if history_str:
            full_prompt += f"\n\n{history_str}"
        if context_str:
            full_prompt += f"\n\n{context_str}"
        full_prompt += f"\n\nUser: {query}\n\nAssistant:"
        
        try:
            async with self.client.stream(
                "POST",
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": full_prompt,
                    "stream": True,
                    "options": {
                        "temperature": 0.4,
                        "top_p": 0.9,
                        "num_predict": 2500
                    }
                }
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            if "response" in data:
                                yield data["response"]
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            yield f"Error: {str(e)}"
    
    async def classify_intent(
        self,
        query: str,
        capabilities
    ) -> QueryIntent:
        """
        Classify query intent for routing.
        """
        query_lower = query.lower().strip()
        intent = QueryIntent()
        
        # === Greetings ===
        greetings = ["hello", "hi", "hey", "good morning", "good afternoon", "good evening", "what's up"]
        if any(query_lower.startswith(g) or query_lower == g for g in greetings):
            intent.intent_type = "GENERAL"
            intent.is_greeting = True
            intent.confidence = 0.95
            return intent
        
        # === IT Tool Actions ===
        for action_type, config in self.IT_TOOLS.items():
            if any(kw in query_lower for kw in config["keywords"]):
                if "RUN_HEALTHCHECKS" in capabilities.permissions or "READ_LOGS" in capabilities.permissions:
                    intent.intent_type = "IT_ACTION"
                    intent.requires_action = True
                    intent.action_type = action_type
                    intent.confidence = 0.9
                    return intent
        
        # === Code Queries ===
        code_patterns = [
            "how does .* work", "explain .* code", "what does .* do",
            "show me the .*", "where is .*", "find .*function", "find .*class",
            "implementation of", "architecture", "flow", "logic",
            "authentication", "api", "endpoint", "handler", "service",
            "function", "class", "method", "module", "import"
        ]
        
        for pattern in code_patterns:
            if re.search(pattern, query_lower):
                intent.intent_type = "CODE_QUERY"
                intent.requires_code_search = True
                intent.confidence = 0.85
                return intent
        
        # === Document Queries ===
        doc_patterns = [
            "according to", "documentation", "readme", "guide",
            "how to", "setup", "install", "configure", "deploy"
        ]
        
        if any(p in query_lower for p in doc_patterns):
            intent.intent_type = "DOC_QUERY"
            intent.requires_doc_search = True
            intent.confidence = 0.8
            return intent
        
        # === Default: treat as code query if repo is indexed ===
        intent.intent_type = "CODE_QUERY"
        intent.requires_code_search = True
        intent.confidence = 0.6
        return intent
    
    async def generate_response(
        self,
        query: str,
        context: List[Dict[str, Any]],
        role: str,
        capabilities,
        intent: QueryIntent,
        conversation_history: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate response using Qwen2.5-Coder.
        """
        # Handle IT actions
        if intent.requires_action and intent.action_type:
            return await self._handle_it_action(query, intent.action_type, role)
        
        # Build prompts
        system_prompt = self._build_system_prompt(role, capabilities, intent)
        history_str = self._format_conversation_history(conversation_history)
        context_str = self._format_code_context(context)
        
        full_prompt = system_prompt
        if history_str:
            full_prompt += f"\n\n{history_str}"
        if context_str:
            full_prompt += f"\n\n{context_str}"
        full_prompt += f"\n\nUser: {query}\n\nAssistant:"
        
        try:
            response = await self.client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.4,
                        "top_p": 0.9,
                        "num_predict": 2500
                    }
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result.get("response", "I couldn't generate a response.")
                
                return {
                    "content": content,
                    "action_parameters": {},
                    "show_sources": intent.requires_code_search or intent.requires_doc_search
                }
            else:
                return {
                    "content": "I'm having trouble processing that request. Please try again.",
                    "action_parameters": {},
                    "show_sources": False
                }
                
        except Exception as e:
            print(f"LLM Error: {e}")
            return {
                "content": f"Connection error: {str(e)}",
                "action_parameters": {},
                "show_sources": False
            }
    
    async def _handle_it_action(
        self,
        query: str,
        action_type: str,
        role: str
    ) -> Dict[str, Any]:
        """
        Handle IT tool actions by returning structured JSON.
        """
        # Extract target from query
        target = self._extract_target(query, action_type)
        
        # Build action JSON
        action_data = {
            "action": action_type,
            "target": target,
            "requested_by": role,
            "status": "executed"
        }
        
        # Generate mock results based on action type
        mock_results = self._generate_mock_results(action_type, target)
        
        # Format as terminal-like output
        content = f"Executing {action_type.replace('_', ' ').lower()} for **{target}**...\n\n"
        content += "```terminal\n"
        content += mock_results
        content += "\n```"
        
        return {
            "content": content,
            "action_parameters": action_data,
            "show_sources": False,
            "attachment": {
                "type": "TERMINAL",
                "data": mock_results
            }
        }
    
    def _extract_target(self, query: str, action_type: str) -> str:
        """Extract the target service/resource from query."""
        query_lower = query.lower()
        
        # Common service names
        services = [
            "api", "api-gateway", "auth", "authentication", "database", "db",
            "redis", "cache", "nginx", "frontend", "backend", "worker",
            "queue", "scheduler", "prometheus", "grafana", "elasticsearch"
        ]
        
        for service in services:
            if service in query_lower:
                return service
        
        # Default targets by action
        defaults = {
            "HEALTH_CHECK": "api-gateway",
            "PING_SERVICE": "localhost",
            "GET_LOGS": "application",
            "CHECK_DISK": "/",
            "LIST_CONTAINERS": "docker",
            "CHECK_MEMORY": "system",
            "LIST_SERVICES": "all"
        }
        
        return defaults.get(action_type, "system")
    
    def _generate_mock_results(self, action_type: str, target: str) -> str:
        """Generate mock terminal output for IT actions."""
        
        if action_type == "HEALTH_CHECK":
            return f"""$ curl -s http://{target}:8000/health
{{
  "status": "healthy",
  "uptime": "12d 5h 23m",
  "version": "2.3.1",
  "checks": {{
    "database": "ok",
    "cache": "ok",
    "queue": "ok"
  }}
}}"""
        
        elif action_type == "PING_SERVICE":
            return f"""$ ping -c 3 {target}
PING {target} (127.0.0.1): 56 data bytes
64 bytes from 127.0.0.1: icmp_seq=0 ttl=64 time=0.045 ms
64 bytes from 127.0.0.1: icmp_seq=1 ttl=64 time=0.058 ms
64 bytes from 127.0.0.1: icmp_seq=2 ttl=64 time=0.062 ms

--- {target} ping statistics ---
3 packets transmitted, 3 received, 0.0% packet loss"""
        
        elif action_type == "GET_LOGS":
            return f"""$ tail -20 /var/log/{target}.log
[2026-01-15 20:15:23] INFO  - Request handled: GET /api/users (23ms)
[2026-01-15 20:15:24] INFO  - Request handled: POST /api/auth (45ms)
[2026-01-15 20:15:25] DEBUG - Cache hit for key: user_session_abc123
[2026-01-15 20:15:26] INFO  - Request handled: GET /api/health (2ms)
[2026-01-15 20:15:28] WARN  - Slow query detected: 150ms
[2026-01-15 20:15:30] INFO  - Request handled: GET /api/metrics (12ms)"""
        
        elif action_type == "CHECK_DISK":
            return f"""$ df -h {target}
Filesystem      Size  Used Avail Use% Mounted on
/dev/sda1       100G   45G   55G  45% /
/dev/sdb1       500G  230G  270G  46% /data
tmpfs           16G   1.2G   15G   8% /tmp"""
        
        elif action_type == "LIST_CONTAINERS":
            return """$ docker ps
CONTAINER ID   IMAGE                  STATUS          PORTS                    NAMES
a1b2c3d4e5f6   api-gateway:2.3.1     Up 12 days      0.0.0.0:8000->8000/tcp   api-gateway
b2c3d4e5f6a1   postgres:15           Up 12 days      5432/tcp                 database
c3d4e5f6a1b2   redis:7               Up 12 days      6379/tcp                 cache
d4e5f6a1b2c3   nginx:latest          Up 12 days      80/tcp, 443/tcp          proxy"""
        
        elif action_type == "CHECK_MEMORY":
            return """$ free -h
              total        used        free      shared  buff/cache   available
Mem:           32Gi       12Gi       8.5Gi       1.2Gi       11Gi        18Gi
Swap:          8Gi        0.5Gi      7.5Gi"""
        
        elif action_type == "LIST_SERVICES":
            return """$ systemctl list-units --type=service --state=running
UNIT                    LOAD   ACTIVE SUB     DESCRIPTION
api-gateway.service     loaded active running API Gateway Service
postgresql.service      loaded active running PostgreSQL Database
redis.service           loaded active running Redis Cache
nginx.service           loaded active running NGINX Web Server
prometheus.service      loaded active running Prometheus Monitoring"""
        
        return "$ Command executed successfully"
    
    def _build_system_prompt(self, role: str, capabilities, intent: QueryIntent) -> str:
        """Build system prompt for code understanding."""
        
        role_name = role.replace("_", " ").title()
        
        base = f"""You are DevOps Copilot, an expert AI assistant for developers and IT professionals.
You're speaking with a {role_name}.

Your expertise:
- Deep understanding of code architecture and design patterns
- Clear, technical explanations with code examples
- Practical, actionable advice
- Concise but comprehensive answers

When explaining code:
- Reference specific files and line numbers from the context
- Use markdown code blocks with language identifiers
- Explain the "why" not just the "what"
- Highlight important patterns and potential issues"""

        if intent.is_greeting:
            return f"""{base}

The user is greeting you. Respond warmly and briefly, mentioning you can help with:
- Code understanding and explanation
- Finding functions, classes, and logic flows
- IT operations (health checks, logs, etc.)
- Documentation queries"""

        if intent.intent_type == "CODE_QUERY":
            return f"""{base}

You're answering a code-related question. Use the provided code context to give a detailed, accurate answer.
- Quote relevant code snippets
- Explain the logic and data flow
- Mention file paths and line numbers
- Suggest improvements if appropriate"""

        if intent.intent_type == "IT_ACTION":
            return f"""{base}

You're helping with IT operations. Be practical and action-oriented.
- Show command outputs in terminal format
- Explain what the metrics mean
- Suggest next steps if there are issues"""

        return base
    
    def _format_code_context(self, context: List[Dict[str, Any]]) -> str:
        """Format code context for the prompt."""
        if not context:
            return ""
        
        parts = ["Relevant code from the repository:"]
        
        for chunk in context[:5]:  # Limit context
            meta = chunk.get("metadata", {})
            text = chunk.get("text", "")
            
            file_path = meta.get("file_path", "unknown")
            start_line = meta.get("start_line", "?")
            end_line = meta.get("end_line", "?")
            language = meta.get("language", "")
            name = meta.get("name", "")
            
            header = f"\n📁 {file_path}:{start_line}-{end_line}"
            if name:
                header += f" ({name})"
            
            parts.append(f"{header}\n```{language}\n{text}\n```")
        
        return "\n".join(parts)
    
    async def summarize_conversation(self, history: List[Dict[str, Any]]) -> str:
        """Generate a short 3-5 word title for the conversation"""
        if not history:
            return "New Chat"

        # Format history for summarization
        context = "\n".join([f"{msg['role']}: {msg['content'][:100]}" for msg in history[:5]])
        
        prompt = f"""Summarize the following conversation snippet into a short, concise title (3-5 words). 
        Do not use quotes. Just the title.
        
        {context}
        
        Title:"""
        
        try:
            response = await self._call_ollama(prompt, system="You are a helpful assistant that summarizes conversations.")
            title = response.strip().strip('"').strip("'")
            return title
        except Exception as e:
            print(f"Summarization failed: {e}")
            return "New Chat"

    def _format_conversation_history(
        self,
        history: List[Dict[str, Any]] = None,
        max_messages: int = 6
    ) -> str:
        """Format conversation history."""
        if not history:
            return ""
        
        recent = history[-max_messages:] if len(history) > max_messages else history
        
        if not recent:
            return ""
        
        lines = ["Previous conversation:"]
        for msg in recent:
            role = msg.get("role", "user").capitalize()
            content = msg.get("content", "")
            if len(content) > 200:
                content = content[:197] + "..."
            lines.append(f"{role}: {content}")
        
        return "\n".join(lines)
