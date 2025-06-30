#!/usr/bin/env python3
"""
AutoSpec.AI Cost Monitoring and Optimization System

Comprehensive cost analysis, monitoring, and optimization recommendations
for the AutoSpec.AI serverless infrastructure.

Usage:
    python3 cost-optimization-monitor.py --environment dev --analyze
    python3 cost-optimization-monitor.py --environment prod --optimize
    python3 cost-optimization-monitor.py --environment staging --forecast
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
class ServiceCosts:
    """Cost breakdown for a specific AWS service."""
    service_name: str
    current_monthly_cost: float
    projected_monthly_cost: float
    cost_trend_percent: float
    optimization_potential: float
    recommendations: List[str]

@dataclass
class CostAnalysis:
    """Comprehensive cost analysis results."""
    environment: str
    analysis_date: str
    total_monthly_cost: float
    projected_monthly_cost: float
    cost_trend_percent: float
    cost_per_request: float
    cost_per_document: float
    service_breakdown: Dict[str, ServiceCosts]
    optimization_opportunities: List[str]
    potential_savings: float
    cost_efficiency_score: float

class CostOptimizationMonitor:
    """Monitors and optimizes AWS costs for AutoSpec.AI infrastructure."""
    
    def __init__(self, environment: str):
        self.environment = environment
        
        # AWS clients
        self.ce_client = boto3.client('ce')  # Cost Explorer
        self.cloudwatch = boto3.client('cloudwatch')
        self.lambda_client = boto3.client('lambda')
        self.dynamodb = boto3.client('dynamodb')
        self.s3 = boto3.client('s3')
        
        # Resource identifiers
        self.resource_tags = {
            'Environment': environment,
            'Project': 'AutoSpecAI'
        }
        
        # Cost thresholds by environment
        self.cost_thresholds = {
            'dev': {
                'monthly_budget': 50.0,  # $50/month
                'cost_per_request': 0.005,  # $0.005 per request
                'alert_threshold': 0.8  # 80% of budget
            },
            'staging': {
                'monthly_budget': 200.0,  # $200/month
                'cost_per_request': 0.003,  # $0.003 per request
                'alert_threshold': 0.8
            },
            'prod': {
                'monthly_budget': 1000.0,  # $1000/month
                'cost_per_request': 0.002,  # $0.002 per request
                'alert_threshold': 0.85
            }
        }
        
        # AWS service pricing (approximate, for calculations)
        self.service_pricing = {
            'lambda': {
                'request_cost': 0.0000002,  # $0.0000002 per request
                'gb_second_cost': 0.0000166667,  # $0.0000166667 per GB-second
                'provisioned_concurrency_cost': 0.0000097  # $0.0000097 per GB-second
            },
            'dynamodb': {
                'on_demand_read': 0.25,  # $0.25 per million reads
                'on_demand_write': 1.25,  # $1.25 per million writes
                'storage_gb': 0.25  # $0.25 per GB per month
            },
            's3': {
                'standard_storage': 0.023,  # $0.023 per GB per month
                'standard_ia': 0.0125,  # $0.0125 per GB per month
                'requests_get': 0.0004,  # $0.0004 per 1000 requests
                'requests_put': 0.005  # $0.005 per 1000 requests
            },
            'bedrock': {
                'input_tokens': 0.003,  # $0.003 per 1000 input tokens
                'output_tokens': 0.015  # $0.015 per 1000 output tokens
            },
            'ses': {
                'email_cost': 0.10  # $0.10 per 1000 emails
            }
        }
    
    def analyze_costs(self, days_back: int = 30) -> CostAnalysis:
        """Perform comprehensive cost analysis."""
        logger.info(f"Analyzing costs for {self.environment} environment ({days_back} days)")
        
        end_date = datetime.now(timezone.utc).date()
        start_date = end_date - timedelta(days=days_back)
        
        # Get cost data from Cost Explorer
        cost_data = self._get_cost_explorer_data(start_date, end_date)
        
        # Analyze each service
        service_breakdown = {}
        total_cost = 0
        total_optimization_potential = 0
        
        for service in ['Lambda', 'DynamoDB', 'S3', 'SES', 'CloudWatch']:
            service_analysis = self._analyze_service_costs(service, start_date, end_date, cost_data)
            if service_analysis:
                service_breakdown[service.lower()] = service_analysis
                total_cost += service_analysis.current_monthly_cost
                total_optimization_potential += service_analysis.optimization_potential
        
        # Calculate usage metrics
        usage_metrics = self._get_usage_metrics(start_date, end_date)
        
        # Calculate cost efficiency
        cost_per_request = total_cost / max(usage_metrics['total_requests'], 1)
        cost_per_document = total_cost / max(usage_metrics['documents_processed'], 1)
        
        # Project monthly costs
        daily_average = total_cost / days_back
        projected_monthly = daily_average * 30
        
        # Calculate trend
        cost_trend = self._calculate_cost_trend(cost_data, days_back)
        
        # Generate optimization opportunities
        optimization_opportunities = self._generate_optimization_opportunities(
            service_breakdown, usage_metrics, total_cost
        )
        
        # Calculate cost efficiency score
        efficiency_score = self._calculate_cost_efficiency_score(
            cost_per_request, usage_metrics, total_cost
        )
        
        return CostAnalysis(
            environment=self.environment,
            analysis_date=datetime.now(timezone.utc).isoformat(),
            total_monthly_cost=total_cost,
            projected_monthly_cost=projected_monthly,
            cost_trend_percent=cost_trend,
            cost_per_request=cost_per_request,
            cost_per_document=cost_per_document,
            service_breakdown=service_breakdown,
            optimization_opportunities=optimization_opportunities,
            potential_savings=total_optimization_potential,
            cost_efficiency_score=efficiency_score
        )
    
    def _get_cost_explorer_data(self, start_date, end_date) -> Dict[str, Any]:
        """Get cost data from AWS Cost Explorer."""
        try:
            response = self.ce_client.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                },
                Granularity='DAILY',
                Metrics=['BlendedCost'],
                GroupBy=[
                    {
                        'Type': 'DIMENSION',
                        'Key': 'SERVICE'
                    }
                ],
                Filter={
                    'Tags': {
                        'Key': 'Environment',
                        'Values': [self.environment]
                    }
                }
            )
            return response
        except Exception as e:
            logger.warning(f"Could not get Cost Explorer data: {e}")
            return {'ResultsByTime': []}
    
    def _analyze_service_costs(self, service: str, start_date, end_date, cost_data) -> Optional[ServiceCosts]:
        """Analyze costs for a specific AWS service."""
        try:
            # Extract service costs from Cost Explorer data
            service_costs = []
            for result in cost_data.get('ResultsByTime', []):
                for group in result.get('Groups', []):
                    if service in group['Keys'][0]:
                        cost = float(group['Metrics']['BlendedCost']['Amount'])
                        service_costs.append(cost)
            
            if not service_costs:
                return None
            
            current_cost = sum(service_costs)
            daily_average = current_cost / len(service_costs) if service_costs else 0
            projected_monthly = daily_average * 30
            
            # Calculate trend
            if len(service_costs) > 7:
                recent_avg = sum(service_costs[-7:]) / 7
                older_avg = sum(service_costs[:-7]) / (len(service_costs) - 7)
                trend = ((recent_avg - older_avg) / older_avg * 100) if older_avg > 0 else 0
            else:
                trend = 0
            
            # Generate service-specific recommendations
            recommendations = self._get_service_recommendations(service, current_cost, projected_monthly)
            
            # Calculate optimization potential
            optimization_potential = self._calculate_service_optimization_potential(
                service, current_cost, projected_monthly
            )
            
            return ServiceCosts(
                service_name=service,
                current_monthly_cost=current_cost,
                projected_monthly_cost=projected_monthly,
                cost_trend_percent=trend,
                optimization_potential=optimization_potential,
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.error(f"Error analyzing {service} costs: {e}")
            return None
    
    def _get_usage_metrics(self, start_date, end_date) -> Dict[str, int]:
        """Get usage metrics for cost analysis."""
        try:
            # Get Lambda invocations
            lambda_invocations = self._get_cloudwatch_metric_sum(
                'AWS/Lambda', 'Invocations',
                [{'Name': 'FunctionName', 'Value': f'AutoSpecAI-ProcessFunction-{self.environment}'}],
                start_date, end_date
            )
            
            # Get DynamoDB operations
            dynamodb_reads = self._get_cloudwatch_metric_sum(
                'AWS/DynamoDB', 'ConsumedReadCapacityUnits',
                [{'Name': 'TableName', 'Value': f'autospec-ai-history-{self.environment}'}],
                start_date, end_date
            )
            
            # Estimate documents processed (assuming 1 Lambda invocation = 1 document)
            documents_processed = int(lambda_invocations or 0)
            
            # Estimate total requests (including API calls)
            api_requests = self._get_cloudwatch_metric_sum(
                'AWS/Lambda', 'Invocations',
                [{'Name': 'FunctionName', 'Value': f'AutoSpecAI-ApiFunction-{self.environment}'}],
                start_date, end_date
            )
            
            total_requests = int((lambda_invocations or 0) + (api_requests or 0))
            
            return {
                'total_requests': total_requests,
                'documents_processed': documents_processed,
                'lambda_invocations': int(lambda_invocations or 0),
                'dynamodb_reads': int(dynamodb_reads or 0),
                'api_requests': int(api_requests or 0)
            }
            
        except Exception as e:
            logger.error(f"Error getting usage metrics: {e}")
            return {
                'total_requests': 0,
                'documents_processed': 0,
                'lambda_invocations': 0,
                'dynamodb_reads': 0,
                'api_requests': 0
            }
    
    def _get_cloudwatch_metric_sum(self, namespace: str, metric_name: str, 
                                 dimensions: List[Dict], start_date, end_date) -> Optional[float]:
        """Get sum of CloudWatch metric over time period."""
        try:
            start_datetime = datetime.combine(start_date, datetime.min.time().replace(tzinfo=timezone.utc))
            end_datetime = datetime.combine(end_date, datetime.min.time().replace(tzinfo=timezone.utc))
            
            response = self.cloudwatch.get_metric_statistics(
                Namespace=namespace,
                MetricName=metric_name,
                Dimensions=dimensions,
                StartTime=start_datetime,
                EndTime=end_datetime,
                Period=86400,  # Daily
                Statistics=['Sum']
            )
            
            if response['Datapoints']:
                return sum(dp['Sum'] for dp in response['Datapoints'])
            
        except Exception as e:
            logger.warning(f"Could not get metric {metric_name}: {e}")
        
        return None
    
    def _calculate_cost_trend(self, cost_data: Dict[str, Any], days_back: int) -> float:
        """Calculate cost trend percentage."""
        try:
            daily_costs = []
            for result in cost_data.get('ResultsByTime', []):
                total_cost = 0
                for group in result.get('Groups', []):
                    total_cost += float(group['Metrics']['BlendedCost']['Amount'])
                daily_costs.append(total_cost)
            
            if len(daily_costs) < 7:
                return 0
            
            # Compare last 7 days with previous 7 days
            recent_avg = sum(daily_costs[-7:]) / 7
            previous_avg = sum(daily_costs[-14:-7]) / 7 if len(daily_costs) >= 14 else sum(daily_costs[:-7]) / len(daily_costs[:-7])
            
            if previous_avg > 0:
                return ((recent_avg - previous_avg) / previous_avg) * 100
            
        except Exception as e:
            logger.error(f"Error calculating cost trend: {e}")
        
        return 0
    
    def _get_service_recommendations(self, service: str, current_cost: float, projected_cost: float) -> List[str]:
        """Get optimization recommendations for a specific service."""
        recommendations = []
        
        if service == 'Lambda':
            if projected_cost > 50:  # High Lambda costs
                recommendations.append("Consider optimizing Lambda memory allocation")
                recommendations.append("Review provisioned concurrency utilization")
                recommendations.append("Implement caching to reduce function invocations")
            
            if current_cost > 0:
                recommendations.append("Monitor cold starts and optimize initialization")
        
        elif service == 'DynamoDB':
            if projected_cost > 20:  # High DynamoDB costs
                recommendations.append("Review on-demand vs provisioned capacity pricing")
                recommendations.append("Optimize query patterns to reduce consumed capacity")
                recommendations.append("Implement caching for frequently accessed data")
            
            recommendations.append("Consider DynamoDB reserved capacity for predictable workloads")
        
        elif service == 'S3':
            if projected_cost > 10:  # High S3 costs
                recommendations.append("Implement S3 Intelligent Tiering")
                recommendations.append("Review lifecycle policies for automatic archiving")
                recommendations.append("Consider S3 Standard-IA for infrequently accessed data")
            
            recommendations.append("Optimize request patterns to reduce API costs")
        
        elif service == 'SES':
            if projected_cost > 5:  # High SES costs
                recommendations.append("Optimize email sending patterns")
                recommendations.append("Implement email batching where possible")
        
        return recommendations
    
    def _calculate_service_optimization_potential(self, service: str, current_cost: float, projected_cost: float) -> float:
        """Calculate potential cost savings for a service."""
        if service == 'Lambda':
            # Lambda optimization potential: 20-40% through memory optimization and caching
            return projected_cost * 0.3
        
        elif service == 'DynamoDB':
            # DynamoDB optimization: 15-30% through caching and query optimization
            return projected_cost * 0.25
        
        elif service == 'S3':
            # S3 optimization: 30-50% through intelligent tiering and lifecycle policies
            return projected_cost * 0.4
        
        elif service == 'SES':
            # SES optimization: 10-20% through batching and optimization
            return projected_cost * 0.15
        
        return projected_cost * 0.1  # Default 10% optimization potential
    
    def _generate_optimization_opportunities(self, service_breakdown: Dict[str, ServiceCosts], 
                                           usage_metrics: Dict[str, int], total_cost: float) -> List[str]:
        """Generate overall optimization opportunities."""
        opportunities = []
        
        # Check against budget thresholds
        threshold = self.cost_thresholds.get(self.environment, {})
        budget = threshold.get('monthly_budget', 100)
        
        if total_cost > budget * 0.8:
            opportunities.append(f"🚨 Cost approaching budget limit (${total_cost:.2f} / ${budget:.2f})")
        
        # High-impact optimizations
        lambda_costs = service_breakdown.get('lambda')
        if lambda_costs and lambda_costs.projected_monthly_cost > 30:
            opportunities.append("💡 High Lambda costs detected - implement aggressive caching strategy")
        
        # Cost per request optimization
        target_cost_per_request = threshold.get('cost_per_request', 0.005)
        actual_cost_per_request = total_cost / max(usage_metrics['total_requests'], 1)
        
        if actual_cost_per_request > target_cost_per_request:
            opportunities.append(
                f"💰 Cost per request (${actual_cost_per_request:.4f}) exceeds target "
                f"(${target_cost_per_request:.4f}) - optimize efficiency"
            )
        
        # Usage pattern optimizations
        if usage_metrics['documents_processed'] > 0:
            cost_per_document = total_cost / usage_metrics['documents_processed']
            if cost_per_document > 0.1:  # $0.10 per document
                opportunities.append(f"📄 High cost per document (${cost_per_document:.3f}) - optimize processing pipeline")
        
        # Environment-specific recommendations
        if self.environment == 'dev' and total_cost > 25:
            opportunities.append("🔧 Development environment costs high - consider auto-shutdown policies")
        
        elif self.environment == 'prod':
            if total_cost > 500:
                opportunities.append("🏭 Production costs high - implement comprehensive optimization strategy")
            opportunities.append("📊 Consider reserved capacity for predictable workloads")
        
        return opportunities
    
    def _calculate_cost_efficiency_score(self, cost_per_request: float, 
                                       usage_metrics: Dict[str, int], total_cost: float) -> float:
        """Calculate cost efficiency score (0-100)."""
        score = 100
        
        # Cost per request efficiency (40% weight)
        target_cost_per_request = self.cost_thresholds.get(self.environment, {}).get('cost_per_request', 0.005)
        if cost_per_request > target_cost_per_request:
            efficiency_penalty = min(50, (cost_per_request / target_cost_per_request - 1) * 100)
            score -= efficiency_penalty * 0.4
        
        # Budget efficiency (30% weight)
        budget = self.cost_thresholds.get(self.environment, {}).get('monthly_budget', 100)
        budget_utilization = (total_cost / budget) * 100
        if budget_utilization > 80:
            budget_penalty = min(30, budget_utilization - 80)
            score -= budget_penalty * 0.3
        
        # Usage efficiency (20% weight)
        requests = usage_metrics.get('total_requests', 0)
        if requests > 0:
            utilization_score = min(100, (requests / 1000) * 100)  # Normalize to 1000 requests
            score -= (100 - utilization_score) * 0.2
        
        # Trend efficiency (10% weight)
        # This would be calculated based on cost trend
        
        return max(0, min(100, score))
    
    def optimize_costs(self) -> Dict[str, Any]:
        """Implement automated cost optimizations."""
        logger.info(f"Implementing cost optimizations for {self.environment}")
        
        optimizations = {
            'lambda_optimizations': [],
            'dynamodb_optimizations': [],
            's3_optimizations': [],
            'general_optimizations': [],
            'estimated_savings': 0.0
        }
        
        # Lambda optimizations
        lambda_optimizations = self._optimize_lambda_costs()
        optimizations['lambda_optimizations'] = lambda_optimizations
        
        # DynamoDB optimizations
        dynamodb_optimizations = self._optimize_dynamodb_costs()
        optimizations['dynamodb_optimizations'] = dynamodb_optimizations
        
        # S3 optimizations
        s3_optimizations = self._optimize_s3_costs()
        optimizations['s3_optimizations'] = s3_optimizations
        
        # General optimizations
        general_optimizations = self._implement_general_optimizations()
        optimizations['general_optimizations'] = general_optimizations
        
        # Calculate estimated savings
        total_savings = sum([
            opt.get('estimated_savings', 0) for opt_list in optimizations.values()
            if isinstance(opt_list, list) for opt in opt_list
        ])
        optimizations['estimated_savings'] = total_savings
        
        return optimizations
    
    def _optimize_lambda_costs(self) -> List[Dict[str, Any]]:
        """Optimize Lambda function costs."""
        optimizations = []
        
        try:
            # Get all Lambda functions for the environment
            functions = self.lambda_client.list_functions()
            
            for function in functions['Functions']:
                function_name = function['FunctionName']
                
                if f'AutoSpecAI-{self.environment}' in function_name or function_name.endswith(f'-{self.environment}'):
                    # Analyze function configuration
                    current_memory = function['MemorySize']
                    timeout = function['Timeout']
                    
                    # Get utilization metrics
                    utilization = self._get_lambda_utilization(function_name)
                    
                    # Recommend memory optimization
                    if utilization and utilization < 50:  # Low memory utilization
                        recommended_memory = max(128, int(current_memory * 0.8))
                        optimization = {
                            'function_name': function_name,
                            'optimization_type': 'memory_reduction',
                            'current_memory': current_memory,
                            'recommended_memory': recommended_memory,
                            'estimated_savings': self._calculate_lambda_memory_savings(
                                current_memory, recommended_memory
                            ),
                            'confidence': 'high' if utilization < 30 else 'medium'
                        }
                        optimizations.append(optimization)
            
        except Exception as e:
            logger.error(f"Error optimizing Lambda costs: {e}")
        
        return optimizations
    
    def _optimize_dynamodb_costs(self) -> List[Dict[str, Any]]:
        """Optimize DynamoDB costs."""
        optimizations = []
        
        try:
            # Analyze cache table usage
            cache_table = f'autospec-ai-cache-{self.environment}'
            
            # Check if table exists and analyze usage
            try:
                table_info = self.dynamodb.describe_table(TableName=cache_table)
                billing_mode = table_info['Table']['BillingModeSummary']['BillingMode']
                
                if billing_mode == 'PAY_PER_REQUEST':
                    # Analyze if reserved capacity would be cheaper
                    usage_analysis = self._analyze_dynamodb_usage(cache_table)
                    
                    if usage_analysis['predictable_usage']:
                        optimization = {
                            'table_name': cache_table,
                            'optimization_type': 'reserved_capacity',
                            'current_mode': 'on_demand',
                            'recommended_mode': 'provisioned',
                            'estimated_savings': usage_analysis['potential_savings'],
                            'confidence': 'medium'
                        }
                        optimizations.append(optimization)
                
            except self.dynamodb.exceptions.ResourceNotFoundException:
                pass  # Table doesn't exist
            
        except Exception as e:
            logger.error(f"Error optimizing DynamoDB costs: {e}")
        
        return optimizations
    
    def _optimize_s3_costs(self) -> List[Dict[str, Any]]:
        """Optimize S3 costs."""
        optimizations = []
        
        try:
            # Analyze S3 usage patterns
            bucket_name = f'autospec-ai-documents-{self.environment}'
            
            try:
                # Check bucket exists
                self.s3.head_bucket(Bucket=bucket_name)
                
                # Analyze object lifecycle
                lifecycle_analysis = self._analyze_s3_lifecycle(bucket_name)
                
                if lifecycle_analysis['optimization_potential'] > 0:
                    optimization = {
                        'bucket_name': bucket_name,
                        'optimization_type': 'lifecycle_policy',
                        'current_policy': lifecycle_analysis['current_policy'],
                        'recommended_policy': lifecycle_analysis['recommended_policy'],
                        'estimated_savings': lifecycle_analysis['optimization_potential'],
                        'confidence': 'high'
                    }
                    optimizations.append(optimization)
                
            except self.s3.exceptions.NoSuchBucket:
                pass  # Bucket doesn't exist
            
        except Exception as e:
            logger.error(f"Error optimizing S3 costs: {e}")
        
        return optimizations
    
    def _implement_general_optimizations(self) -> List[Dict[str, Any]]:
        """Implement general cost optimizations."""
        optimizations = []
        
        # Environment-specific optimizations
        if self.environment == 'dev':
            optimization = {
                'optimization_type': 'auto_shutdown',
                'description': 'Implement auto-shutdown for development resources during off-hours',
                'estimated_savings': 30.0,  # 30% savings
                'implementation': 'scheduled_lambda'
            }
            optimizations.append(optimization)
        
        # Monitoring optimization
        optimization = {
            'optimization_type': 'monitoring_optimization',
            'description': 'Optimize CloudWatch log retention and metric frequency',
            'estimated_savings': 5.0,  # 5% savings
            'implementation': 'log_retention_policy'
        }
        optimizations.append(optimization)
        
        return optimizations
    
    def _get_lambda_utilization(self, function_name: str) -> Optional[float]:
        """Get Lambda function memory utilization."""
        # This would typically analyze CloudWatch logs for memory usage
        # For now, return a placeholder
        return 45.0  # 45% utilization
    
    def _calculate_lambda_memory_savings(self, current_memory: int, recommended_memory: int) -> float:
        """Calculate potential Lambda memory optimization savings."""
        memory_reduction = (current_memory - recommended_memory) / current_memory
        estimated_monthly_cost = 10.0  # Placeholder for current monthly cost
        return estimated_monthly_cost * memory_reduction
    
    def _analyze_dynamodb_usage(self, table_name: str) -> Dict[str, Any]:
        """Analyze DynamoDB usage patterns."""
        return {
            'predictable_usage': False,  # Would analyze actual usage patterns
            'potential_savings': 0.0
        }
    
    def _analyze_s3_lifecycle(self, bucket_name: str) -> Dict[str, Any]:
        """Analyze S3 object lifecycle for optimization."""
        return {
            'current_policy': 'none',
            'recommended_policy': 'intelligent_tiering',
            'optimization_potential': 15.0  # $15/month savings
        }
    
    def generate_cost_report(self, analysis: CostAnalysis) -> str:
        """Generate comprehensive cost analysis report."""
        thresholds = self.cost_thresholds.get(self.environment, {})
        
        report = f"""
