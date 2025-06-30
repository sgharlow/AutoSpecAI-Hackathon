# AutoSpec.AI Frontend

A modern React-based web application for collaborative document processing and requirements analysis.

## Features

### 🚀 Core Functionality
- **Document Management**: Upload, process, and manage documents (PDF, DOCX, TXT, RTF)
- **Real-time Collaboration**: WebSocket-powered collaborative editing with presence awareness
- **AI-Powered Analysis**: Automated requirements extraction using Amazon Bedrock
- **Version Control**: Complete document versioning with diff visualization
- **Approval Workflows**: Configurable multi-step approval processes
- **Comments & Annotations**: Threaded commenting system with resolution tracking

### 🎨 User Experience
- **Responsive Design**: Mobile-first design that works on all devices
- **Dark/Light Theme**: User-configurable theme preferences
- **Real-time Updates**: Live notifications and status updates
- **Offline Support**: Progressive Web App capabilities
- **Accessibility**: WCAG 2.1 AA compliance

### 🛠 Technical Features
- **Monaco Editor**: Professional code editor with syntax highlighting
- **WebSocket Integration**: Real-time collaboration and notifications
- **Redux Toolkit**: Centralized state management
- **Material-UI**: Consistent design system
- **TypeScript**: Type-safe development
- **Performance Optimized**: Code splitting and lazy loading

## Technology Stack

- **Framework**: React 18 with TypeScript
- **State Management**: Redux Toolkit
- **UI Library**: Material-UI (MUI) v5
- **Editor**: Monaco Editor
- **Real-time**: Socket.IO Client
- **HTTP Client**: Axios
- **Routing**: React Router v6
- **Date Handling**: date-fns
- **Build Tool**: Create React App
- **Testing**: Jest + React Testing Library

## Project Structure

```
src/
├── components/           # Reusable UI components
│   ├── auth/            # Authentication components
│   ├── collaboration/   # Real-time collaboration features
│   ├── common/          # Shared components
│   ├── dashboard/       # Dashboard-specific components
│   ├── documents/       # Document management components
│   ├── layout/          # Layout and navigation
│   ├── notifications/   # Notification system
│   └── workflows/       # Workflow management
├── contexts/            # React contexts
│   ├── AuthContext.tsx
│   ├── NotificationContext.tsx
│   └── WebSocketContext.tsx
├── pages/               # Page components
│   ├── analytics/       # Analytics and reporting
│   ├── auth/           # Login and authentication
│   ├── collaboration/  # Collaboration hub
│   ├── dashboard/      # Main dashboard
│   ├── documents/      # Document pages
│   ├── settings/       # User settings
│   └── workflows/      # Workflow management
├── services/           # API and external services
│   ├── api/            # API client modules
│   ├── auth.ts         # Authentication service
│   ├── websocket.ts    # WebSocket service
│   └── storage.ts      # Local storage utilities
├── store/              # Redux store
│   ├── slices/         # Redux slices
│   └── store.ts        # Store configuration
├── types/              # TypeScript type definitions
├── utils/              # Utility functions
├── App.tsx             # Main application component
└── index.tsx           # Application entry point
```

## Getting Started

### Prerequisites
- Node.js 16+ and npm/yarn
- Access to AutoSpec.AI backend API
- WebSocket endpoint for real-time features

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd AutoSpecAI/frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env.local
   ```
   
   Configure the following variables:
   ```env
   REACT_APP_API_URL=https://api.autospec.ai
   REACT_APP_WEBSOCKET_ENDPOINT=wss://ws.autospec.ai
   REACT_APP_ENVIRONMENT=development
   ```

4. **Start the development server**
   ```bash
   npm start
   ```

5. **Open your browser**
   Navigate to `http://localhost:3000`

## Available Scripts

- **`npm start`**: Start development server
- **`npm run build`**: Create production build
- **`npm test`**: Run test suite
- **`npm run lint`**: Run ESLint
- **`npm run lint:fix`**: Fix ESLint issues
- **`npm run format`**: Format code with Prettier
- **`npm run type-check`**: Run TypeScript type checking
- **`npm run analyze`**: Analyze bundle size

