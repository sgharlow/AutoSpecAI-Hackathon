#!/usr/bin/env python3
"""
AutoSpec.AI Performance Benchmarking Framework

Establishes performance baselines, tracks improvements, and validates
the impact of optimizations like provisioned concurrency.

Usage:
    python3 performance-benchmarks.py --environment dev --baseline
    python3 performance-benchmarks.py --environment prod --compare --before-optimization
    python3 performance-benchmarks.py --environment staging --trend-analysis
"""

import argparse
import boto3
import json
import time
import statistics
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import logging
import asyncio
import subprocess

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class PerformanceBaseline:
    """Performance baseline metrics."""
    environment: str
    timestamp: str
    api_response_time_p50: float
    api_response_time_p95: float
    api_response_time_p99: float
    upload_response_time_p50: float
    upload_response_time_p95: float
    cold_start_duration_avg: float
    cold_start_frequency: float
    throughput_requests_per_second: float
    error_rate_percent: float
    provisioned_concurrency_utilization: float
    lambda_duration_avg: Dict[str, float]
    lambda_memory_utilization: Dict[str, float]
    dynamodb_consumed_capacity: float
    s3_request_latency: float
    bedrock_processing_time: float
    total_cost_per_1000_requests: float

@dataclass
class BenchmarkComparison:
    """Comparison between two benchmarks."""
    before: PerformanceBaseline
    after: PerformanceBaseline
    improvements: Dict[str, float]  # Percentage improvements
    regressions: Dict[str, float]   # Percentage regressions
    overall_performance_score: float
    cost_impact_percent: float

