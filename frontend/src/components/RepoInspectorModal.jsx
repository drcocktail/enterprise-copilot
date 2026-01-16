import React, { useState, useEffect } from 'react';
import { X, GitBranch, Package, ArrowRight, Loader2, Code2, Database } from 'lucide-react';
import api from '../services/api';
import { motion, AnimatePresence } from 'framer-motion';

const RepoInspectorModal = ({ isOpen, onClose, repoId, repoName }) => {
    const [loading, setLoading] = useState(true);
    const [graphData, setGraphData] = useState({ nodes: [], edges: [] });
    const [chunks, setChunks] = useState([]);
    const [activeTab, setActiveTab] = useState('graph');

    useEffect(() => {
        if (isOpen && repoId) {
            loadInspectorData();
        }
    }, [isOpen, repoId]);

    const loadInspectorData = async () => {
        setLoading(true);
        try {
            const [graphRes, chunksRes] = await Promise.all([
                api.get(`/api/repos/${repoId}/graph`),
                api.get(`/api/repos/${repoId}/chunks`)
            ]);
            setGraphData(graphRes.data);
            setChunks(chunksRes.data.chunks || []);
        } catch (e) {
            console.error("Failed to load inspector data:", e);
            // Mock data for demo
            setGraphData({
                nodes: [
                    { id: 'file_main', type: 'file', label: 'main.py' },
                    { id: 'func_authenticate', type: 'function', label: 'authenticate()' },
                    { id: 'func_validate', type: 'function', label: 'validate_token()' },
                    { id: 'class_User', type: 'class', label: 'User' },
                ],
                edges: [
                    { source: 'file_main', target: 'func_authenticate', type: 'CONTAINS' },
                    { source: 'file_main', target: 'class_User', type: 'CONTAINS' },
                    { source: 'func_authenticate', target: 'func_validate', type: 'CALLS' },
                ]
            });
            setChunks([
                { id: 1, content: 'def authenticate(user, password):\n    token = generate_jwt(user)\n    return token', file: 'auth/service.py', lines: '12-24' },
                { id: 2, content: 'class User(BaseModel):\n    id: int\n    email: str\n    role: str', file: 'models/user.py', lines: '1-15' },
                { id: 3, content: 'def validate_token(token: str) -> bool:\n    try:\n        decode_jwt(token)\n        return True\n    except:\n        return False', file: 'auth/service.py', lines: '26-35' },
            ]);
        } finally {
            setLoading(false);
        }
    };

    if (!isOpen) return null;

    return (
        <AnimatePresence>
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4"
                onClick={onClose}
            >
                <motion.div
                    initial={{ scale: 0.9, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    exit={{ scale: 0.9, opacity: 0 }}
                    className="bg-[#0B1120] border border-slate-700 rounded-2xl w-full max-w-6xl h-[80vh] overflow-hidden flex flex-col shadow-2xl"
                    onClick={(e) => e.stopPropagation()}
                >
                    {/* Header */}
                    <div className="h-16 border-b border-slate-800 flex items-center justify-between px-6 bg-slate-900/50">
                        <div className="flex items-center gap-4">
                            <div className="p-2 bg-purple-900/30 rounded-lg border border-purple-500/30">
                                <GitBranch className="w-5 h-5 text-purple-400" />
                            </div>
                            <div>
                                <h2 className="text-lg font-bold text-white">{repoName || 'Repository Inspector'}</h2>
                                <p className="text-xs text-slate-500">AST Graph & Vector Chunks</p>
                            </div>
                        </div>
                        <div className="flex items-center gap-4">
                            {/* Tabs */}
                            <div className="flex bg-slate-800 rounded-lg p-1">
                                <button
                                    onClick={() => setActiveTab('graph')}
                                    className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${activeTab === 'graph' ? 'bg-purple-600 text-white' : 'text-slate-400 hover:text-white'}`}
                                >
                                    <Code2 className="w-4 h-4 inline mr-2" />
                                    AST Graph
                                </button>
                                <button
                                    onClick={() => setActiveTab('chunks')}
                                    className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${activeTab === 'chunks' ? 'bg-purple-600 text-white' : 'text-slate-400 hover:text-white'}`}
                                >
                                    <Database className="w-4 h-4 inline mr-2" />
                                    Vector Chunks
                                </button>
                            </div>
                            <button onClick={onClose} className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors">
                                <X className="w-5 h-5" />
                            </button>
                        </div>
                    </div>

                    {/* Content */}
                    <div className="flex-1 overflow-hidden">
                        {loading ? (
                            <div className="h-full flex items-center justify-center">
                                <Loader2 className="w-8 h-8 text-purple-500 animate-spin" />
                            </div>
                        ) : activeTab === 'graph' ? (
                            /* AST Graph View */
                            <div className="h-full p-6 overflow-auto custom-scrollbar">
                                <div className="grid grid-cols-2 gap-6 h-full">
                                    {/* Nodes */}
                                    <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-4">
                                        <h3 className="text-sm font-bold text-slate-300 uppercase tracking-wider mb-4 flex items-center gap-2">
                                            <Package className="w-4 h-4 text-blue-400" />
                                            Nodes ({graphData.nodes.length})
                                        </h3>
                                        <div className="space-y-2 max-h-[60vh] overflow-y-auto custom-scrollbar">
                                            {graphData.nodes.map((node, idx) => (
                                                <div key={idx} className="flex items-center gap-3 p-3 bg-slate-800/50 rounded-lg border border-slate-700/50 hover:border-slate-600 transition-colors">
                                                    <div className={`w-2 h-2 rounded-full ${node.type === 'file' ? 'bg-yellow-500' :
                                                            node.type === 'function' ? 'bg-blue-500' :
                                                                node.type === 'class' ? 'bg-purple-500' : 'bg-slate-500'
                                                        }`} />
                                                    <span className="text-xs font-mono text-slate-300 flex-1">{node.label}</span>
                                                    <span className="text-[10px] bg-slate-700 text-slate-400 px-2 py-0.5 rounded uppercase">{node.type}</span>
                                                </div>
                                            ))}
                                        </div>
                                    </div>

                                    {/* Edges */}
                                    <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-4">
                                        <h3 className="text-sm font-bold text-slate-300 uppercase tracking-wider mb-4 flex items-center gap-2">
                                            <ArrowRight className="w-4 h-4 text-green-400" />
                                            Edges ({graphData.edges.length})
                                        </h3>
                                        <div className="space-y-2 max-h-[60vh] overflow-y-auto custom-scrollbar">
                                            {graphData.edges.map((edge, idx) => (
                                                <div key={idx} className="flex items-center gap-2 p-3 bg-slate-800/50 rounded-lg border border-slate-700/50">
                                                    <span className="text-xs font-mono text-slate-400 truncate flex-1">{edge.source}</span>
                                                    <span className="text-[10px] bg-green-900/30 text-green-400 px-2 py-0.5 rounded border border-green-900/50">{edge.type}</span>
                                                    <ArrowRight className="w-3 h-3 text-slate-600" />
                                                    <span className="text-xs font-mono text-slate-400 truncate flex-1">{edge.target}</span>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ) : (
                            /* Vector Chunks View */
                            <div className="h-full p-6 overflow-auto custom-scrollbar">
                                <div className="space-y-4">
                                    {chunks.map((chunk, idx) => (
                                        <div key={idx} className="bg-slate-900/50 border border-slate-800 rounded-xl overflow-hidden">
                                            <div className="px-4 py-2 bg-slate-800/50 border-b border-slate-700 flex items-center justify-between">
                                                <div className="flex items-center gap-2">
                                                    <Code2 className="w-4 h-4 text-blue-400" />
                                                    <span className="text-sm font-medium text-slate-200">{chunk.file}</span>
                                                    <span className="text-xs text-slate-500">L{chunk.lines}</span>
                                                </div>
                                                <span className="text-[10px] bg-blue-900/30 text-blue-400 px-2 py-0.5 rounded border border-blue-900/50">
                                                    Chunk #{chunk.id}
                                                </span>
                                            </div>
                                            <pre className="p-4 text-xs font-mono text-slate-300 overflow-x-auto">
                                                <code>{chunk.content}</code>
                                            </pre>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Footer Stats */}
                    <div className="h-12 border-t border-slate-800 flex items-center justify-between px-6 bg-slate-900/30 text-xs text-slate-500">
                        <div className="flex items-center gap-6">
                            <span><strong className="text-slate-300">{graphData.nodes.length}</strong> Nodes</span>
                            <span><strong className="text-slate-300">{graphData.edges.length}</strong> Edges</span>
                            <span><strong className="text-slate-300">{chunks.length}</strong> Chunks</span>
                        </div>
                        <span>Repo ID: <code className="text-slate-400">{repoId}</code></span>
                    </div>
                </motion.div>
            </motion.div>
        </AnimatePresence>
    );
};

export default RepoInspectorModal;
