/**
 * API Service for Enterprise Copilot
 * Handles all communication with the FastAPI backend
 */

import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// ... (existing code)

/**
 * Ingestion API
 */
export const ingestionAPI = {
  /**
   * Trigger document ingestion
   */
  ingestDocuments: async (iamRole) => {
    window.currentIAMRole = iamRole;

    // Fixed path to match backend/routers/ingestion.py
    const response = await apiClient.post('/api/documents/upload');
    return response.data;
  },

  /**
   * Index codebase
   */
  indexCodebase: async (path, iamRole) => {
    window.currentIAMRole = iamRole;

    const response = await apiClient.post('/api/repos/ingest', { url: path }); // Fix: Send JSON body "url" not path param if that's what backend expects.
    // Backend ingestion.py expects RepoRequest(url: str).
    // The previous api.js sent null and params {path}. 
    // New router expects body: { "url": "..." }.

    return response.data;
  }
};

/**
 * Health Check
 */
export const healthAPI = {
  check: async () => {
    const response = await apiClient.get('/api/health');
    return response.data;
  }
};

/**
 * Conversation API
 */
export const conversationAPI = {
  /**
   * List all conversations
   */
  list: async (iamRole) => {
    window.currentIAMRole = iamRole;
    const response = await apiClient.get('/api/conversations');
    return response.data.conversations;
  },

  /**
   * Create a new conversation
   */
  create: async (iamRole, title = null) => {
    window.currentIAMRole = iamRole;
    const response = await apiClient.post('/api/conversations', { title });
    return response.data;
  },

  /**
   * Get conversation with messages
   */
  get: async (conversationId, iamRole) => {
    window.currentIAMRole = iamRole;
    const response = await apiClient.get(`/api/conversations/${conversationId}`);
    return response.data;
  },

  /**
   * Get messages for a conversation
   */
  getMessages: async (conversationId, iamRole, limit = 100) => {
    window.currentIAMRole = iamRole;
    const response = await apiClient.get(`/api/conversations/${conversationId}/messages`, {
      params: { limit }
    });
    return response.data.messages;
  },

  /**
   * Add message to conversation
   */
  addMessage: async (conversationId, iamRole, role, content, metadata = null) => {
    window.currentIAMRole = iamRole;
    const response = await apiClient.post(`/api/conversations/${conversationId}/messages`, {
      role,
      content,
      metadata
    });
    return response.data;
  },

  /**
   * Delete a conversation
   */
  delete: async (conversationId, iamRole) => {
    window.currentIAMRole = iamRole;
    const response = await apiClient.delete(`/api/conversations/${conversationId}`);
    return response.data;
  }
};

/**
 * Document API
 */
export const documentAPI = {
  /**
   * List user's documents
   */
  list: async (iamRole) => {
    window.currentIAMRole = iamRole;
    const response = await apiClient.get('/api/documents');
    return response.data.documents;
  },

  /**
   * Upload a document
   */
  upload: async (file, iamRole) => {
    window.currentIAMRole = iamRole;

    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post('/api/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
    return response.data;
  },

  /**
   * Delete a document
   */
  delete: async (docId, iamRole) => {
    window.currentIAMRole = iamRole;
    const response = await apiClient.delete(`/api/documents/${docId}`);
    return response.data;
  }
};

// Unified API Export
const api = {
  // Direct Axios Methods
  get: (url, config) => apiClient.get(url, config),
  post: (url, data, config) => apiClient.post(url, data, config),
  put: (url, data, config) => apiClient.put(url, data, config),
  delete: (url, config) => apiClient.delete(url, config),

  // Modules
  chatAPI,
  personasAPI,
  auditAPI,
  ingestionAPI,
  healthAPI,
  conversationAPI,
  documentAPI
};

export default api;
