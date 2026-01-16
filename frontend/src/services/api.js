/**
 * API Service for Enterprise Copilot
 * Handles all communication with the FastAPI backend
 */

import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Create axios instance with defaults
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000, // 2 minutes for LLM responses
  headers: {
    'Content-Type': 'application/json'
  }
});

// Request interceptor to add IAM role header
apiClient.interceptors.request.use(
  (config) => {
    // Get current role from somewhere (could be context, local storage, etc.)
    const currentRole = window.currentIAMRole || 'CHIEF_STRATEGY_OFFICER';
    config.headers['x-iam-role'] = currentRole;
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      // Server responded with error status
      console.error('API Error:', error.response.data);

      if (error.response.status === 403) {
        // IAM denial - show appropriate message
        return Promise.reject({
          type: 'IAM_DENIAL',
          message: error.response.data.detail || 'Access denied',
          ...error.response.data
        });
      }
    }
    return Promise.reject(error);
  }
);

/**
 * Chat API
 */
export const chatAPI = {
  /**
   * Send a query to the copilot (legacy linear pipeline)
   */
  sendQuery: async (query, iamRole, sessionId = null) => {
    window.currentIAMRole = iamRole; // Set for interceptor

    const response = await apiClient.post('/api/chat', {
      query,
      conversation_id: sessionId,
      context: {}
    });

    return response.data;
  },

  /**
   * Send a query using the agentic ReAct loop
   */
  sendAgentQuery: async (query, iamRole, sessionId = null) => {
    window.currentIAMRole = iamRole;

    const response = await apiClient.post('/api/chat/agent', {
      query,
      conversation_id: sessionId
    });

    return response.data;
  },

  /**
   * Stream a query response using SSE
   * Returns an async iterator of events
   */
  streamQuery: async function* (query, iamRole, sessionId = null) {
    const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';

    const response = await fetch(`${baseUrl}/api/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-iam-role': iamRole
      },
      body: JSON.stringify({
        query,
        conversation_id: sessionId
      })
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            yield data;
          } catch (e) {
            console.warn('Failed to parse SSE data:', line);
          }
        }
      }
    }
  }
};

/**
 * Personas API
 */
export const personasAPI = {
  /**
   * Get all available personas
   */
  getAll: async () => {
    const response = await apiClient.get('/api/personas');
    return response.data;
  }
};

/**
 * Audit Logs API
 */
export const auditAPI = {
  /**
   * Get recent audit logs
   */
  getLogs: async (limit = 50, iamRole) => {
    window.currentIAMRole = iamRole;

    const response = await apiClient.get('/api/audit/logs', {
      params: { limit }
    });

    return response.data;
  },

  /**
   * Connect to audit log WebSocket stream
   */
  connectStream: (onMessage, onError = null) => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/audit`;

    const ws = new WebSocket(wsUrl);

    ws.onmessage = (event) => {
      try {
        const log = JSON.parse(event.data);
        onMessage(log);
      } catch (e) {
        console.error('Failed to parse audit log:', e);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      if (onError) onError(error);
    };

    ws.onclose = () => {
      console.log('Audit stream disconnected');
    };

    return ws;
  }
};

/**
 * Ingestion API
 */
export const ingestionAPI = {
  /**
   * Trigger document ingestion
   */
  ingestDocuments: async (iamRole) => {
    window.currentIAMRole = iamRole;

    const response = await apiClient.post('/api/ingest/documents');
    return response.data;
  },

  /**
   * Index codebase
   */
  indexCodebase: async (path, iamRole) => {
    window.currentIAMRole = iamRole;

    const response = await apiClient.post('/api/ingest/codebase', null, {
      params: { path }
    });

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
