/**
 * Performance and Load Testing with Artillery
 * Comprehensive performance testing for AutoSpec.AI
 */

const artillery = require('artillery');
const { performance } = require('perf_hooks');

// Load testing configuration
const loadTestConfig = {
  config: {
    target: process.env.LOAD_TEST_TARGET || 'http://localhost:3001',
    phases: [
      {
        duration: 60, // 1 minute
        arrivalRate: 5, // 5 users per second
        name: 'Warm up'
      },
      {
        duration: 300, // 5 minutes
        arrivalRate: 10, // 10 users per second
        name: 'Ramp up load'
      },
      {
        duration: 600, // 10 minutes
        arrivalRate: 20, // 20 users per second
        name: 'Sustained load'
      },
      {
        duration: 300, // 5 minutes
        arrivalRate: 50, // 50 users per second
        name: 'Peak load'
      },
      {
        duration: 180, // 3 minutes
        arrivalRate: 5, // 5 users per second
        name: 'Cool down'
      }
    ],
    defaults: {
      headers: {
        'Content-Type': 'application/json',
        'User-Agent': 'AutoSpec-LoadTest/1.0'
      }
    }
  },
  scenarios: [
    {
      name: 'Authentication Flow',
      weight: 20,
      flow: [
        {
          post: {
            url: '/api/auth/login',
            json: {
              email: '{{ $randomEmail() }}',
              password: 'testpassword123'
            },
            capture: {
              json: '$.token',
              as: 'authToken'
            }
          }
        },
        {
          get: {
            url: '/api/auth/me',
            headers: {
              'Authorization': 'Bearer {{ authToken }}'
            }
          }
        }
      ]
    },
    {
      name: 'Document Upload and Processing',
      weight: 30,
      flow: [
        {
          post: {
            url: '/api/auth/login',
            json: {
              email: 'testuser@example.com',
              password: 'testpassword123'
            },
            capture: {
              json: '$.token',
              as: 'authToken'
            }
          }
        },
        {
          post: {
            url: '/api/documents/upload',
            headers: {
              'Authorization': 'Bearer {{ authToken }}',
              'Content-Type': 'multipart/form-data'
            },
            formData: {
              file: '@./test-files/sample.pdf',
              title: 'Load Test Document {{ $randomString() }}',
              tags: 'load-test,performance'
            },
            capture: {
              json: '$.id',
              as: 'documentId'
            }
          }
        },
        {
          get: {
            url: '/api/documents/{{ documentId }}',
            headers: {
              'Authorization': 'Bearer {{ authToken }}'
            }
          }
        }
      ]
    },
    {
      name: 'Real-time Collaboration',
      weight: 25,
      flow: [
        {
          post: {
            url: '/api/auth/login',
            json: {
              email: 'collaborator@example.com',
              password: 'testpassword123'
            },
            capture: {
              json: '$.token',
              as: 'authToken'
            }
          }
        },
        {
          post: {
            url: '/api/collaboration/sessions',
            headers: {
              'Authorization': 'Bearer {{ authToken }}'
            },
            json: {
              documentId: 'test-document-id',
              sessionType: 'edit'
            },
            capture: {
              json: '$.sessionId',
              as: 'sessionId'
            }
          }
        },
        {
          get: {
            url: '/api/collaboration/presence/test-document-id',
            headers: {
              'Authorization': 'Bearer {{ authToken }}'
            }
          }
        },
        {
          post: {
            url: '/api/collaboration/comments',
            headers: {
              'Authorization': 'Bearer {{ authToken }}'
            },
            json: {
              documentId: 'test-document-id',
              content: 'Load test comment {{ $randomString() }}',
              annotationData: {
                selectionStart: 10,
                selectionEnd: 25,
                selectedText: 'sample text'
              }
            }
          }
        }
      ]
    },
    {
      name: 'Analytics and Reporting',
      weight: 15,
      flow: [
        {
          post: {
            url: '/api/auth/login',
            json: {
              email: 'analytics@example.com',
              password: 'testpassword123'
            },
            capture: {
              json: '$.token',
              as: 'authToken'
            }
          }
        },
        {
          get: {
            url: '/api/analytics/dashboard',
            headers: {
              'Authorization': 'Bearer {{ authToken }}'
            }
          }
        },
        {
          get: {
            url: '/api/analytics/documents',
            headers: {
              'Authorization': 'Bearer {{ authToken }}'
            },
            qs: {
              startDate: '2024-01-01',
              endDate: '2024-01-31'
            }
          }
        }
      ]
    },
    {
      name: 'Workflow Management',
      weight: 10,
      flow: [
        {
          post: {
            url: '/api/auth/login',
            json: {
              email: 'workflow@example.com',
              password: 'testpassword123'
            },
            capture: {
              json: '$.token',
              as: 'authToken'
            }
          }
        },
        {
          get: {
            url: '/api/workflows/tasks',
            headers: {
              'Authorization': 'Bearer {{ authToken }}'
            }
          }
        },
        {
          post: {
            url: '/api/workflows/start',
            headers: {
              'Authorization': 'Bearer {{ authToken }}'
            },
            json: {
              documentId: 'test-document-id',
              workflowType: 'approval',
              approvers: ['approver1@example.com'],
              description: 'Load test workflow'
            }
          }
        }
      ]
    }
  ]
};

