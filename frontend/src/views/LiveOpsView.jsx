import React, { useState, useEffect } from 'react';
import {
    Terminal,
    AlertCircle,
    Microscope,
    RefreshCw,
    Stethoscope,
    CheckCircle,
    Siren,
    ArrowRight,
    BarChart3
} from 'lucide-react';

const LiveOpsView = () => {
    const [logs, setLogs] = useState([]);
    const [activeAlert, setActiveAlert] = useState(null);
    const [diagnosis, setDiagnosis] = useState({ state: 'idle', steps: [] });
    const [simulatedAction, setSimulatedAction] = useState(null);

    useEffect(() => {
        // Simulate incoming logs
        const interval = setInterval(() => {
            const newLogs = [
                { ts: new Date().toLocaleTimeString(), level: "INFO", sys: "K8S_POD", msg: "Container status: Running" },
                { ts: new Date().toLocaleTimeString(), level: "DEBUG", sys: "INGRESS", msg: "Route match: /api/v1/health -> health-check-svc" },
                { ts: new Date().toLocaleTimeString(), level: "WARN", sys: "DB_POOL", msg: "Connection pool utilization > 80%" },
                { ts: new Date().toLocaleTimeString(), level: "INFO", sys: "AUTH", msg: "Token verified for user_jdoe" }
            ];
            const randomLog = newLogs[Math.floor(Math.random() * newLogs.length)];
            setLogs(prev => [...prev.slice(-20), randomLog]);
        }, 1500);
        return () => clearInterval(interval);
    }, []);

    const alerts = [
        { id: 1, sev: 'critical', title: 'Pod CrashLoopBackOff', svc: 'payments-v2', time: '2m ago' },
        { id: 2, sev: 'warning', title: 'High Memory Usage', svc: 'redis-cache-01', time: '15m ago' },
        { id: 3, sev: 'info', title: 'Deployment Rolled Out', svc: 'frontend-web', time: '1h ago' },
    ];

    const startDiagnosis = (alert) => {
        setActiveAlert(alert);
        setDiagnosis({ state: 'analyzing', steps: [] });
        setSimulatedAction(null);

        // Simulate AI thinking process for RCA
        setTimeout(() => setDiagnosis(p => ({ ...p, steps: [...p.steps, { text: `Aggregating logs for service: ${alert.svc}`, status: 'done' }] })), 500);
        setTimeout(() => setDiagnosis(p => ({ ...p, steps: [...p.steps, { text: "Correlating event spikes with deployment window", status: 'done' }] })), 1500);
        setTimeout(() => setDiagnosis(p => ({ ...p, steps: [...p.steps, { text: "Detecting pattern: Connection Leak in DB Pool", status: 'warning' }] })), 2500);
        setTimeout(() => setDiagnosis(p => ({ ...p, state: 'complete' })), 3000);
    };

    const triggerRemediation = (alert) => {
        setSimulatedAction({
            status: 'pending',
            action: alert.id === 1 ? 'restart_pod' : 'scale_replicas',
            target: alert.svc,
            payload: {
                apiVersion: "v1",
                kind: "Pod",
                metadata: { name: alert.svc, namespace: "prod" },
                command: ["kubectl", "delete", "pod", alert.svc]
            }
        });

        // Simulate backend response delay
        setTimeout(() => {
            setSimulatedAction(prev => ({ ...prev, status: 'executing' }));
            setTimeout(() => {
                setSimulatedAction(prev => ({ ...prev, status: 'complete' }));
                setLogs(prev => [...prev, { ts: new Date().toLocaleTimeString(), level: "POST", sys: "OPS_AGENT", msg: `Action executed: ${alert.id === 1 ? 'restart_pod' : 'scale_replicas'} on ${alert.svc}` }]);
            }, 2000);
        }, 1000);
    };

    return (
        <div className="h-[calc(100vh-2rem)] flex flex-col bg-[#050505] font-mono text-sm overflow-hidden rounded-xl border border-slate-800">

            {/* 1. Status Header */}
            <div className="h-14 bg-slate-900/50 border-b border-slate-800 flex items-center px-4 justify-between">
                <div className="flex items-center space-x-2">
                    <Terminal className="w-5 h-5 text-green-500" />
                    <span className="text-slate-200 font-bold tracking-tight">Live Ops Console</span>
                    <span className="text-[10px] bg-slate-800 text-slate-500 px-1.5 py-0.5 rounded border border-slate-700">PROD-US-EAST-1</span>
                </div>

                {/* Metric Sparklines (Mock) */}
                <div className="flex items-center space-x-6">
                    <div className="flex flex-col items-end">
                        <span className="text-[10px] text-slate-500 uppercase font-bold">System Load</span>
                        <div className="flex items-center space-x-2">
                            <div className="flex space-x-0.5 items-end h-4">
                                <div className="w-1 bg-green-500 h-2"></div>
                                <div className="w-1 bg-green-500 h-3"></div>
                                <div className="w-1 bg-yellow-500 h-4"></div>
                                <div className="w-1 bg-green-500 h-2"></div>
                            </div>
                            <span className="text-xs text-slate-300 font-mono">42%</span>
                        </div>
                    </div>
                    <div className="flex flex-col items-end">
                        <span className="text-[10px] text-slate-500 uppercase font-bold">Error Rate</span>
                        <div className="flex items-center space-x-2">
                            <div className="flex space-x-0.5 items-end h-4">
                                <div className="w-1 bg-slate-700 h-1"></div>
                                <div className="w-1 bg-slate-700 h-1"></div>
                                <div className="w-1 bg-red-500 h-2"></div>
                                <div className="w-1 bg-slate-700 h-1"></div>
                            </div>
                            <span className="text-xs text-red-400 font-mono">0.05%</span>
                        </div>
                    </div>
                    <div className="h-6 w-px bg-slate-800"></div>
                    <button className="text-xs bg-red-900/20 text-red-400 px-3 py-1.5 rounded border border-red-900/30 hover:bg-red-900/30 flex items-center animate-pulse">
                        <AlertCircle className="w-3 h-3 mr-2" /> 3 Active Alerts
                    </button>
                </div>
            </div>

            <div className="flex-1 flex overflow-hidden">

                {/* 2. Left Panel: Active Incidents */}
                <div className="w-72 border-r border-slate-800 bg-[#0a0a0a] flex flex-col">
                    <div className="p-3 border-b border-slate-800 bg-slate-900/20">
                        <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Incident Feed</h3>
                    </div>
                    <div className="flex-1 overflow-y-auto">
                        {alerts.map((alert) => (
                            <div
                                key={alert.id}
                                onClick={() => startDiagnosis(alert)}
                                className={`p-4 border-b border-slate-800 cursor-pointer transition-colors ${activeAlert?.id === alert.id ? 'bg-slate-800/50' : 'hover:bg-slate-900/30'}`}
                            >
                                <div className="flex items-center justify-between mb-1">
                                    <div className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded border ${alert.sev === 'critical' ? 'bg-red-900/20 text-red-500 border-red-900/50' :
                                            alert.sev === 'warning' ? 'bg-yellow-900/20 text-yellow-500 border-yellow-900/50' :
                                                'bg-blue-900/20 text-blue-500 border-blue-900/50'
                                        }`}>
                                        {alert.sev}
                                    </div>
                                    <span className="text-[10px] text-slate-600">{alert.time}</span>
                                </div>
                                <h4 className="text-sm font-medium text-slate-200 mb-0.5">{alert.title}</h4>
                                <p className="text-xs text-slate-500 font-mono">{alert.svc}</p>
                            </div>
                        ))}
                    </div>
                </div>

                {/* 3. Center Panel: Telemetry Stream */}
                <div className="flex-1 flex flex-col bg-black relative">
                    <div className="absolute top-0 left-0 right-0 h-8 bg-gradient-to-b from-black to-transparent pointer-events-none"></div>
                    <div className="flex-1 p-4 overflow-y-auto space-y-1 font-mono text-xs custom-scrollbar">
                        {logs.map((log, i) => (
                            <div key={i} className="flex space-x-3 hover:bg-white/5 p-0.5 rounded group">
                                <span className="text-slate-600 shrink-0">[{log.ts}]</span>
                                <span className={`shrink-0 w-12 font-bold ${log.level === 'INFO' ? 'text-blue-500' :
                                        log.level === 'DEBUG' ? 'text-slate-600' :
                                            log.level === 'WARN' ? 'text-yellow-500' :
                                                log.level === 'POST' ? 'text-purple-500' : 'text-green-500'
                                    }`}>{log.level}</span>
                                <span className="text-orange-500 shrink-0 w-24">[{log.sys}]</span>
                                <span className="text-slate-400 group-hover:text-slate-200">{log.msg}</span>
                            </div>
                        ))}
                        <div className="flex items-center text-slate-600 animate-pulse mt-2">
                            <span className="mr-2">_</span> waiting for stream
                        </div>
                    </div>

                    {/* Command Input */}
                    <div className="p-3 border-t border-slate-800 bg-[#0a0a0a]">
                        <div className="flex items-center bg-black border border-slate-800 rounded px-3 py-2">
                            <span className="text-green-500 mr-2">$</span>
                            <input
                                type="text"
                                placeholder="Execute ad-hoc command or filter logs..."
                                className="bg-transparent text-slate-200 w-full focus:outline-none placeholder:text-slate-700"
                            />
                        </div>
                    </div>
                </div>

                {/* 4. Right Panel: AI Investigator (RCA) */}
                <div className="w-96 border-l border-slate-800 bg-[#0a0a0a] flex flex-col">
                    <div className="p-3 border-b border-slate-800 bg-slate-900/20 flex items-center justify-between">
                        <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center">
                            <Microscope className="w-4 h-4 mr-2 text-purple-400" />
                            Auto-Investigator
                        </h3>
                        {diagnosis.state === 'analyzing' && <RefreshCw className="w-3 h-3 text-purple-500 animate-spin" />}
                    </div>

                    <div className="flex-1 p-4 overflow-y-auto">
                        {!activeAlert ? (
                            <div className="h-full flex flex-col items-center justify-center text-slate-600">
                                <Microscope className="w-12 h-12 mb-4 opacity-10" />
                                <p className="text-xs text-center text-slate-500">Select an incident to trigger<br />AI Root Cause Analysis</p>
                            </div>
                        ) : (
                            <div className="space-y-6">

                                {/* AI Diagnosis Trace */}
                                <div className="bg-slate-900/30 rounded-lg p-3 border border-slate-800">
                                    <h4 className="text-xs font-bold text-slate-300 mb-3 flex items-center">
                                        <Stethoscope className="w-3.5 h-3.5 mr-2 text-blue-400" /> Diagnosis Trace
                                    </h4>
                                    <div className="space-y-2">
                                        {diagnosis.steps.map((step, idx) => (
                                            <div key={idx} className="flex items-center text-[10px] animate-fade-in">
                                                {step.status === 'done' && <CheckCircle className="w-3 h-3 text-green-500 mr-2" />}
                                                {step.status === 'warning' && <AlertCircle className="w-3 h-3 text-yellow-500 mr-2" />}
                                                <span className={step.status === 'warning' ? 'text-yellow-200' : 'text-slate-400'}>{step.text}</span>
                                            </div>
                                        ))}
                                        {diagnosis.state === 'analyzing' && (
                                            <div className="flex items-center text-[10px] text-purple-400">
                                                <div className="w-2 h-2 rounded-full bg-purple-500 animate-ping mr-3"></div>
                                                Analyzing dependencies...
                                            </div>
                                        )}
                                    </div>
                                </div>

                                {diagnosis.state === 'complete' && (
                                    <div className="animate-slide-up space-y-6">
                                        {/* Findings */}
                                        <div>
                                            <h4 className="text-sm font-bold text-slate-200 mb-1">RCA Summary</h4>
                                            <div className="p-3 bg-red-900/10 border border-red-900/30 rounded text-xs text-red-200 leading-relaxed">
                                                <span className="font-bold">Root Cause Probability (87%):</span> {activeAlert.title} is likely caused by <span className="text-white font-mono bg-red-900/30 px-1 rounded">db_pool_exhaustion</span>.
                                                <br /><br />
                                                Logs indicate 50+ connection timeouts correlating with the recent deployment `v2.4.1`.
                                            </div>
                                        </div>

                                        {/* Remediation Plan */}
                                        <div>
                                            <h4 className="text-sm font-bold text-slate-200 mb-2 flex items-center">
                                                <Siren className="w-4 h-4 mr-2 text-orange-400" /> Remediation Plan
                                            </h4>

                                            <div className="space-y-2">
                                                <button
                                                    onClick={() => triggerRemediation(activeAlert)}
                                                    className="w-full flex items-center justify-between p-3 bg-slate-800 border border-slate-700 rounded hover:bg-slate-700 hover:border-slate-500 transition-all group"
                                                >
                                                    <div className="flex items-center">
                                                        <div className="p-1.5 bg-blue-900/30 rounded text-blue-400 mr-3 group-hover:text-blue-300">
                                                            <RefreshCw className="w-4 h-4" />
                                                        </div>
                                                        <div className="text-left">
                                                            <div className="text-xs font-bold text-slate-200">Restart Pods</div>
                                                            <div className="text-[10px] text-slate-500">Safe • Quick Recovery</div>
                                                        </div>
                                                    </div>
                                                    <ArrowRight className="w-4 h-4 text-slate-600 group-hover:text-white" />
                                                </button>

                                                <button className="w-full flex items-center justify-between p-3 bg-slate-800 border border-slate-700 rounded hover:bg-slate-700 hover:border-slate-500 transition-all group">
                                                    <div className="flex items-center">
                                                        <div className="p-1.5 bg-purple-900/30 rounded text-purple-400 mr-3 group-hover:text-purple-300">
                                                            <BarChart3 className="w-4 h-4" />
                                                        </div>
                                                        <div className="text-left">
                                                            <div className="text-xs font-bold text-slate-200">Scale Up Replicas</div>
                                                            <div className="text-[10px] text-slate-500">Moderate Risk • Cost Impact</div>
                                                        </div>
                                                    </div>
                                                    <ArrowRight className="w-4 h-4 text-slate-600 group-hover:text-white" />
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                )}

                                {/* Execution Simulator (Log Output) */}
                                {simulatedAction && (
                                    <div className="border border-slate-700 rounded-lg overflow-hidden bg-black animate-in fade-in zoom-in-95 duration-300">
                                        <div className="px-3 py-2 bg-slate-900 border-b border-slate-700 flex justify-between items-center">
                                            <span className="text-[10px] font-bold uppercase text-slate-400">Action Output</span>
                                            {simulatedAction.status === 'complete' ? (
                                                <span className="text-[10px] text-green-500 flex items-center"><CheckCircle className="w-3 h-3 mr-1" /> Success</span>
                                            ) : (
                                                <span className="text-[10px] text-blue-500 flex items-center"><RefreshCw className="w-3 h-3 mr-1 animate-spin" /> Running</span>
                                            )}
                                        </div>

                                        {/* Stream Output */}
                                        <div className="p-3 bg-slate-900/30 h-32 overflow-y-auto font-mono text-[10px] space-y-1">
                                            {simulatedAction.status !== 'pending' && (
                                                <>
                                                    <div className="text-slate-400">&gt; Connecting to k8s cluster... OK</div>
                                                    <div className="text-slate-400">&gt; Authenticating as user_jdoe... OK</div>
                                                    <div className="text-slate-400">&gt; Executing: {simulatedAction.payload.command.join(' ')}</div>
                                                </>
                                            )}
                                            {simulatedAction.status === 'complete' && (
                                                <>
                                                    <div className="text-slate-300">pod "{activeAlert.svc}" deleted</div>
                                                    <div className="text-green-500">Command exited with status 0</div>
                                                </>
                                            )}
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                </div>

            </div>
        </div>
    );
};

export default LiveOpsView;
