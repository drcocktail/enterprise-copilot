# 📡 API Reference - Enterprise Copilot

## Base URL
```
http://localhost:8000
```

---

## 🔐 Authentication

All requests require the `x-iam-role` header:

```http
x-iam-role: CHIEF_STRATEGY_OFFICER
x-iam-role: HR_DIRECTOR
x-iam-role: SR_DEVOPS_ENGINEER
```

---

## 📋 Endpoints

### 1. Chat Interface

**Send Query to Copilot**

```http
POST /api/chat
Content-Type: application/json
x-iam-role: CHIEF_STRATEGY_OFFICER

{
  "query": "Summarize Q3 revenue from the annual report",
  "session_id": "optional-session-id",
  "context": {}
}
```

**Response:**
```json
{
  "content": "Based on the annual report...",
  "attachment": {
    "type": "TICKET|CODE|CALENDAR|GANTT",
    "data": {}
  },
  "iam_role": "CHIEF_STRATEGY_OFFICER",
  "trace_id": "uuid",
  "timestamp": "2026-01-15T...",
  "sources": [
    {
      "document": "Annual-Report.pdf",
      "page": 15,
      "category": "Financial Report",
      "relevance_score": 0.95
    }
  ]
}
```

**Status Codes:**
- `200` - Success
- `403` - Access Denied (IAM violation)
- `500` - Server Error

---

### 2. Get Personas

**List Available Personas**

```http
GET /api/personas
```

**Response:**
```json
[
  {
    "id": "c_suite_01",
    "role": "CHIEF_STRATEGY_OFFICER",
    "name": "Eleanor Vance",
    "permissions": [
      "READ_FINANCIALS",
      "READ_HR_AGGREGATE",
      "WRITE_STRATEGY",
      "CALENDAR_WRITE"
    ],
    "description": "Strategic Overview & Financial Analysis"
  },
  ...
]
```

---

### 3. Audit Logs

**Get Recent Audit Logs**

```http
GET /api/audit/logs?limit=50
x-iam-role: CHIEF_STRATEGY_OFFICER
```

**Response:**
```json
[
  {
    "id": "log_000001",
    "timestamp": "2026-01-15T10:30:00",
    "actor": "Eleanor Vance",
    "iam_role": "CHIEF_STRATEGY_OFFICER",
    "action": "QUERY_PROCESSING",
    "status": "ALLOWED",
    "details": "Processing query: Summarize Q3...",
    "trace_id": "abc123",
    "metadata": {}
  },
  ...
]
```

---

### 4. Real-time Audit Stream

**WebSocket Connection**

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/audit');

ws.onmessage = (event) => {
  const log = JSON.parse(event.data);
  console.log('New audit log:', log);
};
```

---

### 5. Document Ingestion

**Ingest PDF Documents**

```http
POST /api/ingest/documents
x-iam-role: CHIEF_STRATEGY_OFFICER
```

**Response:**
```json
{
  "status": "success",
  "documents_processed": 1,
  "total_chunks": 245
}
```

---

### 6. Codebase Indexing

**Index Python Codebase**

```http
POST /api/ingest/codebase?path=/path/to/code
x-iam-role: SR_DEVOPS_ENGINEER
```

**Response:**
```json
{
  "status": "success",
  "files_processed": 45,
  "functions_indexed": 234,
  "classes_indexed": 67
}
```

---

### 7. Health Check

**Get Service Health**

```http
GET /api/health
```

**Response:**
```json
{
  "status": "healthy",
  "services": {
    "iam": "online",
    "rag": "online",
    "code_intelligence": "online",
    "llm": "online",
    "audit": "online"
  },
  "timestamp": "2026-01-15T10:30:00"
}
```

---

## 🔄 Common Workflows

### Workflow 1: Basic Query
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "x-iam-role: CHIEF_STRATEGY_OFFICER" \
  -d '{"query": "What was our Q3 revenue?"}'
```

### Workflow 2: Test IAM Denial
```bash
# C-Suite tries to access code (should be denied)
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "x-iam-role: CHIEF_STRATEGY_OFFICER" \
  -d '{"query": "Show me the auth function code"}'
```

### Workflow 3: Ingest + Query
```bash
# Step 1: Ingest documents
curl -X POST http://localhost:8000/api/ingest/documents \
  -H "x-iam-role: CHIEF_STRATEGY_OFFICER"

# Step 2: Query ingested data
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "x-iam-role: CHIEF_STRATEGY_OFFICER" \
  -d '{"query": "Summarize the annual report"}'
```