// Performance monitoring functions
class PerformanceMonitor {
  constructor() {
    this.metrics = {
      responseTime: [],
      throughput: [],
      errorRate: [],
      cpuUsage: [],
      memoryUsage: []
    };
    this.startTime = performance.now();
  }

  recordResponseTime(duration) {
    this.metrics.responseTime.push(duration);
  }

  recordError(error) {
    this.metrics.errorRate.push({
      timestamp: Date.now(),
      error: error.message || error,
      type: error.code || 'unknown'
    });
  }

  recordThroughput(requestsPerSecond) {
    this.metrics.throughput.push({
      timestamp: Date.now(),
      rps: requestsPerSecond
    });
  }

  calculatePercentile(values, percentile) {
    const sorted = values.sort((a, b) => a - b);
    const index = Math.ceil((percentile / 100) * sorted.length) - 1;
    return sorted[index];
  }

  generateReport() {
    const totalRequests = this.metrics.responseTime.length;
    const totalErrors = this.metrics.errorRate.length;
    const errorRate = (totalErrors / totalRequests) * 100;
    
    const responseTimes = this.metrics.responseTime;
    const averageResponseTime = responseTimes.reduce((a, b) => a + b, 0) / responseTimes.length;
    const p50 = this.calculatePercentile(responseTimes, 50);
    const p95 = this.calculatePercentile(responseTimes, 95);
    const p99 = this.calculatePercentile(responseTimes, 99);
    
    const maxThroughput = Math.max(...this.metrics.throughput.map(t => t.rps));
    const avgThroughput = this.metrics.throughput.reduce((sum, t) => sum + t.rps, 0) / this.metrics.throughput.length;

    return {
      summary: {
        totalRequests,
        totalErrors,
        errorRate: `${errorRate.toFixed(2)}%`,
        testDuration: `${((performance.now() - this.startTime) / 1000).toFixed(2)}s`
      },
      responseTime: {
        average: `${averageResponseTime.toFixed(2)}ms`,
        p50: `${p50.toFixed(2)}ms`,
        p95: `${p95.toFixed(2)}ms`,
        p99: `${p99.toFixed(2)}ms`,
        min: `${Math.min(...responseTimes).toFixed(2)}ms`,
        max: `${Math.max(...responseTimes).toFixed(2)}ms`
      },
      throughput: {
        average: `${avgThroughput.toFixed(2)} req/s`,
        peak: `${maxThroughput.toFixed(2)} req/s`
      },
      errors: this.metrics.errorRate.map(error => ({
        timestamp: new Date(error.timestamp).toISOString(),
        type: error.type,
        message: error.error
      }))
    };
  }
}

// WebSocket performance testing
class WebSocketLoadTest {
  constructor(url, concurrentConnections = 100) {
    this.url = url;
    this.concurrentConnections = concurrentConnections;
    this.connections = [];
    this.metrics = {
      connectionTime: [],
      messageLatency: [],
      reconnections: 0,
      errors: []
    };
  }

