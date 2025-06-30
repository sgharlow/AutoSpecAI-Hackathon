#!/usr/bin/env python3
"""
AutoSpec.AI Provisioned Concurrency Management Tool

This script helps manage and optimize Lambda provisioned concurrency
based on usage patterns and cost considerations.

Usage:
    python3 manage-provisioned-concurrency.py --environment dev --action analyze
    python3 manage-provisioned-concurrency.py --environment prod --action optimize
    python3 manage-provisioned-concurrency.py --environment staging --action report
"""

import argparse
import boto3
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ProvisionedConcurrencyManager:
    """Manages Lambda provisioned concurrency optimization."""
    
    def __init__(self, environment: str):
        self.environment = environment
        self.lambda_client = boto3.client('lambda')
        self.cloudwatch = boto3.client('cloudwatch')
        self.application_autoscaling = boto3.client('application-autoscaling')
        
        # Function configurations for different environments
        self.function_configs = {
            'dev': {
                'AutoSpecAI-ProcessFunction-dev': {
                    'alias': 'LIVE',
                    'min_capacity': 1,
                    'max_capacity': 3,
                    'target_utilization': 70.0,
                    'critical': True
                },
                'AutoSpecAI-FormatFunction-dev': {
                    'alias': 'LIVE',
                    'min_capacity': 1,
                    'max_capacity': 2,
                    'target_utilization': 60.0,
                    'critical': False
                },
                'AutoSpecAI-ApiFunction-dev': {
                    'alias': 'LIVE',
                    'min_capacity': 2,
                    'max_capacity': 5,
                    'target_utilization': 80.0,
                    'critical': True
                }
            },
            'staging': {
                'AutoSpecAI-ProcessFunction-staging': {
                    'alias': 'LIVE',
                    'min_capacity': 2,
                    'max_capacity': 5,
                    'target_utilization': 70.0,
                    'critical': True
                },
                'AutoSpecAI-FormatFunction-staging': {
                    'alias': 'LIVE',
                    'min_capacity': 1,
                    'max_capacity': 3,
                    'target_utilization': 65.0,
                    'critical': False
                },
                'AutoSpecAI-ApiFunction-staging': {
                    'alias': 'LIVE',
                    'min_capacity': 3,
                    'max_capacity': 8,
                    'target_utilization': 75.0,
                    'critical': True
                }
            },
            'prod': {
                'AutoSpecAI-ProcessFunction-prod': {
                    'alias': 'LIVE',
                    'min_capacity': 3,
                    'max_capacity': 10,
                    'target_utilization': 70.0,
                    'critical': True
                },
                'AutoSpecAI-FormatFunction-prod': {
                    'alias': 'LIVE',
                    'min_capacity': 2,
                    'max_capacity': 5,
                    'target_utilization': 65.0,
                    'critical': False
                },
                'AutoSpecAI-ApiFunction-prod': {
                    'alias': 'LIVE',
                    'min_capacity': 5,
                    'max_capacity': 15,
                    'target_utilization': 75.0,
                    'critical': True
                }
            }
        }

    def analyze_current_state(self) -> Dict[str, Any]:
        """Analyze current provisioned concurrency configuration and usage."""
        logger.info(f"Analyzing provisioned concurrency for environment: {self.environment}")
        
        analysis = {
            'environment': self.environment,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'functions': {},
            'cost_estimate': 0.0,
            'recommendations': []
        }
        
        functions = self.function_configs.get(self.environment, {})
        
        for function_name, config in functions.items():
            logger.info(f"Analyzing function: {function_name}")
            
            # Get current provisioned concurrency configuration
            try:
                pc_response = self.lambda_client.get_provisioned_concurrency_config(
                    FunctionName=function_name,
                    Qualifier=config['alias']
                )
                current_capacity = pc_response['AllocatedConcurrencyExecutions']
                status = pc_response['Status']
            except self.lambda_client.exceptions.ProvisionedConcurrencyConfigNotFoundException:
                current_capacity = 0
                status = 'NotConfigured'
            except Exception as e:
                logger.error(f"Error getting provisioned concurrency for {function_name}: {e}")
                current_capacity = 0
                status = 'Error'
            
            # Get usage metrics
            usage_metrics = self._get_usage_metrics(function_name, config['alias'])
            
            # Calculate cost estimate
            cost_estimate = self._calculate_cost_estimate(current_capacity, usage_metrics)
            
            analysis['functions'][function_name] = {
                'current_capacity': current_capacity,
                'status': status,
                'config': config,
                'usage_metrics': usage_metrics,
                'cost_estimate': cost_estimate,
                'optimization_potential': self._calculate_optimization_potential(
                    current_capacity, usage_metrics, config
                )
            }
            
            analysis['cost_estimate'] += cost_estimate
        
        # Generate recommendations
        analysis['recommendations'] = self._generate_recommendations(analysis['functions'])
        
        return analysis

    def _get_usage_metrics(self, function_name: str, alias: str) -> Dict[str, Any]:
        """Get CloudWatch metrics for a function."""
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=7)  # Last 7 days
        
        metrics = {
            'invocations': 0,
            'duration_avg': 0,
            'errors': 0,
            'concurrent_executions_max': 0,
            'provisioned_concurrency_utilization_avg': 0,
            'cold_starts': 0
        }
        
        try:
            # Get invocation count
            invocations_response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/Lambda',
                MetricName='Invocations',
                Dimensions=[
                    {'Name': 'FunctionName', 'Value': function_name},
                    {'Name': 'Resource', 'Value': f'{function_name}:{alias}'}
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,  # 1 hour periods
                Statistics=['Sum']
            )
            
            if invocations_response['Datapoints']:
                metrics['invocations'] = sum(dp['Sum'] for dp in invocations_response['Datapoints'])
            
            # Get duration
            duration_response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/Lambda',
                MetricName='Duration',
                Dimensions=[
                    {'Name': 'FunctionName', 'Value': function_name},
                    {'Name': 'Resource', 'Value': f'{function_name}:{alias}'}
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,
                Statistics=['Average']
            )
            
            if duration_response['Datapoints']:
                metrics['duration_avg'] = sum(dp['Average'] for dp in duration_response['Datapoints']) / len(duration_response['Datapoints'])
            
            # Get concurrent executions
            concurrent_response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/Lambda',
                MetricName='ConcurrentExecutions',
                Dimensions=[
                    {'Name': 'FunctionName', 'Value': function_name}
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,
                Statistics=['Maximum']
            )
            
            if concurrent_response['Datapoints']:
                metrics['concurrent_executions_max'] = max(dp['Maximum'] for dp in concurrent_response['Datapoints'])
            
            # Get provisioned concurrency utilization
            utilization_response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/Lambda',
                MetricName='ProvisionedConcurrencyUtilization',
                Dimensions=[
                    {'Name': 'FunctionName', 'Value': function_name},
                    {'Name': 'Resource', 'Value': f'{function_name}:{alias}'}
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,
                Statistics=['Average']
            )
            
            if utilization_response['Datapoints']:
                metrics['provisioned_concurrency_utilization_avg'] = sum(dp['Average'] for dp in utilization_response['Datapoints']) / len(utilization_response['Datapoints'])
            
        except Exception as e:
            logger.error(f"Error getting metrics for {function_name}: {e}")
        
        return metrics

    def _calculate_cost_estimate(self, capacity: int, metrics: Dict[str, Any]) -> float:
        """Calculate monthly cost estimate for provisioned concurrency."""
        if capacity == 0:
            return 0.0
        
        # AWS pricing for provisioned concurrency (approximate)
        # $0.0000097 per GB-second for provisioned concurrency
        # Assuming 3008 MB (3 GB) memory allocation
        gb_memory = 3.0
        seconds_per_month = 30 * 24 * 3600  # 30 days
        
        monthly_cost = capacity * gb_memory * seconds_per_month * 0.0000097
        
        return round(monthly_cost, 2)

    def _calculate_optimization_potential(self, current_capacity: int, metrics: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate optimization potential for a function."""
        potential = {
            'recommended_capacity': current_capacity,
            'cost_savings_potential': 0.0,
            'performance_impact': 'None',
            'confidence_level': 'Low'
        }
        
        if metrics['provisioned_concurrency_utilization_avg'] > 0:
            # Calculate recommended capacity based on usage patterns
            utilization = metrics['provisioned_concurrency_utilization_avg']
            max_concurrent = metrics['concurrent_executions_max']
            
            if utilization < 50 and current_capacity > config['min_capacity']:
                # Under-utilized, can reduce capacity
                potential['recommended_capacity'] = max(
                    config['min_capacity'],
                    int(current_capacity * 0.7)  # Reduce by 30%
                )
                potential['cost_savings_potential'] = self._calculate_cost_estimate(
                    current_capacity - potential['recommended_capacity'], metrics
                )
                potential['performance_impact'] = 'Minimal'
                potential['confidence_level'] = 'High' if utilization < 30 else 'Medium'
                
            elif utilization > 80 and current_capacity < config['max_capacity']:
                # Over-utilized, should increase capacity
                potential['recommended_capacity'] = min(
                    config['max_capacity'],
                    int(current_capacity * 1.3)  # Increase by 30%
                )
                potential['cost_savings_potential'] = -self._calculate_cost_estimate(
                    potential['recommended_capacity'] - current_capacity, metrics
                )
                potential['performance_impact'] = 'Improved'
                potential['confidence_level'] = 'High'
        
        return potential

    def _generate_recommendations(self, functions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate optimization recommendations."""
        recommendations = []
        
        for function_name, data in functions.items():
            optimization = data['optimization_potential']
            current = data['current_capacity']
            recommended = optimization['recommended_capacity']
            
            if current != recommended:
                rec = {
                    'function': function_name,
                    'current_capacity': current,
                    'recommended_capacity': recommended,
                    'cost_impact': optimization['cost_savings_potential'],
                    'performance_impact': optimization['performance_impact'],
                    'confidence': optimization['confidence_level'],
                    'priority': 'High' if data['config']['critical'] else 'Medium'
                }
                
                if optimization['cost_savings_potential'] > 10:  # $10+ savings
                    rec['action'] = 'Reduce provisioned concurrency'
                elif optimization['cost_savings_potential'] < -5:  # $5+ additional cost
                    rec['action'] = 'Increase provisioned concurrency'
                else:
                    rec['action'] = 'Minor adjustment'
                
                recommendations.append(rec)
        
        # Sort by cost impact (highest savings first)
        recommendations.sort(key=lambda x: x['cost_impact'], reverse=True)
        
        return recommendations

    def optimize_configuration(self, dry_run: bool = True) -> Dict[str, Any]:
        """Optimize provisioned concurrency based on analysis."""
        logger.info(f"Optimizing provisioned concurrency (dry_run={dry_run})")
        
        analysis = self.analyze_current_state()
        results = {
            'environment': self.environment,
            'dry_run': dry_run,
            'changes_applied': [],
            'total_cost_impact': 0.0,
            'errors': []
        }
        
        for recommendation in analysis['recommendations']:
            function_name = recommendation['function']
            current_capacity = recommendation['current_capacity']
            recommended_capacity = recommendation['recommended_capacity']
            
            if recommendation['confidence'] == 'High' and abs(recommendation['cost_impact']) > 5:
                try:
                    if not dry_run:
                        # Apply the optimization
                        if recommended_capacity == 0:
                            # Delete provisioned concurrency
                            self.lambda_client.delete_provisioned_concurrency_config(
                                FunctionName=function_name,
                                Qualifier='LIVE'
                            )
                        else:
                            # Update provisioned concurrency
                            self.lambda_client.put_provisioned_concurrency_config(
                                FunctionName=function_name,
                                Qualifier='LIVE',
                                ProvisionedConcurrencyExecutions=recommended_capacity
                            )
                        
                        logger.info(f"Updated {function_name}: {current_capacity} -> {recommended_capacity}")
                    
                    results['changes_applied'].append({
                        'function': function_name,
                        'from': current_capacity,
                        'to': recommended_capacity,
                        'cost_impact': recommendation['cost_impact']
                    })
                    
                    results['total_cost_impact'] += recommendation['cost_impact']
                    
                except Exception as e:
                    error_msg = f"Failed to update {function_name}: {str(e)}"
                    logger.error(error_msg)
                    results['errors'].append(error_msg)
        
        return results

    def generate_report(self) -> str:
        """Generate a comprehensive provisioned concurrency report."""
        analysis = self.analyze_current_state()
        
        report = f"""
# AutoSpec.AI Provisioned Concurrency Report
Environment: {self.environment}
Generated: {analysis['timestamp']}

## Current Configuration Summary
Total Monthly Cost Estimate: ${analysis['cost_estimate']:.2f}

### Function Details:
"""
        
        for function_name, data in analysis['functions'].items():
            report += f"""
**{function_name}**
- Current Capacity: {data['current_capacity']}
- Status: {data['status']}
- Monthly Cost: ${data['cost_estimate']:.2f}
- Avg Utilization: {data['usage_metrics']['provisioned_concurrency_utilization_avg']:.1f}%
- Total Invocations (7d): {data['usage_metrics']['invocations']:.0f}
- Max Concurrent Executions: {data['usage_metrics']['concurrent_executions_max']:.0f}
"""
        
        report += "\n## Recommendations:\n"
        
        if analysis['recommendations']:
            for i, rec in enumerate(analysis['recommendations'], 1):
                report += f"""
{i}. **{rec['function']}** ({rec['priority']} Priority)
   - Action: {rec['action']}
   - Current: {rec['current_capacity']} -> Recommended: {rec['recommended_capacity']}
   - Cost Impact: ${rec['cost_impact']:.2f}/month
   - Confidence: {rec['confidence']}
"""
        else:
            report += "No optimization recommendations at this time.\n"
        
        total_savings = sum(rec['cost_impact'] for rec in analysis['recommendations'] if rec['cost_impact'] > 0)
        if total_savings > 0:
            report += f"\n**Total Potential Monthly Savings: ${total_savings:.2f}**\n"
        
        return report

def main():
    parser = argparse.ArgumentParser(description='Manage AutoSpec.AI provisioned concurrency')
    parser.add_argument('--environment', required=True, choices=['dev', 'staging', 'prod'],
                       help='Environment to manage')
    parser.add_argument('--action', required=True, 
                       choices=['analyze', 'optimize', 'report'],
                       help='Action to perform')
    parser.add_argument('--dry-run', action='store_true', default=True,
                       help='Perform dry run (default: True)')
    parser.add_argument('--apply', action='store_true',
                       help='Apply changes (overrides --dry-run)')
    
    args = parser.parse_args()
    
    # Initialize manager
    manager = ProvisionedConcurrencyManager(args.environment)
    
    try:
        if args.action == 'analyze':
            analysis = manager.analyze_current_state()
            print(json.dumps(analysis, indent=2))
            
        elif args.action == 'optimize':
            dry_run = not args.apply
            results = manager.optimize_configuration(dry_run=dry_run)
            print(json.dumps(results, indent=2))
            
        elif args.action == 'report':
            report = manager.generate_report()
            print(report)
            
    except Exception as e:
        logger.error(f"Error executing action {args.action}: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())