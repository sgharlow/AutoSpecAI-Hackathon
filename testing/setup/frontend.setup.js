/**
 * Frontend-specific Jest setup
 * Runs before frontend test files
 */

import '@testing-library/jest-dom';
import { configure } from '@testing-library/react';
import { server } from '../mocks/server';

// Configure React Testing Library
configure({
  testIdAttribute: 'data-testid',
  asyncUtilTimeout: 5000,
});

// Start mock service worker
beforeAll(() => {
  server.listen({
    onUnhandledRequest: 'warn',
  });
});

afterEach(() => {
  server.resetHandlers();
  // Clean up DOM
  document.body.innerHTML = '';
  // Clear all mocks
  jest.clearAllMocks();
  // Clear localStorage and sessionStorage
  localStorage.clear();
  sessionStorage.clear();
});

afterAll(() => {
  server.close();
});

// Mock React Router
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => jest.fn(),
  useLocation: () => ({
    pathname: '/test',
    search: '',
    hash: '',
    state: null,
  }),
  useParams: () => ({}),
}));

// Mock Material-UI components that cause issues in tests
jest.mock('@mui/material/useMediaQuery', () => ({
  __esModule: true,
  default: jest.fn(() => false),
}));

// Mock Monaco Editor
jest.mock('monaco-editor', () => ({
  editor: {
    create: jest.fn(() => ({
      getValue: jest.fn(() => 'mock content'),
      setValue: jest.fn(),
      getPosition: jest.fn(() => ({ lineNumber: 1, column: 1 })),
      focus: jest.fn(),
      dispose: jest.fn(),
      onDidChangeModelContent: jest.fn(() => ({ dispose: jest.fn() })),
      onDidChangeCursorPosition: jest.fn(() => ({ dispose: jest.fn() })),
      onDidFocusEditorText: jest.fn(() => ({ dispose: jest.fn() })),
      onDidBlurEditorText: jest.fn(() => ({ dispose: jest.fn() })),
      updateOptions: jest.fn(),
    })),
    defineTheme: jest.fn(),
    setTheme: jest.fn(),
  },
  Position: jest.fn(),
}));

// Mock Socket.IO
jest.mock('socket.io-client', () => ({
  io: jest.fn(() => ({
    on: jest.fn(),
    off: jest.fn(),
    emit: jest.fn(),
    connect: jest.fn(),
    disconnect: jest.fn(),
    connected: true,
  })),
}));

// Mock file upload
const mockFileUpload = {
  files: [],
  addEventListener: jest.fn(),
  removeEventListener: jest.fn(),
  dispatchEvent: jest.fn(),
};

Object.defineProperty(window.HTMLElement.prototype, 'files', {
  get: () => mockFileUpload.files,
  set: (files) => {
    mockFileUpload.files = files;
  },
});

// Mock drag and drop events
const createDataTransfer = (files = []) => ({
  files,
  items: files.map(file => ({
    kind: 'file',
    type: file.type,
    getAsFile: () => file,
  })),
  types: ['Files'],
});

// Helper to create mock files
global.createMockFile = (name = 'test.pdf', size = 1024, type = 'application/pdf') => {
  const file = new File(['mock content'], name, { type, lastModified: Date.now() });
  Object.defineProperty(file, 'size', { value: size });
  return file;
};

// Helper to create drag events
global.createDragEvent = (type, files = []) => {
  const event = new Event(type, { bubbles: true });
  event.dataTransfer = createDataTransfer(files);
  return event;
};

// Mock Intersection Observer for lazy loading
global.IntersectionObserver = class IntersectionObserver {
  constructor() {}
  observe() {}
  unobserve() {}
  disconnect() {}
};

// Mock clipboard API
Object.defineProperty(navigator, 'clipboard', {
  value: {
    writeText: jest.fn(() => Promise.resolve()),
    readText: jest.fn(() => Promise.resolve('mock text')),
  },
  writable: true,
});

// Mock geolocation
Object.defineProperty(navigator, 'geolocation', {
  value: {
    getCurrentPosition: jest.fn((success) =>
      success({
        coords: {
          latitude: 40.7128,
          longitude: -74.0060,
        },
      })
    ),
    watchPosition: jest.fn(),
    clearWatch: jest.fn(),
  },
  writable: true,
});

// Mock notifications
Object.defineProperty(window, 'Notification', {
  value: class Notification {
    constructor(title, options) {
      this.title = title;
      this.options = options;
    }
    static requestPermission = jest.fn(() => Promise.resolve('granted'));
    static permission = 'granted';
    close = jest.fn();
  },
  writable: true,
});

// Mock performance API
Object.defineProperty(window, 'performance', {
  value: {
    now: jest.fn(() => Date.now()),
    mark: jest.fn(),
    measure: jest.fn(),
    getEntriesByName: jest.fn(() => []),
    getEntriesByType: jest.fn(() => []),
  },
  writable: true,
});

// Custom matchers for better assertions
expect.extend({
  toBeInTheDocument(received) {
    const pass = received && document.body.contains(received);
    return {
      pass,
      message: () =>
        pass
          ? `Expected element not to be in the document`
          : `Expected element to be in the document`,
    };
  },

  toHaveClass(received, className) {
    const pass = received && received.classList.contains(className);
    return {
      pass,
      message: () =>
        pass
          ? `Expected element not to have class "${className}"`
          : `Expected element to have class "${className}"`,
    };
  },

  toBeVisible(received) {
    const pass = received && received.style.display !== 'none' && 
                 received.style.visibility !== 'hidden' &&
                 received.offsetParent !== null;
    return {
      pass,
      message: () =>
        pass
          ? `Expected element not to be visible`
          : `Expected element to be visible`,
    };
  },
});

// Global test helpers
global.renderWithProviders = (ui, options = {}) => {
  const { store, ...renderOptions } = options;
  
  // Import here to avoid circular dependencies
  const { render } = require('@testing-library/react');
  const { Provider } = require('react-redux');
  const { BrowserRouter } = require('react-router-dom');
  const { ThemeProvider, createTheme } = require('@mui/material/styles');
  const { configureStore } = require('@reduxjs/toolkit');
  
  const mockStore = store || configureStore({
    reducer: {
      auth: (state = { user: global.testUtils.mockUser, isAuthenticated: true }) => state,
      documents: (state = { documents: [], currentDocument: null }) => state,
      collaboration: (state = { activeCollaborators: [] }) => state,
      notifications: (state = { notifications: [], unreadCount: 0 }) => state,
    },
  });

  const theme = createTheme();

  const Wrapper = ({ children }) => (
    <Provider store={mockStore}>
      <BrowserRouter>
        <ThemeProvider theme={theme}>
          {children}
        </ThemeProvider>
      </BrowserRouter>
    </Provider>
  );

  return render(ui, { wrapper: Wrapper, ...renderOptions });
};

// User event helper
global.userEvent = require('@testing-library/user-event').default;