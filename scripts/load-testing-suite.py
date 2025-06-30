#!/usr/bin/env python3
"""
AutoSpec.AI Load Testing Suite

Comprehensive load testing tool for validating performance optimizations,
measuring the impact of provisioned concurrency, and establishing benchmarks.

Usage:
    python3 load-testing-suite.py --environment dev --test-type api --duration 300
    python3 load-testing-suite.py --environment prod --test-type full --users 50
    python3 load-testing-suite.py --environment staging --test-type benchmark --report
"""

import argparse
import asyncio
import aiohttp
import boto3
import json
import time
import uuid
import base64
import random
import statistics
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class TestResult:
    """Individual test result."""
    test_id: str
    test_type: str
    start_time: float
    end_time: float
    status_code: int
    response_time_ms: float
    success: bool
    error_message: Optional[str] = None
    request_size_bytes: int = 0
    response_size_bytes: int = 0

@dataclass
class TestSummary:
    """Test execution summary."""
    test_name: str
    environment: str
    start_time: str
    end_time: str
    duration_seconds: float
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time_ms: float
    p50_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    max_response_time_ms: float
    min_response_time_ms: float
    requests_per_second: float
    error_rate_percent: float
    total_bytes_sent: int
    total_bytes_received: int

class AutoSpecLoadTester:
    """Comprehensive load testing suite for AutoSpec.AI."""
    
    def __init__(self, environment: str, api_base_url: Optional[str] = None):
        self.environment = environment
        self.api_base_url = api_base_url or self._get_api_url()
        self.session = None
        self.test_results: List[TestResult] = []
        
        # Load test configuration
        self.config = self._load_test_config()
        
        # Sample documents for testing
        self.sample_documents = self._create_sample_documents()
        
        # CloudWatch client for metrics
        self.cloudwatch = boto3.client('cloudwatch')
        
    def _get_api_url(self) -> str:
        """Get API Gateway URL from CloudFormation stack."""
        try:
            cf_client = boto3.client('cloudformation')
            stack_name = f"AutoSpecAIStackOptimized"
            
            response = cf_client.describe_stacks(StackName=stack_name)
            for stack in response['Stacks']:
                for output in stack.get('Outputs', []):
                    if output['OutputKey'] == 'ApiGatewayUrl':
                        return output['OutputValue']
        except Exception as e:
            logger.warning(f"Could not get API URL from CloudFormation: {e}")
        
        # Fallback URL pattern
        return f"https://api-{self.environment}.autospec.ai"
    
    def _load_test_config(self) -> Dict[str, Any]:
        """Load test configuration based on environment."""
        config = {
            'dev': {
                'max_concurrent_users': 10,
                'ramp_up_duration': 30,
                'test_duration': 300,
                'api_request_rate': 5,
                'document_sizes': ['small', 'medium'],
                'stress_multiplier': 1.0
            },
            'staging': {
                'max_concurrent_users': 25,
                'ramp_up_duration': 60,
                'test_duration': 600,
                'api_request_rate': 10,
                'document_sizes': ['small', 'medium', 'large'],
                'stress_multiplier': 1.5
            },
            'prod': {
                'max_concurrent_users': 50,
                'ramp_up_duration': 120,
                'test_duration': 900,
                'api_request_rate': 20,
                'document_sizes': ['small', 'medium', 'large'],
                'stress_multiplier': 2.0
            }
        }
        
        return config.get(self.environment, config['dev'])
    
    def _create_sample_documents(self) -> Dict[str, Dict[str, Any]]:
        """Create sample documents for testing."""
        documents = {
            'small': {
                'filename': 'test_requirements_small.txt',
                'content': """
System Requirements Document - Small Project

1. User Management
   - User registration and authentication
   - Profile management
   - Password reset functionality

2. Data Storage
   - User data persistence
   - Backup and recovery
   - Data security measures

3. User Interface
   - Responsive web design
   - Mobile compatibility
   - Accessibility compliance
""",
                'size_kb': 1
            },
            'medium': {
                'filename': 'test_requirements_medium.txt',
                'content': """
System Requirements Document - Medium Project

1. Functional Requirements
   1.1 User Management System
       - User registration with email verification
       - Multi-factor authentication
       - Role-based access control
       - Profile management with avatar upload
       - Password complexity requirements
       - Account lockout after failed attempts

   1.2 Content Management
       - Document upload and storage
       - Version control system
       - Collaborative editing
       - Comment and review system
       - Search and filter capabilities
       - Tag and category management

   1.3 Reporting and Analytics
       - Real-time dashboard
       - Custom report generation
       - Data export capabilities
       - Performance metrics tracking
       - User activity monitoring

2. Non-Functional Requirements
   2.1 Performance
       - Page load time < 2 seconds
       - API response time < 500ms
       - Support for 1000 concurrent users
       - 99.9% uptime requirement

   2.2 Security
       - Data encryption in transit and at rest
       - Regular security audits
       - GDPR compliance
       - PCI DSS compliance for payments
       - Vulnerability scanning

   2.3 Scalability
       - Horizontal scaling capabilities
       - Auto-scaling based on load
       - Database sharding support
       - CDN integration
""",
                'size_kb': 5
            },
            'large': {
                'filename': 'test_requirements_large.txt',
                'content': """
Enterprise System Requirements Document - Large Project

EXECUTIVE SUMMARY
This document outlines the comprehensive requirements for a large-scale enterprise system
designed to handle complex business processes, integrate multiple systems, and support
thousands of concurrent users across multiple geographic locations.

1. FUNCTIONAL REQUIREMENTS

1.1 User Management and Authentication
    1.1.1 Multi-tenant Architecture
          - Tenant isolation and data segregation
          - Customizable tenant configurations
          - Tenant-specific branding and themes
          - Resource allocation per tenant
    
    1.1.2 Advanced Authentication
          - Single Sign-On (SSO) integration
          - LDAP/Active Directory integration
          - Multi-factor authentication (MFA)
          - Biometric authentication support
          - Token-based authentication (JWT)
          - OAuth 2.0 and OpenID Connect

    1.1.3 Authorization and Access Control
          - Role-based access control (RBAC)
          - Attribute-based access control (ABAC)
          - Dynamic permission management
          - Hierarchical role structures
          - Time-based access restrictions

1.2 Enterprise Content Management
    1.2.1 Document Management
          - Version control with branching
          - Document lifecycle management
          - Automated workflow approvals
          - Digital signature integration
          - Audit trail for all changes
          - Bulk operations support

    1.2.2 Collaboration Features
          - Real-time collaborative editing
          - Video conferencing integration
          - Comment and annotation system
          - Task assignment and tracking
          - Notification and alert system

1.3 Business Process Management
    1.3.1 Workflow Engine
          - Visual workflow designer
          - Complex conditional logic
          - Parallel and sequential processing
          - Escalation and timeout handling
          - Integration with external systems

    1.3.2 Rule Engine
          - Business rule configuration
          - Dynamic rule evaluation
          - A/B testing capabilities
          - Performance monitoring

1.4 Integration and APIs
    1.4.1 System Integration
          - RESTful API architecture
          - GraphQL support
          - Message queue integration
          - Event-driven architecture
          - Real-time data synchronization

    1.4.2 Third-party Integrations
          - CRM system integration
          - ERP system connectivity
          - Payment gateway integration
          - Email service providers
          - Cloud storage services

2. NON-FUNCTIONAL REQUIREMENTS

2.1 Performance Requirements
    2.1.1 Response Time
          - Web page load time: < 1 second
          - API response time: < 200ms (95th percentile)
          - Database query time: < 100ms (average)
          - File upload time: < 5 seconds for 10MB files

    2.1.2 Throughput
          - Support 10,000 concurrent users
          - Process 1 million transactions per day
          - Handle 100,000 API requests per minute
          - Support real-time updates for 5,000 users

2.2 Scalability Requirements
    2.2.1 Horizontal Scaling
          - Auto-scaling based on CPU and memory usage
          - Database read replicas
          - Load balancing across multiple regions
          - Microservices architecture

    2.2.2 Storage Scaling
          - Petabyte-scale storage capacity
          - Automated data archiving
          - Cloud storage integration
          - Data lifecycle management

2.3 Security Requirements
    2.3.1 Data Protection
          - AES-256 encryption for data at rest
          - TLS 1.3 for data in transit
          - Key management system
          - Regular encryption key rotation

    2.3.2 Compliance
          - SOX compliance for financial data
          - HIPAA compliance for healthcare data
          - GDPR compliance for EU data
          - ISO 27001 certification

2.4 Availability and Reliability
    2.4.1 Uptime Requirements
          - 99.99% availability (52.6 minutes downtime per year)
          - Disaster recovery with RTO < 4 hours
          - RPO < 1 hour for critical data
          - Multi-region redundancy

    2.4.2 Backup and Recovery
          - Automated daily backups
          - Point-in-time recovery
          - Cross-region backup replication
          - Backup verification and testing

3. TECHNICAL REQUIREMENTS

3.1 Architecture Requirements
    3.1.1 Cloud-Native Design
          - Containerized applications
          - Kubernetes orchestration
          - Service mesh architecture
          - Infrastructure as Code

    3.1.2 Database Requirements
          - Multi-master database replication
          - Sharding for horizontal scaling
          - In-memory caching layer
          - Time-series data storage

3.2 Monitoring and Observability
    3.2.1 Application Monitoring
          - Real-time performance metrics
          - Distributed tracing
          - Log aggregation and analysis
          - Custom alerting rules

    3.2.2 Business Intelligence
          - Real-time analytics dashboard
          - Historical trend analysis
          - Predictive analytics
          - Custom report generation

This enterprise system represents a complex, large-scale implementation requiring
significant planning, development resources, and ongoing maintenance to meet
the stringent requirements outlined above.
""",
                'size_kb': 25
            }
        }
        
        # Convert content to base64 for API testing
        for doc_type, doc_data in documents.items():
            content_bytes = doc_data['content'].encode('utf-8')
            doc_data['base64_content'] = base64.b64encode(content_bytes).decode('utf-8')
            doc_data['actual_size_bytes'] = len(content_bytes)
        
        return documents
    
    async def setup_session(self):
        """Setup aiohttp session."""
        timeout = aiohttp.ClientTimeout(total=300)  # 5 minute timeout
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=50)
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers={'User-Agent': 'AutoSpecAI-LoadTester/1.0'}
        )
    
    async def cleanup_session(self):
        """Cleanup aiohttp session."""
        if self.session:
            await self.session.close()
    
    async def single_api_request(self, endpoint: str, method: str = 'GET', 
                                data: Optional[Dict] = None, doc_size: str = 'small') -> TestResult:
        """Execute a single API request and measure performance."""
        test_id = str(uuid.uuid4())
        start_time = time.time()
        
        url = f"{self.api_base_url}/v1/{endpoint}"
        request_size = 0
        response_size = 0
        
        try:
            if method.upper() == 'POST' and endpoint == 'upload':
                # Document upload test
                doc_data = self.sample_documents[doc_size]
                payload = {
                    'filename': doc_data['filename'],
                    'content': doc_data['base64_content'],
                    'sender_email': f'loadtest-{test_id}@autospec.ai'
                }
                request_size = len(json.dumps(payload).encode('utf-8'))
                
                async with self.session.post(url, json=payload) as response:
                    response_text = await response.text()
                    response_size = len(response_text.encode('utf-8'))
                    end_time = time.time()
                    
                    return TestResult(
                        test_id=test_id,
                        test_type=f"upload_{doc_size}",
                        start_time=start_time,
                        end_time=end_time,
                        status_code=response.status,
                        response_time_ms=(end_time - start_time) * 1000,
                        success=200 <= response.status < 300,
                        request_size_bytes=request_size,
                        response_size_bytes=response_size
                    )
            
            elif method.upper() == 'GET':
                # GET request test
                async with self.session.get(url) as response:
                    response_text = await response.text()
                    response_size = len(response_text.encode('utf-8'))
                    end_time = time.time()
                    
                    return TestResult(
                        test_id=test_id,
                        test_type=f"get_{endpoint}",
                        start_time=start_time,
                        end_time=end_time,
                        status_code=response.status,
                        response_time_ms=(end_time - start_time) * 1000,
                        success=200 <= response.status < 300,
                        request_size_bytes=request_size,
                        response_size_bytes=response_size
                    )
                    
        except Exception as e:
            end_time = time.time()
            return TestResult(
                test_id=test_id,
                test_type=f"{method.lower()}_{endpoint}",
                start_time=start_time,
                end_time=end_time,
                status_code=0,
                response_time_ms=(end_time - start_time) * 1000,
                success=False,
                error_message=str(e),
                request_size_bytes=request_size,
                response_size_bytes=response_size
            )
    
    async def sustained_load_test(self, duration_seconds: int, concurrent_users: int) -> List[TestResult]:
        """Run sustained load test with multiple concurrent users."""
        logger.info(f"Starting sustained load test: {concurrent_users} users for {duration_seconds} seconds")
        
        end_time = time.time() + duration_seconds
        semaphore = asyncio.Semaphore(concurrent_users)
        tasks = []
        
        async def user_session():
            """Simulate a single user session."""
            async with semaphore:
                session_results = []
                while time.time() < end_time:
                    # Simulate realistic user behavior
                    endpoints = [
                        ('health', 'GET', None, 'small'),
                        ('upload', 'POST', None, random.choice(self.config['document_sizes'])),
                        ('status', 'GET', None, 'small'),
                        ('formats', 'GET', None, 'small')
                    ]
                    
                    endpoint, method, data, doc_size = random.choice(endpoints)
                    result = await self.single_api_request(endpoint, method, data, doc_size)
                    session_results.append(result)
                    
                    # Wait between requests (simulate user think time)
                    await asyncio.sleep(random.uniform(1, 5))
                
                return session_results
        
        # Create user sessions
        for _ in range(concurrent_users):
            task = asyncio.create_task(user_session())
            tasks.append(task)
        
        # Wait for all sessions to complete
        all_results = []
        for task in asyncio.as_completed(tasks):
            session_results = await task
            all_results.extend(session_results)
        
        logger.info(f"Sustained load test completed: {len(all_results)} requests processed")
        return all_results
    
    async def spike_test(self, peak_users: int, spike_duration: int = 60) -> List[TestResult]:
        """Run spike test to validate system behavior under sudden load."""
        logger.info(f"Starting spike test: {peak_users} users for {spike_duration} seconds")
        
        # Start with minimal load
        base_users = max(1, peak_users // 10)
        
        # Ramp up quickly to peak
        logger.info(f"Ramping up from {base_users} to {peak_users} users")
        results = []
        
        # Base load
        base_results = await self.sustained_load_test(30, base_users)
        results.extend(base_results)
        
        # Spike
        spike_results = await self.sustained_load_test(spike_duration, peak_users)
        results.extend(spike_results)
        
        # Cool down
        cooldown_results = await self.sustained_load_test(30, base_users)
        results.extend(cooldown_results)
        
        logger.info(f"Spike test completed: {len(results)} total requests")
        return results
    
    async def cold_start_test(self) -> List[TestResult]:
        """Test cold start performance by calling functions after idle period."""
        logger.info("Starting cold start test")
        
        # Wait to ensure functions are cold
        logger.info("Waiting 15 minutes for functions to go cold...")
        await asyncio.sleep(900)  # 15 minutes
        
        # Make simultaneous requests to trigger cold starts
        cold_start_tasks = []
        for i in range(5):
            doc_size = random.choice(['small', 'medium'])
            task = asyncio.create_task(
                self.single_api_request('upload', 'POST', None, doc_size)
            )
            cold_start_tasks.append(task)
        
        results = await asyncio.gather(*cold_start_tasks)
        
        logger.info(f"Cold start test completed: {len(results)} requests")
        return list(results)
    
    def analyze_results(self, results: List[TestResult]) -> TestSummary:
        """Analyze test results and generate summary."""
        if not results:
            raise ValueError("No test results to analyze")
        
        successful_results = [r for r in results if r.success]
        failed_results = [r for r in results if not r.success]
        
        response_times = [r.response_time_ms for r in successful_results]
        
        start_time = min(r.start_time for r in results)
        end_time = max(r.end_time for r in results)
        duration = end_time - start_time
        
        summary = TestSummary(
            test_name="AutoSpec.AI Load Test",
            environment=self.environment,
            start_time=datetime.fromtimestamp(start_time, timezone.utc).isoformat(),
            end_time=datetime.fromtimestamp(end_time, timezone.utc).isoformat(),
            duration_seconds=duration,
            total_requests=len(results),
            successful_requests=len(successful_results),
            failed_requests=len(failed_results),
            avg_response_time_ms=statistics.mean(response_times) if response_times else 0,
            p50_response_time_ms=statistics.median(response_times) if response_times else 0,
            p95_response_time_ms=self._percentile(response_times, 95) if response_times else 0,
            p99_response_time_ms=self._percentile(response_times, 99) if response_times else 0,
            max_response_time_ms=max(response_times) if response_times else 0,
            min_response_time_ms=min(response_times) if response_times else 0,
            requests_per_second=len(results) / duration if duration > 0 else 0,
            error_rate_percent=(len(failed_results) / len(results)) * 100,
            total_bytes_sent=sum(r.request_size_bytes for r in results),
            total_bytes_received=sum(r.response_size_bytes for r in results)
        )
        
        return summary
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile of a dataset."""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = (percentile / 100) * (len(sorted_data) - 1)
        if index.is_integer():
            return sorted_data[int(index)]
        else:
            lower = sorted_data[int(index)]
            upper = sorted_data[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))
    
    def generate_performance_report(self, summary: TestSummary, 
                                  results: List[TestResult]) -> str:
        """Generate comprehensive performance report."""
        
        # Group results by test type
        results_by_type = {}
        for result in results:
            if result.test_type not in results_by_type:
                results_by_type[result.test_type] = []
            results_by_type[result.test_type].append(result)
        
        report = f"""
# AutoSpec.AI Load Testing Report

## Test Summary
- **Environment**: {summary.environment}
- **Test Duration**: {summary.duration_seconds:.1f} seconds
- **Start Time**: {summary.start_time}
- **End Time**: {summary.end_time}

## Performance Metrics
- **Total Requests**: {summary.total_requests:,}
- **Successful Requests**: {summary.successful_requests:,}
- **Failed Requests**: {summary.failed_requests:,}
- **Success Rate**: {100 - summary.error_rate_percent:.2f}%
- **Requests/Second**: {summary.requests_per_second:.2f}

## Response Time Analysis
- **Average**: {summary.avg_response_time_ms:.0f}ms
- **Median (P50)**: {summary.p50_response_time_ms:.0f}ms
- **P95**: {summary.p95_response_time_ms:.0f}ms
- **P99**: {summary.p99_response_time_ms:.0f}ms
- **Min**: {summary.min_response_time_ms:.0f}ms
- **Max**: {summary.max_response_time_ms:.0f}ms

## Data Transfer
- **Total Sent**: {summary.total_bytes_sent / 1024 / 1024:.2f} MB
- **Total Received**: {summary.total_bytes_received / 1024 / 1024:.2f} MB

## Performance by Test Type
"""
        
        for test_type, type_results in results_by_type.items():
            successful = [r for r in type_results if r.success]
            if successful:
                avg_time = statistics.mean([r.response_time_ms for r in successful])
                success_rate = (len(successful) / len(type_results)) * 100
                report += f"""
### {test_type}
- **Requests**: {len(type_results):,}
- **Success Rate**: {success_rate:.1f}%
- **Avg Response Time**: {avg_time:.0f}ms
"""
        
        # Performance benchmarks
        report += """

## Performance Benchmarks

### API Response Time Targets
- **Health Check**: < 100ms (actual: {health_time:.0f}ms)
- **Document Upload**: < 2000ms (actual: {upload_time:.0f}ms)
- **Status Check**: < 200ms (actual: {status_time:.0f}ms)

### Load Handling Targets
- **Concurrent Users**: Target {target_users}, Tested {actual_users}
- **Requests/Second**: Target {target_rps:.1f}, Actual {actual_rps:.1f}
- **Error Rate**: Target < 1%, Actual {error_rate:.2f}%

## Recommendations
""".format(
            health_time=self._get_avg_time_for_type(results_by_type, 'get_health'),
            upload_time=self._get_avg_time_for_type(results_by_type, 'upload_'),
            status_time=self._get_avg_time_for_type(results_by_type, 'get_status'),
            target_users=self.config['max_concurrent_users'],
            actual_users=summary.total_requests / summary.duration_seconds,
            target_rps=self.config['api_request_rate'],
            actual_rps=summary.requests_per_second,
            error_rate=summary.error_rate_percent
        )
        
        # Add recommendations based on results
        if summary.error_rate_percent > 5:
            report += "- ⚠️ **High Error Rate**: Investigate failed requests and consider scaling\n"
        
        if summary.p95_response_time_ms > 5000:
            report += "- ⚠️ **High Response Times**: Consider optimizing Lambda performance\n"
        
        if summary.requests_per_second < self.config['api_request_rate']:
            report += "- ⚠️ **Low Throughput**: System may need additional capacity\n"
        
        if summary.error_rate_percent < 1 and summary.p95_response_time_ms < 2000:
            report += "- ✅ **Excellent Performance**: System is performing within targets\n"
        
        report += """
## Next Steps
1. Review CloudWatch metrics during test period
2. Analyze X-Ray traces for performance bottlenecks
3. Check provisioned concurrency utilization
4. Consider auto-scaling adjustments if needed
5. Re-run tests after optimizations
"""
        
        return report
    
    def _get_avg_time_for_type(self, results_by_type: Dict, type_prefix: str) -> float:
        """Get average response time for test types matching prefix."""
        matching_results = []
        for test_type, results in results_by_type.items():
            if test_type.startswith(type_prefix):
                matching_results.extend([r for r in results if r.success])
        
        if matching_results:
            return statistics.mean([r.response_time_ms for r in matching_results])
        return 0
    
    async def run_comprehensive_test_suite(self) -> Dict[str, Any]:
        """Run comprehensive test suite covering multiple scenarios."""
        logger.info("Starting comprehensive load testing suite")
        
        all_results = []
        test_scenarios = {}
        
        # 1. Health check test
        logger.info("Running health check test...")
        health_results = []
        for _ in range(10):
            result = await self.single_api_request('health', 'GET')
            health_results.append(result)
            await asyncio.sleep(0.5)
        
        all_results.extend(health_results)
        test_scenarios['health_check'] = self.analyze_results(health_results)
        
        # 2. Sustained load test
        logger.info("Running sustained load test...")
        sustained_results = await self.sustained_load_test(
            self.config['test_duration'],
            self.config['max_concurrent_users']
        )
        all_results.extend(sustained_results)
        test_scenarios['sustained_load'] = self.analyze_results(sustained_results)
        
        # 3. Spike test
        logger.info("Running spike test...")
        spike_results = await self.spike_test(
            int(self.config['max_concurrent_users'] * self.config['stress_multiplier'])
        )
        all_results.extend(spike_results)
        test_scenarios['spike_test'] = self.analyze_results(spike_results)
        
        # Overall summary
        overall_summary = self.analyze_results(all_results)
        
        return {
            'overall_summary': overall_summary,
            'test_scenarios': test_scenarios,
            'detailed_results': all_results
        }

async def main():
    parser = argparse.ArgumentParser(description='AutoSpec.AI Load Testing Suite')
    parser.add_argument('--environment', required=True, choices=['dev', 'staging', 'prod'],
                       help='Environment to test')
    parser.add_argument('--test-type', choices=['api', 'full', 'spike', 'cold-start', 'benchmark'],
                       default='api', help='Type of test to run')
    parser.add_argument('--duration', type=int, help='Test duration in seconds')
    parser.add_argument('--users', type=int, help='Number of concurrent users')
    parser.add_argument('--api-url', help='API Gateway URL (optional)')
    parser.add_argument('--report', action='store_true', help='Generate detailed report')
    parser.add_argument('--output-file', help='Output file for results')
    
    args = parser.parse_args()
    
    # Initialize load tester
    tester = AutoSpecLoadTester(args.environment, args.api_url)
    
    try:
        await tester.setup_session()
        
        if args.test_type == 'api':
            # Quick API test
            results = []
            for _ in range(10):
                result = await tester.single_api_request('health', 'GET')
                results.append(result)
            
        elif args.test_type == 'full':
            # Comprehensive test suite
            test_data = await tester.run_comprehensive_test_suite()
            results = test_data['detailed_results']
            
        elif args.test_type == 'spike':
            # Spike test
            users = args.users or tester.config['max_concurrent_users'] * 2
            results = await tester.spike_test(users)
            
        elif args.test_type == 'cold-start':
            # Cold start test
            results = await tester.cold_start_test()
            
        elif args.test_type == 'benchmark':
            # Benchmark test
            duration = args.duration or tester.config['test_duration']
            users = args.users or tester.config['max_concurrent_users']
            results = await tester.sustained_load_test(duration, users)
        
        # Analyze results
        summary = tester.analyze_results(results)
        
        # Generate report
        if args.report:
            report = tester.generate_performance_report(summary, results)
            
            if args.output_file:
                with open(args.output_file, 'w') as f:
                    f.write(report)
                logger.info(f"Report saved to {args.output_file}")
            else:
                print(report)
        else:
            # Print summary
            print(f"Test completed: {summary.total_requests} requests")
            print(f"Success rate: {100 - summary.error_rate_percent:.1f}%")
            print(f"Average response time: {summary.avg_response_time_ms:.0f}ms")
            print(f"Requests/second: {summary.requests_per_second:.1f}")
        
    finally:
        await tester.cleanup_session()

if __name__ == '__main__':
    asyncio.run(main())