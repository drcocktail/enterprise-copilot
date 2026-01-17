"""
Agent Loop for DevOps Copilot V3
ReAct-style reasoning with tool execution.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import json
import re
from datetime import datetime


class AgentStep(BaseModel):
    """Single step in agent execution"""
    step_num: int
    thought: str
    action: Optional[str] = None
    action_input: Optional[Dict[str, Any]] = None
    observation: Optional[str] = None
    

class AgentResult(BaseModel):
    """Final result from agent execution"""
    answer: str
    trace: List[Dict[str, Any]]
    actions: List[Dict[str, Any]]
    

class AgentLoop:
    """
    ReAct-style reasoning loop.
    
    While not done:
      1. Think (LLM decides next action)
      2. Act (execute tool)
      3. Observe (capture output)
      4. Repeat or respond
    """
    
    def __init__(
        self,
        llm_service,
        hybrid_retriever,
        code_ingestion=None,
        rag_service=None,
        max_steps: int = 5
    ):
        self.llm = llm_service
        self.retriever = hybrid_retriever
        self.code_ingestion = code_ingestion
        self.rag_service = rag_service
        self.max_steps = max_steps
        
        # Tool registry
        self.tools = {
            "search_code": self._search_code,
            "search_docs": self._search_docs,
            "jira_create": self._jira_create,
            "slack_post": self._slack_post,
            "k8s_exec": self._k8s_exec,
            "calendar_event": self._calendar_event,
            "final_answer": self._final_answer,
        }
        
        self.tool_descriptions = """
available Tools:
- search_code: Search the indexed repositories (code, READMEs, config files). Input: {"query": "search terms"}
- search_docs: Search USER UPLOADED PDF documents (e.g. manuals, annual reports). Input: {"query": "search terms"}
- jira_create: Create a JIRA ticket. Input: {"summary": "...", "description": "...", "priority": "High/Medium/Low"}
- slack_post: Post a message to Slack. Input: {"channel": "#channel-name", "message": "..."}
- k8s_exec: Execute a Kubernetes command. Input: {"command": "kubectl ..."}
- calendar_event: Create a calendar event. Input: {"title": "...", "participants": [...], "time": "..."}
- final_answer: Provide the final answer to the user. Input: {"answer": "your response"}
"""

    async def run(
        self,
        query: str,
        role: str,
        capabilities,
        conversation_history: List[Dict[str, Any]] = None
    ) -> AgentResult:
        """Execute the agent loop (non-streaming wrapper)"""
        trace = []
        actions = []
        answer = ""
        
        async for event in self.run_stream(query, role, capabilities, conversation_history):
            if event["type"] == "step":
                trace.append({
                    "step": len(trace) + 1,
                    "text": event["text"],
                    "state": event["state"]
                })
            elif event["type"] == "action":
                # Actions are collected in run_stream's internal logic, 
                # but we need them in the result. 
                # Simpler: extraction from the stream events if needed
                pass 
            elif event["type"] == "answer":
                answer += event.get("content", "")
            elif event["type"] == "action_result":
                actions.append(event["data"])
                
        return AgentResult(
            answer=answer,
            trace=trace,
            actions=actions
        )

    async def run_stream(
        self,
        query: str,
        role: str,
        capabilities,
        conversation_history: List[Dict[str, Any]] = None
    ):
        """Execute the agent loop yielding events"""
        step_num = 0
        # Handle None capabilities gracefully
        permissions_str = ', '.join(capabilities.permissions) if capabilities else 'READ_DOCS'
        
        # Format history
        history_str = ""
        if conversation_history:
            for msg in conversation_history:
                # Handle both Dict and Object (Pydantic) types safely
                r = msg.get("role", "") if isinstance(msg, dict) else getattr(msg, "role", "")
                c = msg.get("content", "") if isinstance(msg, dict) else getattr(msg, "content", "")
                if r and c:
                    history_str += f"{r.upper()}: {c}\n"

        context = f"""User Query: {query}
Role: {role}
Permissions: {permissions_str}

Conversation History:
{history_str}

{self.tool_descriptions}

You are an agent designed to answer questions by thinking step-by-step and using tools.
You MUST output your response in this exact format:

