import json
import boto3
import os
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any
import uuid

# Configure structured logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
cloudwatch = boto3.client('cloudwatch')
dynamodb = boto3.resource('dynamodb')
logs_client = boto3.client('logs')

# Environment variables
HISTORY_TABLE = os.environ.get('HISTORY_TABLE')
NAMESPACE = 'AutoSpecAI'

class MetricsCollector:
    """Collect and publish custom CloudWatch metrics."""
    
    def __init__(self):
        self.cloudwatch = cloudwatch
        self.namespace = NAMESPACE
        
    def put_metric(self, metric_name: str, value: float, unit: str = 'Count', 
                   dimensions: Dict[str, str] = None):
        """Put a single metric to CloudWatch."""
        try:
            metric_data = {
                'MetricName': metric_name,
                'Value': value,
                'Unit': unit,
                'Timestamp': datetime.now(timezone.utc)
            }
            
            if dimensions:
                metric_data['Dimensions'] = [
                    {'Name': k, 'Value': v} for k, v in dimensions.items()
                ]
            
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=[metric_data]
            )
            
            logger.info(f"Published metric: {metric_name} = {value} {unit}")
            
        except Exception as e:
            logger.error(f"Failed to publish metric {metric_name}: {str(e)}")
    
    def put_metrics_batch(self, metrics: List[Dict[str, Any]]):
        """Put multiple metrics to CloudWatch in a batch."""
        try:
            metric_data = []
            
            for metric in metrics:
                metric_entry = {
                    'MetricName': metric['name'],
                    'Value': metric['value'],
                    'Unit': metric.get('unit', 'Count'),
                    'Timestamp': datetime.now(timezone.utc)
                }
                
                if 'dimensions' in metric:
                    metric_entry['Dimensions'] = [
                        {'Name': k, 'Value': v} for k, v in metric['dimensions'].items()
                    ]
                
                metric_data.append(metric_entry)
            
            # CloudWatch allows max 20 metrics per batch
            for i in range(0, len(metric_data), 20):
                batch = metric_data[i:i+20]
                self.cloudwatch.put_metric_data(
                    Namespace=self.namespace,
                    MetricData=batch
                )
            
            logger.info(f"Published {len(metrics)} metrics in batch")
            
        except Exception as e:
            logger.error(f"Failed to publish metrics batch: {str(e)}")

