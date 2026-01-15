# 🚀 Quick Start Guide - Enterprise Copilot

## ⚡ 3-Minute Setup

### Step 1: Install Ollama (if not installed)
```bash
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.com/install.sh | sh
```

### Step 2: Start Everything
```bash
cd /Users/praty/Downloads/Projects/nlp-challenge-hcltech
./start.sh
```

That's it! The script will:
- ✅ Start Ollama
- ✅ Pull required models
- ✅ Setup Python environment
- ✅ Install dependencies
- ✅ Start backend server
- ✅ Start frontend server

### Step 3: Open Your Browser
```
http://localhost:3000
```

---

## 🎮 How to Use

### 1. Switch Personas
Click the persona buttons in the sidebar:
- **CH** = Chief Strategy Officer (Financials)
- **HR** = HR Director (People data)
- **SR** = DevOps Engineer (Code)

### 2. Ask Questions
Try these sample queries:

**For C-Suite:**
- "Summarize Q3 revenue from the annual report"
- "Show project timeline"
- "Schedule board meeting"

**For HR:**
- "What is our PTO policy?"
- "Schedule candidate interview"
- "Draft onboarding policy"

**For DevOps:**
- "Find the authentication function"
- "Create Jira ticket for bug"
- "Check server health"

### 3. Test IAM Enforcement
Try asking for unauthorized data:
- C-Suite asking for code → **DENIED** 🚫
- DevOps asking for salaries → **DENIED** 🚫
- HR asking for financials → **DENIED** 🚫

### 4. View Audit Logs
Click "Show IAM Traces" to see real-time logs of all queries and authorization checks.

---

## 📊 Visual Guide

### Frontend UI
```
┌─────────────────────────────────────────────────────────────┐
│  [Sidebar]        [Dashboard Header]          [Avatar][IAM] │
├─────────────┬───────────────────────────────────────────────┤
│             │  ┌─────────┐ ┌─────────┐ ┌─────────┐         │
│ Navigation  │  │ Widget  │ │ Widget  │ │ Widget  │         │
│             │  └─────────┘ └─────────┘ └─────────┘         │
│ Dashboard   │                                                │
│ Projects    │  Recent Activity                              │
│ Directory   │  ┌──────────────────────────────────────┐    │
│ Documents   │  │ • Doc updated 2h ago                 │    │
│             │  │ • Policy reviewed 4h ago             │    │
│ [Personas]  │  └──────────────────────────────────────┘    │
│  ○ C-Suite  │                                                │
│  ○ HR       │                                                │
│  ● DevOps   │                                                │
└─────────────┴───────────────────────────────────────────────┘
                                     
                              ┌──────────────────────┐
                              │  💬 Copilot Widget   │
                              │  ┌────────────────┐  │
                              │  │ Your message   │  │
                              │  └────────────────┘  │
                              │  ┌────────────────┐  │
                              │  │ AI response    │  │
                              │  │ with cards     │  │
                              │  └────────────────┘  │
                              │  [IAM Badge] [Send]  │
                              └──────────────────────┘
```

### Backend API
```
┌────────────────────────────────────────────────┐
│  API Endpoints                                 │
├────────────────────────────────────────────────┤
│  POST /api/chat                                │
│    → Main chat interface                       │
│    → Requires: x-iam-role header               │
│    → Returns: Response + attachments           │
├────────────────────────────────────────────────┤
│  GET /api/personas                             │
│    → Get available personas                    │
├────────────────────────────────────────────────┤
│  GET /api/audit/logs                           │
│    → Recent audit logs                         │
├────────────────────────────────────────────────┤
│  WS /ws/audit                                  │
│    → Real-time audit stream                    │
├────────────────────────────────────────────────┤
│  POST /api/ingest/documents                    │
│    → Trigger PDF ingestion                     │
├────────────────────────────────────────────────┤
│  GET /api/health                               │
│    → Service health check                      │
└────────────────────────────────────────────────┘
```

---

## 🧪 Run Demo Tests

```bash
./demo.sh
```

This will automatically test:
1. ✅ IAM enforcement (allow/deny checks)
2. ✅ Document ingestion
3. ✅ Action execution
4. ✅ Audit logging
5. ✅ Health status

---

## 🛑 Stop Services

```bash
./stop.sh
```

Or press `Ctrl+C` in the terminal running `start.sh`

---

## 📝 Access Points

| Service | URL | Description |
|---------|-----|-------------|
| **Frontend** | http://localhost:3000 | React UI |
| **Backend** | http://localhost:8000 | FastAPI server |
| **API Docs** | http://localhost:8000/docs | Interactive API documentation |

---

## 🐛 Troubleshooting

### "Ollama not running"
```bash
ollama serve
```

### "Backend not responding"
```bash
cd backend
source venv/bin/activate
python main.py
```

### "Frontend not loading"
```bash
cd frontend
npm install
npm run dev
```

### "Port already in use"
```bash
./stop.sh  # Kill all services
./start.sh # Restart
```

---

## 📚 Learn More

- [Main README](README.md) - Comprehensive documentation
- [Backend README](backend/README.md) - API details
- [Frontend README](frontend/README.md) - UI architecture
- [Project Summary](PROJECT_SUMMARY.md) - Complete overview
- [Task Specification](task.md) - Original requirements

---

## 💡 Tips

1. **Suggested Queries**: Click the suggestion chips in the chat for quick queries
2. **Dark Mode**: Automatically follows system preference
3. **Audit Logs**: Shows all queries, even denied ones
4. **Citations**: Look for [Page X] in responses
5. **Health Check**: Green indicator in sidebar shows system status

---

## 🎯 Key Features to Demo

1. **Persona Switching** - Switch between roles and see different permissions
2. **IAM Denial** - Try unauthorized queries to see security in action
3. **Rich Attachments** - Create Jira tickets, view code snippets
4. **Live Logs** - Watch real-time authorization checks
5. **Source Citations** - See document sources with page numbers

---

**Ready? Let's start!**

```bash
./start.sh
```

Then open: **http://localhost:3000** 🚀