Thought: [Your reasoning about what to do next]
Action: [The name of the tool to use, or "final_answer"]
Action Input: [The JSON argument for the tool]

Example 1 (Need to search code):
Thought: The user is asking about the auth flow. I should search for "authentication" in the code.
Action: search_code
Action Input: {{"query": "authentication flow"}}

Example 2 (Answering directly):
Thought: The user said hello. I don't need to use any tools.
Action: final_answer
Action Input: {{"answer": "Hello! How can I help you today?"}}

CRITICAL:
1. ALWAYS start with "Thought:".
2. ALWAYS include "Action:" and "Action Input:".
3. If you have the answer, use "final_answer".
"""
        
        while step_num < self.max_steps:
            step_num += 1
            
            # Yield thinking start
            yield {"type": "step", "text": f"Step {step_num}: Analyzing...", "state": "processing"}
            
            # Think: Ask LLM what to do
            think_response = await self._think(context, conversation_history)
            
            # Parse response
            thought, action, action_input = self._parse_response(think_response)
            
            # Yield step update
            yield {"type": "step", "text": f"Step {step_num}: {thought[:80]}...", "state": "done"}
            
            # Check if done
            if action == "final_answer":
                answer = action_input.get("answer", think_response)
                yield {"type": "answer", "content": answer}
                return
            
            # Act: Execute tool
            if action in self.tools:
                yield {"type": "step", "text": f"Executing {action}...", "state": "processing"}
                
                try:
                    observation = await self.tools[action](action_input, role)
                except Exception as e:
                    observation = f"Error executing tool {action}: {str(e)}"
                
                # Truncate observation - use larger limit for document context
                max_obs_len = 6000  # Increased from 1000 for better document context
                if len(str(observation)) > max_obs_len:
                    observation_truncated = str(observation)[:max_obs_len] + f"... (truncated, {len(str(observation))} total chars)"
                else:
                    observation_truncated = str(observation)
                
                # Yield action result
                if action in ["jira_create", "slack_post", "k8s_exec", "calendar_event"]:
                    action_data = {
                        "system": action.split("_")[0].upper() if "_" in action else action.upper(),
                        "status": "EXECUTED",
                        "payload": action_input,
                        "result": observation_truncated
                    }
                    yield {"type": "action_result", "data": action_data}
                
                yield {"type": "step", "text": f"Executing {action}...", "state": "done"}
                
                # Update context
                context += f"\n\nStep {step_num}:\nThought: {thought}\nAction: {action}\nAction Input: {json.dumps(action_input)}\nObservation: {observation_truncated}\n"
            else:
                context += f"\n\nStep {step_num}:\nThought: {thought}\nAction: {action}\nObservation: Unknown tool '{action}'. Available tools: {list(self.tools.keys())}\n"
        
        # Max steps reached\n        yield {"type": "answer", "content": "I've reached my reasoning limit. Please try rephrasing your question."}
    
    async def _think(self, context: str, history: List[Dict[str, Any]] = None) -> str:
        """Get LLM to think about next step"""
        prompt = f"""{context}

