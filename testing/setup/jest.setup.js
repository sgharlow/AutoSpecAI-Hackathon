/**
 * Global Jest setup configuration
 * Runs before all test files in all projects
 */

// Polyfills for jsdom environment
import 'whatwg-fetch';
import { TextEncoder, TextDecoder } from 'util';

// Make TextEncoder/TextDecoder available globally
global.TextEncoder = TextEncoder;
global.TextDecoder = TextDecoder;

// Mock environment variables
process.env.NODE_ENV = 'test';
process.env.REACT_APP_API_URL = 'http://localhost:3001';
process.env.REACT_APP_WEBSOCKET_ENDPOINT = 'ws://localhost:3001';
process.env.REACT_APP_ENVIRONMENT = 'test';

// Mock AWS SDK
jest.mock('aws-sdk', () => ({
  config: {
    update: jest.fn(),
  },
  S3: jest.fn(() => ({
    upload: jest.fn().mockReturnValue({
      promise: jest.fn().mockResolvedValue({ Location: 'mock-location' }),
    }),
    getObject: jest.fn().mockReturnValue({
      promise: jest.fn().mockResolvedValue({ Body: 'mock-content' }),
    }),
    deleteObject: jest.fn().mockReturnValue({
      promise: jest.fn().mockResolvedValue({}),
    }),
  })),
  DynamoDB: {
    DocumentClient: jest.fn(() => ({
      get: jest.fn().mockReturnValue({
        promise: jest.fn().mockResolvedValue({ Item: {} }),
      }),
      put: jest.fn().mockReturnValue({
        promise: jest.fn().mockResolvedValue({}),
      }),
      update: jest.fn().mockReturnValue({
        promise: jest.fn().mockResolvedValue({}),
      }),
      delete: jest.fn().mockReturnValue({
        promise: jest.fn().mockResolvedValue({}),
      }),
      query: jest.fn().mockReturnValue({
        promise: jest.fn().mockResolvedValue({ Items: [] }),
      }),
      scan: jest.fn().mockReturnValue({
        promise: jest.fn().mockResolvedValue({ Items: [] }),
      }),
    })),
  },
  Lambda: jest.fn(() => ({
    invoke: jest.fn().mockReturnValue({
      promise: jest.fn().mockResolvedValue({
        Payload: JSON.stringify({ statusCode: 200, body: JSON.stringify({}) }),
      }),
    }),
  })),
  StepFunctions: jest.fn(() => ({
    startExecution: jest.fn().mockReturnValue({
      promise: jest.fn().mockResolvedValue({
        executionArn: 'mock-execution-arn',
        startDate: new Date(),
      }),
    }),
    describeExecution: jest.fn().mockReturnValue({
      promise: jest.fn().mockResolvedValue({
        status: 'SUCCEEDED',
        startDate: new Date(),
        stopDate: new Date(),
      }),
    }),
  })),
  SNS: jest.fn(() => ({
    publish: jest.fn().mockReturnValue({
      promise: jest.fn().mockResolvedValue({ MessageId: 'mock-message-id' }),
    }),
  })),
  SES: jest.fn(() => ({
    sendEmail: jest.fn().mockReturnValue({
      promise: jest.fn().mockResolvedValue({ MessageId: 'mock-message-id' }),
    }),
  })),
  CloudWatch: jest.fn(() => ({
    putMetricData: jest.fn().mockReturnValue({
      promise: jest.fn().mockResolvedValue({}),
    }),
  })),
}));

// Mock WebSocket
global.WebSocket = jest.fn(() => ({
  close: jest.fn(),
  send: jest.fn(),
  addEventListener: jest.fn(),
  removeEventListener: jest.fn(),
}));

// Mock IntersectionObserver
global.IntersectionObserver = jest.fn(() => ({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn(),
}));

// Mock ResizeObserver
global.ResizeObserver = jest.fn(() => ({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn(),
}));