  async runTest(duration = 300000) { // 5 minutes default
    console.log(`Starting WebSocket load test with ${this.concurrentConnections} connections`);
    
    // Create connections
    for (let i = 0; i < this.concurrentConnections; i++) {
      setTimeout(() => this.createConnection(i), i * 10); // Stagger connections
    }

    // Run for specified duration
    await new Promise(resolve => setTimeout(resolve, duration));

    // Close all connections
    this.connections.forEach(ws => {
      if (ws && ws.readyState === 1) {
        ws.close();
      }
    });

    return this.generateWebSocketReport();
  }

  createConnection(connectionId) {
    const startTime = performance.now();
    const WebSocket = require('ws');
    const ws = new WebSocket(this.url);

    ws.on('open', () => {
      const connectionTime = performance.now() - startTime;
      this.metrics.connectionTime.push(connectionTime);
      
      // Send periodic messages to test latency
      const messageInterval = setInterval(() => {
        if (ws.readyState === 1) {
          const messageStart = performance.now();
          ws.send(JSON.stringify({
            type: 'ping',
            timestamp: messageStart,
            connectionId
          }));
        } else {
          clearInterval(messageInterval);
        }
      }, 5000); // Every 5 seconds

      ws.on('message', (data) => {
        try {
          const message = JSON.parse(data);
          if (message.type === 'pong' && message.timestamp) {
            const latency = performance.now() - message.timestamp;
            this.metrics.messageLatency.push(latency);
          }
        } catch (e) {
          // Ignore parsing errors
        }
      });

      ws.on('close', () => {
        clearInterval(messageInterval);
        // Attempt reconnection
        setTimeout(() => {
          this.metrics.reconnections++;
          this.createConnection(connectionId);
        }, 1000);
      });

      ws.on('error', (error) => {
        this.metrics.errors.push({
          connectionId,
          error: error.message,
          timestamp: Date.now()
        });
      });
    });

    this.connections[connectionId] = ws;
  }

  generateWebSocketReport() {
    const connectionTimes = this.metrics.connectionTime;
    const latencies = this.metrics.messageLatency;
    
    return {
      connections: {
        total: this.concurrentConnections,
        successful: connectionTimes.length,
        failed: this.concurrentConnections - connectionTimes.length,
        reconnections: this.metrics.reconnections
      },
      connectionTime: {
        average: `${(connectionTimes.reduce((a, b) => a + b, 0) / connectionTimes.length).toFixed(2)}ms`,
        min: `${Math.min(...connectionTimes).toFixed(2)}ms`,
        max: `${Math.max(...connectionTimes).toFixed(2)}ms`
      },
      messageLatency: latencies.length > 0 ? {
        average: `${(latencies.reduce((a, b) => a + b, 0) / latencies.length).toFixed(2)}ms`,
        p95: `${this.calculatePercentile(latencies, 95).toFixed(2)}ms`,
        p99: `${this.calculatePercentile(latencies, 99).toFixed(2)}ms`
      } : 'No messages exchanged',
      errors: this.metrics.errors
    };
  }

  calculatePercentile(values, percentile) {
    const sorted = values.sort((a, b) => a - b);
    const index = Math.ceil((percentile / 100) * sorted.length) - 1;
    return sorted[index];
  }
}

// Database performance testing
class DatabaseLoadTest {
  constructor() {
    this.AWS = require('aws-sdk');
    this.dynamodb = new this.AWS.DynamoDB.DocumentClient({
      region: process.env.AWS_REGION || 'us-east-1'
    });
    this.metrics = {
      readLatency: [],
      writeLatency: [],
      errors: []
    };
  }

  async runConcurrentReads(tableName, concurrency = 50, duration = 60000) {
    console.log(`Running concurrent read test on ${tableName}`);
    
    const endTime = Date.now() + duration;
    const promises = [];

    for (let i = 0; i < concurrency; i++) {
      promises.push(this.continuousReads(tableName, endTime, i));
    }

    await Promise.all(promises);
    return this.generateDatabaseReport('reads');
  }

  async runConcurrentWrites(tableName, concurrency = 25, duration = 60000) {
    console.log(`Running concurrent write test on ${tableName}`);
    
    const endTime = Date.now() + duration;
    const promises = [];

    for (let i = 0; i < concurrency; i++) {
      promises.push(this.continuousWrites(tableName, endTime, i));
    }

    await Promise.all(promises);
    return this.generateDatabaseReport('writes');
  }

