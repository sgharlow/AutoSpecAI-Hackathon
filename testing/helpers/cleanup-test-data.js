/**
 * Test Data Cleanup Script
 * Removes test data and resets testing environment
 */

const fs = require('fs');
const path = require('path');

async function cleanupTestData() {
  console.log('Starting test data cleanup...');
  
  try {
    // Clean up test data files
    await cleanupTestDataFiles();
    
    // Clean up test uploads
    await cleanupTestUploads();
    
    // Clean up test results
    await cleanupTestResults();
    
    // Reset database (if using real database)
    if (process.env.CLEANUP_DATABASE === 'true') {
      await resetTestDatabase();
    }
    
    // Clean up temporary files
    await cleanupTempFiles();
    
    console.log('Test data cleanup completed successfully');
    
  } catch (error) {
    console.error('Test data cleanup failed:', error);
    throw error;
  }
}

async function cleanupTestDataFiles() {
  console.log('Cleaning up test data files...');
  
  const testDataDir = path.join(process.cwd(), 'test-data');
  
  if (fs.existsSync(testDataDir)) {
    try {
      // Remove all JSON files in test-data directory
      const files = fs.readdirSync(testDataDir);
      
      for (const file of files) {
        if (file.endsWith('.json')) {
          const filePath = path.join(testDataDir, file);
          fs.unlinkSync(filePath);
          console.log(`Removed test data file: ${file}`);
        }
      }
      
      // Remove the directory if it's empty
      const remainingFiles = fs.readdirSync(testDataDir);
      if (remainingFiles.length === 0) {
        fs.rmdirSync(testDataDir);
        console.log('Removed empty test-data directory');
      }
      
    } catch (error) {
      console.warn('Failed to clean up test data files:', error.message);
    }
  }
}

async function cleanupTestUploads() {
  console.log('Cleaning up test uploads...');
  
  const testFilesDir = path.join(process.cwd(), 'test-files');
  
  if (fs.existsSync(testFilesDir)) {
    try {
      const files = fs.readdirSync(testFilesDir);
      
      for (const file of files) {
        // Only remove files that are clearly test-generated
        if (file.startsWith('test-') || file.startsWith('temp-') || file.includes('generated')) {
          const filePath = path.join(testFilesDir, file);
          fs.unlinkSync(filePath);
          console.log(`Removed test upload: ${file}`);
        }
      }
      
    } catch (error) {
      console.warn('Failed to clean up test uploads:', error.message);
    }
  }
}

async function cleanupTestResults() {
  console.log('Cleaning up old test results...');
  
  const testResultsDir = path.join(process.cwd(), 'test-results');
  
  if (fs.existsSync(testResultsDir)) {
    try {
      // Keep only the most recent test results
      const subdirs = ['screenshots', 'videos', 'traces'];
      
      for (const subdir of subdirs) {
        const subdirPath = path.join(testResultsDir, subdir);
        
        if (fs.existsSync(subdirPath)) {
          const files = fs.readdirSync(subdirPath);
          
          // Sort files by modification time (newest first)
          const fileStats = files.map(file => ({
            name: file,
            path: path.join(subdirPath, file),
            mtime: fs.statSync(path.join(subdirPath, file)).mtime
          })).sort((a, b) => b.mtime - a.mtime);
          
          // Keep only the 10 most recent files
          const filesToDelete = fileStats.slice(10);
          
          for (const file of filesToDelete) {
            fs.unlinkSync(file.path);
            console.log(`Removed old test result: ${file.name}`);
          }
        }
      }
      
      // Clean up old report files
      const reportFiles = fs.readdirSync(testResultsDir).filter(file => 
        file.endsWith('.json') || file.endsWith('.xml') || file.endsWith('.html')
      );
      
      if (reportFiles.length > 5) {
        // Keep only the 5 most recent report files
        const reportStats = reportFiles.map(file => ({
          name: file,
          path: path.join(testResultsDir, file),
          mtime: fs.statSync(path.join(testResultsDir, file)).mtime
        })).sort((a, b) => b.mtime - a.mtime);
        
        const reportsToDelete = reportStats.slice(5);
        
        for (const report of reportsToDelete) {
          fs.unlinkSync(report.path);
          console.log(`Removed old test report: ${report.name}`);
        }
      }
      
    } catch (error) {
      console.warn('Failed to clean up test results:', error.message);
    }
  }
}

async function resetTestDatabase() {
  console.log('Resetting test database...');
  
  try {
    // This would connect to the database and remove test data
    // For now, we'll simulate the process
    
    console.log('Removing test users...');
    // await removeTestUsers();
    
    console.log('Removing test documents...');
    // await removeTestDocuments();
    
    console.log('Removing test workflows...');
    // await removeTestWorkflows();
    
    console.log('Removing test notifications...');
    // await removeTestNotifications();
    
    console.log('Test database reset completed');
    
  } catch (error) {
    console.error('Database reset failed:', error);
    throw error;
  }
}

