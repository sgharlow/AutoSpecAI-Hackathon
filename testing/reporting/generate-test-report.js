/**
 * Test Report Generator
 * Generates comprehensive test reports from test results
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// Configuration
const REPORT_CONFIG = {
  formats: ['html', 'json', 'junit', 'markdown'],
  includeScreenshots: true,
  includeVideos: false, // Videos are large, only include if explicitly requested
  includeCoverage: true,
  includePerformance: true
};

async function generateTestReport(options = {}) {
  console.log('Generating comprehensive test report...');
  
  const config = { ...REPORT_CONFIG, ...options };
  const timestamp = new Date().toISOString();
  
  try {
    // Collect test data
    const testData = await collectTestData();
    
    // Generate reports in requested formats
    const reports = {};
    
    for (const format of config.formats) {
      console.log(`Generating ${format.toUpperCase()} report...`);
      
      switch (format) {
        case 'html':
          reports.html = await generateHTMLReport(testData, config);
          break;
        case 'json':
          reports.json = await generateJSONReport(testData, config);
          break;
        case 'junit':
          reports.junit = await generateJUnitReport(testData, config);
          break;
        case 'markdown':
          reports.markdown = await generateMarkdownReport(testData, config);
          break;
        default:
          console.warn(`Unknown report format: ${format}`);
      }
    }
    
    // Save reports
    await saveReports(reports, timestamp);
    
    // Generate summary
    const summary = generateSummary(testData);
    console.log('\nTest Report Summary:');
    console.log(`- Total Tests: ${summary.totalTests}`);
    console.log(`- Passed: ${summary.passed} (${summary.passRate}%)`);
    console.log(`- Failed: ${summary.failed}`);
    console.log(`- Skipped: ${summary.skipped}`);
    console.log(`- Duration: ${summary.duration}`);
    console.log(`- Coverage: ${summary.coverage}%`);
    
    return { reports, summary, timestamp };
    
  } catch (error) {
    console.error('Test report generation failed:', error);
    throw error;
  }
}

async function collectTestData() {
  console.log('Collecting test data...');
  
  const testResultsDir = path.join(process.cwd(), 'test-results');
  const testData = {
    results: null,
    coverage: null,
    performance: null,
    screenshots: [],
    videos: [],
    environment: {
      nodeVersion: process.version,
      platform: process.platform,
      arch: process.arch,
      timestamp: new Date().toISOString(),
      environment: process.env.NODE_ENV || 'test',
      baseURL: process.env.E2E_BASE_URL || 'http://localhost:3000'
    }
  };
  
  // Load test results
  try {
    const resultsFile = path.join(testResultsDir, 'results.json');
    if (fs.existsSync(resultsFile)) {
      testData.results = JSON.parse(fs.readFileSync(resultsFile, 'utf8'));
    }
  } catch (error) {
    console.warn('Failed to load test results:', error.message);
  }
  
  // Load coverage data
  try {
    const coverageFile = path.join(testResultsDir, 'coverage/coverage-summary.json');
    if (fs.existsSync(coverageFile)) {
      testData.coverage = JSON.parse(fs.readFileSync(coverageFile, 'utf8'));
    }
  } catch (error) {
    console.warn('Failed to load coverage data:', error.message);
  }
  
  // Load performance data
  try {
    const performanceFiles = fs.readdirSync(testResultsDir)
      .filter(file => file.startsWith('performance-report-'))
      .sort()
      .reverse(); // Get most recent first
    
    if (performanceFiles.length > 0) {
      const performanceFile = path.join(testResultsDir, performanceFiles[0]);
      testData.performance = JSON.parse(fs.readFileSync(performanceFile, 'utf8'));
    }
  } catch (error) {
    console.warn('Failed to load performance data:', error.message);
  }
  
  // Collect screenshots
  try {
    const screenshotsDir = path.join(testResultsDir, 'screenshots');
    if (fs.existsSync(screenshotsDir)) {
      testData.screenshots = fs.readdirSync(screenshotsDir)
        .filter(file => file.match(/\.(png|jpg|jpeg)$/i))
        .map(file => ({
          filename: file,
          path: path.join(screenshotsDir, file),
          size: fs.statSync(path.join(screenshotsDir, file)).size,
          mtime: fs.statSync(path.join(screenshotsDir, file)).mtime
        }));
    }
  } catch (error) {
    console.warn('Failed to collect screenshots:', error.message);
  }
  
  // Collect videos
  try {
    const videosDir = path.join(testResultsDir, 'videos');
    if (fs.existsSync(videosDir)) {
      testData.videos = fs.readdirSync(videosDir)
        .filter(file => file.match(/\.(mp4|webm)$/i))
        .map(file => ({
          filename: file,
          path: path.join(videosDir, file),
          size: fs.statSync(path.join(videosDir, file)).size,
          mtime: fs.statSync(path.join(videosDir, file)).mtime
        }));
    }
  } catch (error) {
    console.warn('Failed to collect videos:', error.message);
  }
  
  return testData;
}

async function generateHTMLReport(testData, config) {
  console.log('Generating HTML report...');
  
  const summary = generateSummary(testData);
  
  const html = `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AutoSpec.AI Test Report</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
            color: #333;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 {
            margin: 0;
            font-size: 2.5em;
            font-weight: 300;
        }
        .header p {
            margin: 10px 0 0 0;
            opacity: 0.9;
        }
        .content {
            padding: 30px;
        }
        .summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .metric {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            border-left: 4px solid #007bff;
        }
        .metric.passed {
            border-left-color: #28a745;
        }
        .metric.failed {
            border-left-color: #dc3545;
        }
        .metric.skipped {
            border-left-color: #ffc107;
        }
        .metric.coverage {
            border-left-color: #17a2b8;
        }
        .metric-value {
            font-size: 2em;
            font-weight: bold;
            margin-bottom: 5px;
        }
        .metric-label {
            color: #6c757d;
            font-size: 0.9em;
        }
        .section {
            margin-bottom: 30px;
        }
        .section h2 {
            color: #495057;
            border-bottom: 2px solid #e9ecef;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }
        .test-suite {
            background: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
        }
        .test-case {
            padding: 10px;
            margin: 10px 0;
            border-radius: 4px;
            background: white;
            border-left: 4px solid #28a745;
        }
        .test-case.failed {
            border-left-color: #dc3545;
        }
        .test-case.skipped {
            border-left-color: #ffc107;
        }
        .test-name {
            font-weight: 600;
            margin-bottom: 5px;
        }
        .test-duration {
            color: #6c757d;
            font-size: 0.9em;
        }
        .error-message {
            background: #f8d7da;
            color: #721c24;
            padding: 10px;
            border-radius: 4px;
            margin-top: 10px;
            font-family: monospace;
            font-size: 0.9em;
        }
        .performance-chart {
            background: white;
            border: 1px solid #e9ecef;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
        }
        .screenshot-gallery {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }
        .screenshot {
            border: 1px solid #e9ecef;
            border-radius: 8px;
            overflow: hidden;
            text-align: center;
        }
        .screenshot img {
            width: 100%;
            height: 120px;
            object-fit: cover;
        }
        .screenshot-name {
            padding: 10px;
            background: #f8f9fa;
            font-size: 0.8em;
            color: #6c757d;
        }
        .footer {
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #6c757d;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>AutoSpec.AI Test Report</h1>
            <p>Generated on ${new Date().toLocaleString()}</p>
        </div>
        
        <div class="content">
            <div class="section">
                <h2>Summary</h2>
                <div class="summary">
                    <div class="metric">
                        <div class="metric-value">${summary.totalTests}</div>
                        <div class="metric-label">Total Tests</div>
                    </div>
                    <div class="metric passed">
                        <div class="metric-value">${summary.passed}</div>
                        <div class="metric-label">Passed</div>
                    </div>
                    <div class="metric failed">
                        <div class="metric-value">${summary.failed}</div>
                        <div class="metric-label">Failed</div>
                    </div>
                    <div class="metric skipped">
                        <div class="metric-value">${summary.skipped}</div>
                        <div class="metric-label">Skipped</div>
                    </div>
                    <div class="metric coverage">
                        <div class="metric-value">${summary.coverage}%</div>
                        <div class="metric-label">Coverage</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">${summary.passRate}%</div>
                        <div class="metric-label">Pass Rate</div>
                    </div>
                </div>
            </div>
            
            ${generateTestSuitesHTML(testData.results)}
            ${generateCoverageHTML(testData.coverage)}
            ${generatePerformanceHTML(testData.performance)}
            ${config.includeScreenshots ? generateScreenshotsHTML(testData.screenshots) : ''}
        </div>
        
        <div class="footer">
            <p>Generated by AutoSpec.AI Test Suite | Environment: ${testData.environment.environment} | Node.js ${testData.environment.nodeVersion}</p>
        </div>
    </div>
</body>
</html>
`;
  
  return html;
}

function generateTestSuitesHTML(results) {
  if (!results || !results.suites) {
    return '<div class="section"><h2>Test Results</h2><p>No test results available.</p></div>';
  }
  
  let html = '<div class="section"><h2>Test Results</h2>';
  
  results.suites.forEach(suite => {
    html += `
      <div class="test-suite">
        <h3>${suite.title || 'Test Suite'}</h3>
        <p><strong>File:</strong> ${suite.file || 'Unknown'}</p>
    `;
    
    if (suite.specs) {
      suite.specs.forEach(spec => {
        if (spec.tests) {
          spec.tests.forEach(test => {
            const status = getTestStatus(test);
            const duration = getTestDuration(test);
            
            html += `
              <div class="test-case ${status}">
                <div class="test-name">${test.title}</div>
                <div class="test-duration">Duration: ${duration}ms</div>
            `;
            
            if (status === 'failed' && test.results) {
              const failedResult = test.results.find(r => r.status === 'failed');
              if (failedResult && failedResult.error) {
                html += `<div class="error-message">${escapeHtml(failedResult.error.message || failedResult.error)}</div>`;
              }
            }
            
            html += '</div>';
          });
        }
      });
    }
    
    html += '</div>';
  });
  
  html += '</div>';
  return html;
}

function generateCoverageHTML(coverage) {
  if (!coverage) {
    return '';
  }
  
  return `
    <div class="section">
      <h2>Code Coverage</h2>
      <div class="performance-chart">
        <p><strong>Overall Coverage:</strong> ${coverage.total?.statements?.pct || 0}%</p>
        <ul>
          <li>Statements: ${coverage.total?.statements?.pct || 0}% (${coverage.total?.statements?.covered || 0}/${coverage.total?.statements?.total || 0})</li>
          <li>Branches: ${coverage.total?.branches?.pct || 0}% (${coverage.total?.branches?.covered || 0}/${coverage.total?.branches?.total || 0})</li>
          <li>Functions: ${coverage.total?.functions?.pct || 0}% (${coverage.total?.functions?.covered || 0}/${coverage.total?.functions?.total || 0})</li>
          <li>Lines: ${coverage.total?.lines?.pct || 0}% (${coverage.total?.lines?.covered || 0}/${coverage.total?.lines?.total || 0})</li>
        </ul>
      </div>
    </div>
  `;
}

function generatePerformanceHTML(performance) {
  if (!performance) {
    return '';
  }
  
  return `
    <div class="section">
      <h2>Performance Results</h2>
      <div class="performance-chart">
        ${performance.results?.httpLoadTest ? `
          <h3>HTTP Load Test</h3>
          <ul>
            <li>Average Response Time: ${performance.results.httpLoadTest.responseTime?.average || 'N/A'}</li>
            <li>95th Percentile: ${performance.results.httpLoadTest.responseTime?.p95 || 'N/A'}</li>
            <li>Peak Throughput: ${performance.results.httpLoadTest.throughput?.peak || 'N/A'}</li>
          </ul>
        ` : ''}
        
        ${performance.results?.webSocketTest ? `
          <h3>WebSocket Test</h3>
          <ul>
            <li>Successful Connections: ${performance.results.webSocketTest.connections?.successful || 'N/A'}</li>
            <li>Failed Connections: ${performance.results.webSocketTest.connections?.failed || 'N/A'}</li>
            <li>Average Latency: ${performance.results.webSocketTest.messageLatency?.average || 'N/A'}</li>
          </ul>
        ` : ''}
        
        ${performance.results?.databaseReads ? `
          <h3>Database Performance</h3>
          <ul>
            <li>Read P95: ${performance.results.databaseReads.performance?.p95 || 'N/A'}</li>
            <li>Write P95: ${performance.results.databaseWrites?.performance?.p95 || 'N/A'}</li>
            <li>Read Throughput: ${performance.results.databaseReads.performance?.throughput || 'N/A'}</li>
          </ul>
        ` : ''}
      </div>
    </div>
  `;
}

function generateScreenshotsHTML(screenshots) {
  if (!screenshots || screenshots.length === 0) {
    return '';
  }
  
  let html = '<div class="section"><h2>Screenshots</h2><div class="screenshot-gallery">';
  
  screenshots.forEach(screenshot => {
    html += `
      <div class="screenshot">
        <img src="screenshots/${screenshot.filename}" alt="${screenshot.filename}">
        <div class="screenshot-name">${screenshot.filename}</div>
      </div>
    `;
  });
  
  html += '</div></div>';
  return html;
}

function getTestStatus(test) {
  if (!test.results || test.results.length === 0) {
    return 'skipped';
  }
  
  const hasFailure = test.results.some(result => result.status === 'failed');
  const hasSkipped = test.results.some(result => result.status === 'skipped');
  
  if (hasFailure) return 'failed';
  if (hasSkipped) return 'skipped';
  return 'passed';
}

function getTestDuration(test) {
  if (!test.results || test.results.length === 0) {
    return 0;
  }
  
  return test.results.reduce((total, result) => total + (result.duration || 0), 0);
}

function escapeHtml(text) {
  const div = { innerHTML: text };
  return div.innerHTML
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

async function generateJSONReport(testData, config) {
  console.log('Generating JSON report...');
  
  const summary = generateSummary(testData);
  
  return {
    summary,
    environment: testData.environment,
    results: testData.results,
    coverage: testData.coverage,
    performance: testData.performance,
    screenshots: config.includeScreenshots ? testData.screenshots : [],
    videos: config.includeVideos ? testData.videos : [],
    generatedAt: new Date().toISOString()
  };
}

async function generateJUnitReport(testData, config) {
  console.log('Generating JUnit XML report...');
  
  const summary = generateSummary(testData);
  
  let xml = `<?xml version="1.0" encoding="UTF-8"?>
`;
  xml += `<testsuites tests="${summary.totalTests}" failures="${summary.failed}" skipped="${summary.skipped}" time="${summary.duration / 1000}">
`;
  
  if (testData.results && testData.results.suites) {
    testData.results.suites.forEach(suite => {
      const suiteTests = countSuiteTests(suite);
      xml += `  <testsuite name="${escapeXml(suite.title || 'Test Suite')}" tests="${suiteTests.total}" failures="${suiteTests.failed}" skipped="${suiteTests.skipped}" time="${suiteTests.duration / 1000}">
`;
      
      if (suite.specs) {
        suite.specs.forEach(spec => {
          if (spec.tests) {
            spec.tests.forEach(test => {
              const status = getTestStatus(test);
              const duration = getTestDuration(test);
              
              xml += `    <testcase name="${escapeXml(test.title)}" classname="${escapeXml(suite.title || 'TestSuite')}" time="${duration / 1000}">
`;
              
              if (status === 'failed' && test.results) {
                const failedResult = test.results.find(r => r.status === 'failed');
                if (failedResult && failedResult.error) {
                  xml += `      <failure message="${escapeXml(failedResult.error.message || 'Test failed')}">
`;
                  xml += `        ${escapeXml(failedResult.error.stack || failedResult.error.message || 'No details available')}
`;
                  xml += `      </failure>
`;
                }
              } else if (status === 'skipped') {
                xml += `      <skipped/>
`;
              }
              
              xml += `    </testcase>
`;
            });
          }
        });
      }
      
      xml += `  </testsuite>
`;
    });
  }
  
  xml += `</testsuites>
`;
  
  return xml;
}

function countSuiteTests(suite) {
  let total = 0, failed = 0, skipped = 0, duration = 0;
  
  if (suite.specs) {
    suite.specs.forEach(spec => {
      if (spec.tests) {
        spec.tests.forEach(test => {
          total++;
          const status = getTestStatus(test);
          const testDuration = getTestDuration(test);
          
          if (status === 'failed') failed++;
          if (status === 'skipped') skipped++;
          duration += testDuration;
        });
      }
    });
  }
  
  return { total, failed, skipped, duration };
}

function escapeXml(text) {
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;');
}

async function generateMarkdownReport(testData, config) {
  console.log('Generating Markdown report...');
  
  const summary = generateSummary(testData);
  
  let markdown = `# AutoSpec.AI Test Report

`;
  markdown += `**Generated:** ${new Date().toLocaleString()}\n`;
  markdown += `**Environment:** ${testData.environment.environment}\n`;
  markdown += `**Node.js Version:** ${testData.environment.nodeVersion}\n\n`;
  
  markdown += `## Summary\n\n`;
  markdown += `| Metric | Value |\n`;
  markdown += `|--------|-------|\n`;
  markdown += `| Total Tests | ${summary.totalTests} |\n`;
  markdown += `| Passed | ${summary.passed} |\n`;
  markdown += `| Failed | ${summary.failed} |\n`;
  markdown += `| Skipped | ${summary.skipped} |\n`;
  markdown += `| Pass Rate | ${summary.passRate}% |\n`;
  markdown += `| Coverage | ${summary.coverage}% |\n`;
  markdown += `| Duration | ${summary.duration}ms |\n\n`;
  
  if (testData.results && testData.results.suites) {
    markdown += `## Test Results\n\n`;
    
    testData.results.suites.forEach(suite => {
      markdown += `### ${suite.title || 'Test Suite'}\n\n`;
      
      if (suite.specs) {
        suite.specs.forEach(spec => {
          if (spec.tests) {
            spec.tests.forEach(test => {
              const status = getTestStatus(test);
              const duration = getTestDuration(test);
              const icon = status === 'passed' ? '✅' : status === 'failed' ? '❌' : '⏭️';
              
              markdown += `${icon} **${test.title}** (${duration}ms)\n`;
              
              if (status === 'failed' && test.results) {
                const failedResult = test.results.find(r => r.status === 'failed');
                if (failedResult && failedResult.error) {
                  markdown += `   - Error: ${failedResult.error.message || 'Test failed'}\n`;
                }
              }
              
              markdown += `\n`;
            });
          }
        });
      }
    });
  }
  
  if (testData.coverage) {
    markdown += `## Code Coverage\n\n`;
    markdown += `| Type | Coverage | Covered/Total |\n`;
    markdown += `|------|----------|---------------|\n`;
    markdown += `| Statements | ${testData.coverage.total?.statements?.pct || 0}% | ${testData.coverage.total?.statements?.covered || 0}/${testData.coverage.total?.statements?.total || 0} |\n`;
    markdown += `| Branches | ${testData.coverage.total?.branches?.pct || 0}% | ${testData.coverage.total?.branches?.covered || 0}/${testData.coverage.total?.branches?.total || 0} |\n`;
    markdown += `| Functions | ${testData.coverage.total?.functions?.pct || 0}% | ${testData.coverage.total?.functions?.covered || 0}/${testData.coverage.total?.functions?.total || 0} |\n`;
    markdown += `| Lines | ${testData.coverage.total?.lines?.pct || 0}% | ${testData.coverage.total?.lines?.covered || 0}/${testData.coverage.total?.lines?.total || 0} |\n\n`;
  }
  
  if (testData.performance) {
    markdown += `## Performance Results\n\n`;
    
    if (testData.performance.results?.httpLoadTest) {
      markdown += `### HTTP Load Test\n`;
      markdown += `- Average Response Time: ${testData.performance.results.httpLoadTest.responseTime?.average || 'N/A'}\n`;
      markdown += `- 95th Percentile: ${testData.performance.results.httpLoadTest.responseTime?.p95 || 'N/A'}\n`;
      markdown += `- Peak Throughput: ${testData.performance.results.httpLoadTest.throughput?.peak || 'N/A'}\n\n`;
    }
    
    if (testData.performance.results?.databaseReads) {
      markdown += `### Database Performance\n`;
      markdown += `- Read P95: ${testData.performance.results.databaseReads.performance?.p95 || 'N/A'}\n`;
      markdown += `- Write P95: ${testData.performance.results.databaseWrites?.performance?.p95 || 'N/A'}\n\n`;
    }
  }
  
  if (config.includeScreenshots && testData.screenshots.length > 0) {
    markdown += `## Screenshots\n\n`;
    testData.screenshots.forEach(screenshot => {
      markdown += `![${screenshot.filename}](screenshots/${screenshot.filename})\n\n`;
    });
  }
  
  return markdown;
}

function generateSummary(testData) {
  const summary = {
    totalTests: 0,
    passed: 0,
    failed: 0,
    skipped: 0,
    duration: 0,
    coverage: 0,
    passRate: 0
  };
  
  // Calculate test summary
  if (testData.results && testData.results.suites) {
    testData.results.suites.forEach(suite => {
      if (suite.specs) {
        suite.specs.forEach(spec => {
          if (spec.tests) {
            spec.tests.forEach(test => {
              summary.totalTests++;
              const status = getTestStatus(test);
              const duration = getTestDuration(test);
              
              if (status === 'passed') summary.passed++;
              else if (status === 'failed') summary.failed++;
              else if (status === 'skipped') summary.skipped++;
              
              summary.duration += duration;
            });
          }
        });
      }
    });
  }
  
  // Calculate pass rate
  summary.passRate = summary.totalTests > 0 
    ? Math.round((summary.passed / summary.totalTests) * 100)
    : 0;
  
  // Get coverage
  if (testData.coverage && testData.coverage.total) {
    summary.coverage = Math.round(testData.coverage.total.statements?.pct || 0);
  }
  
  return summary;
}

async function saveReports(reports, timestamp) {
  console.log('Saving test reports...');
  
  const reportsDir = path.join(process.cwd(), 'test-results');
  
  if (!fs.existsSync(reportsDir)) {
    fs.mkdirSync(reportsDir, { recursive: true });
  }
  
  const savedReports = {};
  
  for (const [format, content] of Object.entries(reports)) {
    const filename = `test-report-${timestamp.replace(/[:.]/g, '-')}.${format}`;
    const filepath = path.join(reportsDir, filename);
    
    if (format === 'json') {
      fs.writeFileSync(filepath, JSON.stringify(content, null, 2));
    } else {
      fs.writeFileSync(filepath, content);
    }
    
    savedReports[format] = filepath;
    console.log(`${format.toUpperCase()} report saved: ${filepath}`);
  }
  
  return savedReports;
}

// Export functions
module.exports = {
  generateTestReport,
  collectTestData,
  generateSummary
};

// Command line interface
if (require.main === module) {
  const args = process.argv.slice(2);
  const options = {};
  
  // Parse command line arguments
  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    
    if (arg === '--format' && i + 1 < args.length) {
      options.formats = args[i + 1].split(',');
      i++;
    } else if (arg === '--no-screenshots') {
      options.includeScreenshots = false;
    } else if (arg === '--include-videos') {
      options.includeVideos = true;
    } else if (arg === '--no-coverage') {
      options.includeCoverage = false;
    }
  }
  
  generateTestReport(options)
    .then((result) => {
      console.log('\nTest report generation completed successfully');
      console.log(`Reports generated: ${Object.keys(result.reports).join(', ')}`);
      process.exit(0);
    })
    .catch((error) => {
      console.error('Test report generation failed:', error);
      process.exit(1);
    });
}