// Mock matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(), // deprecated
    removeListener: jest.fn(), // deprecated
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});

// Mock crypto
Object.defineProperty(global, 'crypto', {
  value: {
    randomUUID: jest.fn(() => 'mock-uuid'),
    getRandomValues: jest.fn(arr => arr.map(() => Math.floor(Math.random() * 256))),
  },
});

// Mock URL.createObjectURL
Object.defineProperty(global.URL, 'createObjectURL', {
  value: jest.fn(() => 'mock-object-url'),
});

Object.defineProperty(global.URL, 'revokeObjectURL', {
  value: jest.fn(),
});

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};
Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
});

// Mock sessionStorage
const sessionStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};
Object.defineProperty(window, 'sessionStorage', {
  value: sessionStorageMock,
});

// Mock console methods for cleaner test output
const originalError = console.error;
beforeAll(() => {
  console.error = (...args) => {
    if (
      typeof args[0] === 'string' &&
      args[0].includes('Warning: ReactDOM.render is no longer supported')
    ) {
      return;
    }
    originalError.call(console, ...args);
  };
});

afterAll(() => {
  console.error = originalError;
});

// Global test utilities
global.testUtils = {
  // Mock user data
  mockUser: {
    id: 'user-123',
    email: 'test@example.com',
    firstName: 'Test',
    lastName: 'User',
    role: 'user',
    organizationId: 'org-123',
    permissions: ['document:read', 'document:write'],
    preferences: {
      theme: 'light',
      language: 'en-US',
      notifications: {
        email: true,
        push: false,
        slack: true,
      },
    },
  },

  // Mock document data
  mockDocument: {
    id: 'doc-123',
    title: 'Test Document',
    type: 'pdf',
    status: 'completed',
    content: 'Test document content',
    originalFileName: 'test.pdf',
    fileSize: 1024,
    uploadedBy: 'user-123',
    uploadedAt: '2024-01-01T00:00:00Z',
    organizationId: 'org-123',
    tags: ['test'],
    metadata: {
      version: 1,
      lastModified: '2024-01-01T00:00:00Z',
      lastModifiedBy: 'user-123',
      collaborators: ['user-123'],
      wordCount: 100,
      pageCount: 1,
    },
    permissions: {
      canEdit: true,
      canShare: true,
      canDelete: true,
      canComment: true,
    },
  },

  // Mock comment data
  mockComment: {
    commentId: 'comment-123',
    documentId: 'doc-123',
    threadId: 'thread-123',
    userId: 'user-123',
    content: 'This is a test comment',
    timestamp: '2024-01-01T00:00:00Z',
    status: 'active',
    type: 'comment',
  },

  // Mock API responses
  mockApiResponse: (data, status = 200) => ({
    data,
    status,
    statusText: 'OK',
    headers: {},
    config: {},
  }),

  // Create mock functions with common patterns
  createMockFunction: (returnValue, shouldReject = false) => {
    const mockFn = jest.fn();
    if (shouldReject) {
      mockFn.mockRejectedValue(new Error('Mock error'));
    } else {
      mockFn.mockResolvedValue(returnValue);
    }
    return mockFn;
  },

  // Wait for async operations
  waitFor: (callback, timeout = 5000) =>
    new Promise((resolve, reject) => {
      const startTime = Date.now();
      const checkCondition = () => {
        try {
          const result = callback();
          if (result) {
            resolve(result);
          } else if (Date.now() - startTime > timeout) {
            reject(new Error('Timeout waiting for condition'));
          } else {
            setTimeout(checkCondition, 100);
          }
        } catch (error) {
          if (Date.now() - startTime > timeout) {
            reject(error);
          } else {
            setTimeout(checkCondition, 100);
          }
        }
      };
      checkCondition();
    }),

  // Flush promises
  flushPromises: () => new Promise(resolve => setImmediate(resolve)),
};

// Set longer timeout for integration tests
jest.setTimeout(30000);