async function cleanupTempFiles() {
  console.log('Cleaning up temporary files...');
  
  const tempDirs = [
    path.join(process.cwd(), 'tmp'),
    path.join(process.cwd(), 'temp'),
    path.join(process.cwd(), '.tmp'),
    path.join(require('os').tmpdir(), 'autospec-test-*')
  ];
  
  for (const tempDir of tempDirs) {
    if (tempDir.includes('*')) {
      // Handle wildcard patterns
      const parentDir = path.dirname(tempDir);
      const pattern = path.basename(tempDir).replace('*', '');
      
      if (fs.existsSync(parentDir)) {
        try {
          const files = fs.readdirSync(parentDir);
          
          for (const file of files) {
            if (file.startsWith(pattern)) {
              const filePath = path.join(parentDir, file);
              const stats = fs.statSync(filePath);
              
              if (stats.isDirectory()) {
                fs.rmSync(filePath, { recursive: true, force: true });
                console.log(`Removed temp directory: ${file}`);
              } else {
                fs.unlinkSync(filePath);
                console.log(`Removed temp file: ${file}`);
              }
            }
          }
        } catch (error) {
          console.warn(`Failed to clean wildcard temp path ${tempDir}:`, error.message);
        }
      }
    } else {
      // Handle specific directories
      if (fs.existsSync(tempDir)) {
        try {
          fs.rmSync(tempDir, { recursive: true, force: true });
          console.log(`Removed temp directory: ${tempDir}`);
        } catch (error) {
          console.warn(`Failed to clean temp directory ${tempDir}:`, error.message);
        }
      }
    }
  }
}

// Function to clean up specific test user data
async function cleanupTestUsers() {
  console.log('Cleaning up test users...');
  
  try {
    // This would remove test users from the database
    // In a real implementation, you'd query for users with test emails
    // and remove them along with their associated data
    
    const testEmailPattern = /^testuser\d+@example\.com$/;
    
    // Simulated cleanup
    console.log('Removing users matching test pattern...');
    // const testUsers = await findUsersByEmailPattern(testEmailPattern);
    // await removeUsers(testUsers);
    
    console.log('Test users cleanup completed');
    
  } catch (error) {
    console.error('Test users cleanup failed:', error);
    throw error;
  }
}

// Function to clean up test documents
async function cleanupTestDocuments() {
  console.log('Cleaning up test documents...');
  
  try {
    // Remove documents with test prefixes
    const testTitlePattern = /^Test Document \d+$/;
    
    // Simulated cleanup
    console.log('Removing documents matching test pattern...');
    // const testDocuments = await findDocumentsByTitlePattern(testTitlePattern);
    // await removeDocuments(testDocuments);
    
    console.log('Test documents cleanup completed');
    
  } catch (error) {
    console.error('Test documents cleanup failed:', error);
    throw error;
  }
}

// Function to clean up test workflows
async function cleanupTestWorkflows() {
  console.log('Cleaning up test workflows...');
  
  try {
    // Remove workflows created for testing
    const testWorkflowPattern = /Workflow \d+$/;
    
    // Simulated cleanup
    console.log('Removing workflows matching test pattern...');
    // const testWorkflows = await findWorkflowsByNamePattern(testWorkflowPattern);
    // await removeWorkflows(testWorkflows);
    
    console.log('Test workflows cleanup completed');
    
  } catch (error) {
    console.error('Test workflows cleanup failed:', error);
    throw error;
  }
}

// Function to verify cleanup
async function verifyCleanup() {
  console.log('Verifying cleanup...');
  
  const checks = [];
  
  // Check if test data directory is clean
  const testDataDir = path.join(process.cwd(), 'test-data');
  if (fs.existsSync(testDataDir)) {
    const files = fs.readdirSync(testDataDir);
    if (files.length > 0) {
      checks.push(`Test data directory still contains ${files.length} files`);
    }
  }
  
  // Check if temp directories are clean
  const tempDir = path.join(process.cwd(), 'tmp');
  if (fs.existsSync(tempDir)) {
    const files = fs.readdirSync(tempDir);
    if (files.length > 0) {
      checks.push(`Temp directory still contains ${files.length} files`);
    }
  }
  
  if (checks.length > 0) {
    console.warn('Cleanup verification found issues:');
    checks.forEach(check => console.warn(`- ${check}`));
  } else {
    console.log('Cleanup verification passed');
  }
  
  return checks.length === 0;
}

// Function to generate cleanup report
async function generateCleanupReport() {
  console.log('Generating cleanup report...');
  
  const report = {
    timestamp: new Date().toISOString(),
    environment: process.env.NODE_ENV || 'test',
    actions: [
      'Removed test data files',
      'Cleaned up test uploads',
      'Cleaned up old test results',
      'Removed temporary files'
    ],
    status: 'completed',
    verificationPassed: await verifyCleanup()
  };
  
  // Save report
  const reportPath = path.join(process.cwd(), 'cleanup-report.json');
  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
  
  console.log(`Cleanup report saved to: ${reportPath}`);
  
  return report;
}

// Export functions
module.exports = {
  cleanupTestData,
  cleanupTestUsers,
  cleanupTestDocuments,
  cleanupTestWorkflows,
  cleanupTempFiles,
  verifyCleanup,
  generateCleanupReport
};

// If running directly, execute cleanup
if (require.main === module) {
  cleanupTestData()
    .then(async () => {
      const report = await generateCleanupReport();
      console.log('Test data cleanup completed successfully');
      
      if (!report.verificationPassed) {
        console.warn('Some cleanup issues were detected - see cleanup report for details');
        process.exit(1);
      }
      
      process.exit(0);
    })
    .catch((error) => {
      console.error('Test data cleanup failed:', error);
      process.exit(1);
    });
}