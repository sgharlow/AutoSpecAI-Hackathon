/**
 * Global Test Teardown
 * Performs cleanup tasks after running E2E tests
 */

const { cleanupTestData } = require('./test-data');
const fs = require('fs');
const path = require('path');

async function globalTeardown() {
  console.log('Starting global test teardown...');
  
  try {
    // 1. Clean up test data
    await cleanupTestData();
    
    // 2. Stop mock services
    await stopMockServices();
    
    // 3. Clean up test files
    await cleanupTestFiles();
    
    // 4. Generate test summary
    await generateTestSummary();
    
    // 5. Archive test results
    await archiveTestResults();
    
    console.log('Global test teardown completed successfully');
    
  } catch (error) {
    console.error('Global test teardown failed:', error);
    // Don't throw error in teardown to avoid masking test failures
  }
}

async function stopMockServices() {
  console.log('Stopping mock services...');
  
  // Stop mock API server if it was started
  if (global.mockServer) {
    try {
      global.mockServer.close();
      console.log('Mock API server stopped');
    } catch (error) {
      console.warn('Failed to stop mock API server:', error.message);
    }
  }
  
  // Stop any other mock services
  if (global.mockWebSocketServer) {
    try {
      global.mockWebSocketServer.close();
      console.log('Mock WebSocket server stopped');
    } catch (error) {
      console.warn('Failed to stop mock WebSocket server:', error.message);
    }
  }
  
  console.log('Mock services cleanup completed');
}

async function cleanupTestFiles() {
  console.log('Cleaning up test files...');
  
  try {
    const testFilesDir = path.join(process.cwd(), 'test-files');
    
    if (fs.existsSync(testFilesDir)) {
      // Remove temporary test files but keep the directory structure
      const files = fs.readdirSync(testFilesDir);
      
      for (const file of files) {
        const filePath = path.join(testFilesDir, file);
        const stats = fs.statSync(filePath);
        
        if (stats.isFile() && file.startsWith('temp-')) {
          fs.unlinkSync(filePath);
        }
      }
    }
    
    console.log('Test files cleanup completed');
    
  } catch (error) {
    console.warn('Failed to clean up test files:', error.message);
  }
}

async function generateTestSummary() {
  console.log('Generating test summary...');
  
  try {
    const testResultsDir = path.join(process.cwd(), 'test-results');
    
    if (!fs.existsSync(testResultsDir)) {
      console.log('No test results found to summarize');
      return;
    }
    
    const summary = {
      executionTime: new Date().toISOString(),
      environment: process.env.NODE_ENV || 'test',
      baseURL: process.env.E2E_BASE_URL || 'http://localhost:3000',
      results: {
        total: 0,
        passed: 0,
        failed: 0,
        skipped: 0
      },
      files: {
        screenshots: 0,
        videos: 0,
        traces: 0
      }
    };
    
    // Count result files
    try {
      const screenshotsDir = path.join(testResultsDir, 'screenshots');
      if (fs.existsSync(screenshotsDir)) {
        summary.files.screenshots = fs.readdirSync(screenshotsDir).length;
      }
      
      const videosDir = path.join(testResultsDir, 'videos');
      if (fs.existsSync(videosDir)) {
        summary.files.videos = fs.readdirSync(videosDir).length;
      }
      
      const tracesDir = path.join(testResultsDir, 'traces');
      if (fs.existsSync(tracesDir)) {
        summary.files.traces = fs.readdirSync(tracesDir).length;
      }
    } catch (error) {
      console.warn('Failed to count result files:', error.message);
    }
    
    // Try to read test results from JSON file
    try {
      const resultsFile = path.join(testResultsDir, 'results.json');
      if (fs.existsSync(resultsFile)) {
        const results = JSON.parse(fs.readFileSync(resultsFile, 'utf8'));
        
        if (results.suites) {
          // Parse Playwright results format
          results.suites.forEach(suite => {
            if (suite.specs) {
              suite.specs.forEach(spec => {
                summary.results.total++;
                
                const hasFailure = spec.tests?.some(test => 
                  test.results?.some(result => result.status === 'failed')
                );
                
                if (hasFailure) {
                  summary.results.failed++;
                } else {
                  summary.results.passed++;
                }
              });
            }
          });
        }
      }
    } catch (error) {
      console.warn('Failed to parse test results:', error.message);
    }
    
    // Write summary
    const summaryPath = path.join(testResultsDir, 'test-summary.json');
    fs.writeFileSync(summaryPath, JSON.stringify(summary, null, 2));
    
    console.log('Test Summary:');
    console.log(`- Total Tests: ${summary.results.total}`);
    console.log(`- Passed: ${summary.results.passed}`);
    console.log(`- Failed: ${summary.results.failed}`);
    console.log(`- Screenshots: ${summary.files.screenshots}`);
    console.log(`- Videos: ${summary.files.videos}`);
    console.log(`- Traces: ${summary.files.traces}`);
    
    console.log(`Test summary saved to: ${summaryPath}`);
    
  } catch (error) {
    console.warn('Failed to generate test summary:', error.message);
  }
}