## Development

### Code Style
- **TypeScript**: Strict mode enabled with comprehensive type definitions
- **ESLint**: Extended from `react-app` with additional rules
- **Prettier**: Consistent code formatting
- **Naming**: PascalCase for components, camelCase for functions/variables

### Component Guidelines
- Use functional components with hooks
- Implement proper error boundaries
- Include loading and error states
- Write comprehensive TypeScript interfaces
- Follow Material-UI design patterns

### State Management
- Use Redux Toolkit for global state
- Local state with `useState` for component-specific data
- Context for cross-cutting concerns (auth, websocket)
- Async operations with `createAsyncThunk`

### Real-time Features
- WebSocket connection managed by context
- Automatic reconnection with exponential backoff
- Presence tracking and collaborative cursors
- Operational transformation for conflict resolution

## API Integration

### Authentication
```typescript
// Login with credentials
const response = await authAPI.login({ email, password });

// SSO login
const response = await authAPI.loginWithSSO('google');

// Refresh token
const response = await authAPI.refreshToken(refreshToken);
```

### Document Operations
```typescript
// Upload document
const document = await documentsAPI.uploadDocument(file, metadata);

// Process with AI
const result = await documentsAPI.processDocument(documentId);

// Real-time collaboration
const session = await collaborationAPI.startSession(documentId);
```

### WebSocket Events
```typescript
// Document collaboration
socket.on('user_joined', handleUserJoined);
socket.on('document_change', handleDocumentChange);
socket.on('presence_update', handlePresenceUpdate);

// Workflow updates
socket.on('workflow_update', handleWorkflowUpdate);
socket.on('approval_required', handleApprovalRequired);
```

## Deployment

### Development
```bash
npm run deploy:dev
```

### Staging
```bash
npm run deploy:staging
```

### Production
```bash
npm run build
npm run deploy:prod
```

### Docker Deployment
```dockerfile
FROM node:16-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY build ./build
EXPOSE 3000
CMD ["npx", "serve", "-s", "build", "-l", "3000"]
```

## Performance Optimization

### Code Splitting
- Route-based splitting with React.lazy()
- Component-level splitting for large features
- Dynamic imports for heavy libraries

### Caching Strategy
- Service worker for offline support
- HTTP caching for static assets
- Redis caching for API responses
- Local storage for user preferences

### Bundle Optimization
- Tree shaking for unused code elimination
- Asset compression and minification
- CDN delivery for static assets
- Progressive loading for images

## Testing

### Unit Tests
```bash
npm test -- --coverage
```

### Integration Tests
```bash
npm run test:integration
```

### E2E Tests
```bash
npm run test:e2e
```

### Testing Strategy
- **Unit**: Individual component testing
- **Integration**: API integration and state management
- **E2E**: Critical user workflows
- **Performance**: Bundle size and runtime performance

## Troubleshooting

### Common Issues

1. **WebSocket Connection Failed**
   - Check REACT_APP_WEBSOCKET_ENDPOINT configuration
   - Verify backend WebSocket server is running
   - Check network firewall settings

2. **Authentication Issues**
   - Clear browser storage and cookies
   - Verify API endpoint configuration
   - Check token expiration

3. **Build Failures**
   - Clear node_modules and reinstall
   - Check Node.js version compatibility
   - Verify all environment variables

### Debug Mode
```bash
REACT_APP_DEBUG=true npm start
```

## Contributing

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Make your changes**
4. **Add tests for new functionality**
5. **Run the test suite**
   ```bash
   npm test
   npm run lint
   npm run type-check
   ```
6. **Commit your changes**
   ```bash
   git commit -m "Add amazing feature"
   ```
7. **Push to your branch**
   ```bash
   git push origin feature/amazing-feature
   ```
8. **Open a Pull Request**

## License

This project is proprietary and confidential. All rights reserved.

## Support

For technical support and questions:
- **Documentation**: [AutoSpec.AI Docs](https://docs.autospec.ai)
- **Support Email**: support@autospec.ai
- **Community**: [AutoSpec.AI Community](https://community.autospec.ai)