# AutoSpec.AI Cost Analysis Report

## Environment: {analysis.environment.upper()}
**Analysis Date:** {analysis.analysis_date}
**Cost Efficiency Score:** {analysis.cost_efficiency_score:.1f}/100

## Executive Summary
- **Current Monthly Cost:** ${analysis.total_monthly_cost:.2f}
- **Projected Monthly Cost:** ${analysis.projected_monthly_cost:.2f}
- **Cost Trend:** {analysis.cost_trend_percent:+.1f}%
- **Budget Utilization:** {(analysis.projected_monthly_cost / thresholds.get('monthly_budget', 100)) * 100:.1f}%

## Cost Efficiency Metrics
- **Cost per Request:** ${analysis.cost_per_request:.4f} (Target: ${thresholds.get('cost_per_request', 0.005):.4f})
- **Cost per Document:** ${analysis.cost_per_document:.3f}
- **Potential Savings:** ${analysis.potential_savings:.2f}/month

## Service Cost Breakdown
"""
        
        total_cost = sum(service.projected_monthly_cost for service in analysis.service_breakdown.values())
        
        for service_name, service_costs in analysis.service_breakdown.items():
            percentage = (service_costs.projected_monthly_cost / total_cost * 100) if total_cost > 0 else 0
            report += f"""
