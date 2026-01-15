import React, { useState, useEffect, useRef } from 'react';
import { 
  Shield, 
  MessageSquare, 
  Terminal, 
  Users, 
  Briefcase, 
  FileText, 
  Calendar, 
  Search, 
  X, 
  Send, 
  CheckCircle, 
  AlertTriangle, 
  Lock, 
  Clock, 
  ChevronRight, 
  Layout, 
  PieChart, 
  Server,
  Code,
  Trello,
  Maximize2,
  Minimize2,
  Activity,
  Eye
} from 'lucide-react';

// --- MOCK DATA & CONFIGURATION ---

const PERSONAS = {
  CSUITE: {
    id: 'c_suite_01',
    role: 'CHIEF_STRATEGY_OFFICER',
    name: 'Eleanor Vance',
    permissions: ['READ_FINANCIALS', 'READ_HR_AGGREGATE', 'WRITE_STRATEGY', 'CALENDAR_WRITE'],
    theme: 'bg-indigo-900',
    context: 'Strategic Overview',
    suggested: ['Summarize Q3 Revenue', 'Show Project Alpha Timeline', 'Schedule Board Sync']
  },
  HR: {
    id: 'hr_lead_04',
    role: 'HR_DIRECTOR',
    name: 'Marcus Thorne',
    permissions: ['READ_EMPLOYEE_PII', 'WRITE_POLICY', 'CALENDAR_WRITE', 'SLACK_BROADCAST'],
    theme: 'bg-rose-800',
    context: 'People & Culture',
    suggested: ['Draft Onboarding Policy', 'Find Interview Slots', 'Analyze Attrition']
  },
  IT: {
    id: 'dev_ops_99',
    role: 'SR_DEVOPS_ENGINEER',
    name: 'Sarah Chen',
    permissions: ['READ_CODEBASE', 'WRITE_JIRA', 'RESTART_SERVICES', 'READ_LOGS'],
    theme: 'bg-emerald-900',
    context: 'Infrastructure & Ops',
    suggested: ['Grep error in auth-service', 'Create Jira Ticket', 'Check Server Health']
  }
};

const MOCK_DOCS = {
  policy: "PTO Policy 2024: Employees are entitled to 20 days annually. Carry-over is limited to 5 days.",
  financials: "Q3 Earnings: Revenue up 15% YoY. EBITDA margin at 22%. Primary driver: Enterprise SaaS adoption.",
  code: "function authenticateUser(token) { \n  // TODO: Fix race condition here \n  if (!verify(token)) throw new Error('Invalid'); \n}"
};

// --- COMPONENTS ---

const IAMBadge = ({ role, permissions }) => (
  <div className="flex items-center gap-2 text-xs font-mono bg-slate-100 dark:bg-slate-800 p-2 rounded border border-slate-200 dark:border-slate-700 mt-1">
    <Lock className="w-3 h-3 text-amber-500" />
    <span className="font-bold text-slate-600 dark:text-slate-300">IAM_CTX:</span>
    <span className="text-blue-600 dark:text-blue-400">{role}</span>
    <span className="text-slate-400">|</span>
    <span className="text-slate-500 truncate max-w-[150px]">{permissions.length} active scopes</span>
  </div>
);

