const { pathsToModuleNameMapper } = require('ts-jest');

module.exports = {
  // Test environment
  testEnvironment: 'jsdom',
  
  // Setup files
  setupFilesAfterEnv: [
    '<rootDir>/testing/setup/jest.setup.js',
    '<rootDir>/testing/setup/msw.setup.js'
  ],
  
  // Module paths
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
    '^@testing/(.*)$': '<rootDir>/testing/$1',
    '^@lambdas/(.*)$': '<rootDir>/lambdas/$1',
    '^@infra/(.*)$': '<rootDir>/infra/$1',
    '\\.(css|less|scss|sass)$': 'identity-obj-proxy',
    '\\.(jpg|jpeg|png|gif|eot|otf|webp|svg|ttf|woff|woff2|mp4|webm|wav|mp3|m4a|aac|oga)$': '<rootDir>/testing/mocks/fileMock.js'
  },
  
  // Transform files
  transform: {
    '^.+\\.(ts|tsx)$': 'ts-jest',
    '^.+\\.(js|jsx)$': 'babel-jest'
  },
  
  // File patterns
  testMatch: [
    '<rootDir>/src/**/__tests__/**/*.(ts|tsx|js)',
    '<rootDir>/src/**/?(*.)(test|spec).(ts|tsx|js)',
    '<rootDir>/lambdas/**/__tests__/**/*.(ts|js)',
    '<rootDir>/lambdas/**/?(*.)(test|spec).(ts|js)',
    '<rootDir>/testing/integration/**/*.(test|spec).(ts|js)'
  ],
  
  // Coverage
  collectCoverageFrom: [
    'src/**/*.{ts,tsx,js,jsx}',
    'lambdas/**/*.{ts,js}',
    '!src/**/*.d.ts',
    '!src/index.tsx',
    '!src/serviceWorker.ts',
    '!**/node_modules/**',
    '!**/coverage/**',
    '!**/build/**'
  ],
  
  coverageThreshold: {
    global: {
      branches: 80,
      functions: 80,
      lines: 80,
      statements: 80
    },
    // Critical paths require higher coverage
    'src/store/': {
      branches: 90,
      functions: 90,
      lines: 90,
      statements: 90
    },
    'src/services/': {
      branches: 85,
      functions: 85,
      lines: 85,
      statements: 85
    },
    'lambdas/': {
      branches: 85,
      functions: 85,
      lines: 85,
      statements: 85
    }
  },
  
  coverageReporters: [
    'text',
    'lcov',
    'html',
    'json-summary'
  ],
  
  // Ignore patterns
  testPathIgnorePatterns: [
    '/node_modules/',
    '/build/',
    '/coverage/',
    '/dist/'
  ],
  
  // Module file extensions
  moduleFileExtensions: [
    'ts',
    'tsx',
    'js',
    'jsx',
    'json'
  ],
  
  // Test timeout
  testTimeout: 30000,
  
  // Globals
  globals: {
    'ts-jest': {
      tsconfig: {
        jsx: 'react-jsx'
      }
    }
  },
  
  // Verbose output
  verbose: true,
  
  // Error on deprecated features
  errorOnDeprecated: true,
  
  // Clear mocks between tests
  clearMocks: true,
  
  // Restore mocks after each test
  restoreMocks: true,
  
  // Reset modules before each test
  resetModules: true,
  
  // Projects for multi-project setup
  projects: [
    {
      displayName: 'Frontend',
      testMatch: ['<rootDir>/src/**/*.(test|spec).(ts|tsx|js|jsx)'],
      testEnvironment: 'jsdom',
      setupFilesAfterEnv: [
        '<rootDir>/testing/setup/jest.setup.js',
        '<rootDir>/testing/setup/frontend.setup.js'
      ]
    },
    {
      displayName: 'Backend',
      testMatch: ['<rootDir>/lambdas/**/*.(test|spec).(ts|js)'],
      testEnvironment: 'node',
      setupFilesAfterEnv: [
        '<rootDir>/testing/setup/jest.setup.js',
        '<rootDir>/testing/setup/backend.setup.js'
      ]
    },
    {
      displayName: 'Integration',
      testMatch: ['<rootDir>/testing/integration/**/*.(test|spec).(ts|js)'],
      testEnvironment: 'node',
      setupFilesAfterEnv: [
        '<rootDir>/testing/setup/jest.setup.js',
        '<rootDir>/testing/setup/integration.setup.js'
      ]
    }
  ],
  
  // Watch plugins
  watchPlugins: [
    'jest-watch-typeahead/filename',
    'jest-watch-typeahead/testname'
  ],
  
  // Reporter configurations
  reporters: [
    'default',
    [
      'jest-junit',
      {
        outputDirectory: './coverage',
        outputName: 'junit.xml',
        suiteName: 'AutoSpec.AI Test Suite'
      }
    ],
    [
      'jest-html-reporters',
      {
        publicPath: './coverage',
        filename: 'report.html',
        pageTitle: 'AutoSpec.AI Test Report'
      }
    ]
  ],
  
  // Maximum worker processes
  maxWorkers: '50%',
  
  // Cache directory
  cacheDirectory: '<rootDir>/.jest-cache'
};