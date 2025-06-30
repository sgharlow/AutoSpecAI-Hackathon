#!/usr/bin/env python3
"""
AutoSpec.AI Cache Performance Analyzer

Analyzes caching performance, identifies optimization opportunities,
and provides recommendations for cache tuning.

Usage:
    python3 cache-performance-analyzer.py --environment dev --analyze
    python3 cache-performance-analyzer.py --environment prod --optimize
    python3 cache-performance-analyzer.py --environment staging --report
"""

import argparse
import boto3
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class CacheMetrics:
    """Cache performance metrics."""
    hit_rate: float
    miss_rate: float
    total_requests: int
    cache_size_bytes: int
    eviction_rate: float
    average_response_time_ms: float
    memory_utilization_percent: float
    cost_per_request: float

@dataclass
class CacheAnalysis:
    """Cache performance analysis results."""
    environment: str
    timestamp: str
    memory_cache: CacheMetrics
    dynamodb_cache: CacheMetrics
    s3_cache: Optional[CacheMetrics]
    redis_cache: Optional[CacheMetrics]
    overall_metrics: CacheMetrics
    recommendations: List[str]
    optimization_score: float

class CachePerformanceAnalyzer:
    """Analyzes and optimizes cache performance across all layers."""
    
    def __init__(self, environment: str):
        self.environment = environment
        self.cloudwatch = boto3.client('cloudwatch')
        self.dynamodb = boto3.client('dynamodb')
        self.s3 = boto3.client('s3')
        
        # Cache table and bucket names
        self.cache_table = f'autospec-ai-cache-{environment}'
        self.cache_bucket = f'autospec-ai-cache-{environment}'
        
        # Performance thresholds
        self.thresholds = {
            'hit_rate_minimum': 70.0,  # 70% minimum hit rate
            'response_time_maximum': 100.0,  # 100ms maximum response time
            'memory_utilization_maximum': 80.0,  # 80% maximum memory usage
            'eviction_rate_maximum': 5.0,  # 5% maximum eviction rate
        }
    
    def analyze_cache_performance(self, hours: int = 24) -> CacheAnalysis:
        """Analyze cache performance across all layers."""
        logger.info(f"Analyzing cache performance for {self.environment} environment")
        
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=hours)
        
        # Analyze each cache layer
        memory_metrics = self._analyze_memory_cache(start_time, end_time)
        dynamodb_metrics = self._analyze_dynamodb_cache(start_time, end_time)
        s3_metrics = self._analyze_s3_cache(start_time, end_time)
        redis_metrics = self._analyze_redis_cache(start_time, end_time)
        
        # Calculate overall metrics
        overall_metrics = self._calculate_overall_metrics([
            memory_metrics, dynamodb_metrics, s3_metrics, redis_metrics
        ])
        
        # Generate recommendations
        recommendations = self._generate_recommendations({
            'memory': memory_metrics,
            'dynamodb': dynamodb_metrics,
            's3': s3_metrics,
            'redis': redis_metrics,
            'overall': overall_metrics
        })
        
        # Calculate optimization score
        optimization_score = self._calculate_optimization_score(overall_metrics)
        
        return CacheAnalysis(
            environment=self.environment,
            timestamp=datetime.now(timezone.utc).isoformat(),
            memory_cache=memory_metrics,
            dynamodb_cache=dynamodb_metrics,
            s3_cache=s3_metrics,
            redis_cache=redis_metrics,
            overall_metrics=overall_metrics,
            recommendations=recommendations,
            optimization_score=optimization_score
        )
    
    def _analyze_memory_cache(self, start_time: datetime, end_time: datetime) -> CacheMetrics:
        """Analyze in-memory cache performance."""
        try:
            # Get custom metrics from Lambda functions
            hit_rate = self._get_cloudwatch_metric(
                'AutoSpecAI/Cache', 'HitRate',
                [{'Name': 'CacheType', 'Value': 'Memory'}],
                start_time, end_time, 'Average'
            ) or 0
            
            response_time = self._get_cloudwatch_metric(
                'AutoSpecAI/Cache', 'ResponseTime',
                [{'Name': 'CacheType', 'Value': 'Memory'}],
                start_time, end_time, 'Average'
            ) or 0
            
            cache_size = self._get_cloudwatch_metric(
                'AutoSpecAI/Cache', 'SizeBytes',
                [{'Name': 'CacheType', 'Value': 'Memory'}],
                start_time, end_time, 'Average'
            ) or 0
            
            return CacheMetrics(
                hit_rate=hit_rate,
                miss_rate=100 - hit_rate,
                total_requests=0,  # Will be populated from Lambda metrics
                cache_size_bytes=cache_size,
                eviction_rate=0,  # Memory cache eviction rate
                average_response_time_ms=response_time,
                memory_utilization_percent=0,  # Memory utilization
                cost_per_request=0.0001  # Estimated cost per request
            )
            
        except Exception as e:
            logger.error(f"Error analyzing memory cache: {e}")
            return self._create_empty_metrics()
    
    def _analyze_dynamodb_cache(self, start_time: datetime, end_time: datetime) -> CacheMetrics:
        """Analyze DynamoDB cache performance."""
        try:
            # Get DynamoDB metrics
            consumed_reads = self._get_cloudwatch_metric(
                'AWS/DynamoDB', 'ConsumedReadCapacityUnits',
                [{'Name': 'TableName', 'Value': self.cache_table}],
                start_time, end_time, 'Sum'
            ) or 0
            
            consumed_writes = self._get_cloudwatch_metric(
                'AWS/DynamoDB', 'ConsumedWriteCapacityUnits',
                [{'Name': 'TableName', 'Value': self.cache_table}],
                start_time, end_time, 'Sum'
            ) or 0
            
            successful_requests = self._get_cloudwatch_metric(
                'AWS/DynamoDB', 'SuccessfulRequestLatency',
                [{'Name': 'TableName', 'Value': self.cache_table}],
                start_time, end_time, 'SampleCount'
            ) or 0
            
            avg_latency = self._get_cloudwatch_metric(
                'AWS/DynamoDB', 'SuccessfulRequestLatency',
                [{'Name': 'TableName', 'Value': self.cache_table}],
                start_time, end_time, 'Average'
            ) or 0
            
            # Estimate hit rate based on read/write ratio
            total_requests = consumed_reads + consumed_writes
            hit_rate = (consumed_reads / total_requests * 100) if total_requests > 0 else 0
            
            # Estimate cache size from item count
            cache_size = self._estimate_dynamodb_cache_size()
            
            return CacheMetrics(
                hit_rate=hit_rate,
                miss_rate=100 - hit_rate,
                total_requests=int(total_requests),
                cache_size_bytes=cache_size,
                eviction_rate=0,  # DynamoDB TTL handles expiration
                average_response_time_ms=avg_latency,
                memory_utilization_percent=0,  # Not applicable
                cost_per_request=self._calculate_dynamodb_cost_per_request(consumed_reads, consumed_writes)
            )
            
        except Exception as e:
            logger.error(f"Error analyzing DynamoDB cache: {e}")
            return self._create_empty_metrics()
    
    def _analyze_s3_cache(self, start_time: datetime, end_time: datetime) -> Optional[CacheMetrics]:
        """Analyze S3 cache performance."""
        try:
            # Check if S3 cache is enabled
            try:
                self.s3.head_bucket(Bucket=self.cache_bucket)
            except:
                return None  # S3 cache not available
            
            # Get S3 metrics
            requests = self._get_cloudwatch_metric(
                'AWS/S3', 'NumberOfObjects',
                [
                    {'Name': 'BucketName', 'Value': self.cache_bucket},
                    {'Name': 'StorageType', 'Value': 'AllStorageTypes'}
                ],
                start_time, end_time, 'Average'
            ) or 0
            
            bucket_size = self._get_cloudwatch_metric(
                'AWS/S3', 'BucketSizeBytes',
                [
                    {'Name': 'BucketName', 'Value': self.cache_bucket},
                    {'Name': 'StorageType', 'Value': 'StandardStorage'}
                ],
                start_time, end_time, 'Average'
            ) or 0
            
            first_byte_latency = self._get_cloudwatch_metric(
                'AWS/S3', 'FirstByteLatency',
                [{'Name': 'BucketName', 'Value': self.cache_bucket}],
                start_time, end_time, 'Average'
            ) or 0
            
            return CacheMetrics(
                hit_rate=80.0,  # Estimated based on S3 usage patterns
                miss_rate=20.0,
                total_requests=int(requests),
                cache_size_bytes=bucket_size,
                eviction_rate=0,  # S3 lifecycle policies handle cleanup
                average_response_time_ms=first_byte_latency,
                memory_utilization_percent=0,  # Not applicable
                cost_per_request=0.0004  # S3 request cost
            )
            
        except Exception as e:
            logger.error(f"Error analyzing S3 cache: {e}")
            return None
    
    def _analyze_redis_cache(self, start_time: datetime, end_time: datetime) -> Optional[CacheMetrics]:
        """Analyze Redis cache performance."""
        if self.environment != 'prod':
            return None  # Redis only enabled in production
        
        try:
            # Get ElastiCache metrics
            hit_rate = self._get_cloudwatch_metric(
                'AWS/ElastiCache', 'CacheHitRate',
                [{'Name': 'CacheClusterId', 'Value': f'autospec-ai-redis-{self.environment}'}],
                start_time, end_time, 'Average'
            ) or 0
            
            cpu_utilization = self._get_cloudwatch_metric(
                'AWS/ElastiCache', 'CPUUtilization',
                [{'Name': 'CacheClusterId', 'Value': f'autospec-ai-redis-{self.environment}'}],
                start_time, end_time, 'Average'
            ) or 0
            
            memory_usage = self._get_cloudwatch_metric(
                'AWS/ElastiCache', 'DatabaseMemoryUsagePercentage',
                [{'Name': 'CacheClusterId', 'Value': f'autospec-ai-redis-{self.environment}'}],
                start_time, end_time, 'Average'
            ) or 0
            
            commands_processed = self._get_cloudwatch_metric(
                'AWS/ElastiCache', 'CmdConfigGet',
                [{'Name': 'CacheClusterId', 'Value': f'autospec-ai-redis-{self.environment}'}],
                start_time, end_time, 'Sum'
            ) or 0
            
            return CacheMetrics(
                hit_rate=hit_rate,
                miss_rate=100 - hit_rate,
                total_requests=int(commands_processed),
                cache_size_bytes=0,  # Would need to calculate from memory usage
                eviction_rate=0,  # Redis eviction rate
                average_response_time_ms=1.0,  # Typical Redis response time
                memory_utilization_percent=memory_usage,
                cost_per_request=0.00001  # ElastiCache cost per request
            )
            
        except Exception as e:
            logger.error(f"Error analyzing Redis cache: {e}")
            return None
    
    def _get_cloudwatch_metric(self, namespace: str, metric_name: str, 
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
                return sum(values) / len(values)
                
        except Exception as e:
            logger.warning(f"Could not get metric {metric_name}: {e}")
        
        return None
    
    def _estimate_dynamodb_cache_size(self) -> int:
        """Estimate DynamoDB cache size."""
        try:
            response = self.dynamodb.describe_table(TableName=self.cache_table)
            item_count = response['Table'].get('ItemCount', 0)
            
            # Estimate average item size (rough calculation)
            avg_item_size = 1024  # 1KB per item estimate
            return item_count * avg_item_size
            
        except Exception as e:
            logger.warning(f"Could not estimate DynamoDB cache size: {e}")
            return 0
    
    def _calculate_dynamodb_cost_per_request(self, reads: float, writes: float) -> float:
        """Calculate DynamoDB cost per request."""
        # On-demand pricing (approximate)
        read_cost = reads * 0.25 / 1000000  # $0.25 per million reads
        write_cost = writes * 1.25 / 1000000  # $1.25 per million writes
        total_requests = reads + writes
        
        if total_requests > 0:
            return (read_cost + write_cost) / total_requests
        return 0
    
    def _calculate_overall_metrics(self, metrics_list: List[CacheMetrics]) -> CacheMetrics:
        """Calculate overall cache metrics."""
        valid_metrics = [m for m in metrics_list if m is not None]
        
        if not valid_metrics:
            return self._create_empty_metrics()
        
        # Weighted average based on request volume
        total_requests = sum(m.total_requests for m in valid_metrics)
        
        if total_requests == 0:
            # Simple average if no request data
            return CacheMetrics(
                hit_rate=sum(m.hit_rate for m in valid_metrics) / len(valid_metrics),
                miss_rate=sum(m.miss_rate for m in valid_metrics) / len(valid_metrics),
                total_requests=0,
                cache_size_bytes=sum(m.cache_size_bytes for m in valid_metrics),
                eviction_rate=sum(m.eviction_rate for m in valid_metrics) / len(valid_metrics),
                average_response_time_ms=sum(m.average_response_time_ms for m in valid_metrics) / len(valid_metrics),
                memory_utilization_percent=sum(m.memory_utilization_percent for m in valid_metrics) / len(valid_metrics),
                cost_per_request=sum(m.cost_per_request for m in valid_metrics) / len(valid_metrics)
            )
        
        # Weighted average
        weighted_hit_rate = sum(m.hit_rate * m.total_requests for m in valid_metrics) / total_requests
        weighted_response_time = sum(m.average_response_time_ms * m.total_requests for m in valid_metrics) / total_requests
        
        return CacheMetrics(
            hit_rate=weighted_hit_rate,
            miss_rate=100 - weighted_hit_rate,
            total_requests=total_requests,
            cache_size_bytes=sum(m.cache_size_bytes for m in valid_metrics),
            eviction_rate=sum(m.eviction_rate for m in valid_metrics) / len(valid_metrics),
            average_response_time_ms=weighted_response_time,
            memory_utilization_percent=max(m.memory_utilization_percent for m in valid_metrics),
            cost_per_request=sum(m.cost_per_request * m.total_requests for m in valid_metrics) / total_requests
        )
    
    def _create_empty_metrics(self) -> CacheMetrics:
        """Create empty metrics object."""
        return CacheMetrics(
            hit_rate=0.0,
            miss_rate=100.0,
            total_requests=0,
            cache_size_bytes=0,
            eviction_rate=0.0,
            average_response_time_ms=0.0,
            memory_utilization_percent=0.0,
            cost_per_request=0.0
        )
    
    def _generate_recommendations(self, metrics: Dict[str, CacheMetrics]) -> List[str]:
        """Generate optimization recommendations."""
        recommendations = []
        overall = metrics['overall']
        
        # Hit rate recommendations
        if overall.hit_rate < self.thresholds['hit_rate_minimum']:
            recommendations.append(
                f"⚠️ Low cache hit rate ({overall.hit_rate:.1f}%). "
                f"Consider increasing cache TTL or improving cache key strategies."
            )
        
        # Response time recommendations
        if overall.average_response_time_ms > self.thresholds['response_time_maximum']:
            recommendations.append(
                f"⚠️ High cache response time ({overall.average_response_time_ms:.1f}ms). "
                f"Consider optimizing cache layer hierarchy or adding Redis for production."
            )
        
        # Memory utilization recommendations
        if overall.memory_utilization_percent > self.thresholds['memory_utilization_maximum']:
            recommendations.append(
                f"⚠️ High memory utilization ({overall.memory_utilization_percent:.1f}%). "
                f"Consider increasing cache size limits or implementing more aggressive eviction."
            )
        
        # DynamoDB specific recommendations
        dynamodb_metrics = metrics.get('dynamodb')
        if dynamodb_metrics and dynamodb_metrics.total_requests > 1000:
            if dynamodb_metrics.hit_rate < 80:
                recommendations.append(
                    "💡 DynamoDB cache hit rate could be improved. "
                    "Consider longer TTL for stable data or better cache key design."
                )
        
        # S3 cache recommendations
        s3_metrics = metrics.get('s3')
        if s3_metrics and s3_metrics.cache_size_bytes > 1024 * 1024 * 1024:  # 1GB
            recommendations.append(
                "💡 Large S3 cache detected. "
                "Consider implementing intelligent tiering or lifecycle policies for cost optimization."
            )
        
        # Redis recommendations
        redis_metrics = metrics.get('redis')
        if self.environment == 'prod' and not redis_metrics:
            recommendations.append(
                "💡 Consider implementing Redis cache for production workloads "
                "to achieve sub-millisecond response times."
            )
        
        # Cost optimization recommendations
        if overall.cost_per_request > 0.001:  # 0.1 cents per request
            recommendations.append(
                f"💰 High caching cost per request (${overall.cost_per_request:.4f}). "
                f"Review cache strategies and consider cost-effective alternatives."
            )
        
        # General optimization recommendations
        if overall.hit_rate > 90 and overall.average_response_time_ms < 50:
            recommendations.append(
                "✅ Excellent cache performance! "
                "Consider documenting current configuration as best practice."
            )
        
        return recommendations
    
    def _calculate_optimization_score(self, metrics: CacheMetrics) -> float:
        """Calculate overall optimization score (0-100)."""
        score = 0
        
        # Hit rate score (40% weight)
        hit_rate_score = min(metrics.hit_rate / 100 * 100, 100)
        score += hit_rate_score * 0.4
        
        # Response time score (30% weight)
        response_time_score = max(0, 100 - (metrics.average_response_time_ms / 10))
        score += response_time_score * 0.3
        
        # Memory utilization score (20% weight)
        memory_score = max(0, 100 - metrics.memory_utilization_percent)
        score += memory_score * 0.2
        
        # Cost efficiency score (10% weight)
        cost_score = max(0, 100 - (metrics.cost_per_request * 10000))
        score += cost_score * 0.1
        
        return min(max(score, 0), 100)
    
    def generate_performance_report(self, analysis: CacheAnalysis) -> str:
        """Generate comprehensive cache performance report."""
        report = f"""
# AutoSpec.AI Cache Performance Analysis Report

## Environment: {analysis.environment.upper()}
**Generated:** {analysis.timestamp}
**Optimization Score:** {analysis.optimization_score:.1f}/100

## Overall Cache Performance

### Key Metrics
- **Hit Rate**: {analysis.overall_metrics.hit_rate:.1f}%
- **Average Response Time**: {analysis.overall_metrics.average_response_time_ms:.1f}ms
- **Total Cache Size**: {analysis.overall_metrics.cache_size_bytes / 1024 / 1024:.1f}MB
- **Cost per Request**: ${analysis.overall_metrics.cost_per_request:.4f}

## Cache Layer Analysis

### Memory Cache (In-Lambda)
- **Hit Rate**: {analysis.memory_cache.hit_rate:.1f}%
- **Response Time**: {analysis.memory_cache.average_response_time_ms:.1f}ms
- **Cache Size**: {analysis.memory_cache.cache_size_bytes / 1024:.0f}KB

### DynamoDB Cache (Distributed)
- **Hit Rate**: {analysis.dynamodb_cache.hit_rate:.1f}%
- **Response Time**: {analysis.dynamodb_cache.average_response_time_ms:.1f}ms
- **Total Requests**: {analysis.dynamodb_cache.total_requests:,}
- **Cache Size**: {analysis.dynamodb_cache.cache_size_bytes / 1024 / 1024:.1f}MB
"""
        
        if analysis.s3_cache:
            report += f"""
### S3 Cache (Large Objects)
- **Hit Rate**: {analysis.s3_cache.hit_rate:.1f}%
- **Response Time**: {analysis.s3_cache.average_response_time_ms:.1f}ms
- **Cache Size**: {analysis.s3_cache.cache_size_bytes / 1024 / 1024:.1f}MB
"""
        
        if analysis.redis_cache:
            report += f"""
### Redis Cache (High Performance)
- **Hit Rate**: {analysis.redis_cache.hit_rate:.1f}%
- **Memory Utilization**: {analysis.redis_cache.memory_utilization_percent:.1f}%
- **Total Requests**: {analysis.redis_cache.total_requests:,}
"""
        
        report += "\n## Recommendations\n"
        for i, recommendation in enumerate(analysis.recommendations, 1):
            report += f"{i}. {recommendation}\n"
        
        report += f"""

## Performance Thresholds
- **Minimum Hit Rate**: {self.thresholds['hit_rate_minimum']}%
- **Maximum Response Time**: {self.thresholds['response_time_maximum']}ms
- **Maximum Memory Usage**: {self.thresholds['memory_utilization_maximum']}%

## Next Steps
1. Monitor cache metrics daily for the first week
2. Implement high-priority recommendations
3. Re-run analysis after optimizations
4. Consider A/B testing for cache configuration changes
5. Document optimal cache configurations for future reference

## Optimization Commands
```bash
# Re-run analysis
python3 cache-performance-analyzer.py --environment {analysis.environment} --analyze

# Generate optimization report
python3 cache-performance-analyzer.py --environment {analysis.environment} --report

# Monitor cache performance
python3 performance-monitoring-dashboard.py --environment {analysis.environment} --action create
```
"""
        
        return report

def main():
    parser = argparse.ArgumentParser(description='AutoSpec.AI Cache Performance Analyzer')
    parser.add_argument('--environment', required=True, choices=['dev', 'staging', 'prod'],
                       help='Environment to analyze')
    parser.add_argument('--action', choices=['analyze', 'report', 'optimize'],
                       default='analyze', help='Action to perform')
    parser.add_argument('--hours', type=int, default=24,
                       help='Hours of data to analyze (default: 24)')
    parser.add_argument('--output', help='Output file for report')
    
    args = parser.parse_args()
    
    analyzer = CachePerformanceAnalyzer(args.environment)
    
    try:
        if args.action == 'analyze':
            analysis = analyzer.analyze_cache_performance(args.hours)
            print(json.dumps(asdict(analysis), indent=2))
            
        elif args.action == 'report':
            analysis = analyzer.analyze_cache_performance(args.hours)
            report = analyzer.generate_performance_report(analysis)
            
            if args.output:
                with open(args.output, 'w') as f:
                    f.write(report)
                logger.info(f"Report saved to {args.output}")
            else:
                print(report)
                
        elif args.action == 'optimize':
            analysis = analyzer.analyze_cache_performance(args.hours)
            
            # Auto-implement optimizations (placeholder)
            logger.info("Auto-optimization not yet implemented")
            logger.info(f"Optimization score: {analysis.optimization_score:.1f}/100")
            
            for recommendation in analysis.recommendations:
                logger.info(f"Recommendation: {recommendation}")
    
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())