class PerformanceMonitor:
    """Monitor performance metrics and KPIs."""
    
    def __init__(self):
        self.metrics = MetricsCollector()
        self.dynamodb = dynamodb
        
    def collect_processing_metrics(self):
        """Collect document processing performance metrics."""
        try:
            table = self.dynamodb.Table(HISTORY_TABLE)
            
            # Get metrics for the last hour
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=1)
            
            # Query recent requests
            response = table.scan(
                FilterExpression='#ts BETWEEN :start AND :end',
                ExpressionAttributeNames={'#ts': 'timestamp'},
                ExpressionAttributeValues={
                    ':start': start_time.isoformat(),
                    ':end': end_time.isoformat()
                }
            )
            
            metrics = self._analyze_processing_data(response['Items'])
            
            # Publish metrics
            self.metrics.put_metrics_batch(metrics)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting processing metrics: {str(e)}")
            return []
    
    def _analyze_processing_data(self, items: List[Dict]) -> List[Dict]:
        """Analyze processing data and generate metrics."""
        metrics = []
        
        # Count by status
        status_counts = {}
        stage_counts = {}
        file_type_counts = {}
        processing_times = []
        file_sizes = []
        
        for item in items:
            # Status metrics
            status = item.get('status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
            
            # Stage metrics
            stage = item.get('processingStage', 'unknown')
            stage_counts[stage] = stage_counts.get(stage, 0) + 1
            
            # File type metrics
            file_type = item.get('fileType', 'unknown')
            file_type_counts[file_type] = file_type_counts.get(file_type, 0) + 1
            
            # Processing time metrics
            if item.get('processedAt') and item.get('timestamp'):
                try:
                    start = datetime.fromisoformat(item['timestamp'].replace('Z', '+00:00'))
                    end = datetime.fromisoformat(item['processedAt'].replace('Z', '+00:00'))
                    processing_time = (end - start).total_seconds()
                    processing_times.append(processing_time)
                except Exception:
                    pass
            
            # File size metrics
            if 'fileSize' in item:
                try:
                    file_sizes.append(float(item['fileSize']))
                except (ValueError, TypeError):
                    pass
        
        # Create status metrics
        for status, count in status_counts.items():
            metrics.append({
                'name': 'DocumentsProcessed',
                'value': count,
                'dimensions': {'Status': status}
            })
        
        # Create stage metrics
        for stage, count in stage_counts.items():
            metrics.append({
                'name': 'ProcessingStages',
                'value': count,
                'dimensions': {'Stage': stage}
            })
        
        # Create file type metrics
        for file_type, count in file_type_counts.items():
            metrics.append({
                'name': 'DocumentsByType',
                'value': count,
                'dimensions': {'FileType': file_type}
            })
        
        # Processing time metrics
        if processing_times:
            metrics.extend([
                {
                    'name': 'ProcessingTimeAverage',
                    'value': sum(processing_times) / len(processing_times),
                    'unit': 'Seconds'
                },
                {
                    'name': 'ProcessingTimeMax',
                    'value': max(processing_times),
                    'unit': 'Seconds'
                },
                {
                    'name': 'ProcessingTimeMin',
                    'value': min(processing_times),
                    'unit': 'Seconds'
                }
            ])
        
        # File size metrics
        if file_sizes:
            metrics.extend([
                {
                    'name': 'FileSizeAverage',
                    'value': sum(file_sizes) / len(file_sizes),
                    'unit': 'Bytes'
                },
                {
                    'name': 'FileSizeMax',
                    'value': max(file_sizes),
                    'unit': 'Bytes'
                },
                {
                    'name': 'FileSizeTotal',
                    'value': sum(file_sizes),
                    'unit': 'Bytes'
                }
            ])
        
        # Overall metrics
        metrics.extend([
            {
                'name': 'TotalRequests',
                'value': len(items)
            },
            {
                'name': 'SuccessRate',
                'value': (status_counts.get('delivered', 0) / len(items) * 100) if items else 0,
                'unit': 'Percent'
            },
            {
                'name': 'ErrorRate',
                'value': (status_counts.get('failed', 0) / len(items) * 100) if items else 0,
                'unit': 'Percent'
            }
        ])
        
        return metrics

class AlertManager:
    """Manage CloudWatch alarms and notifications."""
    
    def __init__(self):
        self.cloudwatch = cloudwatch
        self.namespace = NAMESPACE
    
    def create_alarms(self):
        """Create CloudWatch alarms for key metrics."""
        alarms = [
            {
                'AlarmName': 'AutoSpecAI-HighErrorRate',
                'MetricName': 'ErrorRate',
                'Threshold': 10.0,  # 10% error rate
                'ComparisonOperator': 'GreaterThanThreshold',
                'EvaluationPeriods': 2,
                'Period': 300,  # 5 minutes
                'Statistic': 'Average',
                'AlarmDescription': 'High error rate in document processing'
            },
            {
                'AlarmName': 'AutoSpecAI-LongProcessingTime',
                'MetricName': 'ProcessingTimeAverage',
                'Threshold': 600.0,  # 10 minutes
                'ComparisonOperator': 'GreaterThanThreshold',
                'EvaluationPeriods': 2,
                'Period': 300,
                'Statistic': 'Average',
                'AlarmDescription': 'Processing time exceeding normal thresholds'
            },
            {
                'AlarmName': 'AutoSpecAI-LowThroughput',
                'MetricName': 'TotalRequests',
                'Threshold': 1.0,
                'ComparisonOperator': 'LessThanThreshold',
                'EvaluationPeriods': 3,
                'Period': 1800,  # 30 minutes
                'Statistic': 'Sum',
                'AlarmDescription': 'Unusually low request volume'
            }
        ]
        
        for alarm_config in alarms:
            try:
                self.cloudwatch.put_metric_alarm(
                    AlarmName=alarm_config['AlarmName'],
                    ComparisonOperator=alarm_config['ComparisonOperator'],
                    EvaluationPeriods=alarm_config['EvaluationPeriods'],
                    MetricName=alarm_config['MetricName'],
                    Namespace=self.namespace,
                    Period=alarm_config['Period'],
                    Statistic=alarm_config['Statistic'],
                    Threshold=alarm_config['Threshold'],
                    ActionsEnabled=True,
                    AlarmDescription=alarm_config['AlarmDescription'],
                    Unit='Percent' if 'Rate' in alarm_config['MetricName'] else 'None'
                )
                
                logger.info(f"Created alarm: {alarm_config['AlarmName']}")
                
            except Exception as e:
                logger.error(f"Failed to create alarm {alarm_config['AlarmName']}: {str(e)}")

class LogAnalyzer:
    """Analyze CloudWatch logs for insights and anomalies."""
    
    def __init__(self):
        self.logs_client = logs_client
        self.metrics = MetricsCollector()
    
    def analyze_error_patterns(self, log_group: str, hours: int = 1):
        """Analyze error patterns in CloudWatch logs."""
        try:
            end_time = int(time.time() * 1000)
            start_time = end_time - (hours * 60 * 60 * 1000)
            
            # Query for error patterns
            query = """
            fields @timestamp, @message
            | filter @message like /ERROR/
            | stats count() by bin(5m)
            """
            
            response = self.logs_client.start_query(
                logGroupName=log_group,
                startTime=start_time,
                endTime=end_time,
                queryString=query
            )
            
            query_id = response['queryId']
            
            # Wait for query completion
            while True:
                result = self.logs_client.get_query_results(queryId=query_id)
                if result['status'] == 'Complete':
                    break
                elif result['status'] == 'Failed':
                    logger.error("Log query failed")
                    return
                time.sleep(1)
            
            # Analyze results
            error_counts = []
            for row in result['results']:
                if len(row) >= 2:
                    count = int(row[1]['value'])
                    error_counts.append(count)
            
            if error_counts:
                # Publish error metrics
                self.metrics.put_metric(
                    'LogErrorCount',
                    sum(error_counts),
                    dimensions={'LogGroup': log_group.split('/')[-1]}
                )
                
                self.metrics.put_metric(
                    'LogErrorRate',
                    sum(error_counts) / len(error_counts),
                    'Count/Minute',
                    dimensions={'LogGroup': log_group.split('/')[-1]}
                )
            
        except Exception as e:
            logger.error(f"Error analyzing log patterns: {str(e)}")

def handler(event, context):
    """
    Lambda handler for monitoring and metrics collection.
    Can be triggered by CloudWatch Events or direct invocation.
    """
    try:
        logger.info(f"Monitoring function invoked: {json.dumps(event)}")
        
        # Initialize monitoring components
        performance_monitor = PerformanceMonitor()
        alert_manager = AlertManager()
        log_analyzer = LogAnalyzer()
        
        # Collect performance metrics
        metrics = performance_monitor.collect_processing_metrics()
        
        # Create alarms if not exists (idempotent)
        alert_manager.create_alarms()
        
        # Analyze logs for error patterns
        log_groups = [
            '/aws/lambda/AutoSpecAI-IngestFunction',
            '/aws/lambda/AutoSpecAI-ProcessFunction',
            '/aws/lambda/AutoSpecAI-FormatFunction',
            '/aws/lambda/AutoSpecAI-ApiFunction'
        ]
        
        for log_group in log_groups:
            try:
                log_analyzer.analyze_error_patterns(log_group)
            except Exception as e:
                logger.warning(f"Could not analyze log group {log_group}: {str(e)}")
        
        # Generate summary report
        summary = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'metrics_collected': len(metrics),
            'monitoring_status': 'healthy',
            'next_run': (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
        }
        
        logger.info(f"Monitoring summary: {json.dumps(summary)}")
        
        return {
            'statusCode': 200,
            'body': json.dumps(summary)
        }
        
    except Exception as e:
        logger.error(f"Monitoring function error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Monitoring failed',
                'message': str(e)
            })
        }

