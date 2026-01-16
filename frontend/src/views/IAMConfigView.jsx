import React from 'react';
import { ChevronRight, CheckCircle, ToggleRight, ToggleLeft } from 'lucide-react';

const IAMConfigView = () => (
    <div className="flex-1 p-8 overflow-y-auto h-full">
        <div className="max-w-5xl mx-auto space-y-8">
            <div>
                <h2 className="text-2xl font-bold text-white mb-1">IAM Configuration</h2>
                <p className="text-slate-400 text-sm">Define role-based capability envelopes and scope boundaries.</p>
            </div>

            <div className="bg-[#111827] border border-slate-700 rounded-xl overflow-hidden shadow-xl flex flex-col md:flex-row min-h-[500px]">
                {/* Sidebar */}
                <div className="w-full md:w-64 border-r border-slate-700 bg-slate-900/50 p-4">
                    <div className="flex border-b border-slate-700 mb-4 pb-1 space-x-1">
                        <button className="flex-1 pb-2 text-sm font-medium text-blue-400 border-b-2 border-blue-500">Roles</button>
                        <button className="flex-1 pb-2 text-sm font-medium text-slate-500 hover:text-slate-300">Policies</button>
                        <button className="flex-1 pb-2 text-sm font-medium text-slate-500 hover:text-slate-300">Audit</button>
                    </div>

                    <div className="space-y-1">
                        {['Admin', 'Senior Engineer', 'Junior Engineer', 'HR Manager', 'Auditor'].map((role, i) => (
                            <button key={i} className={`w-full text-left px-4 py-3 rounded-lg text-sm font-medium flex justify-between items-center transition-all ${i === 1 ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/20' : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'}`}>
                                {role}
                                {i === 1 && <ChevronRight className="w-4 h-4" />}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Editor Area */}
                <div className="flex-1 p-8 bg-[#0B1120]">
                    <div className="flex justify-between items-center mb-8">
                        <div className="flex items-center gap-4">
                            <h3 className="text-xl font-bold text-white">Role: Senior Engineer</h3>
                            <div className="flex items-center px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 text-xs font-bold border border-emerald-500/20">
                                <CheckCircle className="w-3 h-3 mr-1.5" /> Active
                            </div>
                        </div>
                        <button className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 px-3 py-2 rounded-lg border border-slate-700 transition-colors font-medium">
                            Duplicate Role
                        </button>
                    </div>

                    <div className="space-y-8 max-w-2xl">
                        <div>
                            <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">Scope: Repositories</label>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div className="flex items-center justify-between p-4 bg-slate-900/50 rounded-lg border border-slate-700 shadow-sm">
                                    <span className="text-sm font-medium text-slate-200">Read Access</span>
                                    <ToggleRight className="w-6 h-6 text-emerald-500 cursor-pointer" />
                                </div>
                                <div className="flex items-center justify-between p-4 bg-slate-900/50 rounded-lg border border-slate-700 shadow-sm">
                                    <span className="text-sm font-medium text-slate-200">Write (Feature Branch)</span>
                                    <ToggleRight className="w-6 h-6 text-emerald-500 cursor-pointer" />
                                </div>
                                <div className="flex items-center justify-between p-4 bg-slate-900/50 rounded-lg border border-slate-700 shadow-sm opacity-75">
                                    <span className="text-sm font-medium text-slate-400">Write (Main Branch)</span>
                                    <ToggleLeft className="w-6 h-6 text-slate-600 cursor-pointer" />
                                </div>
                                <div className="flex items-center justify-between p-4 bg-slate-900/50 rounded-lg border border-slate-700 shadow-sm opacity-75">
                                    <span className="text-sm font-medium text-slate-400">Delete Repo</span>
                                    <ToggleLeft className="w-6 h-6 text-slate-600 cursor-pointer" />
                                </div>
                            </div>
                        </div>

                        <div>
                            <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">Scope: Integrations</label>
                            <div className="space-y-3">
                                <div className="flex items-center justify-between p-4 bg-slate-900/50 rounded-lg border border-slate-700 shadow-sm">
                                    <span className="text-sm font-medium text-slate-200">JIRA (Create/Edit Tickets)</span>
                                    <span className="text-xs font-bold text-emerald-400 uppercase tracking-wider bg-emerald-500/10 px-2 py-1 rounded border border-emerald-500/20">Allowed</span>
                                </div>
                                <div className="flex items-center justify-between p-4 bg-slate-900/50 rounded-lg border border-slate-700 shadow-sm opacity-75">
                                    <span className="text-sm font-medium text-slate-400">Production DB (Write)</span>
                                    <span className="text-xs font-bold text-red-400 uppercase tracking-wider bg-red-500/10 px-2 py-1 rounded border border-red-500/20">Denied</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
);

export default IAMConfigView;
