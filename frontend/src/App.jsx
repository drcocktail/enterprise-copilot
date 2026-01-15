import React, { useState, useEffect, useRef } from 'react';
import {
  MessageSquare, Users, Briefcase, FileText,
  X, Send, AlertTriangle, ChevronRight,
  PieChart, Server, Code, Activity, Eye,
  Loader2, CheckCircle, XCircle, Sparkles,
  LayoutDashboard, FolderOpen, Cpu, Bot, ArrowRight
} from 'lucide-react';

import { chatAPI, auditAPI, personasAPI, healthAPI } from './services/api';
import { IAMBadge } from './components/IAMBadge';
import { ChatMessage } from './components/ChatMessage';
import { DashboardWidget } from './components/DashboardWidget';
import { AuditLogPanel } from './components/AuditLogPanel';
import { DocumentsPanel } from './components/DocumentsPanel';

const DEFAULT_PERSONAS = {
  CSUITE: {
    id: 'c_suite_01',
    role: 'CHIEF_STRATEGY_OFFICER',
    name: 'Eleanor Vance',
    permissions: ['READ_FINANCIALS', 'READ_HR_AGGREGATE', 'WRITE_STRATEGY', 'CALENDAR_WRITE'],
    color: 'bg-violet-100 text-violet-700',
    accent: 'bg-violet-500',
    context: 'Strategy & Finance',
    emoji: '📊',
    suggested: ['Summarize Q3 Revenue', 'Show Project Timeline', 'Schedule Board Sync']
  },
  HR: {
    id: 'hr_lead_04',
    role: 'HR_DIRECTOR',
    name: 'Marcus Thorne',
    permissions: ['READ_EMPLOYEE_PII', 'WRITE_POLICY', 'CALENDAR_WRITE', 'SLACK_BROADCAST'],
    color: 'bg-rose-100 text-rose-700',
    accent: 'bg-rose-500',
    context: 'People & Culture',
    emoji: '👥',
    suggested: ['Draft Onboarding Policy', 'Find Interview Slots', 'Analyze Attrition']
  },
  IT: {
    id: 'dev_ops_99',
    role: 'SR_DEVOPS_ENGINEER',
    name: 'Sarah Chen',
    permissions: ['READ_CODEBASE', 'WRITE_JIRA', 'RESTART_SERVICES', 'READ_LOGS'],
    color: 'bg-emerald-100 text-emerald-700',
    accent: 'bg-emerald-500',
    context: 'Infrastructure & Ops',
    emoji: '⚙️',
    suggested: ['Grep error in auth-service', 'Create Jira Ticket', 'Check Server Health']
  }
};

