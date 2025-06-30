/**
 * API Configuration for AutoSpecAI Frontend
 * Production configuration with API keys and endpoints
 */

// Production API Configuration - reads from environment variables
export const API_CONFIG = {
  BASE_URL: process.env.REACT_APP_API_BASE_URL || 'https://api.example.com',
  VERSION: process.env.REACT_APP_API_VERSION || 'v1',
  TIMEOUT: 30000, // 30 seconds
  
  // API Keys should be configured via environment variables
  API_KEYS: [
    process.env.REACT_APP_API_KEY_1,
    process.env.REACT_APP_API_KEY_2,
    process.env.REACT_APP_API_KEY_3
  ].filter(Boolean), // Remove undefined values
  
  // Use the first API key as default or from env
  DEFAULT_API_KEY: process.env.REACT_APP_DEFAULT_API_KEY || '',
  
  // Rate limiting configuration
  RATE_LIMIT: {
    REQUESTS_PER_HOUR: 100,
    BURST_LIMIT: 10
  }
};

// API Endpoints
export const API_ENDPOINTS = {
  HEALTH: '/v1/health',
  UPLOAD: '/v1/upload',
  UPLOAD_INITIATE: '/v1/upload/initiate',
  UPLOAD_COMPLETE: '/v1/upload/complete',
  STATUS: '/v1/status',
  HISTORY: '/v1/history',
  FORMATS: '/v1/formats',
  DOCS: '/v1/docs'
};

// Build full URLs
export const buildApiUrl = (endpoint: string): string => {
  return `${API_CONFIG.BASE_URL}${endpoint}`;
};

// Default headers for API requests
export const getDefaultHeaders = (apiKey?: string): Record<string, string> => {
  return {
    'Content-Type': 'application/json',
    'X-API-Key': apiKey || API_CONFIG.DEFAULT_API_KEY,
    'Accept': 'application/json'
  };
};

// Environment detection
export const getEnvironment = (): 'development' | 'staging' | 'production' => {
  const hostname = window.location.hostname;
  
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    return 'development';
  } else if (hostname.includes('staging')) {
    return 'staging';
  } else {
    return 'production';
  }
};

// WebSocket configuration (for real-time features)
export const WEBSOCKET_CONFIG = {
  URL: 'wss://api.autospec.ai/ws', // Will be configured when WebSocket is deployed
  RECONNECT_INTERVAL: 5000,
  MAX_RECONNECT_ATTEMPTS: 5
};

export default API_CONFIG;