import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import {
    MessageSquare,
    FileText,
    GitBranch,
    Blocks,
    Shield,
    Activity,
    Settings,
    LogOut,
    ChevronRight,
    Menu,
    X
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const Sidebar = ({ isLiveOpsOpen, setIsLiveOpsOpen }) => {
    const [isMobileOpen, setIsMobileOpen] = useState(false);

    const navItems = [
        { icon: MessageSquare, label: 'Copilot Chat', path: '/chat' },
        { icon: FileText, label: 'Documents', path: '/documents' },
        { icon: GitBranch, label: 'Repositories', path: '/repos' },
        { icon: Blocks, label: 'Integrations', path: '/integrations' },
        { icon: Shield, label: 'IAM Config', path: '/iam' },
    ];

    return (
        <>
            {/* Mobile Toggle */}
            <div className="lg:hidden fixed top-4 left-4 z-50">
                <button
                    onClick={() => setIsMobileOpen(!isMobileOpen)}
                    className="p-2 bg-slate-800 rounded-lg text-white border border-slate-700"
                >
                    {isMobileOpen ? <X size={20} /> : <Menu size={20} />}
                </button>
            </div>

            {/* Sidebar */}
            <aside className={`
        fixed inset-y-0 left-0 z-40 w-64 bg-[#0B1120] border-r border-slate-800/50 
        transition-transform duration-300 transform 
        ${isMobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
      `}>
                <div className="flex flex-col h-full">
                    {/* Logo */}
                    <div className="p-6 border-b border-slate-800/50">
                        <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-blue-600 to-sky-400 flex items-center justify-center shadow-lg shadow-blue-500/20">
                                <Shield className="text-white" size={18} fill="currentColor" />
                            </div>
                            <div>
                                <h1 className="text-lg font-bold text-white tracking-tight leading-none">Nexus</h1>
                                <span className="text-[10px] font-bold text-blue-400 tracking-widest uppercase">Enterprise</span>
                            </div>
                        </div>
                    </div>

                    {/* Navigation */}
                    <nav className="flex-1 p-4 space-y-1 overflow-y-auto custom-scrollbar">
                        {navItems.map((item) => (
                            <NavLink
                                key={item.path}
                                to={item.path}
                                className={({ isActive }) => `
                  flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 group relative
                  ${isActive
                                        ? 'bg-blue-600/10 text-blue-400 ring-1 ring-blue-500/20 shadow-[0_0_15px_rgba(59,130,246,0.1)]'
                                        : 'text-slate-400 hover:text-white hover:bg-slate-800/50'}
                `}
                            >
                                {({ isActive }) => (
                                    <>
                                        <item.icon size={20} className={`transition-colors ${isActive ? 'text-blue-400' : 'group-hover:text-white'}`} />
                                        <span className="font-medium text-sm">{item.label}</span>
                                        {isActive && (
                                            <motion.div
                                                layoutId="activeIndicator"
                                                className="absolute right-2 w-1.5 h-1.5 rounded-full bg-blue-400 shadow-[0_0_8px_rgba(56,189,248,0.8)]"
                                            />
                                        )}
                                    </>
                                )}
                            </NavLink>
                        ))}
                    </nav>

                    {/* Live Ops Console */}
                    <div className="p-4 border-t border-slate-800/50">
                        <NavLink
                            to="/live-console"
                            className={({ isActive }) => `
                                w-full flex items-center justify-between p-4 rounded-xl border transition-all duration-300 group
                                ${isActive
                                    ? 'bg-slate-800/80 border-green-500/30 shadow-[0_0_20px_rgba(15,23,42,0.5)]'
                                    : 'bg-slate-900/50 border-slate-800 hover:border-slate-700'}
                            `}
                        >
                            <div className="flex items-center gap-3">
                                <Activity size={18} className="text-green-500 group-hover:animate-pulse" />
                                <span className="text-sm font-semibold text-white">
                                    Live Ops Console
                                </span>
                            </div>
                            <ChevronRight
                                size={16}
                                className="text-slate-600 group-hover:text-green-500 transition-colors"
                            />
                        </NavLink>
                    </div>

                    {/* User Profile */}
                    <div className="p-4 bg-slate-900/30">
                        <div className="flex items-center gap-3 p-2 rounded-lg hover:bg-slate-800/50 cursor-pointer transition-colors">
                            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white font-bold text-sm shadow-md">
                                JD
                            </div>
                            <div className="flex-1 min-w-0">
                                <div className="text-sm font-medium text-white truncate">John Doe</div>
                                <div className="flex items-center gap-1.5 text-xs text-blue-400">
                                    <Shield size={10} fill="currentColor" />
                                    <span>Level 3 Eng</span>
                                </div>
                            </div>
                            <Settings size={16} className="text-slate-500 hover:text-white transition-colors" />
                        </div>
                    </div>
                </div>
            </aside>

            {/* Overlay for mobile */}
            {isMobileOpen && (
                <div
                    className="fixed inset-0 bg-black/50 z-30 lg:hidden backdrop-blur-sm"
                    onClick={() => setIsMobileOpen(false)}
                />
            )}
        </>
    );
};

export default Sidebar;