  async continuousReads(tableName, endTime, workerId) {
    while (Date.now() < endTime) {
      const startTime = performance.now();
      
      try {
        await this.dynamodb.get({
          TableName: tableName,
          Key: { id: `test-item-${Math.floor(Math.random() * 1000)}` }
        }).promise();
        
        const latency = performance.now() - startTime;
        this.metrics.readLatency.push(latency);
      } catch (error) {
        this.metrics.errors.push({
          operation: 'read',
          workerId,
          error: error.message,
          timestamp: Date.now()
        });
      }

      // Small delay to prevent overwhelming
      await new Promise(resolve => setTimeout(resolve, 10));
    }
  }

  async continuousWrites(tableName, endTime, workerId) {
    let itemCount = 0;
    
    while (Date.now() < endTime) {
      const startTime = performance.now();
      
      try {
        await this.dynamodb.put({
          TableName: tableName,
          Item: {
            id: `load-test-${workerId}-${itemCount++}`,
            data: `Load test data from worker ${workerId}`,
            timestamp: new Date().toISOString(),
            workerId,
            itemCount
          }
        }).promise();
        
        const latency = performance.now() - startTime;
        this.metrics.writeLatency.push(latency);
      } catch (error) {
        this.metrics.errors.push({
          operation: 'write',
          workerId,
          error: error.message,
          timestamp: Date.now()
        });
      }

      // Small delay to prevent overwhelming
      await new Promise(resolve => setTimeout(resolve, 20));
    }
  }

  generateDatabaseReport(operation) {
    const latencies = operation === 'reads' ? this.metrics.readLatency : this.metrics.writeLatency;
    const errors = this.metrics.errors.filter(e => e.operation === operation.slice(0, -1));
    
    return {
      operation,
      performance: {
        totalOperations: latencies.length,
        averageLatency: `${(latencies.reduce((a, b) => a + b, 0) / latencies.length).toFixed(2)}ms`,
        p50: `${this.calculatePercentile(latencies, 50).toFixed(2)}ms`,
        p95: `${this.calculatePercentile(latencies, 95).toFixed(2)}ms`,
        p99: `${this.calculatePercentile(latencies, 99).toFixed(2)}ms`,
        throughput: `${(latencies.length / 60).toFixed(2)} ops/sec`
      },
      errors: {
        count: errors.length,
        rate: `${((errors.length / latencies.length) * 100).toFixed(2)}%`,
        details: errors.slice(0, 10) // Show first 10 errors
      }
    };
  }

  calculatePercentile(values, percentile) {
    const sorted = values.sort((a, b) => a - b);
    const index = Math.ceil((percentile / 100) * sorted.length) - 1;
    return sorted[index];
  }
}