const ChatMessage = ({ msg }) => {
  const isUser = msg.type === 'user';
  
  return (
    <div className={`flex w-full mb-4 ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`flex flex-col max-w-[85%] ${isUser ? 'items-end' : 'items-start'}`}>
        <div className={`p-3 rounded-lg shadow-sm text-sm ${
          isUser 
            ? 'bg-blue-600 text-white rounded-br-none' 
            : 'bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 border border-slate-200 dark:border-slate-700 rounded-bl-none'
        }`}>
          {msg.content}
        </div>
        
        {/* Render Rich Attachments/Cards if Agent */}
        {!isUser && msg.attachment && (
          <div className="mt-2 w-full">
            {msg.attachment.type === 'TICKET' && (
              <div className="bg-white dark:bg-slate-800 border-l-4 border-orange-500 rounded shadow p-3 text-xs font-mono">
                <div className="flex justify-between items-center mb-2">
                  <span className="font-bold flex items-center gap-1"><Trello size={12}/> JIRA-4201</span>
                  <span className="bg-orange-100 text-orange-800 px-1 rounded">TO DO</span>
                </div>
                <div className="text-slate-600 dark:text-slate-400 mb-2">{msg.attachment.data.title}</div>
                <div className="flex gap-2 text-[10px] text-slate-400">
                  <span>Assignee: {msg.attachment.data.assignee}</span>
                  <span>•</span>
                  <span>Priority: {msg.attachment.data.priority}</span>
                </div>
              </div>
            )}
            
            {msg.attachment.type === 'CODE' && (
              <div className="bg-slate-900 text-slate-300 rounded shadow p-3 text-xs font-mono overflow-x-auto">
                <div className="flex justify-between items-center mb-2 border-b border-slate-700 pb-1">
                  <span className="flex items-center gap-1"><Code size={12}/> {msg.attachment.data.file}</span>
                  <span className="text-[10px] opacity-50">Lines 45-48</span>
                </div>
                <pre>{msg.attachment.data.snippet}</pre>
              </div>
            )}

            {msg.attachment.type === 'GANTT' && (
              <div className="bg-white dark:bg-slate-800 rounded shadow p-3 text-xs border border-slate-200 dark:border-slate-700">
                <div className="flex items-center gap-2 mb-3 font-bold text-slate-700 dark:text-slate-200">
                  <Activity size={12} /> Project Roadmap
                </div>
                <div className="space-y-2">
                  {msg.attachment.data.tasks.map((task, i) => (
                    <div key={i} className="relative h-6 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden w-full">
                      <div 
                        className="absolute h-full bg-blue-500 opacity-80 flex items-center pl-2 text-white text-[10px] whitespace-nowrap"
                        style={{ width: `${task.progress}%` }}
                      >
                        {task.name}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {msg.attachment.type === 'CALENDAR' && (
               <div className="bg-white dark:bg-slate-800 rounded shadow p-3 text-xs border border-slate-200 dark:border-slate-700">
                 <div className="flex items-center gap-2 mb-2 font-bold text-slate-700 dark:text-slate-200">
                   <Calendar size={12} /> Proposed Slots
                 </div>
                 <div className="flex gap-2">
                   {msg.attachment.data.slots.map((slot, i) => (
                     <button key={i} className="flex-1 py-2 px-1 bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400 border border-green-200 dark:border-green-800 rounded text-center hover:bg-green-100 transition-colors">
                       {slot}
                     </button>
                   ))}
                 </div>
               </div>
            )}
          </div>
        )}

        {/* IAM Trace Footer */}
        {!isUser && (
          <div className="flex items-center gap-1 mt-1 opacity-50 text-[10px] text-slate-500">
            <Shield size={10} />
            <span>Authorized via {msg.iamRole}</span>
          </div>
        )}
      </div>
    </div>
  );
};

const DashboardWidget = ({ title, value, trend, icon: Icon, color }) => (
  <div className="bg-white dark:bg-slate-800 p-6 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm">
    <div className="flex justify-between items-start">
      <div>
        <p className="text-sm font-medium text-slate-500 dark:text-slate-400">{title}</p>
        <h3 className="text-2xl font-bold text-slate-900 dark:text-white mt-2">{value}</h3>
      </div>
      <div className={`p-2 rounded-lg ${color}`}>
        <Icon className="w-5 h-5 text-white" />
      </div>
    </div>
    <div className="mt-4 flex items-center text-sm">
      <span className={trend.startsWith('+') ? 'text-green-500' : 'text-red-500'}>{trend}</span>
      <span className="text-slate-400 ml-2">vs last month</span>
    </div>
  </div>
);

// --- MAIN APPLICATION ---

export default function CorporateCopilot() {
  const [activePersona, setActivePersona] = useState(PERSONAS.CSUITE);
  const [isCopilotOpen, setIsCopilotOpen] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false); // For dashboard/log split
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [auditLogs, setAuditLogs] = useState([]);
  const [showLogs, setShowLogs] = useState(false);
  
  const scrollRef = useRef(null);

  // Reset chat when persona changes
  useEffect(() => {
    setMessages([{
      type: 'agent',
      content: `Hello ${activePersona.name}. I am active with IAM Role: ${activePersona.role}. How can I assist with ${activePersona.context}?`,
      iamRole: activePersona.role,
      id: Date.now()
    }]);
    setIsCopilotOpen(false); // Close initially
    // Clear logs for demo clarity or keep them to show history? Let's keep them.
  }, [activePersona]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isTyping]);

  const addAuditLog = (action, status, details) => {
    const newLog = {
      id: Date.now(),
      timestamp: new Date().toISOString(),
      actor: activePersona.name,
      iamRole: activePersona.role,
      action: action,
      status: status,
      details: details,
      traceId: `req_${Math.random().toString(36).substr(2, 9)}`
    };
    setAuditLogs(prev => [newLog, ...prev]);
  };

  const handleSend = async () => {
    if (!input.trim()) return;
    
    const userMsg = { type: 'user', content: input, id: Date.now() };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsTyping(true);

    // Simulate Agent Logic
    setTimeout(() => {
      let responseContent = "I can't help with that based on your current permissions.";
      let attachment = null;
      let actionType = "GENERAL_QUERY";
      let status = "ALLOWED";

      const lowerInput = userMsg.content.toLowerCase();

      // --- LOGIC: IT PERSONA ---
      if (activePersona.role === 'SR_DEVOPS_ENGINEER') {
        if (lowerInput.includes('ticket') || lowerInput.includes('bug') || lowerInput.includes('jira')) {
          actionType = "WRITE_JIRA";
          responseContent = "I've drafted a Jira ticket for this issue based on the logs.";
          attachment = {
            type: 'TICKET',
            data: { title: 'Auth Service Timeout in Prod', assignee: 'Sarah Chen', priority: 'High' }
          };
        } else if (lowerInput.includes('code') || lowerInput.includes('grep') || lowerInput.includes('function')) {
          actionType = "READ_CODEBASE";
          responseContent = "Found the relevant snippet in `auth-service/src/main.js`.";
          attachment = {
            type: 'CODE',
            data: { file: 'auth-service.js', snippet: MOCK_DOCS.code }
          };
        }
      }

      // --- LOGIC: HR PERSONA ---
      if (activePersona.role === 'HR_DIRECTOR') {
        if (lowerInput.includes('policy') || lowerInput.includes('pto')) {
          actionType = "READ_POLICY_DOCS";
          responseContent = "According to the 2024 Employee Handbook:";
          attachment = {
            type: 'TICKET', // Reusing Ticket style for simplicity or generic card
            data: { title: 'PTO Policy Summary', assignee: 'HR Dept', priority: 'Info' } // Just a placeholder
          };
           // Override specifically for text
           responseContent = MOCK_DOCS.policy;
        } else if (lowerInput.includes('interview') || lowerInput.includes('schedule')) {
          actionType = "CALENDAR_WRITE";
          responseContent = "I found these available slots for the candidate interview.";
          attachment = {
            type: 'CALENDAR',
            data: { slots: ['Tue 10:00 AM', 'Tue 2:00 PM', 'Wed 11:30 AM'] }
          };
        }
      }

      // --- LOGIC: C-SUITE PERSONA ---
      if (activePersona.role === 'CHIEF_STRATEGY_OFFICER') {
        if (lowerInput.includes('revenue') || lowerInput.includes('financial')) {
          actionType = "READ_FINANCIALS";
          responseContent = MOCK_DOCS.financials;
        } else if (lowerInput.includes('project') || lowerInput.includes('timeline')) {
          actionType = "READ_STRATEGY";
          responseContent = "Here is the high-level roadmap for Project Alpha.";
          attachment = {
            type: 'GANTT',
            data: { tasks: [{name: 'Q1 Planning', progress: 100}, {name: 'Q2 Execution', progress: 45}, {name: 'Q3 Launch', progress: 0}] }
          };
        }
      }

      // --- IAM CHECK SIMULATION ---
      // If the user asks for something their role doesn't support
      if (
        (lowerInput.includes('code') && activePersona.role !== 'SR_DEVOPS_ENGINEER') ||
        (lowerInput.includes('financial') && activePersona.role !== 'CHIEF_STRATEGY_OFFICER')
      ) {
        status = "DENIED";
        responseContent = `Access Denied: Your IAM Role [${activePersona.role}] does not have permission to access this resource. This attempt has been logged.`;
        attachment = null;
      }

      const agentMsg = {
        type: 'agent',
        content: responseContent,
        attachment: attachment,
        iamRole: activePersona.role,
        id: Date.now() + 1
      };

      setMessages(prev => [...prev, agentMsg]);
      setIsTyping(false);
      addAuditLog(actionType, status, `Generated response for user input: "${userMsg.content.substring(0, 20)}..."`);

    }, 1200);
  };

  return (
    <div className="flex h-screen bg-slate-50 dark:bg-slate-900 font-sans text-slate-900 dark:text-slate-100 overflow-hidden">
      
      {/* SIDEBAR (Navigation) */}
      <aside className="w-64 bg-slate-900 text-slate-300 flex flex-col hidden md:flex border-r border-slate-800">
        <div className="p-6 flex items-center gap-3 text-white">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
            <Layout size={18} />
          </div>
          <span className="font-bold text-lg tracking-tight">CorpPortal</span>
        </div>
        
        <nav className="flex-1 px-4 space-y-2 mt-4">
          <div className="px-2 text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Main</div>
          <button className="flex items-center gap-3 w-full p-2 rounded hover:bg-slate-800 text-white bg-slate-800/50">
            <PieChart size={18} /> Dashboard
          </button>
          <button className="flex items-center gap-3 w-full p-2 rounded hover:bg-slate-800">
            <Briefcase size={18} /> Projects
          </button>
          <button className="flex items-center gap-3 w-full p-2 rounded hover:bg-slate-800">
            <Users size={18} /> Directory
          </button>
          
          <div className="px-2 text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2 mt-6">Resources</div>
          <button className="flex items-center gap-3 w-full p-2 rounded hover:bg-slate-800">
            <FileText size={18} /> Documents
          </button>
          <button className="flex items-center gap-3 w-full p-2 rounded hover:bg-slate-800">
            <Server size={18} /> Infrastructure
          </button>
        </nav>

        {/* Persona Switcher in Sidebar Footer */}
        <div className="p-4 bg-slate-950 border-t border-slate-800">
          <p className="text-xs text-slate-500 mb-2 uppercase font-semibold">Simulate Persona</p>
          <div className="flex gap-2 justify-between">
            {Object.values(PERSONAS).map(p => (
              <button
                key={p.id}
                onClick={() => setActivePersona(p)}
                className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
                  activePersona.id === p.id 
                    ? 'bg-blue-500 text-white ring-2 ring-blue-500 ring-offset-2 ring-offset-slate-900 scale-110' 
                    : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
                }`}
                title={p.role}
              >
                {p.role.substring(0, 2)}
              </button>
            ))}
          </div>
          <div className="mt-3 text-xs text-slate-400 flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${activePersona.id === PERSONAS.IT.id ? 'bg-emerald-500' : activePersona.id === PERSONAS.HR.id ? 'bg-rose-500' : 'bg-indigo-500'}`}></div>
            {activePersona.name}
          </div>
        </div>
      </aside>

      {/* MAIN CONTENT AREA */}
      <main className="flex-1 flex flex-col relative overflow-hidden">
        
        {/* Header */}
        <header className="h-16 bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between px-6 shadow-sm z-10">
          <div className="flex items-center gap-4">
            <h1 className="text-xl font-semibold text-slate-800 dark:text-white">{activePersona.context} Dashboard</h1>
            <span className="px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-xs text-slate-500 border border-slate-200 dark:border-slate-700">
              {new Date().toLocaleDateString()}
            </span>
          </div>
          <div className="flex items-center gap-4">
            <button 
              onClick={() => setShowLogs(!showLogs)}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-sm border transition-colors ${
                showLogs 
                ? 'bg-amber-50 border-amber-200 text-amber-700 dark:bg-amber-900/20 dark:border-amber-800 dark:text-amber-400' 
                : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50 dark:bg-slate-800 dark:border-slate-700 dark:text-slate-300'
              }`}
            >
              <Eye size={16} />
              {showLogs ? 'Hide IAM Traces' : 'Show IAM Traces'}
            </button>
            <div className="w-8 h-8 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
               <img src={`https://api.dicebear.com/7.x/initials/svg?seed=${activePersona.name}`} alt="Avatar" />
            </div>
          </div>
        </header>

        {/* Dashboard Grid Content (Changes based on Persona) */}
        <div className="flex-1 overflow-y-auto p-6 bg-slate-50 dark:bg-black/20">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
            {activePersona.id === PERSONAS.IT.id && (
              <>
                <DashboardWidget title="Active Incidents" value="12" trend="+2" icon={AlertTriangle} color="bg-red-500" />
                <DashboardWidget title="System Uptime" value="99.9%" trend="+0.1%" icon={Server} color="bg-emerald-500" />
                <DashboardWidget title="Open PRs" value="34" trend="-5" icon={Code} color="bg-blue-500" />
              </>
            )}
            {activePersona.id === PERSONAS.HR.id && (
              <>
                <DashboardWidget title="Open Roles" value="8" trend="+1" icon={Users} color="bg-rose-500" />
                <DashboardWidget title="Onboarding" value="3" trend="0" icon={UserPlusIcon} color="bg-purple-500" />
                <DashboardWidget title="eNPS Score" value="42" trend="+4" icon={HeartIcon} color="bg-pink-500" />
              </>
            )}
            {activePersona.id === PERSONAS.CSUITE.id && (
              <>
                <DashboardWidget title="Q3 Revenue" value="$4.2M" trend="+15%" icon={DollarIcon} color="bg-indigo-500" />
                <DashboardWidget title="Burn Rate" value="$180k" trend="-2%" icon={FlameIcon} color="bg-orange-500" />
                <DashboardWidget title="Market Share" value="12%" trend="+1%" icon={PieChart} color="bg-cyan-500" />
              </>
            )}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-96">
            <div className="lg:col-span-2 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6 shadow-sm">
              <h3 className="font-semibold mb-4">Recent Activity</h3>
              <div className="space-y-4">
                {[1,2,3].map(i => (
                  <div key={i} className="flex items-center gap-4 pb-4 border-b border-slate-100 dark:border-slate-700 last:border-0 last:pb-0">
                    <div className="w-10 h-10 rounded bg-slate-100 dark:bg-slate-700 flex items-center justify-center text-slate-400">
                      <FileText size={20} />
                    </div>
                    <div>
                      <p className="text-sm font-medium">Document updated by {activePersona.id === PERSONAS.IT.id ? 'System Admin' : 'Legal Team'}</p>
                      <p className="text-xs text-slate-500">2 hours ago</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6 shadow-sm">
              <h3 className="font-semibold mb-4">Quick Links</h3>
              <div className="space-y-2">
                 <button className="w-full text-left px-3 py-2 rounded hover:bg-slate-50 dark:hover:bg-slate-700 text-sm flex justify-between group">
                   <span>Company Policies</span>
                   <ChevronRight size={16} className="text-slate-400 group-hover:text-blue-500" />
                 </button>
                 <button className="w-full text-left px-3 py-2 rounded hover:bg-slate-50 dark:hover:bg-slate-700 text-sm flex justify-between group">
                   <span>Submit Expense</span>
                   <ChevronRight size={16} className="text-slate-400 group-hover:text-blue-500" />
                 </button>
                 <button className="w-full text-left px-3 py-2 rounded hover:bg-slate-50 dark:hover:bg-slate-700 text-sm flex justify-between group">
                   <span>IT Helpdesk</span>
                   <ChevronRight size={16} className="text-slate-400 group-hover:text-blue-500" />
                 </button>
              </div>
            </div>
          </div>
        </div>

        {/* IAM AUDIT LOG OVERLAY (Slide up) */}
        {showLogs && (
          <div className="absolute bottom-0 left-0 right-0 h-64 bg-slate-900 border-t border-slate-700 shadow-[0_-10px_40px_rgba(0,0,0,0.5)] z-20 transition-transform">
            <div className="flex items-center justify-between px-4 py-2 bg-slate-950 border-b border-slate-800">
              <div className="flex items-center gap-2 text-amber-500 font-mono text-xs font-bold uppercase tracking-wider">
                <Shield size={14} /> Live IAM Trace Stream
              </div>
              <button onClick={() => setShowLogs(false)} className="text-slate-500 hover:text-white">
                <Minimize2 size={14} />
              </button>
            </div>
            <div className="overflow-y-auto h-full p-4 font-mono text-xs space-y-2 pb-12">
              {auditLogs.length === 0 && <div className="text-slate-600 italic">No actions recorded yet. Interact with the Copilot.</div>}
              {auditLogs.map((log) => (
                <div key={log.id} className="flex gap-4 border-b border-slate-800 pb-2 mb-2 last:border-0">
                  <div className="text-slate-500 min-w-[120px]">{log.timestamp.split('T')[1].split('.')[0]}</div>
                  <div className={`font-bold ${log.status === 'DENIED' ? 'text-red-400' : 'text-emerald-400'}`}>
                    [{log.status}]
                  </div>
                  <div className="text-blue-400 min-w-[150px]">{log.action}</div>
                  <div className="text-slate-300 flex-1 truncate">
                    <span className="text-amber-600 mr-2">role:{log.iamRole}</span>
                    {log.details}
                  </div>
                  <div className="text-slate-600 text-[10px]">{log.traceId}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>

      {/* COPILOT WIDGET (Persistent Overlay) */}
      <div className={`fixed bottom-6 right-6 z-50 flex flex-col items-end transition-all duration-300 ${isCopilotOpen ? 'w-[400px]' : 'w-auto'}`}>
        
        {isCopilotOpen && (
          <div className="mb-4 w-full h-[600px] bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-700 flex flex-col overflow-hidden animate-in slide-in-from-bottom-10 fade-in duration-200">
            {/* Copilot Header */}
            <div className="p-4 border-b border-slate-100 dark:border-slate-800 flex justify-between items-center bg-gradient-to-r from-slate-50 to-white dark:from-slate-900 dark:to-slate-800">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-white shadow-lg shadow-blue-500/30">
                  <Terminal size={16} />
                </div>
                <div>
                  <h2 className="font-bold text-sm">Enterprise Assistant</h2>
                  <div className="flex items-center gap-1 text-[10px] text-green-500 font-medium">
                    <span className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse"></span>
                    Online • {activePersona.role.replace('_', ' ')}
                  </div>
                </div>
              </div>
              <button onClick={() => setIsCopilotOpen(false)} className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200">
                <X size={18} />
              </button>
            </div>

            {/* Chat Area */}
            <div className="flex-1 overflow-y-auto p-4 bg-slate-50/50 dark:bg-black/20" ref={scrollRef}>
              {messages.map(msg => (
                <ChatMessage key={msg.id} msg={msg} />
              ))}
              {isTyping && (
                <div className="flex items-center gap-2 text-slate-400 text-xs ml-2">
                  <div className="w-2 h-2 bg-slate-300 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-slate-300 rounded-full animate-bounce delay-75"></div>
                  <div className="w-2 h-2 bg-slate-300 rounded-full animate-bounce delay-150"></div>
                  <span>Processing with IAM context...</span>
                </div>
              )}
            </div>

            {/* Suggestions */}
            <div className="px-4 py-2 border-t border-slate-100 dark:border-slate-800 flex gap-2 overflow-x-auto no-scrollbar">
              {activePersona.suggested.map((sug, i) => (
                <button 
                  key={i} 
                  onClick={() => setInput(sug)}
                  className="whitespace-nowrap px-3 py-1 bg-slate-100 dark:bg-slate-800 hover:bg-blue-50 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300 text-xs rounded-full border border-slate-200 dark:border-slate-700 transition-colors"
                >
                  {sug}
                </button>
              ))}
            </div>

            {/* Input Area */}
            <div className="p-4 bg-white dark:bg-slate-900">
              <IAMBadge role={activePersona.role} permissions={activePersona.permissions} />
              <div className="mt-2 flex gap-2 items-center bg-slate-50 dark:bg-slate-800 p-2 rounded-xl border border-slate-200 dark:border-slate-700 focus-within:ring-2 focus-within:ring-blue-500/20 transition-all">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                  placeholder="Ask about tickets, metrics, or schedule..."
                  className="flex-1 bg-transparent border-none outline-none text-sm px-2"
                />
                <button 
                  onClick={handleSend}
                  disabled={!input.trim()}
                  className="p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-transform active:scale-95"
                >
                  <Send size={16} />
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Trigger Button */}
        {!isCopilotOpen && (
          <button
            onClick={() => setIsCopilotOpen(true)}
            className="group flex items-center gap-3 bg-blue-600 hover:bg-blue-700 text-white p-4 rounded-full shadow-lg shadow-blue-600/30 transition-all hover:scale-105 active:scale-95"
          >
            <div className="relative">
              <MessageSquare size={24} />
              <span className="absolute -top-1 -right-1 flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500 border border-white"></span>
              </span>
            </div>
            <span className="font-semibold max-w-0 overflow-hidden group-hover:max-w-xs transition-all duration-300 whitespace-nowrap">
              Open Copilot
            </span>
          </button>
        )}
      </div>

    </div>
  );
}

// Icons for the dashboard widgets to prevent referencing undefined variables
const UserPlusIcon = ({ className }) => <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" /></svg>;
const HeartIcon = ({ className }) => <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" /></svg>;
const DollarIcon = ({ className }) => <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>;
const FlameIcon = ({ className }) => <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 18.657A8 8 0 016.343 7.343S7 9 9 10c0-2 .5-5 2.986-7C14 5 16.09 5.777 17.656 7.343A7.975 7.975 0 0120 13a7.975 7.975 0 01-2.343 5.657z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.879 16.121A3 3 0 1012.015 11L11 14H9c0 .768.293 1.536.879 2.121z" /></svg>;