class PerformanceBenchmarkingFramework:
    """Framework for measuring and tracking AutoSpec.AI performance."""
    
    def __init__(self, environment: str):
        self.environment = environment
        self.cloudwatch = boto3.client('cloudwatch')
        self.lambda_client = boto3.client('lambda')
        self.dynamodb = boto3.client('dynamodb')
        self.s3 = boto3.client('s3')
        
        # Performance targets by environment
        self.performance_targets = {
            'dev': {
                'api_response_time_p95': 2000,  # ms
                'upload_response_time_p95': 5000,  # ms
                'cold_start_duration_avg': 2000,  # ms
                'throughput_rps': 10,
                'error_rate_percent': 5.0,
                'cost_per_1000_requests': 0.50  # USD
            },
            'staging': {
                'api_response_time_p95': 1500,
                'upload_response_time_p95': 4000,
                'cold_start_duration_avg': 1500,
                'throughput_rps': 25,
                'error_rate_percent': 2.0,
                'cost_per_1000_requests': 0.40
            },
            'prod': {
                'api_response_time_p95': 1000,
                'upload_response_time_p95': 3000,
                'cold_start_duration_avg': 1000,
                'throughput_rps': 50,
                'error_rate_percent': 1.0,
                'cost_per_1000_requests': 0.30
            }
        }
    
    async def collect_current_metrics(self, duration_hours: int = 1) -> PerformanceBaseline:
        """Collect current performance metrics for baseline."""
        logger.info(f"Collecting performance metrics for {self.environment} environment")
        
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=duration_hours)
        
        # Collect metrics in parallel
        metrics_tasks = [
            self._get_api_metrics(start_time, end_time),
            self._get_lambda_metrics(start_time, end_time),
            self._get_dynamodb_metrics(start_time, end_time),
            self._get_s3_metrics(start_time, end_time),
            self._get_cost_metrics(start_time, end_time)
        ]
        
        api_metrics, lambda_metrics, dynamodb_metrics, s3_metrics, cost_metrics = \
            await asyncio.gather(*metrics_tasks)
        
        # Combine into baseline
        baseline = PerformanceBaseline(
            environment=self.environment,
            timestamp=datetime.now(timezone.utc).isoformat(),
            api_response_time_p50=api_metrics.get('response_time_p50', 0),
            api_response_time_p95=api_metrics.get('response_time_p95', 0),
            api_response_time_p99=api_metrics.get('response_time_p99', 0),
            upload_response_time_p50=api_metrics.get('upload_time_p50', 0),
            upload_response_time_p95=api_metrics.get('upload_time_p95', 0),
            cold_start_duration_avg=lambda_metrics.get('cold_start_avg', 0),
            cold_start_frequency=lambda_metrics.get('cold_start_frequency', 0),
            throughput_requests_per_second=api_metrics.get('throughput_rps', 0),
            error_rate_percent=api_metrics.get('error_rate', 0),
            provisioned_concurrency_utilization=lambda_metrics.get('pc_utilization', 0),
            lambda_duration_avg=lambda_metrics.get('duration_by_function', {}),
            lambda_memory_utilization=lambda_metrics.get('memory_utilization', {}),
            dynamodb_consumed_capacity=dynamodb_metrics.get('consumed_capacity', 0),
            s3_request_latency=s3_metrics.get('request_latency', 0),
            bedrock_processing_time=lambda_metrics.get('bedrock_processing_time', 0),
            total_cost_per_1000_requests=cost_metrics.get('cost_per_1000_requests', 0)
        )
        
        return baseline
    
    async def _get_api_metrics(self, start_time: datetime, end_time: datetime) -> Dict[str, float]:
        """Get API Gateway and Lambda metrics."""
        metrics = {}
        
        try:
            # API Gateway metrics
            api_function_name = f"AutoSpecAI-ApiFunction-{self.environment}"
            
            # Response time percentiles
            for percentile in [50, 95, 99]:
                response = await self._get_cloudwatch_metric(
                    'AWS/Lambda', 'Duration', 
                    [{'Name': 'FunctionName', 'Value': api_function_name}],
                    start_time, end_time, f'p{percentile}'
                )
                if response:
                    metrics[f'response_time_p{percentile}'] = response
            
            # Throughput
            invocations = await self._get_cloudwatch_metric(
                'AWS/Lambda', 'Invocations',
                [{'Name': 'FunctionName', 'Value': api_function_name}],
                start_time, end_time, 'Sum'
            )
            duration_hours = (end_time - start_time).total_seconds() / 3600
            metrics['throughput_rps'] = (invocations or 0) / (duration_hours * 3600)
            
            # Error rate
            errors = await self._get_cloudwatch_metric(
                'AWS/Lambda', 'Errors',
                [{'Name': 'FunctionName', 'Value': api_function_name}],
                start_time, end_time, 'Sum'
            )
            if invocations and invocations > 0:
                metrics['error_rate'] = ((errors or 0) / invocations) * 100
            
            # Upload-specific metrics (Process function)
            process_function_name = f"AutoSpecAI-ProcessFunction-{self.environment}"
            for percentile in [50, 95]:
                upload_time = await self._get_cloudwatch_metric(
                    'AWS/Lambda', 'Duration',
                    [{'Name': 'FunctionName', 'Value': process_function_name}],
                    start_time, end_time, f'p{percentile}'
                )
                if upload_time:
                    metrics[f'upload_time_p{percentile}'] = upload_time
            
        except Exception as e:
            logger.error(f"Error collecting API metrics: {e}")
        
        return metrics
    
    async def _get_lambda_metrics(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Get Lambda-specific metrics."""
        metrics = {
            'duration_by_function': {},
            'memory_utilization': {},
            'cold_start_avg': 0,
            'cold_start_frequency': 0,
            'pc_utilization': 0,
            'bedrock_processing_time': 0
        }
        
        function_names = [
            f"AutoSpecAI-IngestFunction-{self.environment}",
            f"AutoSpecAI-ProcessFunction-{self.environment}",
            f"AutoSpecAI-FormatFunction-{self.environment}",
            f"AutoSpecAI-ApiFunction-{self.environment}",
            f"AutoSpecAI-SlackFunction-{self.environment}",
            f"AutoSpecAI-MonitoringFunction-{self.environment}"
        ]
        
        try:
            for function_name in function_names:
                # Duration
                duration = await self._get_cloudwatch_metric(
                    'AWS/Lambda', 'Duration',
                    [{'Name': 'FunctionName', 'Value': function_name}],
                    start_time, end_time, 'Average'
                )
                if duration:
                    metrics['duration_by_function'][function_name] = duration
                
                # Memory utilization (if available)
                # Note: This would require custom metrics from Lambda functions
                
                # Cold start metrics
                init_duration = await self._get_cloudwatch_metric(
                    'AWS/Lambda', 'InitDuration',
                    [{'Name': 'FunctionName', 'Value': function_name}],
                    start_time, end_time, 'Average'
                )
                if init_duration:
                    metrics['cold_start_avg'] = max(metrics['cold_start_avg'], init_duration)
                
                # Provisioned concurrency utilization
                if 'ProcessFunction' in function_name or 'FormatFunction' in function_name or 'ApiFunction' in function_name:
                    pc_util = await self._get_cloudwatch_metric(
                        'AWS/Lambda', 'ProvisionedConcurrencyUtilization',
                        [
                            {'Name': 'FunctionName', 'Value': function_name},
                            {'Name': 'Resource', 'Value': f'{function_name}:LIVE'}
                        ],
                        start_time, end_time, 'Average'
                    )
                    if pc_util:
                        metrics['pc_utilization'] = max(metrics['pc_utilization'], pc_util)
            
            # Bedrock processing time (from Process function)
            process_function = f"AutoSpecAI-ProcessFunction-{self.environment}"
            bedrock_time = await self._get_cloudwatch_metric(
                'AWS/Lambda', 'Duration',
                [{'Name': 'FunctionName', 'Value': process_function}],
                start_time, end_time, 'Average'
            )
            if bedrock_time:
                metrics['bedrock_processing_time'] = bedrock_time
                
        except Exception as e:
            logger.error(f"Error collecting Lambda metrics: {e}")
        
        return metrics
    
    async def _get_dynamodb_metrics(self, start_time: datetime, end_time: datetime) -> Dict[str, float]:
        """Get DynamoDB metrics."""
        metrics = {}
        
        try:
            table_name = f"autospec-ai-history-{self.environment}"
            
            # Consumed capacity
            consumed_capacity = await self._get_cloudwatch_metric(
                'AWS/DynamoDB', 'ConsumedReadCapacityUnits',
                [{'Name': 'TableName', 'Value': table_name}],
                start_time, end_time, 'Sum'
            )
            metrics['consumed_capacity'] = consumed_capacity or 0
            
        except Exception as e:
            logger.error(f"Error collecting DynamoDB metrics: {e}")
        
        return metrics
    
    async def _get_s3_metrics(self, start_time: datetime, end_time: datetime) -> Dict[str, float]:
        """Get S3 metrics."""
        metrics = {}
        
        try:
            bucket_name = f"autospec-ai-documents-{self.environment}"
            
            # Request latency
            latency = await self._get_cloudwatch_metric(
                'AWS/S3', 'FirstByteLatency',
                [
                    {'Name': 'BucketName', 'Value': bucket_name},
                    {'Name': 'FilterId', 'Value': 'EntireBucket'}
                ],
                start_time, end_time, 'Average'
            )
            metrics['request_latency'] = latency or 0
            
        except Exception as e:
            logger.error(f"Error collecting S3 metrics: {e}")
        
        return metrics
    
    async def _get_cost_metrics(self, start_time: datetime, end_time: datetime) -> Dict[str, float]:
        """Get cost metrics (estimated)."""
        metrics = {}
        
        try:
            # This is a simplified cost calculation
            # In practice, you'd use AWS Cost Explorer API or detailed billing data
            
            # Lambda invocations
            total_invocations = 0
            function_names = [
                f"AutoSpecAI-IngestFunction-{self.environment}",
                f"AutoSpecAI-ProcessFunction-{self.environment}",
                f"AutoSpecAI-FormatFunction-{self.environment}",
                f"AutoSpecAI-ApiFunction-{self.environment}"
            ]
            
            for function_name in function_names:
                invocations = await self._get_cloudwatch_metric(
                    'AWS/Lambda', 'Invocations',
                    [{'Name': 'FunctionName', 'Value': function_name}],
                    start_time, end_time, 'Sum'
                )
                total_invocations += invocations or 0
            
            # Simplified cost calculation (approximate)
            # Lambda: $0.0000166667 per GB-second + $0.0000002 per request
            # Provisioned concurrency: $0.0000097 per GB-second
            estimated_cost = (total_invocations * 0.0000002) + (total_invocations * 0.001)  # Simplified
            
            if total_invocations > 0:
                metrics['cost_per_1000_requests'] = (estimated_cost / total_invocations) * 1000
            
        except Exception as e:
            logger.error(f"Error collecting cost metrics: {e}")
        
        return metrics
    
    async def _get_cloudwatch_metric(self, namespace: str, metric_name: str, 
                                   dimensions: List[Dict], start_time: datetime, 
                                   end_time: datetime, statistic: str) -> Optional[float]:
        """Get CloudWatch metric value."""
        try:
            response = self.cloudwatch.get_metric_statistics(
                Namespace=namespace,
                MetricName=metric_name,
                Dimensions=dimensions,
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,  # 1 hour
                Statistics=[statistic]
            )
            
            if response['Datapoints']:
                values = [dp[statistic] for dp in response['Datapoints']]
                return statistics.mean(values)
                
        except Exception as e:
            logger.warning(f"Could not get metric {metric_name}: {e}")
        
        return None
    
    def save_baseline(self, baseline: PerformanceBaseline, filename: Optional[str] = None):
        """Save baseline to file."""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"baseline_{self.environment}_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(asdict(baseline), f, indent=2)
        
        logger.info(f"Baseline saved to {filename}")
        return filename
    
    def load_baseline(self, filename: str) -> PerformanceBaseline:
        """Load baseline from file."""
        with open(filename, 'r') as f:
            data = json.load(f)
        
        return PerformanceBaseline(**data)
    
    def compare_baselines(self, before: PerformanceBaseline, 
                         after: PerformanceBaseline) -> BenchmarkComparison:
        """Compare two baselines and calculate improvements."""
        improvements = {}
        regressions = {}
        
        # Compare key metrics
        comparisons = {
            'api_response_time_p95': 'lower_is_better',
            'upload_response_time_p95': 'lower_is_better',
            'cold_start_duration_avg': 'lower_is_better',
            'throughput_requests_per_second': 'higher_is_better',
            'error_rate_percent': 'lower_is_better',
            'provisioned_concurrency_utilization': 'target_70_percent',
            'total_cost_per_1000_requests': 'lower_is_better'
        }
        
        for metric, direction in comparisons.items():
            before_value = getattr(before, metric, 0)
            after_value = getattr(after, metric, 0)
            
            if before_value == 0:
                continue
                
            percent_change = ((after_value - before_value) / before_value) * 100
            
            if direction == 'lower_is_better':
                if percent_change < 0:  # Improvement
                    improvements[metric] = abs(percent_change)
                else:  # Regression
                    regressions[metric] = percent_change
            elif direction == 'higher_is_better':
                if percent_change > 0:  # Improvement
                    improvements[metric] = percent_change
                else:  # Regression
                    regressions[metric] = abs(percent_change)
            elif direction == 'target_70_percent':
                # Optimal utilization is around 70%
                before_distance = abs(before_value - 70)
                after_distance = abs(after_value - 70)
                if after_distance < before_distance:
                    improvements[metric] = ((before_distance - after_distance) / before_distance) * 100
        
        # Calculate overall performance score
        score_factors = {
            'api_response_time_p95': 0.25,
            'throughput_requests_per_second': 0.20,
            'error_rate_percent': 0.20,
            'cold_start_duration_avg': 0.15,
            'total_cost_per_1000_requests': 0.20
        }
        
        overall_score = 0
        for metric, weight in score_factors.items():
            if metric in improvements:
                overall_score += improvements[metric] * weight
            elif metric in regressions:
                overall_score -= regressions[metric] * weight
        
        # Cost impact
        cost_impact = 0
        if before.total_cost_per_1000_requests > 0:
            cost_impact = ((after.total_cost_per_1000_requests - before.total_cost_per_1000_requests) 
                          / before.total_cost_per_1000_requests) * 100
        
        return BenchmarkComparison(
            before=before,
            after=after,
            improvements=improvements,
            regressions=regressions,
            overall_performance_score=overall_score,
            cost_impact_percent=cost_impact
        )
    
    def generate_benchmark_report(self, baseline: PerformanceBaseline, 
                                comparison: Optional[BenchmarkComparison] = None) -> str:
        """Generate comprehensive benchmark report."""
        targets = self.performance_targets.get(self.environment, {})
        
        report = f"""
# AutoSpec.AI Performance Benchmark Report

## Environment: {baseline.environment.upper()}
- **Timestamp**: {baseline.timestamp}
- **Collection Duration**: 1 hour of metrics

## Current Performance Metrics

### API Performance
- **Response Time P50**: {baseline.api_response_time_p50:.0f}ms
- **Response Time P95**: {baseline.api_response_time_p95:.0f}ms (Target: {targets.get('api_response_time_p95', 'N/A')}ms)
- **Response Time P99**: {baseline.api_response_time_p99:.0f}ms
- **Upload P95**: {baseline.upload_response_time_p95:.0f}ms (Target: {targets.get('upload_response_time_p95', 'N/A')}ms)

### Throughput & Reliability
- **Requests/Second**: {baseline.throughput_requests_per_second:.1f} (Target: {targets.get('throughput_rps', 'N/A')})
- **Error Rate**: {baseline.error_rate_percent:.2f}% (Target: <{targets.get('error_rate_percent', 'N/A')}%)

### Lambda Performance
- **Cold Start Avg**: {baseline.cold_start_duration_avg:.0f}ms (Target: <{targets.get('cold_start_duration_avg', 'N/A')}ms)
- **PC Utilization**: {baseline.provisioned_concurrency_utilization:.1f}%
- **Bedrock Processing**: {baseline.bedrock_processing_time:.0f}ms

### Infrastructure
- **DynamoDB Capacity**: {baseline.dynamodb_consumed_capacity:.1f} units
- **S3 Latency**: {baseline.s3_request_latency:.0f}ms

### Cost Efficiency
- **Cost/1000 Requests**: ${baseline.total_cost_per_1000_requests:.3f} (Target: <${targets.get('cost_per_1000_requests', 'N/A')})

## Function Performance Breakdown
"""
        
        for function_name, duration in baseline.lambda_duration_avg.items():
            report += f"- **{function_name}**: {duration:.0f}ms average\n"
        
        if comparison:
            report += f"""

## Performance Comparison

### Overall Performance Score: {comparison.overall_performance_score:+.1f}%

### Improvements 🚀
"""
            for metric, improvement in comparison.improvements.items():
                report += f"- **{metric}**: {improvement:.1f}% better\n"
            
            if comparison.regressions:
                report += "\n### Regressions ⚠️\n"
                for metric, regression in comparison.regressions.items():
                    report += f"- **{metric}**: {regression:.1f}% worse\n"
            
            report += f"""

### Cost Impact
- **Cost Change**: {comparison.cost_impact_percent:+.1f}%
"""
        
        # Performance assessment
        report += "\n## Performance Assessment\n"
        
        # Check against targets
        meets_targets = []
        fails_targets = []
        
        for metric, target in targets.items():
            current_value = getattr(baseline, metric, None)
            if current_value is not None:
                if metric in ['api_response_time_p95', 'upload_response_time_p95', 'cold_start_duration_avg', 
                             'error_rate_percent', 'cost_per_1000_requests']:
                    # Lower is better
                    if current_value <= target:
                        meets_targets.append(f"✅ {metric}: {current_value} ≤ {target}")
                    else:
                        fails_targets.append(f"❌ {metric}: {current_value} > {target}")
                else:
                    # Higher is better
                    if current_value >= target:
                        meets_targets.append(f"✅ {metric}: {current_value} ≥ {target}")
                    else:
                        fails_targets.append(f"❌ {metric}: {current_value} < {target}")
        
        if meets_targets:
            report += "\n### Targets Met:\n"
            for target in meets_targets:
                report += f"{target}\n"
        
        if fails_targets:
            report += "\n### Targets Not Met:\n"
            for target in fails_targets:
                report += f"{target}\n"
        
        report += """

## Recommendations

### Performance Optimization
1. Monitor provisioned concurrency utilization - target 70-80%
2. Review cold start frequency and optimize Lambda initialization
3. Analyze P99 response times for outlier identification
4. Consider auto-scaling adjustments based on throughput patterns

### Cost Optimization
1. Review provisioned concurrency allocation weekly
2. Monitor usage patterns for right-sizing opportunities
3. Consider scheduled scaling for predictable workloads
4. Evaluate memory allocation vs cost trade-offs

### Monitoring
1. Set up alerts for performance degradation
2. Implement trend analysis for capacity planning
3. Regular benchmark comparisons (weekly/monthly)
4. Dashboard monitoring for real-time visibility
"""
        
        return report
    
    async def run_load_test_benchmark(self) -> PerformanceBaseline:
        """Run load test and collect baseline metrics."""
        logger.info("Running load test to generate benchmark data")
        
        # Run load test
        load_test_cmd = [
            'python3', 'load-testing-suite.py',
            '--environment', self.environment,
            '--test-type', 'benchmark',
            '--duration', '300',  # 5 minutes
            '--users', str(self.performance_targets[self.environment]['throughput_rps'])
        ]
        
        try:
            result = subprocess.run(load_test_cmd, capture_output=True, text=True, check=True)
            logger.info("Load test completed successfully")
        except subprocess.CalledProcessError as e:
            logger.error(f"Load test failed: {e}")
            logger.error(f"Stdout: {e.stdout}")
            logger.error(f"Stderr: {e.stderr}")
        
        # Wait for metrics to be available
        await asyncio.sleep(300)  # 5 minutes
        
        # Collect baseline metrics
        baseline = await self.collect_current_metrics(duration_hours=1)
        return baseline

async def main():
    parser = argparse.ArgumentParser(description='AutoSpec.AI Performance Benchmarking')
    parser.add_argument('--environment', required=True, choices=['dev', 'staging', 'prod'],
                       help='Environment to benchmark')
    parser.add_argument('--baseline', action='store_true',
                       help='Collect and save new baseline')
    parser.add_argument('--compare', action='store_true',
                       help='Compare with previous baseline')
    parser.add_argument('--before-file', help='Before baseline file for comparison')
    parser.add_argument('--after-file', help='After baseline file for comparison')
    parser.add_argument('--load-test', action='store_true',
                       help='Run load test before collecting baseline')
    parser.add_argument('--output', help='Output file for report')
    
    args = parser.parse_args()
    
    framework = PerformanceBenchmarkingFramework(args.environment)
    
    try:
        if args.baseline:
            # Collect new baseline
            if args.load_test:
                baseline = await framework.run_load_test_benchmark()
            else:
                baseline = await framework.collect_current_metrics()
            
            filename = framework.save_baseline(baseline)
            report = framework.generate_benchmark_report(baseline)
            
            if args.output:
                with open(args.output, 'w') as f:
                    f.write(report)
                logger.info(f"Benchmark report saved to {args.output}")
            else:
                print(report)
                
        elif args.compare:
            # Compare baselines
            if not args.before_file or not args.after_file:
                logger.error("Both --before-file and --after-file required for comparison")
                return 1
            
            before = framework.load_baseline(args.before_file)
            after = framework.load_baseline(args.after_file)
            
            comparison = framework.compare_baselines(before, after)
            report = framework.generate_benchmark_report(after, comparison)
            
            if args.output:
                with open(args.output, 'w') as f:
                    f.write(report)
                logger.info(f"Comparison report saved to {args.output}")
            else:
                print(report)
        else:
            # Just collect current metrics and report
            baseline = await framework.collect_current_metrics()
            report = framework.generate_benchmark_report(baseline)
            print(report)
            
    except Exception as e:
        logger.error(f"Benchmarking failed: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    exit(asyncio.run(main()))