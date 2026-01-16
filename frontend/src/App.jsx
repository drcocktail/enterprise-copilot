import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import ChatView from './views/ChatView';

import DocumentsView from './views/DocumentsView';
import RepositoriesView from './views/RepositoriesView';
import IntegrationsView from './views/IntegrationsView';
import IAMConfigView from './views/IAMConfigView';
import LiveOpsView from './views/LiveOpsView';

// We will implement these views in the next steps

const App = () => {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/chat" replace />} />
          <Route path="chat" element={<ChatView />} />
          <Route path="documents" element={<DocumentsView />} />
          <Route path="repos" element={<RepositoriesView />} />
          <Route path="integrations" element={<IntegrationsView />} />
          <Route path="iam" element={<IAMConfigView />} />
          <Route path="live-console" element={<LiveOpsView />} />
        </Route>
      </Routes>
    </Router>
  );
};

export default App;
