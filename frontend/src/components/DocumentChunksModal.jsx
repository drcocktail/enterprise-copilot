import React, { useState, useEffect } from 'react';
import { X, FileText, Database, Loader2 } from 'lucide-react';
import api from '../services/api';
import { motion, AnimatePresence } from 'framer-motion';

const DocumentChunksModal = ({ isOpen, onClose, docId, docName }) => {
    const [loading, setLoading] = useState(true);
    const [chunks, setChunks] = useState([]);

    useEffect(() => {
        if (isOpen && docId) {
            loadChunks();
        }
    }, [isOpen, docId]);

    const loadChunks = async () => {
        setLoading(true);
        try {
            const res = await api.get(`/api/documents/${docId}/chunks?limit=100`, {
                headers: { 'x-iam-role': 'sde_ii' }
            });
            setChunks(res.data.chunks || []);
        } catch (e) {
            console.error("Failed to load chunks:", e);
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
                    className="bg-[#0B1120] border border-slate-700 rounded-2xl w-full max-w-4xl h-[80vh] overflow-hidden flex flex-col shadow-2xl"
                    onClick={(e) => e.stopPropagation()}
                >
                    {/* Header */}
                    <div className="h-16 border-b border-slate-800 flex items-center justify-between px-6 bg-slate-900/50">
                        <div className="flex items-center gap-4">
                            <div className="p-2 bg-blue-900/30 rounded-lg border border-blue-500/30">
                                <FileText className="w-5 h-5 text-blue-400" />
                            </div>
                            <div>
                                <h2 className="text-lg font-bold text-white">{docName || 'Document Viewer'}</h2>
                                <p className="text-xs text-slate-500">Vector Embeddings View</p>
                            </div>
                        </div>
                        <button onClick={onClose} className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors">
                            <X className="w-5 h-5" />
                        </button>
                    </div>

                    {/* Content */}
                    <div className="flex-1 overflow-hidden p-6">
                        {loading ? (
                            <div className="h-full flex items-center justify-center">
                                <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
                            </div>
                        ) : chunks.length === 0 ? (
                            <div className="h-full flex flex-col items-center justify-center text-slate-500">
                                <Database className="w-12 h-12 mb-4 opacity-50" />
                                <p>No chunks found for this document.</p>
                            </div>
                        ) : (
                            <div className="h-full overflow-y-auto custom-scrollbar space-y-4">
                                {chunks.map((chunk, idx) => (
                                    <div key={idx} className="bg-slate-900/50 border border-slate-800 rounded-xl overflow-hidden">
                                        <div className="px-4 py-2 bg-slate-800/50 border-b border-slate-700 flex items-center justify-between">
                                            <div className="flex items-center gap-2">
                                                <span className="text-xs font-mono text-blue-400">Chunk {chunk.chunk_index}</span>
                                                <span className="text-xs text-slate-500">Page {chunk.page}</span>
                                            </div>
                                            <span className="text-[10px] bg-slate-800 text-slate-400 px-2 py-0.5 rounded border border-slate-700 font-mono">
                                                ID: {chunk.id?.substring(0, 8)}...
                                            </span>
                                        </div>
                                        <div className="p-4 text-sm text-slate-300 font-mono whitespace-pre-wrap leading-relaxed">
                                            {chunk.content}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Footer */}
                    <div className="h-12 border-t border-slate-800 flex items-center justify-between px-6 bg-slate-900/30 text-xs text-slate-500">
                        <span>Total Chunks: <strong className="text-slate-300">{chunks.length}</strong></span>
                        <span>Document ID: <code className="text-slate-400">{docId}</code></span>
                    </div>
                </motion.div>
            </motion.div>
        </AnimatePresence>
    );
};

export default DocumentChunksModal;
