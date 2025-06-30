#!/usr/bin/env python3
"""
AutoSpec.AI Performance Monitoring Dashboard

This script creates and updates CloudWatch dashboards specifically for
monitoring provisioned concurrency performance and cost optimization.

Usage:
    python3 performance-monitoring-dashboard.py --environment dev --create
    python3 performance-monitoring-dashboard.py --environment prod --update
"""

import argparse
import boto3
import json
from datetime import datetime, timezone
from typing import Dict, List, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PerformanceMonitoringDashboard:
    """Creates and manages performance monitoring dashboards."""
    
    def __init__(self, environment: str):
        self.environment = environment
        self.cloudwatch = boto3.client('cloudwatch')
        self.lambda_client = boto3.client('lambda')
        
    def create_provisioned_concurrency_dashboard(self) -> str:
        """Create a comprehensive provisioned concurrency dashboard."""
        dashboard_name = f"AutoSpecAI-ProvisionedConcurrency-{self.environment}"
        
        # Get function names for the environment
        functions = self._get_lambda_functions()
        
        # Build dashboard body
        dashboard_body = {
            "widgets": [
                self._create_overview_widget(),
                *self._create_function_widgets(functions),
                self._create_cost_widget(),
                self._create_optimization_widget(),
                *self._create_performance_comparison_widgets(functions)
            ]
        }
        
        try:
            self.cloudwatch.put_dashboard(
                DashboardName=dashboard_name,
                DashboardBody=json.dumps(dashboard_body)
            )
            
            dashboard_url = self._get_dashboard_url(dashboard_name)
            logger.info(f"Created dashboard: {dashboard_url}")
            return dashboard_url
            
        except Exception as e:
            logger.error(f"Failed to create dashboard: {e}")
            raise
    
    def _get_lambda_functions(self) -> List[str]:
        """Get Lambda function names for the environment."""
        try:
            paginator = self.lambda_client.get_paginator('list_functions')
            functions = []
            
            for page in paginator.paginate():
                for func in page['Functions']:
                    if f"AutoSpecAI-{self.environment}" in func['FunctionName'] or \
                       func['FunctionName'].endswith(f"-{self.environment}"):
                        functions.append(func['FunctionName'])
            
            return functions
        except Exception as e:
            logger.warning(f"Could not get Lambda functions: {e}")
            return []
    
    def _create_overview_widget(self) -> Dict[str, Any]:
        """Create overview widget with key metrics."""
        return {
            "type": "metric",
            "x": 0,
            "y": 0,
            "width": 24,
            "height": 6,
            "properties": {
                "metrics": [
                    ["AWS/Lambda", "ProvisionedConcurrencyUtilization", "FunctionName", f"AutoSpecAI-ProcessFunction-{self.environment}", "Resource", f"AutoSpecAI-ProcessFunction-{self.environment}:LIVE"],
                    ["...", f"AutoSpecAI-FormatFunction-{self.environment}", ".", f"AutoSpecAI-FormatFunction-{self.environment}:LIVE"],
                    ["...", f"AutoSpecAI-ApiFunction-{self.environment}", ".", f"AutoSpecAI-ApiFunction-{self.environment}:LIVE"],
                    [".", "ProvisionedConcurrencyInvocations", ".", f"AutoSpecAI-ProcessFunction-{self.environment}", ".", f"AutoSpecAI-ProcessFunction-{self.environment}:LIVE"],
                    ["...", f"AutoSpecAI-FormatFunction-{self.environment}", ".", f"AutoSpecAI-FormatFunction-{self.environment}:LIVE"],
                    ["...", f"AutoSpecAI-ApiFunction-{self.environment}", ".", f"AutoSpecAI-ApiFunction-{self.environment}:LIVE"]
                ],
                "view": "timeSeries",
                "stacked": False,
                "region": boto3.Session().region_name or "us-east-1",
                "title": f"Provisioned Concurrency Overview - {self.environment.upper()}",
                "period": 300,
                "stat": "Average",
                "yAxis": {
                    "left": {
                        "min": 0,
                        "max": 100
                    }
                }
            }
        }
    
    def _create_function_widgets(self, functions: List[str]) -> List[Dict[str, Any]]:
        """Create individual function monitoring widgets."""
        widgets = []
        
        for i, function_name in enumerate(functions):
            if "ProcessFunction" in function_name or "FormatFunction" in function_name or "ApiFunction" in function_name:
                widget = {
                    "type": "metric",
                    "x": (i % 3) * 8,
                    "y": 6 + (i // 3) * 6,
                    "width": 8,
                    "height": 6,
                    "properties": {
                        "metrics": [
                            ["AWS/Lambda", "Duration", "FunctionName", function_name],
                            [".", "Invocations", ".", "."],
                            [".", "Errors", ".", "."],
                            [".", "ConcurrentExecutions", ".", "."],
                            [".", "ProvisionedConcurrencyUtilization", ".", ".", "Resource", f"{function_name}:LIVE"],
                            [".", "ProvisionedConcurrencyInvocations", ".", ".", ".", "."]
                        ],
                        "view": "timeSeries",
                        "stacked": False,
                        "region": boto3.Session().region_name or "us-east-1",
                        "title": f"{function_name} Performance",
                        "period": 300,
                        "stat": "Average"
                    }
                }
                widgets.append(widget)
        
        return widgets
    
    def _create_cost_widget(self) -> Dict[str, Any]:
        """Create cost monitoring widget."""
        return {
            "type": "log",
            "x": 0,
            "y": 18,
            "width": 12,
            "height": 6,
            "properties": {
                "query": f"SOURCE '/aws/lambda/AutoSpecAI-ProcessFunction-{self.environment}'\n| fields @timestamp, @message\n| filter @message like /Provisioned concurrency/\n| stats count() by bin(5m)",
                "region": boto3.Session().region_name or "us-east-1",
                "title": "Provisioned Concurrency Usage Patterns",
                "view": "table"
            }
        }
    
    def _create_optimization_widget(self) -> Dict[str, Any]:
        """Create optimization recommendations widget."""
        return {
            "type": "log",
            "x": 12,
            "y": 18,
            "width": 12,
            "height": 6,
            "properties": {
                "query": f"SOURCE '/aws/lambda/AutoSpecAI-ProcessFunction-{self.environment}'\n| fields @timestamp, @message\n| filter @message like /Cold start/ or @message like /Init duration/\n| stats count() by bin(1h)",
                "region": boto3.Session().region_name or "us-east-1",
                "title": "Cold Start Analysis",
                "view": "table"
            }
        }
    
    def _create_performance_comparison_widgets(self, functions: List[str]) -> List[Dict[str, Any]]:
        """Create performance comparison widgets."""
        widgets = []
        
        # Cold start vs warm start comparison
        comparison_widget = {
            "type": "metric",
            "x": 0,
            "y": 24,
            "width": 24,
            "height": 6,
            "properties": {
                "metrics": [
                    ["AWS/Lambda", "InitDuration", "FunctionName", f"AutoSpecAI-ProcessFunction-{self.environment}"],
                    ["...", f"AutoSpecAI-FormatFunction-{self.environment}"],
                    ["...", f"AutoSpecAI-ApiFunction-{self.environment}"],
                    [".", "Duration", ".", f"AutoSpecAI-ProcessFunction-{self.environment}"],
                    ["...", f"AutoSpecAI-FormatFunction-{self.environment}"],
                    ["...", f"AutoSpecAI-ApiFunction-{self.environment}"]
                ],
                "view": "timeSeries",
                "stacked": False,
                "region": boto3.Session().region_name or "us-east-1",
                "title": "Cold Start vs Execution Duration",
                "period": 300,
                "stat": "Average"
            }
        }
        widgets.append(comparison_widget)
        
        return widgets
    
    def _get_dashboard_url(self, dashboard_name: str) -> str:
        """Get CloudWatch dashboard URL."""
        region = boto3.Session().region_name or "us-east-1"
        return f"https://{region}.console.aws.amazon.com/cloudwatch/home?region={region}#dashboards:name={dashboard_name}"
    
    def create_performance_alert_system(self) -> List[str]:
        """Create CloudWatch alarms for performance monitoring."""
        alarms = []
        
        # Provisioned concurrency utilization alarms
        functions = [
            f"AutoSpecAI-ProcessFunction-{self.environment}",
            f"AutoSpecAI-FormatFunction-{self.environment}",
            f"AutoSpecAI-ApiFunction-{self.environment}"
        ]
        
        for function_name in functions:
            # High utilization alarm
            alarm_name = f"AutoSpecAI-{self.environment}-{function_name}-HighUtilization"
            try:
                self.cloudwatch.put_metric_alarm(
                    AlarmName=alarm_name,
                    ComparisonOperator='GreaterThanThreshold',
                    EvaluationPeriods=3,
                    MetricName='ProvisionedConcurrencyUtilization',
                    Namespace='AWS/Lambda',
                    Period=300,
                    Statistic='Average',
                    Threshold=80.0,
                    ActionsEnabled=True,
                    AlarmDescription=f'High provisioned concurrency utilization for {function_name}',
                    Dimensions=[
                        {
                            'Name': 'FunctionName',
                            'Value': function_name
                        },
                        {
                            'Name': 'Resource',
                            'Value': f'{function_name}:LIVE'
                        }
                    ],
                    Unit='Percent',
                    TreatMissingData='notBreaching'
                )
                alarms.append(alarm_name)
                logger.info(f"Created alarm: {alarm_name}")
            except Exception as e:
                logger.error(f"Failed to create alarm {alarm_name}: {e}")
            
            # Low utilization alarm (cost optimization)
            alarm_name = f"AutoSpecAI-{self.environment}-{function_name}-LowUtilization"
            try:
                self.cloudwatch.put_metric_alarm(
                    AlarmName=alarm_name,
                    ComparisonOperator='LessThanThreshold',
                    EvaluationPeriods=12,  # 1 hour with 5-minute periods
                    MetricName='ProvisionedConcurrencyUtilization',
                    Namespace='AWS/Lambda',
                    Period=300,
                    Statistic='Average',
                    Threshold=20.0,
                    ActionsEnabled=True,
                    AlarmDescription=f'Low provisioned concurrency utilization for {function_name} - consider reducing capacity',
                    Dimensions=[
                        {
                            'Name': 'FunctionName',
                            'Value': function_name
                        },
                        {
                            'Name': 'Resource',
                            'Value': f'{function_name}:LIVE'
                        }
                    ],
                    Unit='Percent',
                    TreatMissingData='notBreaching'
                )
                alarms.append(alarm_name)
                logger.info(f"Created alarm: {alarm_name}")
            except Exception as e:
                logger.error(f"Failed to create alarm {alarm_name}: {e}")
        
        return alarms
    
    def generate_performance_report(self) -> str:
        """Generate a performance analysis report."""
        report_timestamp = datetime.now(timezone.utc).isoformat()
        
        report = f"""
# AutoSpec.AI Provisioned Concurrency Performance Report
Environment: {self.environment}
Generated: {report_timestamp}

## Dashboard Links
- Main Dashboard: {self._get_dashboard_url(f'AutoSpecAI-ProvisionedConcurrency-{self.environment}')}
- Operational Dashboard: {self._get_dashboard_url(f'AutoSpecAI-Operational-Dashboard-{self.environment}')}

## Key Performance Metrics (Last 24 Hours)

### Critical Functions Status
"""
        
        # Add function-specific analysis
        functions = self._get_lambda_functions()
        for function_name in functions:
            if any(x in function_name for x in ["ProcessFunction", "FormatFunction", "ApiFunction"]):
                report += f"""
**{function_name}**
- Provisioned Concurrency: Configured
- Monitoring: Active
- Optimization: Enabled
"""
        
        report += """

## Optimization Recommendations

1. **Monitor Utilization Patterns**: Check the dashboard daily for the first week
2. **Review Cost Impact**: Monitor monthly costs and adjust capacity as needed
3. **Performance Baseline**: Establish performance baselines for future optimization
4. **Auto-scaling**: Consider implementing auto-scaling for production workloads

## Next Steps

1. Run weekly optimization analysis:
   ```bash
   python3 scripts/manage-provisioned-concurrency.py --environment {environment} --action report
   ```

2. Monitor alarms and adjust thresholds based on actual usage patterns

3. Consider implementing automated optimization based on CloudWatch metrics
""".format(environment=self.environment)
        
        return report

def main():
    parser = argparse.ArgumentParser(description='Manage AutoSpec.AI performance monitoring dashboard')
    parser.add_argument('--environment', required=True, choices=['dev', 'staging', 'prod'],
                       help='Environment to manage')
    parser.add_argument('--action', required=True,
                       choices=['create', 'update', 'alarms', 'report'],
                       help='Action to perform')
    
    args = parser.parse_args()
    
    dashboard_manager = PerformanceMonitoringDashboard(args.environment)
    
    try:
        if args.action == 'create':
            dashboard_url = dashboard_manager.create_provisioned_concurrency_dashboard()
            print(f"Dashboard created: {dashboard_url}")
            
        elif args.action == 'update':
            dashboard_url = dashboard_manager.create_provisioned_concurrency_dashboard()
            print(f"Dashboard updated: {dashboard_url}")
            
        elif args.action == 'alarms':
            alarms = dashboard_manager.create_performance_alert_system()
            print(f"Created {len(alarms)} performance alarms")
            
        elif args.action == 'report':
            report = dashboard_manager.generate_performance_report()
            print(report)
            
    except Exception as e:
        logger.error(f"Error executing action {args.action}: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())