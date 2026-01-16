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
        document_ingestion=None,
        max_steps: int = 5
    ):
        self.llm = llm_service
        self.retriever = hybrid_retriever
        self.code_ingestion = code_ingestion
        self.document_ingestion = document_ingestion
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
Available Tools:
- search_code: Search the indexed codebase for relevant code snippets. Input: {"query": "search terms"}
- search_docs: Search uploaded documents. Input: {"query": "search terms"}
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
        context = f"""User Query: {query}
Role: {role}
Permissions: {', '.join(capabilities.permissions)}

{self.tool_descriptions}

You must respond in the following format:
Thought: [your reasoning about what to do next]
Action: [tool name from the list above]
Action Input: [JSON input for the tool]

When you have enough information to answer, use the 'final_answer' tool.
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
                
                # Truncate observation
                max_obs_len = 1000
                if len(str(observation)) > max_obs_len:
                    observation_truncated = str(observation)[:max_obs_len] + f"... (truncated)"
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
        
        # Max steps reached
        yield {"type": "answer", "content": "I've reached my reasoning limit. " + trace[-1].get("thought", "") if trace else ""}
    
    async def _think(self, context: str, history: List[Dict[str, Any]] = None) -> str:
        """Get LLM to think about next step"""
        prompt = f"""{context}

Now, think step by step about what to do next."""
        
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
        
        # Extract thought
        thought_match = re.search(r'Thought:\s*(.+?)(?=Action:|$)', response, re.DOTALL)
        if thought_match:
            thought = thought_match.group(1).strip()
        
        # Extract action
        action_match = re.search(r'Action:\s*(\w+)', response)
        if action_match:
            action = action_match.group(1).strip()
        
        # Extract action input
        input_match = re.search(r'Action Input:\s*({.+?})', response, re.DOTALL)
        if input_match:
            try:
                action_input = json.loads(input_match.group(1))
            except json.JSONDecodeError:
                action_input = {"raw": input_match.group(1)}
        
        return thought, action, action_input
    
    # ==================== TOOL IMPLEMENTATIONS ====================
    
    async def _search_code(self, input: Dict, role: str) -> str:
        """Search codebase"""
        query = input.get("query", "")
        if self.retriever:
            results = await self.retriever.hybrid_search(query, top_k=3)
            if results:
                return "\n".join([
                    f"[{r.get('file_path', 'unknown')}] {r.get('text', '')[:200]}..."
                    for r in results
                ])
        return "No code results found."
    
    async def _search_docs(self, input: Dict, role: str) -> str:
        """Search documents using Knowledge Graph"""
        query = input.get("query", "")
        if self.document_ingestion:
            return await self.document_ingestion.get_context_for_query(query)
        return "Document ingestion service not available."
    
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
