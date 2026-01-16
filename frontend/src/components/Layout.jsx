import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import { motion, AnimatePresence } from 'framer-motion';
import { Terminal, X, Activity, Server, Database, Globe } from 'lucide-react';

const Layout = () => {
    const [isLiveOpsOpen, setIsLiveOpsOpen] = useState(false);

    return (
        <div className="min-h-screen bg-[#0B1120] text-slate-200 font-sans selection:bg-blue-500/30">
            <Sidebar isLiveOpsOpen={isLiveOpsOpen} setIsLiveOpsOpen={setIsLiveOpsOpen} />

            {/* Main Content */}
            <main className={`
        transition-all duration-300 ease-in-out min-h-screen relative
        lg:pl-64
        ${isLiveOpsOpen ? 'pb-80' : ''} 
      `}>
                <div className="p-4 lg:p-8 max-w-7xl mx-auto">
                    <Outlet />
                </div>
            </main>

            {/* Live Ops Console Overlay */}
            <AnimatePresence>
                {isLiveOpsOpen && (
                    <motion.div
                        initial={{ y: '100%' }}
                        animate={{ y: 0 }}
                        exit={{ y: '100%' }}
                        transition={{ type: 'spring', damping: 25, stiffness: 200 }}
                        className="fixed bottom-0 left-0 lg:left-64 right-0 h-80 bg-[#0f172a] border-t border-slate-700/50 shadow-[0_-10px_40px_-10px_rgba(0,0,0,0.5)] z-30 flex flex-col"
                    >
                        {/* Console Header */}
                        <div className="h-10 bg-slate-900 border-b border-slate-700/50 flex items-center justify-between px-4">
                            <div className="flex items-center gap-4">
                                <div className="flex items-center gap-2 text-blue-400">
                                    <Terminal size={14} />
                                    <span className="text-xs font-bold uppercase tracking-wider">Live Ops Console</span>
                                </div>
                                <div className="h-4 w-px bg-slate-700"></div>
                                <div className="flex items-center gap-3 text-xs text-slate-400">
                                    <div className="flex items-center gap-1.5">
                                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_5px_rgba(34,197,94,0.5)]"></span>
                                        US-EAST-1
                                    </div>
                                    <div className="flex items-center gap-1.5">
                                        <Activity size={12} />
                                        Latency: 24ms
                                    </div>
                                </div>
                            </div>
                            <div className="flex items-center gap-2">
                                <button onClick={() => setIsLiveOpsOpen(false)} className="text-slate-500 hover:text-white transition-colors">
                                    <X size={16} />
                                </button>
                            </div>
                        </div>

                        {/* Console Body */}
                        <div className="flex-1 p-0 overflow-hidden flex">
                            {/* Metrics Sidebar */}
                            <div className="w-48 bg-slate-900/50 border-r border-slate-800 p-3 space-y-2 overflow-y-auto">
                                <MetricItem icon={Server} label="API Gateway" value="99.9%" status="good" />
                                <MetricItem icon={Database} label="Primary DB" value="45% CPU" status="warning" />
                                <MetricItem icon={Globe} label="CDN Hits" value="1.2k/s" status="good" />
                                <MetricItem icon={Activity} label="Error Rate" value="0.01%" status="good" />
                            </div>

                            {/* Terminal Output */}
                            <div className="flex-1 bg-[#0B1120] p-4 font-mono text-sm overflow-y-auto custom-scrollbar">
                                <div className="text-slate-500 mb-2">System initialized. Listening for events...</div>
                                <LogEntry time="22:04:15" level="INFO" source="Autoscaler" message="Scaling up worker pool to 5 instances" />
                                <LogEntry time="22:04:18" level="SUCCESS" source="HealthCheck" message="Service 'payments-v2' responded in 45ms" />
                                <LogEntry time="22:05:02" level="WARN" source="Database" message="Long running query detected on 'users' table (150ms)" />
                                <div className="text-blue-400 mt-2 flex items-center gap-2">
                                    <span className="animate-pulse">_</span>
                                </div>
                            </div>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
};

const MetricItem = ({ icon: Icon, label, value, status }) => {
    const statusColors = {
        good: 'text-emerald-400',
        warning: 'text-amber-400',
        error: 'text-red-400'
    };

    return (
        <div className="flex items-center justify-between p-2 rounded-lg bg-slate-800/40 border border-slate-700/50">
            <div className="flex items-center gap-2">
                <Icon size={14} className="text-slate-400" />
                <span className="text-xs text-slate-300 font-medium">{label}</span>
            </div>
            <span className={`text-xs font-mono ${statusColors[status]}`}>{value}</span>
        </div>
    );
}

const LogEntry = ({ time, level, source, message }) => {
    const levelColors = {
        INFO: 'text-blue-400',
        SUCCESS: 'text-emerald-400',
        WARN: 'text-amber-400',
        ERROR: 'text-red-400'
    };

    return (
        <div className="flex gap-3 mb-1 font-mono text-xs opacity-90 hover:opacity-100 transition-opacity">
            <span className="text-slate-600">[{time}]</span>
            <span className={`w-16 font-bold ${levelColors[level]}`}>{level}</span>
            <span className="text-purple-400 w-24 truncate">{source}</span>
            <span className="text-slate-300">{message}</span>
        </div>
    );
}

export default Layout;
