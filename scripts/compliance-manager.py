#!/usr/bin/env python3
"""
AutoSpec.AI Compliance and Audit Management

Comprehensive compliance management, audit logging, violation detection,
and regulatory framework support.

Usage:
    python3 compliance-manager.py --environment prod --action audit-events
    python3 compliance-manager.py --environment staging --action generate-report
    python3 compliance-manager.py --environment dev --action check-violations
"""

import argparse
import boto3
import json
import time
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import logging
import uuid
import csv
import io

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ComplianceViolation:
    """Compliance violation structure."""
    violation_id: str
    framework: str
    rule_id: str
    severity: str
    title: str
    description: str
    organization_id: str
    status: str
    timestamp: str

@dataclass
class AuditEvent:
    """Audit event structure."""
    event_id: str
    timestamp: str
    user_id: str
    organization_id: str
    event_type: str
    action: str
    resource_type: str
    resource_id: str
    result: str
    source_ip: str
    compliance_tags: List[str]

@dataclass
class ComplianceReport:
    """Compliance report structure."""
    report_id: str
    organization_id: str
    frameworks: List[str]
    overall_score: float
    violations_count: int
    report_date: str
    report_files: List[str]

class ComplianceManager:
    """Manages compliance and audit operations for AutoSpec.AI."""
    
    def __init__(self, environment: str):
        self.environment = environment
        
        # AWS clients
        self.lambda_client = boto3.client('lambda')
        self.dynamodb = boto3.client('dynamodb')
        self.s3 = boto3.client('s3')
        self.kinesis = boto3.client('kinesis')
        self.athena = boto3.client('athena')
        self.stepfunctions = boto3.client('stepfunctions')
        
        # Function names
        self.audit_event_logger_function = f'AutoSpecAI-AuditEventLogger-{environment}'
        self.audit_data_processor_function = f'AutoSpecAI-AuditDataProcessor-{environment}'
        self.compliance_monitor_function = f'AutoSpecAI-ComplianceMonitor-{environment}'
        self.violation_detector_function = f'AutoSpecAI-ViolationDetector-{environment}'
        self.compliance_reporter_function = f'AutoSpecAI-ComplianceReporter-{environment}'
        self.privacy_controls_function = f'AutoSpecAI-PrivacyControlsManager-{environment}'
        
        # Resource names
        self.audit_stream_name = f'autospec-ai-audit-stream-{environment}'
        self.audit_logs_bucket = f'autospec-ai-audit-logs-{environment}'
        self.compliance_reports_bucket = f'autospec-ai-compliance-reports-{environment}'
        self.compliance_workflow_arn = self._get_workflow_arn()
        
        # Table names
        self.compliance_policies_table = f'autospec-ai-compliance-policies-{environment}'
        self.compliance_violations_table = f'autospec-ai-compliance-violations-{environment}'
        self.data_subject_requests_table = f'autospec-ai-data-subject-requests-{environment}'
        self.compliance_reports_table = f'autospec-ai-compliance-reports-{environment}'
        
        # Load configuration
        self.config = self._load_config()
    
    def _get_workflow_arn(self) -> str:
        """Get compliance workflow ARN."""
        try:
            return f'arn:aws:states:us-east-1:123456789012:stateMachine:AutoSpecAI-ComplianceWorkflow-{self.environment}'
        except Exception:
            return ''
    
    def _load_config(self) -> Dict[str, Any]:
        """Load compliance configuration."""
        try:
            with open('config/environments/compliance.json', 'r') as f:
                config = json.load(f)
                return config.get(self.environment, {})
        except Exception as e:
            logger.warning(f"Could not load compliance config: {e}")
            return {}
    
    def log_audit_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Log an audit event."""
        logger.info(f"Logging audit event: {event_data.get('event_type')} for user {event_data.get('user_id')}")
        
        try:
            # Invoke audit event logger
            payload = {
                'user_id': event_data.get('user_id', 'unknown'),
                'organization_id': event_data.get('organization_id', 'unknown'),
                'event_type': event_data.get('event_type', 'unknown'),
                'action': event_data.get('action', 'unknown'),
                'resource_type': event_data.get('resource_type', 'unknown'),
                'resource_id': event_data.get('resource_id', 'unknown'),
                'result': event_data.get('result', 'unknown'),
                'source_ip': event_data.get('source_ip', 'unknown'),
                'user_agent': event_data.get('user_agent', 'unknown'),
                'session_id': event_data.get('session_id', ''),
                'request_id': event_data.get('request_id', ''),
                'details': event_data.get('details', {}),
            }
            
            response = self.lambda_client.invoke(
                FunctionName=self.audit_event_logger_function,
                Payload=json.dumps(payload)
            )
            
            result = json.loads(response['Payload'].read())
            
            if result['statusCode'] == 200:
                logger.info("Audit event logged successfully")
                return json.loads(result['body'])
            else:
                logger.error(f"Failed to log audit event: {result['body']}")
                return {'error': json.loads(result['body'])['error']}
                
        except Exception as e:
            logger.error(f"Audit event logging failed: {str(e)}")
            return {'error': str(e)}
    
    def send_bulk_audit_events(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Send multiple audit events to Kinesis stream."""
        logger.info(f"Sending {len(events)} audit events to stream")
        
        try:
            success_count = 0
            failed_count = 0
            
            for event in events:
                try:
                    # Add event metadata
                    event_record = {
                        'event_id': str(uuid.uuid4()),
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                        **event
                    }
                    
                    # Send to Kinesis
                    response = self.kinesis.put_record(
                        StreamName=self.audit_stream_name,
                        Data=json.dumps(event_record),
                        PartitionKey=event.get('organization_id', 'unknown')
                    )
                    
                    success_count += 1
                    logger.debug(f"Sent event to Kinesis: {response['SequenceNumber']}")
                    
                except Exception as e:
                    logger.error(f"Failed to send event: {str(e)}")
                    failed_count += 1
            
            return {
                'message': 'Bulk audit events processed',
                'total_events': len(events),
                'success_count': success_count,
                'failed_count': failed_count
            }
            
        except Exception as e:
            logger.error(f"Bulk audit event sending failed: {str(e)}")
            return {'error': str(e)}
    
    def check_compliance_violations(self, organization_id: str = None) -> Dict[str, Any]:
        """Check for compliance violations."""
        logger.info(f"Checking compliance violations for organization: {organization_id or 'all'}")
        
        try:
            payload = {
                'action': 'monitor',
                'organization_id': organization_id
            }
            
            response = self.lambda_client.invoke(
                FunctionName=self.compliance_monitor_function,
                Payload=json.dumps(payload)
            )
            
            result = json.loads(response['Payload'].read())
            
            if result['statusCode'] == 200:
                return json.loads(result['body'])
            else:
                return {'error': json.loads(result['body'])['error']}
                
        except Exception as e:
            logger.error(f"Compliance violation check failed: {str(e)}")
            return {'error': str(e)}
    
    def get_compliance_dashboard(self, organization_id: str = None) -> Dict[str, Any]:
        """Get compliance dashboard data."""
        logger.info(f"Getting compliance dashboard for organization: {organization_id or 'all'}")
        
        try:
            payload = {
                'action': 'dashboard',
                'organization_id': organization_id
            }
            
            response = self.lambda_client.invoke(
                FunctionName=self.compliance_monitor_function,
                Payload=json.dumps(payload)
            )
            
            result = json.loads(response['Payload'].read())
            
            if result['statusCode'] == 200:
                return json.loads(result['body'])
            else:
                return {'error': json.loads(result['body'])['error']}
                
        except Exception as e:
            logger.error(f"Compliance dashboard retrieval failed: {str(e)}")
            return {'error': str(e)}
    
    def generate_compliance_report(self, report_config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a compliance report."""
        logger.info(f"Generating compliance report for organization: {report_config.get('organization_id', 'all')}")
        
        try:
            payload = {
                'action': 'generate_report',
                'report_config': report_config
            }
            
            response = self.lambda_client.invoke(
                FunctionName=self.compliance_reporter_function,
                Payload=json.dumps(payload)
            )
            
            result = json.loads(response['Payload'].read())
            
            if result['statusCode'] == 200:
                logger.info("Compliance report generated successfully")
                return json.loads(result['body'])
            else:
                logger.error(f"Failed to generate compliance report: {result['body']}")
                return {'error': json.loads(result['body'])['error']}
                
        except Exception as e:
            logger.error(f"Compliance report generation failed: {str(e)}")
            return {'error': str(e)}
    
    def get_compliance_violations(self, organization_id: str = None, 
                                 severity: str = None, 
                                 start_date: str = None, 
                                 end_date: str = None) -> Dict[str, Any]:
        """Get compliance violations with filtering."""
        logger.info(f"Getting compliance violations with filters")
        
        try:
            if not start_date:
                start_date = (datetime.now() - timedelta(days=30)).date().isoformat()
            if not end_date:
                end_date = datetime.now().date().isoformat()
            
            # Query violations table
            query_params = {
                'TableName': self.compliance_violations_table,
                'FilterExpression': '#timestamp BETWEEN :start_date AND :end_date',
                'ExpressionAttributeNames': {'#timestamp': 'timestamp'},
                'ExpressionAttributeValues': {
                    ':start_date': {'S': start_date},
                    ':end_date': {'S': end_date}
                }
            }
            
            # Add organization filter if specified
            if organization_id:
                query_params['IndexName'] = 'OrganizationIndex'
                query_params['KeyConditionExpression'] = 'organizationId = :org_id AND #timestamp BETWEEN :start_date AND :end_date'
                query_params['ExpressionAttributeValues'][':org_id'] = {'S': organization_id}
                response = self.dynamodb.query(**query_params)
            else:
                response = self.dynamodb.scan(**query_params)
            
            # Process violations
            violations = []
            for item in response['Items']:
                violation = {
                    'violation_id': item['violationId']['S'],
                    'timestamp': item['timestamp']['S'],
                    'framework': item.get('framework', {}).get('S', 'unknown'),
                    'rule_id': item.get('ruleId', {}).get('S', 'unknown'),
                    'severity': item.get('severity', {}).get('S', 'unknown'),
                    'title': item.get('title', {}).get('S', 'unknown'),
                    'description': item.get('description', {}).get('S', 'unknown'),
                    'organization_id': item.get('organizationId', {}).get('S', 'unknown'),
                    'status': item.get('status', {}).get('S', 'unknown'),
                }
                
                # Apply severity filter
                if not severity or violation['severity'] == severity:
                    violations.append(violation)
            
            # Sort by timestamp (newest first)
            violations.sort(key=lambda x: x['timestamp'], reverse=True)
            
            return {
                'violations': violations,
                'total_count': len(violations),
                'filters': {
                    'organization_id': organization_id,
                    'severity': severity,
                    'start_date': start_date,
                    'end_date': end_date
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get compliance violations: {str(e)}")
            return {'error': str(e)}
    
    def create_data_subject_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a data subject request (GDPR)."""
        logger.info(f"Creating data subject request for user: {request_data.get('user_id')}")
        
        try:
            payload = {
                'action': 'create_request',
                'request_data': request_data
            }
            
            response = self.lambda_client.invoke(
                FunctionName=self.privacy_controls_function,
                Payload=json.dumps(payload)
            )
            
            result = json.loads(response['Payload'].read())
            
            if result['statusCode'] == 200:
                return json.loads(result['body'])
            else:
                return {'error': json.loads(result['body'])['error']}
                
        except Exception as e:
            logger.error(f"Data subject request creation failed: {str(e)}")
            return {'error': str(e)}
    
    def process_data_subject_request(self, request_id: str) -> Dict[str, Any]:
        """Process a data subject request."""
        logger.info(f"Processing data subject request: {request_id}")
        
        try:
            payload = {
                'action': 'process_request',
                'request_id': request_id
            }
            
            response = self.lambda_client.invoke(
                FunctionName=self.privacy_controls_function,
                Payload=json.dumps(payload)
            )
            
            result = json.loads(response['Payload'].read())
            
            if result['statusCode'] == 200:
                return json.loads(result['body'])
            else:
                return {'error': json.loads(result['body'])['error']}
                
        except Exception as e:
            logger.error(f"Data subject request processing failed: {str(e)}")
            return {'error': str(e)}
    
    def get_data_subject_requests(self, user_id: str) -> Dict[str, Any]:
        """Get data subject requests for a user."""
        logger.info(f"Getting data subject requests for user: {user_id}")
        
        try:
            payload = {
                'action': 'get_requests',
                'user_id': user_id
            }
            
            response = self.lambda_client.invoke(
                FunctionName=self.privacy_controls_function,
                Payload=json.dumps(payload)
            )
            
            result = json.loads(response['Payload'].read())
            
            if result['statusCode'] == 200:
                return json.loads(result['body'])
            else:
                return {'error': json.loads(result['body'])['error']}
                
        except Exception as e:
            logger.error(f"Data subject requests retrieval failed: {str(e)}")
            return {'error': str(e)}
    
    def run_compliance_workflow(self, workflow_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the compliance workflow."""
        logger.info("Running compliance workflow")
        
        try:
            if not self.compliance_workflow_arn:
                return {'error': 'Compliance workflow not configured'}
            
            response = self.stepfunctions.start_execution(
                stateMachineArn=self.compliance_workflow_arn,
                input=json.dumps(workflow_input)
            )
            
            execution_arn = response['executionArn']
            logger.info(f"Compliance workflow started: {execution_arn}")
            
            return {
                'message': 'Compliance workflow started',
                'execution_arn': execution_arn,
                'start_date': response['startDate'].isoformat()
            }
            
        except Exception as e:
            logger.error(f"Compliance workflow execution failed: {str(e)}")
            return {'error': str(e)}
    
    def query_audit_logs(self, query_params: Dict[str, Any]) -> Dict[str, Any]:
        """Query audit logs using Athena."""
        logger.info("Querying audit logs")
        
        try:
            # Construct Athena query
            database = f'autospec_ai_audit_{self.environment}'
            table = 'audit_logs'
            
            # Build WHERE clause
            where_conditions = []
            
            if 'organization_id' in query_params:
                where_conditions.append(f"organization_id = '{query_params['organization_id']}'")
            
            if 'event_type' in query_params:
                where_conditions.append(f"event_type = '{query_params['event_type']}'")
            
            if 'start_date' in query_params:
                where_conditions.append(f"timestamp >= timestamp '{query_params['start_date']}'")
            
            if 'end_date' in query_params:
                where_conditions.append(f"timestamp <= timestamp '{query_params['end_date']}'")
            
            where_clause = ' AND '.join(where_conditions) if where_conditions else '1=1'
            
            query = f"""
            SELECT *
            FROM {database}.{table}
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT {query_params.get('limit', 1000)}
            """
            
            # Execute Athena query
            query_execution_id = self._execute_athena_query(query)
            
            if query_execution_id:
                # Wait for query completion and get results
                results = self._get_athena_results(query_execution_id)
                return {
                    'query_execution_id': query_execution_id,
                    'results': results,
                    'query': query
                }
            else:
                return {'error': 'Failed to execute Athena query'}
                
        except Exception as e:
            logger.error(f"Audit log query failed: {str(e)}")
            return {'error': str(e)}
    
    def _execute_athena_query(self, query: str) -> Optional[str]:
        """Execute Athena query and return execution ID."""
        try:
            response = self.athena.start_query_execution(
                QueryString=query,
                ResultConfiguration={
                    'OutputLocation': f's3://{self.audit_logs_bucket}/athena-results/'
                }
            )
            return response['QueryExecutionId']
        except Exception as e:
            logger.error(f"Athena query execution failed: {str(e)}")
            return None
    
    def _get_athena_results(self, query_execution_id: str, max_wait_time: int = 60) -> List[Dict[str, Any]]:
        """Get Athena query results."""
        try:
            # Wait for query completion
            start_time = time.time()
            while time.time() - start_time < max_wait_time:
                response = self.athena.get_query_execution(
                    QueryExecutionId=query_execution_id
                )
                
                status = response['QueryExecution']['Status']['State']
                
                if status == 'SUCCEEDED':
                    break
                elif status in ['FAILED', 'CANCELLED']:
                    logger.error(f"Athena query failed: {response['QueryExecution']['Status']}")
                    return []
                
                time.sleep(2)
            
            # Get query results
            results = []
            paginator = self.athena.get_paginator('get_query_results')
            
            for page in paginator.paginate(QueryExecutionId=query_execution_id):
                for row in page['ResultSet']['Rows'][1:]:  # Skip header row
                    row_data = {}
                    for i, col in enumerate(page['ResultSet']['ResultSetMetadata']['ColumnInfo']):
                        col_name = col['Name']
                        col_value = row['Data'][i].get('VarCharValue', '')
                        row_data[col_name] = col_value
                    results.append(row_data)
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to get Athena results: {str(e)}")
            return []
    
    def export_compliance_data(self, export_config: Dict[str, Any]) -> Dict[str, Any]:
        """Export compliance data for external analysis."""
        logger.info("Exporting compliance data")
        
        try:
            export_type = export_config.get('type', 'violations')
            format_type = export_config.get('format', 'csv')
            organization_id = export_config.get('organization_id')
            
            if export_type == 'violations':
                data = self.get_compliance_violations(organization_id)
                if 'error' in data:
                    return data
                export_data = data['violations']
            elif export_type == 'audit_summary':
                data = self.get_compliance_dashboard(organization_id)
                if 'error' in data:
                    return data
                export_data = [data]  # Single record summary
            else:
                return {'error': f'Unknown export type: {export_type}'}
            
            # Generate export file
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{export_type}_{timestamp}.{format_type}"
            
            if format_type == 'csv':
                file_content = self._generate_csv_export(export_data)
                content_type = 'text/csv'
            elif format_type == 'json':
                file_content = json.dumps(export_data, indent=2)
                content_type = 'application/json'
            else:
                return {'error': f'Unsupported format: {format_type}'}
            
            # Upload to S3
            s3_key = f"exports/{export_type}/{filename}"
            self.s3.put_object(
                Bucket=self.compliance_reports_bucket,
                Key=s3_key,
                Body=file_content,
                ContentType=content_type
            )
            
            return {
                'message': 'Compliance data exported successfully',
                'export_file': filename,
                's3_location': f's3://{self.compliance_reports_bucket}/{s3_key}',
                'record_count': len(export_data)
            }
            
        except Exception as e:
            logger.error(f"Compliance data export failed: {str(e)}")
            return {'error': str(e)}
    
    def _generate_csv_export(self, data: List[Dict[str, Any]]) -> str:
        """Generate CSV export from data."""
        if not data:
            return ""
        
        output = io.StringIO()
        fieldnames = data[0].keys()
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
        return output.getvalue()
    
    def validate_compliance_setup(self) -> Dict[str, Any]:
        """Validate that compliance infrastructure is properly configured."""
        logger.info("Validating compliance setup")
        
        try:
            validation_results = {
                'overall_status': 'healthy',
                'components': {},
                'issues': []
            }
            
            # Check Lambda functions
            functions_to_check = [
                self.audit_event_logger_function,
                self.compliance_monitor_function,
                self.compliance_reporter_function,
                self.privacy_controls_function
            ]
            
            for function_name in functions_to_check:
                try:
                    response = self.lambda_client.get_function(FunctionName=function_name)
                    validation_results['components'][function_name] = 'healthy'
                except Exception as e:
                    validation_results['components'][function_name] = 'error'
                    validation_results['issues'].append(f"Function {function_name} not accessible: {str(e)}")
            
            # Check Kinesis stream
            try:
                response = self.kinesis.describe_stream(StreamName=self.audit_stream_name)
                if response['StreamDescription']['StreamStatus'] == 'ACTIVE':
                    validation_results['components']['audit_stream'] = 'healthy'
                else:
                    validation_results['components']['audit_stream'] = 'warning'
                    validation_results['issues'].append(f"Audit stream status: {response['StreamDescription']['StreamStatus']}")
            except Exception as e:
                validation_results['components']['audit_stream'] = 'error'
                validation_results['issues'].append(f"Audit stream not accessible: {str(e)}")
            
            # Check S3 buckets
            buckets_to_check = [self.audit_logs_bucket, self.compliance_reports_bucket]
            
            for bucket_name in buckets_to_check:
                try:
                    self.s3.head_bucket(Bucket=bucket_name)
                    validation_results['components'][bucket_name] = 'healthy'
                except Exception as e:
                    validation_results['components'][bucket_name] = 'error'
                    validation_results['issues'].append(f"Bucket {bucket_name} not accessible: {str(e)}")
            
            # Check DynamoDB tables
            tables_to_check = [
                self.compliance_violations_table,
                self.compliance_reports_table,
                self.data_subject_requests_table
            ]
            
            for table_name in tables_to_check:
                try:
                    response = self.dynamodb.describe_table(TableName=table_name)
                    if response['Table']['TableStatus'] == 'ACTIVE':
                        validation_results['components'][table_name] = 'healthy'
                    else:
                        validation_results['components'][table_name] = 'warning'
                        validation_results['issues'].append(f"Table {table_name} status: {response['Table']['TableStatus']}")
                except Exception as e:
                    validation_results['components'][table_name] = 'error'
                    validation_results['issues'].append(f"Table {table_name} not accessible: {str(e)}")
            
            # Determine overall status
            if any(status == 'error' for status in validation_results['components'].values()):
                validation_results['overall_status'] = 'error'
            elif any(status == 'warning' for status in validation_results['components'].values()):
                validation_results['overall_status'] = 'warning'
            
            return validation_results
            
        except Exception as e:
            logger.error(f"Compliance setup validation failed: {str(e)}")
            return {'error': str(e)}

def main():
    parser = argparse.ArgumentParser(description='AutoSpec.AI Compliance Management')
    parser.add_argument('--environment', required=True, choices=['dev', 'staging', 'prod'],
                       help='Environment to manage')
    parser.add_argument('--action', required=True,
                       choices=['log-event', 'bulk-events', 'check-violations', 'dashboard',
                               'generate-report', 'get-violations', 'create-dsr', 'process-dsr',
                               'get-dsr', 'query-logs', 'export-data', 'validate-setup'],
                       help='Action to perform')
    parser.add_argument('--organization-id', help='Organization ID for filtering')
    parser.add_argument('--user-id', help='User ID for operations')
    parser.add_argument('--config-file', help='JSON configuration file')
    parser.add_argument('--severity', choices=['critical', 'high', 'medium', 'low'],
                       help='Violation severity filter')
    parser.add_argument('--start-date', help='Start date for filtering (YYYY-MM-DD)')
    parser.add_argument('--end-date', help='End date for filtering (YYYY-MM-DD)')
    parser.add_argument('--export-type', choices=['violations', 'audit_summary'],
                       help='Type of data to export')
    parser.add_argument('--format', choices=['csv', 'json'], default='json',
                       help='Output format')
    parser.add_argument('--output', help='Output file for results')
    parser.add_argument('--request-id', help='Data subject request ID')
    
    args = parser.parse_args()
    
    compliance_manager = ComplianceManager(args.environment)
    
    try:
        if args.action == 'log-event':
            if not args.config_file:
                print("Error: --config-file required for log-event")
                return 1
            
            with open(args.config_file, 'r') as f:
                event_data = json.load(f)
            
            result = compliance_manager.log_audit_event(event_data)
            print(json.dumps(result, indent=2))
            
        elif args.action == 'bulk-events':
            if not args.config_file:
                print("Error: --config-file required for bulk-events")
                return 1
            
            with open(args.config_file, 'r') as f:
                events_data = json.load(f)
            
            result = compliance_manager.send_bulk_audit_events(events_data.get('events', []))
            print(json.dumps(result, indent=2))
            
        elif args.action == 'check-violations':
            result = compliance_manager.check_compliance_violations(args.organization_id)
            print(json.dumps(result, indent=2))
            
        elif args.action == 'dashboard':
            result = compliance_manager.get_compliance_dashboard(args.organization_id)
            print(json.dumps(result, indent=2))
            
        elif args.action == 'generate-report':
            if not args.config_file:
                print("Error: --config-file required for generate-report")
                return 1
            
            with open(args.config_file, 'r') as f:
                report_config = json.load(f)
            
            result = compliance_manager.generate_compliance_report(report_config)
            print(json.dumps(result, indent=2))
            
        elif args.action == 'get-violations':
            result = compliance_manager.get_compliance_violations(
                args.organization_id, args.severity, args.start_date, args.end_date
            )
            print(json.dumps(result, indent=2))
            
        elif args.action == 'create-dsr':
            if not args.config_file:
                print("Error: --config-file required for create-dsr")
                return 1
            
            with open(args.config_file, 'r') as f:
                request_data = json.load(f)
            
            result = compliance_manager.create_data_subject_request(request_data)
            print(json.dumps(result, indent=2))
            
        elif args.action == 'process-dsr':
            if not args.request_id:
                print("Error: --request-id required for process-dsr")
                return 1
            
            result = compliance_manager.process_data_subject_request(args.request_id)
            print(json.dumps(result, indent=2))
            
        elif args.action == 'get-dsr':
            if not args.user_id:
                print("Error: --user-id required for get-dsr")
                return 1
            
            result = compliance_manager.get_data_subject_requests(args.user_id)
            print(json.dumps(result, indent=2))
            
        elif args.action == 'query-logs':
            if not args.config_file:
                print("Error: --config-file required for query-logs")
                return 1
            
            with open(args.config_file, 'r') as f:
                query_params = json.load(f)
            
            result = compliance_manager.query_audit_logs(query_params)
            print(json.dumps(result, indent=2))
            
        elif args.action == 'export-data':
            export_config = {
                'type': args.export_type or 'violations',
                'format': args.format,
                'organization_id': args.organization_id
            }
            
            result = compliance_manager.export_compliance_data(export_config)
            
            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(result, f, indent=2)
                logger.info(f"Export result saved to {args.output}")
            else:
                print(json.dumps(result, indent=2))
                
        elif args.action == 'validate-setup':
            result = compliance_manager.validate_compliance_setup()
            print(json.dumps(result, indent=2))
    
    except Exception as e:
        logger.error(f"Compliance management failed: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())