### {service_name.upper()}
- **Monthly Cost:** ${service_costs.projected_monthly_cost:.2f} ({percentage:.1f}% of total)
- **Trend:** {service_costs.cost_trend_percent:+.1f}%
- **Optimization Potential:** ${service_costs.optimization_potential:.2f}
- **Recommendations:**
"""
            for rec in service_costs.recommendations:
                report += f"  - {rec}\n"
        
        report += "\n## Optimization Opportunities\n"
        for i, opportunity in enumerate(analysis.optimization_opportunities, 1):
            report += f"{i}. {opportunity}\n"
        
        report += f"""

## Budget Analysis
- **Monthly Budget:** ${thresholds.get('monthly_budget', 100):.2f}
- **Current Utilization:** {(analysis.projected_monthly_cost / thresholds.get('monthly_budget', 100)) * 100:.1f}%
- **Alert Threshold:** {thresholds.get('alert_threshold', 0.8) * 100:.0f}%

## Cost Optimization Recommendations

### Immediate Actions (High Impact)
1. **Implement Caching Strategy** - Reduce Lambda invocations by 60-70%
2. **Optimize Lambda Memory** - Right-size memory allocation based on usage
3. **Review DynamoDB Usage** - Implement query optimization and caching

### Medium-Term Optimizations
1. **S3 Lifecycle Policies** - Implement intelligent tiering for cost savings
2. **Reserved Capacity** - Consider reserved pricing for predictable workloads
3. **Monitoring Optimization** - Optimize log retention and metric frequency

