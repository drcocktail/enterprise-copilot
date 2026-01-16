import React from 'react';
import { Settings } from 'lucide-react';

const IntegrationsView = () => (
    <div className="flex-1 p-8 overflow-y-auto h-full">
        <div className="max-w-5xl mx-auto space-y-8">
            <div>
                <h2 className="text-2xl font-bold text-white mb-1">Integrations & Telemetry</h2>
                <p className="text-slate-400 text-sm">Connect external tools and subscribe to live event streams.</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {[
                    { name: "JIRA Cloud", icon: "J", color: "bg-blue-600", connected: true, streams: ["IssueCreated", "StatusChanged"] },
                    { name: "GitHub Enterprise", icon: "G", color: "bg-slate-900", connected: true, streams: ["PushEvent", "PullRequest"] },
                    { name: "Datadog", icon: "D", color: "bg-purple-600", connected: false, streams: [] },
                    { name: "Slack", icon: "S", color: "bg-orange-500", connected: true, streams: ["Message", "Mention"] },
                    { name: "ServiceNow", icon: "SN", color: "bg-emerald-600", connected: false, streams: [] },
                    { name: "PagerDuty", icon: "P", color: "bg-green-600", connected: false, streams: [] },
                ].map((tool, i) => (
                    <div key={i} className="bg-slate-900 border border-slate-700 rounded-xl p-5 flex flex-col justify-between h-48 hover:border-slate-500 transition-colors shadow-sm cursor-default hover:shadow-md group">
                        <div className="flex justify-between items-start">
                            <div className="flex items-center space-x-3">
                                <div className={`w-10 h-10 rounded-lg ${tool.color} flex items-center justify-center text-white font-bold text-lg shadow-lg`}>
                                    {tool.icon}
                                </div>
                                <div>
                                    <h3 className="font-bold text-slate-200 group-hover:text-white transition-colors">{tool.name}</h3>
                                    <div className="flex items-center mt-1">
                                        <div className={`w-2 h-2 rounded-full mr-2 ${tool.connected ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]' : 'bg-slate-600'}`}></div>
                                        <span className="text-xs text-slate-500 font-medium">{tool.connected ? 'Connected' : 'Disconnected'}</span>
                                    </div>
                                </div>
                            </div>
                            <button className="text-slate-500 hover:text-white transition-colors">
                                <Settings className="w-4 h-4" />
                            </button>
                        </div>

                        {tool.connected && (
                            <div className="space-y-2">
                                <p className="text-[10px] uppercase tracking-wider text-slate-500 font-bold">Active Subscriptions</p>
                                <div className="flex flex-wrap gap-2">
                                    {tool.streams.map((stream, idx) => (
                                        <span key={idx} className="text-[10px] bg-slate-800 text-blue-300/90 px-2 py-1 rounded border border-slate-700 font-mono">
                                            {stream}
                                        </span>
                                    ))}
                                    <button className="text-[10px] bg-slate-800 text-slate-400 px-2 py-1 rounded border border-slate-700 hover:text-white hover:border-slate-500 transition-colors">
                                        + Add
                                    </button>
                                </div>
                            </div>
                        )}

                        {!tool.connected && (
                            <button className="w-full py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded-lg text-xs font-medium transition-all border border-transparent hover:border-slate-600">
                                Connect Integration
                            </button>
                        )}
                    </div>
                ))}
            </div>
        </div>
    </div>
);

export default IntegrationsView;
