/**
 * AutoSpec.AI Web UI Configuration
 * Configuration template - Replace placeholder values with actual values
 */

// API Configuration - reads from environment or window globals
export const API_CONFIG = {
  BASE_URL: window.AUTOSPEC_API_URL || process.env.REACT_APP_API_BASE_URL || 'YOUR_API_GATEWAY_URL',
  VERSION: 'v1',
  TIMEOUT: 30000,
  
  // API Keys - should be configured via environment or build-time injection
  API_KEYS: [
    window.AUTOSPEC_API_KEY || process.env.REACT_APP_API_KEY || 'YOUR_API_KEY_HERE'
  ],
  
  DEFAULT_API_KEY: window.AUTOSPEC_API_KEY || process.env.REACT_APP_API_KEY || 'YOUR_API_KEY_HERE'
};

// API Endpoints
export const ENDPOINTS = {
  HEALTH: '/v1/health',
  UPLOAD: '/v1/upload',
  STATUS: '/v1/status',
  HISTORY: '/v1/history',
  FORMATS: '/v1/formats',
  DOCS: '/v1/docs'
};

// Application Configuration
export const APP_CONFIG = {
  NAME: 'AutoSpec.AI',
  VERSION: '1.0.0',
  DESCRIPTION: 'Intelligent Document Analysis Platform',
  
  // File Upload Limits
  MAX_FILE_SIZE: 10 * 1024 * 1024, // 10MB
  ALLOWED_FORMATS: ['pdf', 'docx', 'txt'],
  
  // UI Configuration
  THEME: {
    PRIMARY_COLOR: '#1976d2',
    SECONDARY_COLOR: '#dc004e',
    SUCCESS_COLOR: '#2e7d32',
    ERROR_COLOR: '#d32f2f',
    WARNING_COLOR: '#ed6c02'
  },
  
  // Polling Configuration
  STATUS_POLL_INTERVAL: 5000, // 5 seconds
  MAX_POLL_ATTEMPTS: 60 // 5 minutes total
};

// Build API URL helper
export const buildApiUrl = (endpoint) => {
  return `${API_CONFIG.BASE_URL}${endpoint}`;
};

// Default headers helper
export const getDefaultHeaders = (apiKey = null) => {
  return {
    'Content-Type': 'application/json',
    'X-API-Key': apiKey || API_CONFIG.DEFAULT_API_KEY,
    'Accept': 'application/json'
  };
};

export default {
  API_CONFIG,
  ENDPOINTS,
  APP_CONFIG,
  buildApiUrl,
  getDefaultHeaders
};