# Utility functions for structured logging
def log_request_start(request_id: str, function_name: str, **kwargs):
    """Log request start with structured data."""
    log_data = {
        'event': 'request_start',
        'request_id': request_id,
        'function': function_name,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        **kwargs
    }
    logger.info(json.dumps(log_data))

def log_request_end(request_id: str, function_name: str, duration: float, status: str, **kwargs):
    """Log request end with structured data."""
    log_data = {
        'event': 'request_end',
        'request_id': request_id,
        'function': function_name,
        'duration_ms': duration * 1000,
        'status': status,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        **kwargs
    }
    logger.info(json.dumps(log_data))

def log_error(request_id: str, function_name: str, error: Exception, **kwargs):
    """Log error with structured data."""
    log_data = {
        'event': 'error',
        'request_id': request_id,
        'function': function_name,
        'error_type': type(error).__name__,
        'error_message': str(error),
        'timestamp': datetime.now(timezone.utc).isoformat(),
        **kwargs
    }
    logger.error(json.dumps(log_data))

def log_metric(metric_name: str, value: float, unit: str = 'Count', **kwargs):
    """Log custom metric for CloudWatch Insights."""
    log_data = {
        'event': 'metric',
        'metric_name': metric_name,
        'metric_value': value,
        'metric_unit': unit,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        **kwargs
    }
    logger.info(json.dumps(log_data))