---

## 🎭 Persona-Specific Examples

### C-Suite Executive

**✅ Allowed Queries:**
```bash
# Financial data
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "x-iam-role: CHIEF_STRATEGY_OFFICER" \
  -d '{"query": "Show Q3 earnings breakdown"}'

# Strategy documents
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "x-iam-role: CHIEF_STRATEGY_OFFICER" \
  -d '{"query": "What is our market share?"}'
```

**🚫 Denied Queries:**
```bash
# Code access (denied)
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "x-iam-role: CHIEF_STRATEGY_OFFICER" \
  -d '{"query": "Show me the authentication code"}'
# Returns: 403 Access Denied
```

### HR Director

**✅ Allowed Queries:**
```bash
# HR policies
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "x-iam-role: HR_DIRECTOR" \
  -d '{"query": "What is our PTO policy?"}'

# Employee data
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "x-iam-role: HR_DIRECTOR" \
  -d '{"query": "Schedule interview slots"}'
```

**🚫 Denied Queries:**
```bash
# Code access (denied)
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "x-iam-role: HR_DIRECTOR" \
  -d '{"query": "Show codebase structure"}'
# Returns: 403 Access Denied
```

### DevOps Engineer

**✅ Allowed Queries:**
```bash
# Code search
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "x-iam-role: SR_DEVOPS_ENGINEER" \
  -d '{"query": "Find the auth middleware function"}'

# Create tickets
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "x-iam-role: SR_DEVOPS_ENGINEER" \
  -d '{"query": "Create Jira ticket for bug fix"}'
```

**🚫 Denied Queries:**
```bash
# Employee PII (denied)
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "x-iam-role: SR_DEVOPS_ENGINEER" \
  -d '{"query": "Show employee salary data"}'
# Returns: 403 Access Denied
```

---

## 📊 Response Types

### Standard Text Response
```json
{
  "content": "Here is the answer...",
  "attachment": null,
  "iam_role": "CHIEF_STRATEGY_OFFICER",
  "trace_id": "abc123",
  "timestamp": "2026-01-15T10:30:00"
}
```

### Response with Jira Ticket
```json
{
  "content": "I've created a ticket for this issue.",
  "attachment": {
    "type": "TICKET",
    "data": {
      "ticket_id": "JIRA-4201",
      "title": "Fix auth timeout in production",
      "priority": "High",
      "assignee": "Sarah Chen",
      "status": "TO DO"
    }
  },
  ...
}
```

### Response with Code
```json
{
  "content": "Found the function in auth-service.js",
  "attachment": {
    "type": "CODE",
    "data": {
      "file": "auth-service.js",
      "snippet": "function authenticate(token) {...}",
      "lines": "45-48"
    }
  },
  ...
}
```

### Response with Calendar
```json
{
  "content": "Here are available interview slots.",
  "attachment": {
    "type": "CALENDAR",
    "data": {
      "slots": ["Tue 10:00 AM", "Tue 2:00 PM", "Wed 11:30 AM"]
    }
  },
  ...
}
```

---

## 🛡️ Error Responses

### IAM Denial (403)
```json
{
  "detail": "Access Denied: Your role does not have code access permissions"
}
```

### Server Error (500)
```json
{
  "detail": "Internal server error message"
}
```

### Validation Error (422)
```json
{
  "detail": [
    {
      "loc": ["body", "query"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

## 🔧 Interactive API Documentation

FastAPI provides interactive documentation:

**Swagger UI:**
```
http://localhost:8000/docs
```

**ReDoc:**
```
http://localhost:8000/redoc
```

---

## 📝 Notes

- All endpoints support JSON request/response
- WebSocket endpoints use WS protocol
- Audit logs are retained for the session (in-memory)
- Document ingestion is async and may take time
- Health check does not require authentication

---

## 🚀 Quick Test

```bash
# Test health
curl http://localhost:8000/api/health

# Test personas
curl http://localhost:8000/api/personas

# Test chat (allowed)
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "x-iam-role: CHIEF_STRATEGY_OFFICER" \
  -d '{"query": "Hello"}'

# Test IAM denial
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "x-iam-role: CHIEF_STRATEGY_OFFICER" \
  -d '{"query": "Show me the code"}'
```

---

**For more details, see:**
- [Main README](README.md)
- [Backend README](backend/README.md)
- [Interactive API Docs](http://localhost:8000/docs)
