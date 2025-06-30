/**
 * Global Test Setup
 * Performs setup tasks before running E2E tests
 */

const { chromium } = require('@playwright/test');
const { cleanupTestData } = require('./test-data');

async function globalSetup() {
  console.log('Starting global test setup...');
  
  try {
    // 1. Environment validation
    await validateEnvironment();
    
    // 2. Test data preparation
    await prepareTestData();
    
    // 3. Test browser setup
    await setupTestBrowser();
    
    // 4. Mock services setup
    await setupMockServices();
    
    // 5. Database preparation
    await prepareDatabaseForTesting();
    
    console.log('Global test setup completed successfully');
    
  } catch (error) {
    console.error('Global test setup failed:', error);
    throw error;
  }
}

async function validateEnvironment() {
  console.log('Validating test environment...');
  
  // Check required environment variables
  const requiredEnvVars = [
    'NODE_ENV',
    'E2E_BASE_URL'
  ];
  
  const missingVars = requiredEnvVars.filter(varName => !process.env[varName]);
  
  if (missingVars.length > 0) {
    throw new Error(`Missing required environment variables: ${missingVars.join(', ')}`);
  }
  
  // Set default values for optional variables
  if (!process.env.E2E_BASE_URL) {
    process.env.E2E_BASE_URL = 'http://localhost:3000';
  }
  
  if (!process.env.TEST_TIMEOUT) {
    process.env.TEST_TIMEOUT = '60000';
  }
  
  console.log('Environment validation completed');
}

async function prepareTestData() {
  console.log('Preparing test data...');
  
  // Clean up any existing test data
  await cleanupTestData();
  
  // Create test directories
  const fs = require('fs');
  const path = require('path');
  
  const testDirs = [
    'test-results',
    'test-results/screenshots',
    'test-results/videos',
    'test-results/traces',
    'test-files'
  ];
  
  for (const dir of testDirs) {
    const dirPath = path.join(process.cwd(), dir);
    if (!fs.existsSync(dirPath)) {
      fs.mkdirSync(dirPath, { recursive: true });
    }
  }
  
  // Create sample test files
  await createTestFiles();
  
  console.log('Test data preparation completed');
}

async function createTestFiles() {
  const fs = require('fs');
  const path = require('path');
  
  const testFilesDir = path.join(process.cwd(), 'test-files');
  
  // Create sample PDF content
  const samplePDF = `%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
xref
0 2
0000000000 65535 f 
0000000009 00000 n 
trailer
<<
/Size 2
/Root 1 0 R
>>
startxref
25
%%EOF`;
  
  fs.writeFileSync(path.join(testFilesDir, 'sample.pdf'), samplePDF);
  
  // Create sample text file
  const sampleText = `Test Document

This is a sample document for testing.

Requirements:
REQ-001: The system shall work correctly
REQ-002: The system shall be user-friendly`;
  
  fs.writeFileSync(path.join(testFilesDir, 'sample.txt'), sampleText);
  
  console.log('Test files created');
}

async function setupTestBrowser() {
  console.log('Setting up test browser...');
  
  // Launch browser to warm up and verify it works
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();
  
  // Test basic browser functionality
  await page.goto('data:text/html,<h1>Test</h1>');
  const title = await page.textContent('h1');
  
  if (title !== 'Test') {
    throw new Error('Browser setup verification failed');
  }
  
  await browser.close();
  console.log('Test browser setup completed');
}

async function setupMockServices() {
  console.log('Setting up mock services...');
  
  // Start mock API server if needed
  if (process.env.USE_MOCK_API === 'true') {
    const express = require('express');
    const app = express();
    
    app.use(express.json());
    
    // Mock authentication endpoint
    app.post('/api/auth/login', (req, res) => {
      const { email, password } = req.body;
      
      if (email === 'test@example.com' && password === 'testpassword123') {
        res.json({
          token: 'mock-jwt-token',
          user: {
            id: 'user-123',
            email: 'test@example.com',
            firstName: 'Test',
            lastName: 'User'
          }
        });
      } else {
        res.status(401).json({ message: 'Invalid credentials' });
      }
    });
    
    // Mock document upload endpoint
    app.post('/api/documents/upload', (req, res) => {
      res.json({
        id: 'doc-123',
        filename: 'test-document.pdf',
        status: 'processing'
      });
    });
    
    // Start mock server
    const mockServer = app.listen(3001, () => {
      console.log('Mock API server started on port 3001');
    });
    
    // Store server reference for cleanup
    global.mockServer = mockServer;
  }
  
  console.log('Mock services setup completed');
}

async function prepareDatabaseForTesting() {
  console.log('Preparing database for testing...');
  
  // In a real implementation, this would:
  // 1. Create test database
  // 2. Run migrations
  // 3. Seed with test data
  // 4. Set up database connection
  
  // For now, we'll just simulate the process
  if (process.env.DATABASE_URL) {
    console.log('Database connection configured');
  } else {
    console.log('Using mock database for testing');
  }
  
  console.log('Database preparation completed');
}

// Health check function
async function healthCheck() {
  console.log('Performing health check...');
  
  try {
    const baseURL = process.env.E2E_BASE_URL || 'http://localhost:3000';
    
    // Use node-fetch if available, otherwise skip HTTP check
    try {
      const fetch = require('node-fetch');
      const response = await fetch(baseURL, { timeout: 5000 });
      
      if (!response.ok) {
        console.warn(`Application health check returned status: ${response.status}`);
      } else {
        console.log('Application is healthy');
      }
    } catch (fetchError) {
      console.warn('Could not perform HTTP health check:', fetchError.message);
    }
    
  } catch (error) {
    console.warn('Health check failed:', error.message);
  }
}

// Export the global setup function
module.exports = globalSetup;

// If running directly, execute setup
if (require.main === module) {
  globalSetup()
    .then(() => {
      console.log('Global setup completed successfully');
      process.exit(0);
    })
    .catch((error) => {
      console.error('Global setup failed:', error);
      process.exit(1);
    });
}