async function archiveTestResults() {
  console.log('Archiving test results...');
  
  try {
    const testResultsDir = path.join(process.cwd(), 'test-results');
    
    if (!fs.existsSync(testResultsDir)) {
      console.log('No test results to archive');
      return;
    }
    
    // Create archive directory with timestamp
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const archiveDir = path.join(process.cwd(), 'test-archives', timestamp);
    
    if (!fs.existsSync(path.dirname(archiveDir))) {
      fs.mkdirSync(path.dirname(archiveDir), { recursive: true });
    }
    
    // Copy important files to archive
    const filesToArchive = [
      'results.json',
      'junit.xml',
      'test-summary.json'
    ];
    
    fs.mkdirSync(archiveDir, { recursive: true });
    
    for (const filename of filesToArchive) {
      const sourcePath = path.join(testResultsDir, filename);
      const destPath = path.join(archiveDir, filename);
      
      if (fs.existsSync(sourcePath)) {
        fs.copyFileSync(sourcePath, destPath);
      }
    }
    
    // Copy screenshots if any failures occurred
    const screenshotsDir = path.join(testResultsDir, 'screenshots');
    if (fs.existsSync(screenshotsDir)) {
      const screenshots = fs.readdirSync(screenshotsDir);
      if (screenshots.length > 0) {
        const archiveScreenshotsDir = path.join(archiveDir, 'screenshots');
        fs.mkdirSync(archiveScreenshotsDir, { recursive: true });
        
        for (const screenshot of screenshots) {
          fs.copyFileSync(
            path.join(screenshotsDir, screenshot),
            path.join(archiveScreenshotsDir, screenshot)
          );
        }
      }
    }
    
    console.log(`Test results archived to: ${archiveDir}`);
    
    // Clean up old archives (keep last 10)
    await cleanupOldArchives();
    
  } catch (error) {
    console.warn('Failed to archive test results:', error.message);
  }
}

async function cleanupOldArchives() {
  try {
    const archivesDir = path.join(process.cwd(), 'test-archives');
    
    if (!fs.existsSync(archivesDir)) {
      return;
    }
    
    const archives = fs.readdirSync(archivesDir)
      .map(name => ({
        name,
        path: path.join(archivesDir, name),
        time: fs.statSync(path.join(archivesDir, name)).mtime
      }))
      .sort((a, b) => b.time - a.time); // Newest first
    
    // Keep only the 10 most recent archives
    const archivesToDelete = archives.slice(10);
    
    for (const archive of archivesToDelete) {
      try {
        fs.rmSync(archive.path, { recursive: true, force: true });
        console.log(`Deleted old archive: ${archive.name}`);
      } catch (error) {
        console.warn(`Failed to delete archive ${archive.name}:`, error.message);
      }
    }
    
  } catch (error) {
    console.warn('Failed to cleanup old archives:', error.message);
  }
}

// Additional cleanup for CI environments
async function cleanupCIEnvironment() {
  if (process.env.CI) {
    console.log('Performing CI-specific cleanup...');
    
    try {
      // Upload test results to external service if configured
      if (process.env.TEST_RESULTS_UPLOAD_URL) {
        await uploadTestResults();
      }
      
      // Clean up large files to save space
      const testResultsDir = path.join(process.cwd(), 'test-results');
      const videosDir = path.join(testResultsDir, 'videos');
      
      if (fs.existsSync(videosDir)) {
        fs.rmSync(videosDir, { recursive: true, force: true });
        console.log('Cleaned up video files to save CI space');
      }
      
    } catch (error) {
      console.warn('CI cleanup failed:', error.message);
    }
  }
}

async function uploadTestResults() {
  // Placeholder for uploading test results to external service
  console.log('Uploading test results to external service...');
  // Implementation would depend on the specific service being used
}

// Export the global teardown function
module.exports = globalTeardown;

// If running directly, execute teardown
if (require.main === module) {
  globalTeardown()
    .then(() => {
      console.log('Global teardown completed successfully');
      process.exit(0);
    })
    .catch((error) => {
      console.error('Global teardown failed:', error);
      process.exit(1);
    });
}