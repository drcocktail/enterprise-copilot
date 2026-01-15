# Enterprise Copilot Frontend

React frontend for the IAM-First Agentic Enterprise Assistant.

## Features

- **Dynamic Persona Switching**: Simulate different user roles (C-Suite, HR, IT)
- **Real-time Chat Interface**: Natural language interaction with the copilot
- **IAM-Aware UI**: Visual feedback on permission boundaries
- **Live Audit Logs**: Real-time streaming of authorization checks via WebSocket
- **Rich Attachments**: Interactive cards for tickets, code snippets, calendars, and more
- **Source Citations**: Automatic citations from RAG retrieval
- **Health Monitoring**: Real-time service health status

## Tech Stack

- **React 18** - UI framework
- **Vite** - Build tool and dev server
- **Tailwind CSS** - Styling
- **Axios** - HTTP client
- **Lucide React** - Icon library

## Setup

### Install Dependencies

```bash
cd frontend
npm install
```

### Environment Configuration

Create a `.env` file (optional):

```env
VITE_API_URL=http://localhost:8000
```

### Development Server

```bash
npm run dev
```

The app will be available at `http://localhost:3000`

### Build for Production

```bash
npm run build
npm run preview
```

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── IAMBadge.jsx          # IAM context indicator
│   │   ├── ChatMessage.jsx       # Chat message with attachments
│   │   ├── DashboardWidget.jsx   # Dashboard metrics widget
│   │   └── AuditLogPanel.jsx     # Live audit log viewer
│   ├── services/
│   │   └── api.js                # Backend API client
│   ├── App.jsx                   # Main application
│   ├── main.jsx                  # Entry point
│   └── index.css                 # Global styles
├── index.html
├── vite.config.js
├── tailwind.config.js
└── package.json
```

## API Integration

The frontend communicates with the FastAPI backend through:

1. **REST API** - Chat queries, persona management, audit logs
2. **WebSocket** - Real-time audit log streaming

All requests include the `x-iam-role` header for authorization.

### API Methods

```javascript
import { chatAPI, auditAPI, personasAPI } from './services/api';

// Send a chat query
const response = await chatAPI.sendQuery(query, iamRole);

// Get audit logs
const logs = await auditAPI.getLogs(50, iamRole);

// Stream audit logs
const ws = auditAPI.connectStream((log) => {
  console.log('New log:', log);
});

// Get available personas
const personas = await personasAPI.getAll();
```

## Features in Detail

### Persona Switching

Three personas with distinct permissions:

- **C-Suite Executive**: Financial reports, strategy documents
- **HR Director**: Employee data, policies
- **DevOps Engineer**: Codebase access, infrastructure

### IAM Enforcement

- Pre-query validation with visual feedback
- Denied requests show clear error messages
- All actions logged to audit trail

### Rich Attachments

The copilot can return structured data:

- **TICKET**: Jira-style ticket cards
- **CODE**: Syntax-highlighted code snippets
- **CALENDAR**: Meeting slot suggestions
- **GANTT**: Project timeline visualization

### Audit Logging

Real-time audit panel shows:
- Timestamp
- Actor & IAM role
- Action type
- Status (ALLOWED/DENIED/ERROR)
- Trace ID for debugging

## Customization

### Adding New Personas

Edit `src/services/api.js` to add more personas. Backend must also be updated.

### Styling

Tailwind CSS classes are used throughout. Modify `tailwind.config.js` for theme changes.

### Dark Mode

Dark mode is supported via Tailwind's `dark:` prefix. Toggle based on system preference.

## Troubleshooting

### Connection Issues

```bash
# Ensure backend is running
curl http://localhost:8000/api/health

# Check CORS configuration
# Vite proxy should handle this automatically
```

### WebSocket Fails

WebSocket connections may require proper proxy configuration in `vite.config.js`.

### Build Errors

```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
```

## Production Considerations

1. **Environment Variables**: Set `VITE_API_URL` for production backend
2. **Build Optimization**: Run `npm run build` for optimized bundle
3. **CDN**: Consider serving static assets from CDN
4. **Error Tracking**: Integrate Sentry or similar
5. **Analytics**: Add analytics for user interactions

## Testing

```bash
# Run linter
npm run lint

# For future: Add tests
npm test
```