Now, think step by step about what to do next. Remember to use 'Thought:', 'Action:', and 'Action Input:'."""
        
        try:
            response = await self.llm._call_ollama(
                prompt,
                system="You are an AI agent that reasons step-by-step to answer user queries. Follow the ReAct format: Thought, Action, Action Input."
            )
            return response
        except Exception as e:
            return f"Thought: I encountered an error. Let me provide a direct answer.\nAction: final_answer\nAction Input: {{\"answer\": \"I apologize, but I encountered an issue processing your request.\"}}"
    
    def _parse_response(self, response: str) -> tuple:
        """Parse LLM response into thought, action, action_input"""
        thought = ""
        action = "final_answer"
        action_input = {}
        
        # Normalize newlines
        response = response.replace("\r\n", "\n")
        
        # Extract thought (lazy match until Action: or end)
        thought_match = re.search(r'Thought:(.+?)(?=Action:|$)', response, re.DOTALL | re.IGNORECASE)
        if thought_match:
            thought = thought_match.group(1).strip()
        else:
             # If no explicit "Thought:", but starts with text before Action, treat as thought
             pre_action = re.split(r'Action:', response, flags=re.IGNORECASE)[0]
             if pre_action.strip():
                 thought = pre_action.strip()
        
        # Extract action
        action_match = re.search(r'Action:\s*[*`]*([a-zA-Z0-9_]+)[*`]*', response, re.IGNORECASE)
        if action_match:
            action = action_match.group(1).strip()
        
        # Extract action input
        input_match = re.search(r'Action Input:\s*(?:```(?:json)?\s*)?({.+?})(?:\s*```)?', response, re.DOTALL | re.IGNORECASE)
        if input_match:
            try:
                action_input = json.loads(input_match.group(1))
            except json.JSONDecodeError:
                try:
                    import ast
                    action_input = ast.literal_eval(input_match.group(1))
                    if not isinstance(action_input, dict): action_input = {}
                except:
                     action_input = {"raw": input_match.group(1)}
        
        # Fallback: If no Action explicit, check if direct answer
        if action == "final_answer" and not input_match:
             if "Action:" not in response:
                 action_input = {"answer": response}
                 if not thought: thought = "Answering directly."
        
        return thought, action, action_input
    
    # ==================== TOOL IMPLEMENTATIONS ====================
    
    async def _search_code(self, input: Dict, role: str) -> str:
        """Search codebase"""
        query = input.get("query", "")
        if self.retriever:
            # Increase top_k and length for better context
            results = await self.retriever.hybrid_search(query, top_k=5)
            if results:
                return "\n\n".join([
                    f"--- File: {r.get('file_path', 'unknown')} ---\n{r.get('text', '')[:1000]}\n..."
                    for r in results
                ])
        return "No code results found. Try a different query."
    
    async def _search_docs(self, input: Dict, role: str) -> str:
        """Search documents using RAG"""
        query = input.get("query", "")
        if self.rag_service:
            # Increase limit to 15 for more context (LLM has large context window)
            results = self.rag_service.search(query, limit=15)
            if results:
                return "\n\n".join([
                    f"[Doc: {r.get('metadata', {}).get('filename')}, Chunk {r.get('metadata', {}).get('chunk_index', '?')}]\n{r.get('text', '')}" 
                    for r in results
                ])
        return "No documents found."
    
    async def _jira_create(self, input: Dict, role: str) -> str:
        """Create JIRA ticket (mock)"""
        summary = input.get("summary", "New Ticket")
        priority = input.get("priority", "Medium")
        ticket_id = f"DEV-{datetime.now().strftime('%H%M%S')}"
        return f"Created JIRA ticket {ticket_id}: '{summary}' with priority {priority}"
    
    async def _slack_post(self, input: Dict, role: str) -> str:
        """Post to Slack (mock)"""
        channel = input.get("channel", "#general")
        message = input.get("message", "")
        return f"Posted to {channel}: {message[:100]}..."
    
    async def _k8s_exec(self, input: Dict, role: str) -> str:
        """Execute K8s command (mock)"""
        command = input.get("command", "kubectl get pods")
        
        # Mock output
        mock_outputs = {
            "get pods": "NAME                     READY   STATUS    RESTARTS   AGE\napi-gateway-7f9d8c6b4-x2k3m   1/1     Running   0          3h\npayments-v2-5c8d7b4a3-y9n8z   1/1     Running   0          1h",
            "get nodes": "NAME           STATUS   ROLES    AGE   VERSION\nmaster-01      Ready    master   30d   v1.28.0\nworker-01      Ready    <none>   30d   v1.28.0",
            "get services": "NAME         TYPE        CLUSTER-IP     EXTERNAL-IP   PORT(S)   AGE\nkubernetes   ClusterIP   10.96.0.1      <none>        443/TCP   30d"
        }
        
        for key, output in mock_outputs.items():
            if key in command.lower():
                return f"$ {command}\n{output}"
        
        return f"$ {command}\nCommand executed successfully."
    
    async def _calendar_event(self, input: Dict, role: str) -> str:
        """Create calendar event (mock)"""
        title = input.get("title", "Meeting")
        participants = input.get("participants", [])
        time = input.get("time", "Tomorrow 10:00 AM")
        
        return f"Created calendar event: '{title}' at {time} with {len(participants)} participants"
    
    async def _final_answer(self, input: Dict, role: str) -> str:
        """Provide final answer"""
        return input.get("answer", "")
