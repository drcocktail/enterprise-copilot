import React, { useState, useEffect, useCallback } from 'react';
import { Upload, FileText, Trash2, CheckCircle, XCircle, Loader2, FolderOpen } from 'lucide-react';
import { documentAPI } from '../services/api';

export const DocumentsPanel = ({ activePersona }) => {
    const [documents, setDocuments] = useState([]);
    const [uploading, setUploading] = useState(false);
    const [isDragging, setIsDragging] = useState(false);
    const [error, setError] = useState(null);

    const loadDocuments = useCallback(async () => {
        try {
            const docs = await documentAPI.list(activePersona.role);
            setDocuments(docs);
        } catch (e) {
            console.error('Failed to load documents:', e);
        }
    }, [activePersona.role]);

    useEffect(() => {
        loadDocuments();
    }, [loadDocuments]);

    const handleUpload = async (files) => {
        setUploading(true);
        setError(null);

        for (const file of files) {
            if (!file.name.toLowerCase().endsWith('.pdf')) {
                setError('Only PDF files are supported');
                continue;
            }

            try {
                await documentAPI.upload(file, activePersona.role);
            } catch (e) {
                setError(`Failed to upload ${file.name}`);
                console.error('Upload error:', e);
            }
        }

        setUploading(false);
        loadDocuments();
    };

    const handleDelete = async (docId) => {
        if (!confirm('Are you sure you want to delete this document?')) return;

        try {
            await documentAPI.delete(docId, activePersona.role);
            loadDocuments();
        } catch (e) {
            setError('Failed to delete document');
        }
    };

    const handleDragOver = (e) => {
        e.preventDefault();
        setIsDragging(true);
    };

    const handleDragLeave = (e) => {
        e.preventDefault();
        setIsDragging(false);
    };

    const handleDrop = (e) => {
        e.preventDefault();
        setIsDragging(false);

        const files = Array.from(e.dataTransfer.files).filter(f => f.name.toLowerCase().endsWith('.pdf'));
        if (files.length > 0) {
            handleUpload(files);
        }
    };

    const handleFileSelect = (e) => {
        const files = Array.from(e.target.files);
        if (files.length > 0) {
            handleUpload(files);
        }
    };

    const formatFileSize = (bytes) => {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    };

    const formatDate = (dateStr) => {
        return new Date(dateStr).toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    return (
        <div className="flex-1 overflow-y-auto p-6 bg-stone-50">
            <h1 className="text-2xl font-bold text-stone-800 mb-6">Documents</h1>

            {/* Upload Zone */}
            <div
                className={`border-2 border-dashed rounded-2xl p-8 text-center transition-all mb-6 ${isDragging
                        ? 'border-violet-500 bg-violet-50'
                        : 'border-stone-300 bg-white hover:border-violet-300'
                    }`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
            >
                <input
                    type="file"
                    accept=".pdf"
                    multiple
                    onChange={handleFileSelect}
                    className="hidden"
                    id="file-upload"
                />

                {uploading ? (
                    <div className="flex flex-col items-center gap-3">
                        <Loader2 size={32} className="animate-spin text-violet-500" />
                        <p className="text-stone-600">Uploading...</p>
                    </div>
                ) : (
                    <label htmlFor="file-upload" className="cursor-pointer flex flex-col items-center gap-3">
                        <div className="w-16 h-16 rounded-2xl bg-violet-100 flex items-center justify-center">
                            <Upload size={28} className="text-violet-600" />
                        </div>
                        <div>
                            <p className="text-stone-700 font-medium">Drop PDFs here or click to browse</p>
                            <p className="text-sm text-stone-400 mt-1">Only PDF files are supported</p>
                        </div>
                    </label>
                )}
            </div>

            {error && (
                <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-xl text-red-600 text-sm flex items-center gap-2">
                    <XCircle size={16} />
                    {error}
                </div>
            )}

            {/* Document List */}
            <div className="space-y-3">
                {documents.length === 0 ? (
                    <div className="text-center py-12 text-stone-400">
                        <FolderOpen size={48} className="mx-auto mb-3 opacity-50" />
                        <p>No documents uploaded yet</p>
                        <p className="text-sm mt-1">Upload PDFs to chat with your documents</p>
                    </div>
                ) : (
                    documents.map(doc => (
                        <div
                            key={doc.id}
                            className="bg-white rounded-xl p-4 shadow-soft flex items-center gap-4"
                        >
                            <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${doc.status === 'ready' ? 'bg-emerald-100' :
                                    doc.status === 'error' ? 'bg-red-100' : 'bg-amber-100'
                                }`}>
                                <FileText size={20} className={
                                    doc.status === 'ready' ? 'text-emerald-600' :
                                        doc.status === 'error' ? 'text-red-600' : 'text-amber-600'
                                } />
                            </div>

                            <div className="flex-1 min-w-0">
                                <p className="font-medium text-stone-700 truncate">{doc.original_filename}</p>
                                <div className="flex items-center gap-3 text-xs text-stone-400 mt-1">
                                    <span>{formatFileSize(doc.file_size)}</span>
                                    <span>•</span>
                                    <span>{doc.chunk_count} chunks</span>
                                    <span>•</span>
                                    <span>{formatDate(doc.uploaded_at)}</span>
                                </div>
                            </div>

                            <div className="flex items-center gap-2">
                                {doc.status === 'ready' && (
                                    <span className="flex items-center gap-1 px-2 py-1 bg-emerald-100 text-emerald-600 rounded-lg text-xs font-medium">
                                        <CheckCircle size={12} />
                                        Ready
                                    </span>
                                )}
                                {doc.status === 'processing' && (
                                    <span className="flex items-center gap-1 px-2 py-1 bg-amber-100 text-amber-600 rounded-lg text-xs font-medium">
                                        <Loader2 size={12} className="animate-spin" />
                                        Processing
                                    </span>
                                )}
                                {doc.status === 'error' && (
                                    <span className="flex items-center gap-1 px-2 py-1 bg-red-100 text-red-600 rounded-lg text-xs font-medium" title={doc.error_message}>
                                        <XCircle size={12} />
                                        Error
                                    </span>
                                )}

                                <button
                                    onClick={() => handleDelete(doc.id)}
                                    className="p-2 rounded-lg hover:bg-red-50 text-stone-400 hover:text-red-500 transition-colors"
                                >
                                    <Trash2 size={16} />
                                </button>
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
};
