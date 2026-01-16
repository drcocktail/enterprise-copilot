import React, { useState, useRef, useEffect } from 'react';
import { Menu, Shield, Send, Terminal, Activity, ChevronDown, ChevronRight, Loader2, Sparkles } from 'lucide-react';
import ActionCard from '../components/ActionCard';
import ThinkingStep from '../components/ThinkingStep';
import api from '../services/api';
import { motion, AnimatePresence } from 'framer-motion';

const ThinkingPanel = ({ thoughts }) => {
    const [isOpen, setIsOpen] = useState(false);

    // Auto-open if there are active processing steps
    useEffect(() => {
        if (thoughts.some(t => t.state === 'processing')) {
            setIsOpen(true);
        }
    }, [thoughts]);

    if (!thoughts || thoughts.length === 0) return null;

    return (
        <div className="mb-3 rounded-lg overflow-hidden border border-blue-900/30 bg-[#131c2e]">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="w-full flex items-center gap-2 px-4 py-2 bg-[#1a2438] hover:bg-[#1e293b] transition-colors text-left"
            >
                <div className={`p-1 rounded bg-blue-500/10 text-blue-400`}>
                    <Activity size={14} />
                </div>
                <span className="text-xs font-bold text-slate-300 uppercase tracking-wider flex-1">
                    Reasoning Trace
                </span>
                {isOpen ? <ChevronDown size={14} className="text-slate-500" /> : <ChevronRight size={14} className="text-slate-500" />}
            </button>

            <AnimatePresence>
                {isOpen && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        className="border-t border-blue-900/20"
                    >
                        <div className="p-3 space-y-1 bg-[#0f1522]">
                            {thoughts.map((t, i) => <ThinkingStep key={i} text={t.text} state={t.state} />)}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
};

const ChatView = ({ isSidebarOpen, setSidebarOpen }) => {
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [messages, setMessages] = useState([]);
    const scrollRef = useRef(null);

    const scrollToBottom = () => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const handleSend = async () => {
        if (!input.trim() || isLoading) return;

        const userText = input;
        setInput('');
        setIsLoading(true);

        const userMsg = {
            id: Date.now(),
            role: 'user',
            content: userText,
            timestamp: new Date().toLocaleTimeString()
        };
        setMessages(prev => [...prev, userMsg]);

        // Placeholder for initial thinking state
        const botMsgId = Date.now() + 1;
        const initialBotMsg = {
            id: botMsgId,
            role: 'assistant',
            thoughts: [
                { text: "Analyzing user intent...", state: "processing" }
            ],
            content: "",
            timestamp: new Date().toLocaleTimeString()
        };
        setMessages(prev => [...prev, initialBotMsg]);

        try {
            // Simulate incremental thinking updates (since backend doesn't stream yet)
            setTimeout(() => {
                setMessages(prev => prev.map(m => m.id === botMsgId ? {
                    ...m,
                    thoughts: [
                        { text: "Analyzing user intent...", state: "done" },
                        { text: "Checking permissions...", state: "processing" }
                    ]
                } : m));
            }, 800);

            const res = await api.chatAPI.sendQuery(userText, 'senior_engineer');

            setMessages(prev => prev.map(m => m.id === botMsgId ? {
                ...m,
                thoughts: [
                    { text: "Analyzing user intent...", state: "done" },
                    { text: "Checking permissions...", state: "done" },
                    { text: "Generatng response...", state: "done" }
                ], // We can enrich this if backend returns traces
                content: res.content || res.message, // adjust based on actual API response
                action: res.attachment ? res.attachment : null // if backend returns 'attachment'
            } : m));

        } catch (e) {
            console.error(e);
            setMessages(prev => prev.map(m => m.id === botMsgId ? {
                ...m,
                thoughts: [
                    ...m.thoughts.map(t => ({ ...t, state: t.state === 'processing' ? 'error' : t.state })),
                    { text: "Connection failed", state: "error" }
                ],
                content: "I encountered an error connecting to the Nexus backend. Please ensure the services are running."
            } : m));
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <>
            <header className="h-16 border-b border-white/5 bg-[#0f172a]/80 backdrop-blur-md flex items-center justify-between px-6 sticky top-0 z-10">
                <div className="flex items-center space-x-4">
                    <button onClick={() => setSidebarOpen(!isSidebarOpen)} className="lg:hidden text-slate-400 hover:text-white transition-colors">
                        <Menu className="w-5 h-5" />
                    </button>
                    <div className="h-6 w-px bg-white/10 hidden lg:block"></div>
                    <div className="flex items-center text-slate-400 text-sm">
                        <span className="font-medium text-slate-200">Session ID:</span>
                        <span className="ml-2 font-mono text-xs bg-white/5 px-2 py-1 rounded text-slate-400">8f2a-99b1</span>
                    </div>
                </div>
                <div className="flex items-center space-x-3">
                    <div className="flex items-center px-3 py-1.5 bg-blue-500/10 border border-blue-500/20 rounded-full">
                        <div className="w-1.5 h-1.5 bg-blue-500 rounded-full mr-2 animate-pulse"></div>
                        <span className="text-[10px] font-bold text-blue-300 uppercase tracking-wide">Secure Environment</span>
                    </div>
                </div>
            </header>

            <div className="flex-1 overflow-y-auto p-4 md:p-8 space-y-8 scroll-smooth custom-scrollbar" ref={scrollRef}>
                {messages.length === 0 && (
                    <div className="h-full flex flex-col items-center justify-center opacity-50 space-y-6 select-none pointer-events-none">
                        <div className="w-24 h-24 rounded-3xl bg-blue-500/10 flex items-center justify-center border border-blue-500/20 shadow-2xl shadow-blue-500/10">
                            <Sparkles className="text-blue-400" size={48} />
                        </div>
                        <div className="text-center">
                            <h2 className="text-2xl font-bold text-slate-200">Nexus Enterprise</h2>
                            <p className="text-slate-500 mt-2 max-w-sm">
                                Ready to assist with infrastructure, deployments, and security operations.
                            </p>
                        </div>
                    </div>
                )}

                {messages.map((msg) => (
                    <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} group max-w-4xl mx-auto w-full`}>
                        {msg.role === 'assistant' && (
                            <div className="w-8 h-8 rounded bg-gradient-to-b from-blue-600 to-blue-700 flex-shrink-0 mr-4 flex items-center justify-center shadow-lg shadow-blue-900/20 mt-1">
                                <Shield className="w-4 h-4 text-white" />
                            </div>
                        )}
                        <div className={`max-w-2xl w-full ${msg.role === 'user' ? 'order-1' : 'order-2'}`}>
                            {msg.role === 'user' && (
                                <div className="bg-slate-800 text-slate-200 px-5 py-3.5 rounded-2xl rounded-tr-sm border border-white/5 shadow-md ml-auto w-fit">
                                    <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                                </div>
                            )}
                            {msg.role === 'assistant' && (
                                <div className="space-y-3">
                                    <ThinkingPanel thoughts={msg.thoughts} />

                                    {msg.content && (
                                        <div className="text-slate-300 text-sm leading-relaxed whitespace-pre-wrap">
                                            {msg.content}
                                        </div>
                                    )}

                                    {msg.action && <ActionCard {...msg.action} />}
                                </div>
                            )}
                            <div className={`mt-2 text-[10px] text-slate-600 ${msg.role === 'user' ? 'text-right pr-1' : 'pl-1'} opacity-0 group-hover:opacity-100 transition-opacity`}>
                                {msg.timestamp}
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            <div className="p-6 bg-[#0f172a] relative border-t border-slate-800/50">
                <div className="max-w-4xl mx-auto">
                    <div className={`relative flex items-center bg-[#1e293b] rounded-xl border transition-all ${isLoading ? 'border-blue-500/30' : 'border-white/10 shadow-xl focus-within:ring-1 focus-within:ring-blue-500/50'}`}>
                        <div className="pl-4 text-slate-500">
                            {isLoading ? <Loader2 className="w-5 h-5 animate-spin text-blue-400" /> : <Terminal className="w-5 h-5" />}
                        </div>
                        <input
                            type="text"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                            placeholder={isLoading ? "Processing..." : "Type a command or ask a question..."}
                            className="w-full bg-transparent text-slate-200 text-sm py-4 px-4 focus:outline-none placeholder:text-slate-600 disabled:opacity-50"
                            disabled={isLoading}
                        />
                        <div className="pr-2">
                            <button
                                onClick={handleSend}
                                disabled={!input.trim() || isLoading}
                                className="p-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition-colors disabled:opacity-50 disabled:bg-slate-700"
                            >
                                <Send className="w-4 h-4" />
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </>
    );
};

export default ChatView;
