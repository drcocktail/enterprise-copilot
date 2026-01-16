import React from 'react';
import { Shield, Unlock, Lock } from 'lucide-react';

const ActionCard = ({ system, payload, status, iamReason }) => (
    <div className="mt-4 mb-2 bg-slate-900 border border-slate-700 rounded-lg overflow-hidden shadow-lg shadow-black/20">
        <div className="bg-slate-800/50 px-4 py-2 flex items-center justify-between border-b border-slate-700">
            <div className="flex items-center space-x-2">
                {system === 'JIRA' && <div className="w-2 h-2 rounded-full bg-blue-500"></div>}
                {system === 'GITHUB' && <div className="w-2 h-2 rounded-full bg-purple-500"></div>}
                {system === 'CALENDAR' && <div className="w-2 h-2 rounded-full bg-orange-500"></div>}
                {system === 'KUBERNETES' && <div className="w-2 h-2 rounded-full bg-blue-400"></div>}
                <span className="text-xs font-bold text-slate-300 tracking-wide uppercase">{system} Integration</span>
            </div>
            <div className={`flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${status === 'AUTHORIZED' ? 'bg-green-900/30 text-green-400 border border-green-800' : 'bg-red-900/30 text-red-400 border border-red-800'
                }`}>
                {status === 'AUTHORIZED' ? <Unlock className="w-3 h-3 mr-1" /> : <Lock className="w-3 h-3 mr-1" />}
                {status}
            </div>
        </div>
        <div className="p-4 bg-slate-950/50 font-mono text-xs">
            <div className="flex justify-between items-start mb-2">
                <span className="text-slate-500">// Proposed Action Payload</span>
            </div>
            <pre className="text-slate-300 overflow-x-auto p-2 rounded bg-black/20 border border-white/5">
                {JSON.stringify(payload, null, 2)}
            </pre>
        </div>
        <div className="px-4 py-3 bg-slate-800/30 border-t border-slate-700 flex items-center justify-between">
            <div className="flex items-center space-x-2">
                <Shield className={`w-4 h-4 ${status === 'AUTHORIZED' ? 'text-green-500' : 'text-red-500'}`} />
                <span className="text-xs text-slate-400">
                    IAM Check: <span className={status === 'AUTHORIZED' ? 'text-green-400' : 'text-red-400'}>{iamReason}</span>
                </span>
            </div>
            {status === 'AUTHORIZED' ? (
                <button className="px-3 py-1 bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium rounded transition-colors shadow-lg shadow-blue-900/20">
                    Execute Action
                </button>
            ) : (
                <button disabled className="px-3 py-1 bg-slate-700 text-slate-500 text-xs font-medium rounded cursor-not-allowed opacity-50">
                    Elevation Required
                </button>
            )}
        </div>
    </div>
);

export default ActionCard;
