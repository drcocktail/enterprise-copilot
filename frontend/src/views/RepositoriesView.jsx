import React, { useState, useEffect } from 'react';
import { GitBranch, Plus, Trash2, Eye, RefreshCw, Loader2, X } from 'lucide-react';
import api from '../services/api';
import RepoInspectorModal from '../components/RepoInspectorModal';
import AddRepoModal from '../components/AddRepoModal';

const RepositoriesView = () => {
    const [repos, setRepos] = useState([]);
    const [loading, setLoading] = useState(true);
    const [inspectorOpen, setInspectorOpen] = useState(false);
    const [addRepoOpen, setAddRepoOpen] = useState(false);
    const [selectedRepo, setSelectedRepo] = useState(null);

    const demoRepos = [
        { id: 'demo_1', name: 'payments-v2-backend', lang: 'TYPESCRIPT', nodes: '14.2k', updated: '2 mins ago', density: 'high' },
        { id: 'demo_2', name: 'legacy-auth-service', lang: 'JAVA', nodes: '45.1k', updated: '1 hour ago', density: 'high' },
        { id: 'demo_3', name: 'frontend-dashboard', lang: 'REACT', nodes: '22.8k', updated: 'Yesterday', density: 'medium' }
    ];

    useEffect(() => {
        loadRepos();
        // Poll for updates every 3 seconds
        const interval = setInterval(loadRepos, 10000);
        return () => clearInterval(interval);
    }, []);

    const loadRepos = async () => {
        // Don't show full loading spinner on poll updates
        if (repos.length === 0) setLoading(true);

        try {
            const res = await api.get('/api/github/repos', { headers: { 'x-iam-role': 'sde_ii' } });
            const repoData = Array.isArray(res.data) ? res.data : (res.data.repos || []);

            if (repoData.length === 0) {
                setRepos([]);
            } else {
                setRepos(repoData.map((r) => ({
                    id: r.id,
                    name: r.name,
                    lang: r.language || 'UNKNOWN',
                    nodes: r.nodes_count || 0,
                    updated: r.last_indexed_at ? new Date(r.last_indexed_at).toLocaleTimeString() : 'N/A',
                    status: r.status || 'ready',
                    error: r.error_message
                })));
            }
        } catch (e) {
            console.error("Failed to load repos", e);
        } finally {
            setLoading(false);
        }
    };

    const handleOpenInspector = (repo) => {
        setSelectedRepo(repo);
        setInspectorOpen(true);
    };

    return (
        <>
            <div className="space-y-6">
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="heading-1">Source Code Repositories</h1>
                        <p className="heading-2 text-slate-400">Manage AST parsing and Tree-sitter indexing for connected codebases.</p>
                    </div>
                    <button
                        onClick={() => setAddRepoOpen(true)}
                        className="px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white rounded-lg font-medium flex items-center gap-2 shadow-lg shadow-purple-500/20 transition-all"
                    >
                        <Plus size={18} />
                        <span>Add Repository</span>
                    </button>
                </div>

                {loading ? (
                    <div className="flex items-center justify-center py-12">
                        <Loader2 className="w-8 h-8 text-purple-500 animate-spin" />
                    </div>
                ) : (
                    <div className="space-y-4">
                        {repos.map((repo, idx) => (
                            <div key={idx} className="glass-card p-5 flex items-center justify-between group">
                                <div className="flex items-center gap-5">
                                    <div className={`w-12 h-12 rounded-xl border flex items-center justify-center
                                        ${repo.status === 'ready' ? 'bg-purple-900/30 border-purple-500/30' :
                                            repo.status === 'error' ? 'bg-red-900/30 border-red-500/30' :
                                                'bg-blue-900/30 border-blue-500/30 animate-pulse'}`}>
                                        {repo.status === 'ready' ? <GitBranch size={24} className="text-purple-400" /> :
                                            repo.status === 'error' ? <X size={24} className="text-red-400" /> :
                                                <Loader2 size={24} className="text-blue-400 animate-spin" />}
                                    </div>
                                    <div>
                                        <div className="flex items-center gap-3">
                                            <h3 className="text-lg font-bold text-slate-100 group-hover:text-purple-400 transition-colors">
                                                {repo.name}
                                            </h3>
                                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold border tracking-wider uppercase
                                                ${repo.status === 'ready' ? 'bg-slate-800 border-slate-700 text-slate-400' :
                                                    repo.status === 'error' ? 'bg-red-900/20 border-red-500/30 text-red-400' :
                                                        'bg-blue-900/20 border-blue-500/30 text-blue-400'
                                                }`}>
                                                {repo.status}
                                            </span>
                                        </div>
                                        <div className="flex items-center gap-4 text-xs text-slate-500 mt-1.5 font-mono">
                                            {repo.status === 'error' ? (
                                                <span className="text-red-400">{repo.error || "Unknown Error"}</span>
                                            ) : (
                                                <>
                                                    <div className="flex items-center gap-1.5">
                                                        <GitBranch size={12} />
                                                        <span>{repo.nodes} AST Nodes</span>
                                                    </div>
                                                    <div className="flex items-center gap-1.5">
                                                        <RefreshCw size={12} />
                                                        <span>Updated {repo.updated}</span>
                                                    </div>
                                                </>
                                            )}
                                        </div>
                                    </div>
                                </div>

                                {/* Actions */}
                                <div className="flex items-center gap-2">
                                    <button
                                        onClick={() => handleOpenInspector(repo)}
                                        disabled={repo.status !== 'ready'}
                                        className="p-2 text-slate-500 hover:text-purple-400 hover:bg-purple-900/20 rounded-lg transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                                        title="Inspect Repository"
                                    >
                                        <Eye size={18} />
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Inspector Modal */}
            <RepoInspectorModal
                isOpen={inspectorOpen}
                onClose={() => setInspectorOpen(false)}
                repoId={selectedRepo?.id}
                repoName={selectedRepo?.name}
            />

            {/* Add Repo Modal */}
            <AddRepoModal
                isOpen={addRepoOpen}
                onClose={() => setAddRepoOpen(false)}
                onAdded={loadRepos}
            />
        </>
    );
};

export default RepositoriesView;