export default function App() {
  const [activePersona, setActivePersona] = useState(DEFAULT_PERSONAS.CSUITE);
  const [isCopilotOpen, setIsCopilotOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [auditLogs, setAuditLogs] = useState([]);
  const [showLogs, setShowLogs] = useState(false);
  const [personas, setPersonas] = useState(DEFAULT_PERSONAS);
  const [healthStatus, setHealthStatus] = useState({ status: 'checking' });
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('dashboard'); // 'dashboard', 'documents', 'projects', 'team'

  const scrollRef = useRef(null);
  const wsRef = useRef(null);

  useEffect(() => {
    loadPersonas();
    checkHealth();
    const healthInterval = setInterval(checkHealth, 30000);
    return () => clearInterval(healthInterval);
  }, []);

  useEffect(() => {
    if (showLogs && !wsRef.current) {
      try {
        wsRef.current = auditAPI.connectStream(
          (log) => setAuditLogs(prev => [log, ...prev].slice(0, 50)),
          (error) => console.error('Audit stream error:', error)
        );
      } catch (e) {
        console.error('Failed to connect to audit stream:', e);
      }
    }
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [showLogs]);

  useEffect(() => {
    setMessages([{
      type: 'agent',
      content: `Hi ${activePersona.name.split(' ')[0]}! 👋 I'm here to help with ${activePersona.context}. What can I do for you today?`,
      iamRole: activePersona.role,
      id: Date.now()
    }]);
    setError(null);
  }, [activePersona]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isTyping]);

  const loadPersonas = async () => {
    try {
      const data = await personasAPI.getAll();
      const personasMap = {};
      data.forEach(p => {
        const key = p.role.includes('CHIEF') ? 'CSUITE' : p.role.includes('HR') ? 'HR' : 'IT';
        personasMap[key] = {
          ...p,
          color: DEFAULT_PERSONAS[key].color,
          accent: DEFAULT_PERSONAS[key].accent,
          context: p.description,
          emoji: DEFAULT_PERSONAS[key].emoji,
          suggested: DEFAULT_PERSONAS[key].suggested
        };
      });
      setPersonas(personasMap);
    } catch (e) {
      console.error('Failed to load personas:', e);
    }
  };

  const checkHealth = async () => {
    try {
      const health = await healthAPI.check();
      setHealthStatus(health);
    } catch (e) {
      setHealthStatus({ status: 'error', services: {} });
    }
  };

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMsg = { type: 'user', content: input, id: Date.now() };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsTyping(true);
    setError(null);

    try {
      const response = await chatAPI.sendQuery(userMsg.content, activePersona.role);

      const agentMsg = {
        type: 'agent',
        content: response.content,
        attachment: response.attachment,
        iamRole: response.iam_role,
        sources: response.sources,
        traceId: response.trace_id,
        id: Date.now() + 1
      };

      setMessages(prev => [...prev, agentMsg]);
    } catch (err) {
      console.error('Chat error:', err);

      let errorMessage = "Oops! Something went wrong. Please try again.";
      if (err.type === 'IAM_DENIAL') {
        errorMessage = `Sorry, you don't have access to that information.`;
      } else if (err.message) {
        errorMessage = err.message;
      }

      const errorMsg = {
        type: 'agent',
        content: errorMessage,
        iamRole: activePersona.role,
        isError: true,
        id: Date.now() + 1
      };

      setMessages(prev => [...prev, errorMsg]);
      setError(err.message);
    } finally {
      setIsTyping(false);
    }
  };

  const loadAuditLogs = async () => {
    try {
      const logs = await auditAPI.getLogs(50, activePersona.role);
      setAuditLogs(logs);
    } catch (e) {
      console.error('Failed to load audit logs:', e);
    }
  };

  useEffect(() => {
    if (showLogs) loadAuditLogs();
  }, [showLogs]);

  return (
    <div className="flex h-screen bg-stone-50 font-sans text-stone-800 overflow-hidden">

      {/* === LEFT SIDEBAR === */}
      <aside className="w-[280px] bg-white border-r border-stone-200 flex flex-col shrink-0">

        {/* Logo */}
        <div className="h-16 px-6 flex items-center gap-3 border-b border-stone-100">
          <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-violet-200">
            <Sparkles size={20} className="text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-stone-800">Copilot</h1>
            <p className="text-xs text-stone-400">Enterprise Assistant</p>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-1">
          <p className="text-xs font-semibold text-stone-400 uppercase tracking-wider px-3 mb-3">Menu</p>

          <button
            onClick={() => setActiveTab('dashboard')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-colors ${activeTab === 'dashboard' ? 'bg-violet-50 text-violet-700' : 'hover:bg-stone-50 text-stone-500'
              }`}
          >
            <LayoutDashboard size={18} />
            Dashboard
          </button>
          <button
            onClick={() => setActiveTab('projects')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-colors ${activeTab === 'projects' ? 'bg-violet-50 text-violet-700' : 'hover:bg-stone-50 text-stone-500'
              }`}
          >
            <Briefcase size={18} />
            Projects
          </button>
          <button
            onClick={() => setActiveTab('team')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-colors ${activeTab === 'team' ? 'bg-violet-50 text-violet-700' : 'hover:bg-stone-50 text-stone-500'
              }`}
          >
            <Users size={18} />
            Team
          </button>
          <button
            onClick={() => setActiveTab('documents')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-colors ${activeTab === 'documents' ? 'bg-violet-50 text-violet-700' : 'hover:bg-stone-50 text-stone-500'
              }`}
          >
            <FolderOpen size={18} />
            Documents
          </button>
        </nav>

        {/* Role Switcher */}
        <div className="p-4 border-t border-stone-100">
          <p className="text-xs font-semibold text-stone-400 uppercase tracking-wider mb-3">Switch Role</p>

          <div className="space-y-2">
            {Object.values(personas).map(p => (
              <button
                key={p.id}
                onClick={() => setActivePersona(p)}
                className={`w-full flex items-center gap-3 p-3 rounded-xl transition-all ${activePersona.id === p.id
                  ? 'bg-stone-100 shadow-soft'
                  : 'hover:bg-stone-50'
                  }`}
              >
                <div className={`w-10 h-10 rounded-xl ${p.color} flex items-center justify-center text-lg`}>
                  {p.emoji}
                </div>
                <div className="flex-1 text-left">
                  <p className="text-sm font-semibold text-stone-700">{p.name}</p>
                  <p className="text-xs text-stone-400">{p.context}</p>
                </div>
                {activePersona.id === p.id && (
                  <div className="w-2 h-2 rounded-full bg-emerald-500" />
                )}
              </button>
            ))}
          </div>

          {/* Status */}
          <div className="mt-4 pt-4 border-t border-stone-100">
            <div className="flex items-center gap-2 text-xs">
              {healthStatus.status === 'healthy' ? (
                <>
                  <CheckCircle size={14} className="text-emerald-500" />
                  <span className="text-emerald-600 font-medium">All systems online</span>
                </>
              ) : healthStatus.status === 'checking' ? (
                <>
                  <Loader2 size={14} className="animate-spin text-amber-500" />
                  <span className="text-amber-600">Checking...</span>
                </>
              ) : (
                <>
                  <XCircle size={14} className="text-red-500" />
                  <span className="text-red-600 font-medium">Issues detected</span>
                </>
              )}
            </div>
          </div>
        </div>
      </aside>

      {/* === MAIN CONTENT === */}
      <div className="flex-1 flex overflow-hidden">

        <main className={`flex flex-col h-full overflow-hidden transition-all duration-500 ease-out ${isCopilotOpen ? 'w-[55%]' : 'w-full'}`}>

          {/* Header */}
          <header className="h-16 bg-white border-b border-stone-100 flex items-center justify-between px-6 shrink-0 shadow-soft">
            <div className="flex items-center gap-4">
              <h2 className="text-xl font-bold text-stone-800">{activePersona.context}</h2>
              <span className="px-3 py-1 rounded-full bg-stone-100 text-xs text-stone-500 font-medium">
                {new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' })}
              </span>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={() => setShowLogs(!showLogs)}
                className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all ${showLogs
                  ? 'bg-amber-100 text-amber-700'
                  : 'bg-stone-100 text-stone-600 hover:bg-stone-200'
                  }`}
              >
                <Eye size={16} />
                {showLogs ? 'Hide Logs' : 'View Logs'}
              </button>

              <div className="w-10 h-10 rounded-xl overflow-hidden bg-stone-100">
                <img
                  src={`https://api.dicebear.com/7.x/notionists-neutral/svg?seed=${activePersona.name}&backgroundColor=f5f5f4`}
                  alt="Avatar"
                  className="w-full h-full"
                />
              </div>
            </div>
          </header>

          {/* Main Content - Dynamic based on activeTab */}
          {activeTab === 'dashboard' && (
            <div className="flex-1 overflow-y-auto p-6 bg-stone-50">

              {/* Stats */}
              <div className="grid grid-cols-3 gap-5 mb-6">
                {activePersona.id === personas.IT?.id && (
                  <>
                    <DashboardWidget title="Active Incidents" value="12" trend="+2" icon={AlertTriangle} color="bg-red-500" />
                    <DashboardWidget title="System Uptime" value="99.9%" trend="+0.1%" icon={Server} color="bg-emerald-500" />
                    <DashboardWidget title="Open PRs" value="34" trend="-5" icon={Code} color="bg-blue-500" />
                  </>
                )}
                {activePersona.id === personas.HR?.id && (
                  <>
                    <DashboardWidget title="Open Roles" value="8" trend="+1" icon={Users} color="bg-rose-500" />
                    <DashboardWidget title="Onboarding" value="3" trend="0" icon={Users} color="bg-purple-500" />
                    <DashboardWidget title="eNPS Score" value="42" trend="+4" icon={Activity} color="bg-pink-500" />
                  </>
                )}
                {activePersona.id === personas.CSUITE?.id && (
                  <>
                    <DashboardWidget title="Q3 Revenue" value="$4.2M" trend="+15%" icon={PieChart} color="bg-violet-500" />
                    <DashboardWidget title="Burn Rate" value="$180k" trend="-2%" icon={Activity} color="bg-orange-500" />
                    <DashboardWidget title="Market Share" value="12%" trend="+1%" icon={PieChart} color="bg-cyan-500" />
                  </>
                )}
              </div>

              {/* Cards */}
              <div className="grid grid-cols-2 gap-5">
                <div className="bg-white rounded-2xl p-6 shadow-soft">
                  <h3 className="text-base font-bold text-stone-700 mb-4">Recent Activity</h3>
                  <div className="space-y-4">
                    {[
                      { text: 'Budget report updated', time: '2h ago' },
                      { text: 'New team member onboarded', time: '4h ago' },
                      { text: 'Q3 projections reviewed', time: 'Yesterday' }
                    ].map((item, i) => (
                      <div key={i} className="flex items-center gap-4 pb-4 border-b border-stone-100 last:border-0 last:pb-0">
                        <div className="w-10 h-10 rounded-xl bg-stone-100 flex items-center justify-center text-stone-400">
                          <FileText size={18} />
                        </div>
                        <div className="flex-1">
                          <p className="text-sm font-medium text-stone-700">{item.text}</p>
                          <p className="text-xs text-stone-400">{item.time}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="bg-white rounded-2xl p-6 shadow-soft">
                  <h3 className="text-base font-bold text-stone-700 mb-4">Quick Actions</h3>
                  <div className="space-y-2">
                    {['View Reports', 'Schedule Meeting', 'Submit Request'].map(label => (
                      <button key={label} className="w-full flex items-center justify-between px-4 py-3 rounded-xl hover:bg-stone-50 transition-colors group">
                        <span className="text-sm text-stone-600">{label}</span>
                        <ArrowRight size={16} className="text-stone-300 group-hover:text-violet-500 transition-colors" />
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'documents' && (
            <DocumentsPanel activePersona={activePersona} />
          )}

          {activeTab === 'projects' && (
            <div className="flex-1 overflow-y-auto p-6 bg-stone-50 flex items-center justify-center">
              <div className="text-center text-stone-400">
                <Briefcase size={48} className="mx-auto mb-3 opacity-50" />
                <p className="font-medium">Projects</p>
                <p className="text-sm mt-1">Coming soon</p>
              </div>
            </div>
          )}

          {activeTab === 'team' && (
            <div className="flex-1 overflow-y-auto p-6 bg-stone-50 flex items-center justify-center">
              <div className="text-center text-stone-400">
                <Users size={48} className="mx-auto mb-3 opacity-50" />
                <p className="font-medium">Team</p>
                <p className="text-sm mt-1">Coming soon</p>
              </div>
            </div>
          )}

          {showLogs && <AuditLogPanel logs={auditLogs} onClose={() => setShowLogs(false)} />}

          {/* Copilot Button */}
          {!isCopilotOpen && (
            <button
              onClick={() => setIsCopilotOpen(true)}
              className="absolute bottom-6 right-6 z-50 flex items-center gap-3 px-6 py-4 rounded-full bg-gradient-to-r from-violet-500 to-indigo-600 text-white font-semibold text-sm shadow-lg shadow-violet-300 hover:shadow-violet-400 transition-all hover:scale-[1.02] active:scale-[0.98]"
            >
              <Bot size={20} />
              <span>Ask Copilot</span>
            </button>
          )}
        </main>

        {/* === COPILOT PANEL === */}
        <div className={`bg-white border-l border-stone-200 flex flex-col transition-all duration-500 ease-out ${isCopilotOpen ? 'w-[45%]' : 'w-0 overflow-hidden'}`}>
          {isCopilotOpen && (
            <>
              {/* Header */}
              <div className="h-16 px-6 border-b border-stone-100 flex items-center justify-between shrink-0">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-violet-200">
                    <Bot size={18} className="text-white" />
                  </div>
                  <div>
                    <h2 className="text-base font-bold text-stone-800">Copilot</h2>
                    <p className="text-xs text-emerald-500 font-medium flex items-center gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                      Ready to help
                    </p>
                  </div>
                </div>
                <button onClick={() => setIsCopilotOpen(false)} className="p-2 rounded-xl hover:bg-stone-100 text-stone-400 hover:text-stone-600 transition-all">
                  <X size={20} />
                </button>
              </div>

              {/* Messages */}
              <div className="flex-1 overflow-y-auto p-6 space-y-4 bg-stone-50" ref={scrollRef}>
                {messages.map(msg => (
                  <ChatMessage key={msg.id} msg={msg} />
                ))}
                {isTyping && (
                  <div className="flex items-center gap-3 text-stone-400 text-sm">
                    <div className="w-8 h-8 rounded-xl bg-white flex items-center justify-center shadow-soft">
                      <Loader2 size={14} className="animate-spin text-violet-500" />
                    </div>
                    <span>Thinking...</span>
                  </div>
                )}
              </div>

              {/* Input */}
              <div className="p-4 border-t border-stone-100 bg-white">

                {messages.length <= 2 && (
                  <div className="flex flex-wrap gap-2 mb-4">
                    {activePersona.suggested?.map((sug, i) => (
                      <button
                        key={i}
                        onClick={() => setInput(sug)}
                        className="px-4 py-2 rounded-full bg-stone-100 hover:bg-violet-100 text-sm text-stone-600 hover:text-violet-700 transition-colors"
                      >
                        {sug}
                      </button>
                    ))}
                  </div>
                )}

                <IAMBadge role={activePersona.role} permissions={activePersona.permissions} />

                <div className="mt-3 flex items-end gap-3 p-3 rounded-2xl bg-stone-50 border border-stone-200 focus-within:border-violet-300 focus-within:ring-2 focus-within:ring-violet-100 transition-all">
                  <textarea
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        handleSend();
                      }
                    }}
                    placeholder="Ask me anything..."
                    className="flex-1 bg-transparent border-none outline-none text-sm text-stone-700 placeholder:text-stone-400 resize-none min-h-[48px] max-h-32"
                    disabled={isTyping}
                  />
                  <button
                    onClick={handleSend}
                    disabled={!input.trim() || isTyping}
                    className={`p-3 rounded-xl transition-all ${input.trim()
                      ? 'bg-gradient-to-r from-violet-500 to-indigo-600 text-white shadow-lg shadow-violet-200 hover:shadow-violet-300'
                      : 'bg-stone-200 text-stone-400'
                      } disabled:opacity-50`}
                  >
                    {isTyping ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
