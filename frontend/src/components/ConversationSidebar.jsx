import React, { useState, useEffect } from 'react';
import { MessageSquare, Plus, Trash2, Clock, ChevronRight } from 'lucide-react';
import api from '../services/api';
import { motion, AnimatePresence } from 'framer-motion';

const ConversationSidebar = ({
    currentConversationId,
    onSelectConversation,
    onNewChat,
    iamRole = 'senior_engineer'
}) => {
    const [conversations, setConversations] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadConversations();
    }, []);

    const loadConversations = async () => {
        try {
            const convos = await api.conversationAPI.list(iamRole);
            setConversations(convos || []);
        } catch (e) {
            console.error("Failed to load conversations:", e);
        } finally {
            setLoading(false);
        }
    };

    const handleNewChat = async () => {
        try {
            const newConvo = await api.conversationAPI.create(iamRole);
            setConversations(prev => [newConvo, ...prev]);
            onNewChat(newConvo.id);
        } catch (e) {
            console.error("Failed to create conversation:", e);
        }
    };

    const handleDelete = async (e, convoId) => {
        e.stopPropagation();
        try {
            await api.conversationAPI.delete(convoId, iamRole);
            setConversations(prev => prev.filter(c => c.id !== convoId));
            if (currentConversationId === convoId) {
                onNewChat(null);
            }
        } catch (e) {
            console.error("Failed to delete conversation:", e);
        }
    };

    const formatDate = (dateStr) => {
        if (!dateStr) return '';
        const date = new Date(dateStr);
        const now = new Date();
        const diff = now - date;

        if (diff < 60000) return 'Just now';
        if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
        if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
        return date.toLocaleDateString();
    };

    return (
        <div className="h-full flex flex-col bg-[#0B1120] border-r border-slate-800/50">
            {/* Header */}
            <div className="p-4 border-b border-slate-800/50">
                <button
                    onClick={handleNewChat}
                    className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-xl font-medium transition-all shadow-lg shadow-blue-900/30 hover:shadow-blue-900/50"
                >
                    <Plus size={18} />
                    <span>New Chat</span>
                </button>
            </div>

            {/* Conversation List */}
            <div className="flex-1 overflow-y-auto custom-scrollbar p-2 space-y-1">
                {loading && (
                    <div className="p-4 text-center text-slate-500 text-sm">
                        Loading conversations...
                    </div>
                )}

                {!loading && conversations.length === 0 && (
                    <div className="p-4 text-center text-slate-500 text-sm">
                        <MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-30" />
                        No conversations yet
                    </div>
                )}

                <AnimatePresence>
                    {conversations.map((convo) => (
                        <motion.button
                            key={convo.id}
                            initial={{ opacity: 0, x: -20 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: -20 }}
                            onClick={() => onSelectConversation(convo.id)}
                            className={`
                                w-full flex items-start gap-3 p-3 rounded-lg text-left transition-all group
                                ${currentConversationId === convo.id
                                    ? 'bg-blue-600/10 border border-blue-500/20 text-white'
                                    : 'hover:bg-slate-800/50 text-slate-400 hover:text-white border border-transparent'}
                            `}
                        >
                            <MessageSquare size={16} className="mt-0.5 flex-shrink-0" />
                            <div className="flex-1 min-w-0">
                                <p className="text-sm font-medium truncate">
                                    {convo.title || 'New conversation'}
                                </p>
                                <div className="flex items-center gap-2 mt-1">
                                    <Clock size={10} className="text-slate-600" />
                                    <span className="text-[10px] text-slate-600">
                                        {formatDate(convo.updated_at || convo.created_at)}
                                    </span>
                                </div>
                            </div>

                            {currentConversationId === convo.id ? (
                                <ChevronRight size={14} className="text-blue-400 mt-0.5" />
                            ) : (
                                <button
                                    onClick={(e) => handleDelete(e, convo.id)}
                                    className="p-1 text-slate-600 hover:text-red-400 hover:bg-red-900/20 rounded opacity-0 group-hover:opacity-100 transition-all"
                                >
                                    <Trash2 size={12} />
                                </button>
                            )}
                        </motion.button>
                    ))}
                </AnimatePresence>
            </div>

            {/* Footer */}
            <div className="p-3 border-t border-slate-800/50 text-center">
                <span className="text-[10px] text-slate-600">
                    {conversations.length} conversation{conversations.length !== 1 ? 's' : ''}
                </span>
            </div>
        </div>
    );
};

export default ConversationSidebar;
