import React, { useState, useEffect } from 'react';
import { Activity, CheckCircle, XCircle, AlertTriangle } from 'lucide-react';

const SystemStatus = () => {
    const [status, setStatus] = useState('loading'); // loading, ok, error, warning
    const [services, setServices] = useState({});
    const [isOpen, setIsOpen] = useState(false);

    const checkHealth = async () => {
        try {
            // Gateway check
            const res = await fetch('http://localhost:8000/api/system/health');
            if (res.ok) {
                const data = await res.json();
                setServices({
                    gateway: true,
                    ingestion: true, // We assume these for now if gateway is up, or gateway returns them
                    chat: true,
                    core: true
                });
                setStatus('ok');
            } else {
                setStatus('error');
            }
        } catch (e) {
            setStatus('error');
        }
    };

    useEffect(() => {
        checkHealth();
        const interval = setInterval(checkHealth, 10000); // Check every 10s
        return () => clearInterval(interval);
    }, []);

    const getIcon = () => {
        if (status === 'loading') return <Activity className="w-4 h-4 text-slate-500 animate-pulse" />;
        if (status === 'ok') return <CheckCircle className="w-4 h-4 text-emerald-400" />;
        if (status === 'error') return <XCircle className="w-4 h-4 text-red-500" />;
        return <AlertTriangle className="w-4 h-4 text-yellow-500" />;
    };

    return (
        <div className="px-4 py-3 border-t border-slate-800">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="flex items-center space-x-3 w-full hover:bg-slate-800 p-2 rounded-lg transition-colors"
            >
                {getIcon()}
                <div className="flex-1 text-left">
                    <p className="text-xs font-medium text-slate-300">System Status</p>
                    <p className="text-[10px] text-slate-500 capitalize">{status === 'ok' ? 'All Systems Operational' : status}</p>
                </div>
            </button>

            {isOpen && (
                <div className="mt-2 text-xs space-y-1 pl-9">
                    <div className="flex items-center justify-between text-slate-400">
                        <span>Gateway</span>
                        <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                    </div>
                    <div className="flex items-center justify-between text-slate-400">
                        <span>Ingestion</span>
                        <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                    </div>
                    <div className="flex items-center justify-between text-slate-400">
                        <span>Chat</span>
                        <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                    </div>
                    <div className="flex items-center justify-between text-slate-400">
                        <span>Core</span>
                        <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                    </div>
                </div>
            )}
        </div>
    );
};

export default SystemStatus;
