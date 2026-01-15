import React from 'react';
import { Shield, X, Activity } from 'lucide-react';

export const AuditLogPanel = ({ logs, onClose }) => (
  <div className="absolute bottom-0 left-0 right-0 h-80 bg-white border-t border-stone-200 shadow-soft-lg z-20 animate-slide-up">
    <div className="flex items-center justify-between px-6 py-4 border-b border-stone-100">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-amber-100 flex items-center justify-center">
          <Activity size={18} className="text-amber-600" />
        </div>
        <div>
          <h3 className="text-base font-bold text-stone-700">Activity Log</h3>
          <p className="text-xs text-stone-400">Real-time audit events</p>
        </div>
      </div>
      <button onClick={onClose} className="p-2 rounded-xl hover:bg-stone-100 text-stone-400 hover:text-stone-600 transition-all">
        <X size={18} />
      </button>
    </div>

    <div className="overflow-y-auto h-full p-4 space-y-2 pb-20">
      {logs.length === 0 && (
        <div className="text-stone-400 text-center py-8">
          <Shield size={24} className="mx-auto mb-2 opacity-50" />
          <p className="text-sm">No activity yet</p>
          <p className="text-xs mt-1">Events will appear here as you use the app</p>
        </div>
      )}

      {logs.map((log) => (
        <div key={log.id} className="flex items-center gap-4 p-3 rounded-xl bg-stone-50 hover:bg-stone-100 transition-colors">
          <div className="text-xs text-stone-400 min-w-[70px]">
            {new Date(log.timestamp).toLocaleTimeString()}
          </div>

          <div className={`px-2 py-1 rounded-lg text-xs font-semibold min-w-[70px] text-center ${log.status === 'DENIED' ? 'bg-red-100 text-red-600' :
              log.status === 'ERROR' ? 'bg-orange-100 text-orange-600' :
                'bg-emerald-100 text-emerald-600'
            }`}>
            {log.status}
          </div>

          <div className="text-sm font-medium text-stone-600 min-w-[140px]">{log.action}</div>

          <div className="flex-1 text-sm text-stone-500 truncate">
            {log.details}
          </div>
        </div>
      ))}
    </div>
  </div>
);