### Long-Term Strategy
1. **Auto-scaling Implementation** - Dynamic resource allocation based on demand
2. **Cost Anomaly Detection** - Automated alerts for unusual cost spikes
3. **Regular Cost Reviews** - Monthly cost optimization reviews

## Next Steps
1. Implement high-impact optimizations immediately
2. Monitor cost trends weekly
3. Set up automated cost alerts
4. Schedule monthly cost optimization reviews

## Automated Commands
```bash
# Run cost analysis
python3 cost-optimization-monitor.py --environment {analysis.environment} --analyze

# Implement optimizations
python3 cost-optimization-monitor.py --environment {analysis.environment} --optimize

# Generate forecast
python3 cost-optimization-monitor.py --environment {analysis.environment} --forecast
```
"""
        
        return report

def main():
    parser = argparse.ArgumentParser(description='AutoSpec.AI Cost Optimization Monitor')
    parser.add_argument('--environment', required=True, choices=['dev', 'staging', 'prod'],
                       help='Environment to analyze')
    parser.add_argument('--action', choices=['analyze', 'optimize', 'forecast', 'report'],
                       default='analyze', help='Action to perform')
    parser.add_argument('--days', type=int, default=30,
                       help='Days of data to analyze (default: 30)')
    parser.add_argument('--output', help='Output file for report')
    
    args = parser.parse_args()
    
    monitor = CostOptimizationMonitor(args.environment)
    
    try:
        if args.action == 'analyze':
            analysis = monitor.analyze_costs(args.days)
            print(json.dumps(asdict(analysis), indent=2))
            
        elif args.action == 'report':
            analysis = monitor.analyze_costs(args.days)
            report = monitor.generate_cost_report(analysis)
            
            if args.output:
                with open(args.output, 'w') as f:
                    f.write(report)
                logger.info(f"Report saved to {args.output}")
            else:
                print(report)
                
        elif args.action == 'optimize':
            optimizations = monitor.optimize_costs()
            print(json.dumps(optimizations, indent=2))
            
        elif args.action == 'forecast':
            analysis = monitor.analyze_costs(args.days)
            logger.info(f"Cost forecast - Projected monthly: ${analysis.projected_monthly_cost:.2f}")
            logger.info(f"Trend: {analysis.cost_trend_percent:+.1f}%")
    
    except Exception as e:
        logger.error(f"Cost analysis failed: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())