// Main test execution
async function runPerformanceTests() {
  console.log('Starting AutoSpec.AI Performance Tests');
  console.log('=====================================');

  const results = {};

  try {
    // 1. HTTP Load Testing
    console.log('\n1. Running HTTP Load Tests...');
    const monitor = new PerformanceMonitor();
    
    // Run Artillery load test
    const runner = artillery.runner(loadTestConfig, {
      environment: process.env.NODE_ENV || 'test'
    });
    
    runner.on('phaseStarted', (phase) => {
      console.log(`Phase started: ${phase.name}`);
    });
    
    runner.on('phaseCompleted', (phase) => {
      console.log(`Phase completed: ${phase.name}`);
    });
    
    runner.on('stats', (stats) => {
      if (stats.latency) {
        monitor.recordResponseTime(stats.latency.p95);
      }
      if (stats.rps) {
        monitor.recordThroughput(stats.rps.mean);
      }
    });
    
    await new Promise((resolve, reject) => {
      runner.run((err, report) => {
        if (err) reject(err);
        else {
          results.httpLoadTest = monitor.generateReport();
          resolve(report);
        }
      });
    });

    // 2. WebSocket Load Testing
    console.log('\n2. Running WebSocket Load Tests...');
    const wsTest = new WebSocketLoadTest(
      process.env.WS_TEST_URL || 'ws://localhost:3001',
      parseInt(process.env.WS_CONNECTIONS || '50')
    );
    
    results.webSocketTest = await wsTest.runTest(120000); // 2 minutes

    // 3. Database Performance Testing
    console.log('\n3. Running Database Performance Tests...');
    const dbTest = new DatabaseLoadTest();
    
    // Test document reads
    results.databaseReads = await dbTest.runConcurrentReads(
      process.env.DOCUMENTS_TABLE || 'autospec-ai-documents-test',
      25, // concurrency
      60000 // 1 minute
    );
    
    // Test document writes
    results.databaseWrites = await dbTest.runConcurrentWrites(
      process.env.DOCUMENTS_TABLE || 'autospec-ai-documents-test',
      15, // concurrency
      60000 // 1 minute
    );

    // 4. Generate final report
    console.log('\n4. Generating Performance Report...');
    const finalReport = {
      testExecutedAt: new Date().toISOString(),
      environment: process.env.NODE_ENV || 'test',
      configuration: {
        target: process.env.LOAD_TEST_TARGET || 'http://localhost:3001',
        wsTarget: process.env.WS_TEST_URL || 'ws://localhost:3001',
        dbTable: process.env.DOCUMENTS_TABLE || 'autospec-ai-documents-test'
      },
      results,
      recommendations: generateRecommendations(results)
    };

    // Save report
    const fs = require('fs');
    const reportPath = `./test-results/performance-report-${Date.now()}.json`;
    fs.writeFileSync(reportPath, JSON.stringify(finalReport, null, 2));
    
    console.log(`\nPerformance test completed. Report saved to: ${reportPath}`);
    console.log('\nSummary:');
    console.log(`HTTP Response Time P95: ${results.httpLoadTest?.responseTime?.p95 || 'N/A'}`);
    console.log(`WebSocket Connection Success: ${results.webSocketTest?.connections?.successful || 'N/A'}`);
    console.log(`Database Read P95: ${results.databaseReads?.performance?.p95 || 'N/A'}`);
    console.log(`Database Write P95: ${results.databaseWrites?.performance?.p95 || 'N/A'}`);

    return finalReport;

  } catch (error) {
    console.error('Performance test failed:', error);
    throw error;
  }
}

function generateRecommendations(results) {
  const recommendations = [];

  // HTTP performance recommendations
  if (results.httpLoadTest?.responseTime?.p95) {
    const p95 = parseFloat(results.httpLoadTest.responseTime.p95);
    if (p95 > 2000) {
      recommendations.push({
        category: 'HTTP Performance',
        severity: 'high',
        message: `Response time P95 (${p95}ms) exceeds 2s threshold. Consider caching, CDN, or infrastructure scaling.`
      });
    } else if (p95 > 1000) {
      recommendations.push({
        category: 'HTTP Performance',
        severity: 'medium',
        message: `Response time P95 (${p95}ms) could be improved. Review database queries and API optimizations.`
      });
    }
  }

  // WebSocket recommendations
  if (results.webSocketTest?.connections?.failed > 0) {
    recommendations.push({
      category: 'WebSocket Performance',
      severity: 'high',
      message: `${results.webSocketTest.connections.failed} WebSocket connections failed. Check connection limits and network stability.`
    });
  }

  // Database recommendations
  if (results.databaseReads?.performance?.p95) {
    const readP95 = parseFloat(results.databaseReads.performance.p95);
    if (readP95 > 100) {
      recommendations.push({
        category: 'Database Performance',
        severity: 'medium',
        message: `Database read P95 (${readP95}ms) is high. Consider adding indexes or read replicas.`
      });
    }
  }

  if (results.databaseWrites?.performance?.p95) {
    const writeP95 = parseFloat(results.databaseWrites.performance.p95);
    if (writeP95 > 200) {
      recommendations.push({
        category: 'Database Performance',
        severity: 'medium',
        message: `Database write P95 (${writeP95}ms) is high. Consider write capacity scaling or batch operations.`
      });
    }
  }

  return recommendations;
}

// Export for use in other scripts
module.exports = {
  runPerformanceTests,
  PerformanceMonitor,
  WebSocketLoadTest,
  DatabaseLoadTest,
  loadTestConfig
};

// Run tests if called directly
if (require.main === module) {
  runPerformanceTests()
    .then(() => process.exit(0))
    .catch((error) => {
      console.error('Performance tests failed:', error);
      process.exit(1);
    });
}