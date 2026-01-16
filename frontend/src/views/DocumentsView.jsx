
import { Upload, FileText, RefreshCw, CheckCircle, Trash2, Loader2 } from 'lucide-react';
import api from '../services/api';

const DocumentsView = () => {
    const [documents, setDocuments] = useState([]);
    const [loading, setLoading] = useState(true);
    const [uploading, setUploading] = useState(false);
    const [isDragging, setIsDragging] = useState(false);

    useEffect(() => {
        loadDocuments();
    }, []);

    const loadDocuments = async () => {
        try {
            const docs = await api.documentAPI.list('sde_ii');
            // enhance docs with status if missing (mocking status for now as backend might not return it fully)
            const enhancedDocs = docs.map(d => ({
                ...d,
                status: d.status || 'Indexed',
                size: d.file_size ? (d.file_size / 1024 / 1024).toFixed(2) + ' MB' : 'Unknown',
                date: new Date(d.uploaded_at).toLocaleDateString()
            }));
            setDocuments(enhancedDocs);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const handleDrop = async (e) => {
        e.preventDefault();
        setIsDragging(false);
        const files = Array.from(e.dataTransfer.files);
        if (files.length > 0) handleUpload(files[0]);
    };

    const handleUpload = async (file) => {
        setUploading(true);
        try {
            await api.documentAPI.upload(file, 'sde_ii');
            await loadDocuments();
        } catch (e) {
            console.error("Upload failed", e);
        } finally {
            setUploading(false);
        }
    };

    return (
        <div className="flex-1 p-8 overflow-y-auto h-full">
            <div className="max-w-5xl mx-auto space-y-8">
                <div className="flex justify-between items-center">
                    <div>
                        <h2 className="text-2xl font-bold text-white mb-1">Knowledge Base</h2>
                        <p className="text-slate-400 text-sm">Upload and manage vectorized documents for RAG context.</p>
                    </div>
                    <button className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg flex items-center text-sm font-medium shadow-lg shadow-blue-900/20 transition-all hover:translate-y-px">
                        <Upload className="w-4 h-4 mr-2" /> Upload Files
                    </button>
                </div>

                {/* Drag Drop Zone */}
                <div
                    onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                    onDragLeave={() => setIsDragging(false)}
                    onDrop={handleDrop}
                    className={`border-2 border-dashed rounded-xl p-12 text-center transition-all cursor-pointer group
                        ${isDragging ? 'border-blue-500 bg-blue-500/10' : 'border-slate-700 bg-slate-800/20 hover:bg-slate-800/40 hover:border-blue-500/50'}
                    `}
                >
                    {uploading ? (
                        <div className="flex flex-col items-center">
                            <Loader2 className="w-10 h-10 text-blue-500 animate-spin mb-4" />
                            <h3 className="text-lg font-medium text-slate-300">Processing Document...</h3>
                            <p className="text-slate-500 text-sm mt-1">Vectorizing content for semantic search</p>
                        </div>
                    ) : (
                        <>
                            <div className="w-16 h-16 bg-slate-800 rounded-full flex items-center justify-center mx-auto mb-4 group-hover:bg-slate-700 transition-colors shadow-lg">
                                <Upload className="w-8 h-8 text-slate-400 group-hover:text-blue-400" />
                            </div>
                            <h3 className="text-lg font-medium text-slate-300">Drag & Drop files here</h3>
                            <p className="text-slate-500 text-sm mt-1">Support for PDF, DOCX, TXT (Max 50MB)</p>
                        </>
                    )}
                </div>

                {/* File List */}
                <div className="bg-slate-900/50 border border-slate-700 rounded-xl overflow-hidden shadow-sm">
                    <div className="px-6 py-4 border-b border-slate-700 flex justify-between items-center bg-slate-800/30">
                        <h3 className="text-sm font-bold text-slate-300 uppercase tracking-wider">Indexed Documents</h3>
                        <span className="text-xs bg-slate-800 px-2 py-1 rounded text-slate-400 border border-slate-700">Total: {documents.length}</span>
                    </div>
                    <div className="divide-y divide-slate-800">
                        {loading && <div className="p-8 text-center text-slate-500">Loading documents...</div>}
                        {!loading && documents.length === 0 && <div className="p-8 text-center text-slate-500">No documents found.</div>}

                        {documents.map((doc, i) => (
                            <div key={i} className="px-6 py-4 flex items-center justify-between hover:bg-slate-800/30 transition-colors group">
                                <div className="flex items-center space-x-4">
                                    <div className="p-2.5 bg-blue-900/20 rounded-lg text-blue-400 border border-blue-900/30">
                                        <FileText className="w-5 h-5" />
                                    </div>
                                    <div>
                                        <p className="text-sm font-semibold text-slate-200 group-hover:text-blue-400 transition-colors">{doc.key || doc.original_filename || doc.name}</p>
                                        <p className="text-xs text-slate-500 mt-0.5">{doc.size || 'N/A'} • Uploaded {doc.date || 'Unknown'}</p>
                                    </div>
                                </div>
                                <div className="flex items-center space-x-6">
                                    <div className="flex items-center">
                                        {doc.status === 'Processing' ? (
                                            <div className="flex items-center text-blue-400 text-xs bg-blue-900/20 px-2.5 py-1 rounded-full border border-blue-900/30 font-medium">
                                                <RefreshCw className="w-3 h-3 mr-2 animate-spin" /> {doc.status}
                                            </div>
                                        ) : (
                                            <div className="flex items-center text-emerald-500 text-xs bg-emerald-900/20 px-2.5 py-1 rounded-full border border-emerald-900/30 font-medium">
                                                <CheckCircle className="w-3 h-3 mr-2" /> {doc.status || 'Indexed'}
                                            </div>
                                        )}
                                    </div>
                                    <button className="p-2 text-slate-600 hover:text-red-400 hover:bg-red-900/20 rounded transition-colors opacity-0 group-hover:opacity-100">
                                        <Trash2 className="w-4 h-4" />
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default DocumentsView;
