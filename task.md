Project Task Plan: Agentic Enterprise Copilot (IAM-First)

1. Architectural Vision

Goal: Build a privacy-first, role-aware corporate assistant that serves multiple personas (C-Suite, HR, IT) from a single interface.
Core Philosophy: "The copilot can never exceed the authority of the user it serves."
Stack:

AI Engine: Ollama (Llama 3.2 or Qwen 2.5 for Code)

Embeddings: nomic-embed-text (Local, high performance)

Vector Store: ChromaDB (Local/Dockerized) or Pinecone (Free Tier)

Frontend: React (Single Page App with Persona Switcher)

Code Intelligence: Local AST Parser/Indexer + Vector RAG

Backend: Python/FastAPI or Node.js (Middleware for IAM & RAG)

2. Phase I: IAM & Persona Foundation (The "Brain")

Define who is asking before defining what is answered.

$$$$

 Define Persona Configuration (iam_config.json)

$$$$

 Create rigid definitions for: CSUITE (Strategy/Finance), HR_ADMIN (PII/Policy), IT_DEVOPS (Code/Logs).

$$$$

 Define Permission Scopes (e.g., scope:calendar:write, scope:code:read, scope:strategy:read).

$$$$

 Output: A JSON file loaded at system startup.

$$$$

 Implement "Capability Envelope" Logic

$$$$

 Write a middleware function resolve_capabilities(user_role, user_query).

$$$$

 Pre-computation Check: Before sending to LLM, check if the Intent matches the Role.

$$$$

 Failure Mode: If an HR user asks for "AWS Secret Keys", block immediately without invoking the LLM (Deterministic Security).

$$$$

 Build Audit Logging System

$$$$

 Create an immutable log format: {timestamp, actor_iam, action_attempt, status, trace_id}.

$$$$

 Implement visual feedback loop (the "Console" seen in the wireframe) to show these logs in real-time.

3. Phase II: Document Intelligence (Advanced RAG)

For Annual Reports, HR Policies, and Strategy Docs.

$$$$

 Ingestion Pipeline with Metadata Extraction

$$$$

 Chunking Strategy: Do not just chunk by characters. Chunk by semantic sections.

$$$$

 Metadata Extraction: For every chunk, extract:

page_number (Critical for citations)

document_category (e.g., "Financial Report", "Employee Handbook")

sensitivity_level (e.g., "Public", "Internal", "Confidential")

$$$$

 Embedding: Use nomic-embed-text via Ollama for dense vector creation.

$$$$

 Retrieval & Reranking Strategy

$$$$

 Hybrid Search: Combine Keyword Search (BM25) with Vector Search.

$$$$

 Metadata Filtering: Apply IAM filters during retrieval (e.g., filter: { sensitivity: { $lte: user.clearance_level } }).

$$$$

 Reranking: Implement a lightweight re-ranking step (Cross-Encoder) to sort chunks by relevance before feeding to the LLM.

$$$$

 Agentic Synthesis

$$$$

 System Prompt: "You are an analyst. Use the provided context chunks. Cite every claim with [Page X]."

$$$$

 Output: A report-style answer, not just a chat response.

4. Phase III: Code Intelligence (Local Static Analysis & RAG)

Index and explain existing legacy codebases without relying on CI/CD triggers.

$$$$

 The "Indexer" Script (Local Execution)

$$$$

 Create a local script (e.g., indexer.py) that accepts a target directory path (the legacy codebase).

$$$$

 AST Parsing: Use tree-sitter or language-specific AST parsers to walk the directory and identify logical units (functions, classes, API endpoints) instead of just lines.

$$$$

 Metadata Extraction: For each code chunk, extract: file_path, function_name, dependencies, and docstrings.

$$$$

 Embedding: Embed the code signatures and comments using nomic-embed-text and store in the Vector DB with metadata type: "codebase".

$$$$

 The "Retriever" Logic (Context-Aware)

$$$$

 Semantic Search: When IT asks "Where is the auth middleware?", perform a vector search against the codebase index.

$$$$

 Retrieval: Fetch the relevant function definition and its file path.

$$$$

 Answer Generation: The Agent explains the logic of the legacy code found, rather than just returning the file.

5. Phase IV: Action Execution & JSON Guardrails

Generating structured outputs for Jira, Slack, Calendar.

$$$$

 Define Tool Schemas (JSON)

$$$$

 create_jira_ticket: { title, priority, description, assignee }

$$$$

 schedule_meeting: { participants[], duration, time_range }

$$$$

 search_logs: { service_name, error_code, time_window }

$$$$

 Implement "Strict JSON" Mode

$$$$

 Use Ollama's format: "json" parameter (if available) or specific System Prompt engineering: "You must ONLY output valid JSON."

$$$$

 Retry Logic: If JSON.parse() fails, feed the error back to the LLM and ask it to fix the syntax (Self-Correction Loop).

$$$$

 Dummy Integration Layer

$$$$

 Instead of calling real APIs, the backend simply validates the JSON against the schema.

$$$$

 If valid -> Return "Success" + The JSON (for the Frontend to render as a UI Card).

6. Phase V: Frontend Integration (React)

Connecting the Wireframe to the Logic.

$$$$

 Connect Persona Switcher to Backend

$$$$

 Sending x-iam-role header with every request.

$$$$

 Render "Agent Actions"

$$$$

 If backend returns { type: "JIRA_TICKET", data: {...} }, render the Ticket Component.

$$$$

 If backend returns { type: "CODE_SNIPPET", data: {...} }, render the Syntax Highlighter Component.

$$$$

 Stream Audit Logs

$$$$

 Poll or WebSocket connection to show the IAM authorization checks happening in real-time.

Summary Checklist for "NLP Challenge" Submission

$$$$

 PDF Chat: Verify retrieval accuracy on the HCLTech Annual Report (Page citations).

$$$$

 Action Test: Verify schedule_meeting produces perfect JSON.

$$$$

 IAM Demo: Verify HR cannot access Code, and IT cannot access Salary data.