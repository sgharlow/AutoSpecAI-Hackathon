#!/usr/bin/env python3
"""
AutoSpec.AI Collaboration and Workflow Management

Comprehensive collaboration management, real-time coordination, 
workflow automation, and team productivity optimization.

Usage:
    python3 collaboration-manager.py --environment prod --action start-session
    python3 collaboration-manager.py --environment staging --action manage-workflows
    python3 collaboration-manager.py --environment dev --action analytics-report
"""

import argparse
import boto3
import json
import time
import websocket
import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import logging
import uuid
import asyncio
import concurrent.futures

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class CollaborationSession:
    """Collaboration session structure."""
    session_id: str
    document_id: str
    user_id: str
    status: str
    started_at: str
    last_activity: str

@dataclass
class Comment:
    """Comment structure."""
    comment_id: str
    document_id: str
    user_id: str
    content: str
    thread_id: str
    timestamp: str
    status: str

@dataclass
class WorkflowInstance:
    """Workflow instance structure."""
    instance_id: str
    document_id: str
    workflow_id: str
    organization_id: str
    status: str
    current_step: int
    created_at: str

@dataclass
class DocumentVersion:
    """Document version structure."""
    document_id: str
    version_number: int
    user_id: str
    content_hash: str
    timestamp: str
    change_description: str

class CollaborationManager:
    """Manages collaboration and workflow operations for AutoSpec.AI."""
    
    def __init__(self, environment: str):
        self.environment = environment
        
        # AWS clients
        self.lambda_client = boto3.client('lambda')
        self.dynamodb = boto3.client('dynamodb')
        self.s3 = boto3.client('s3')
        self.stepfunctions = boto3.client('stepfunctions')
        self.apigateway = boto3.client('apigatewayv2')
        self.cloudwatch = boto3.client('cloudwatch')
        self.sns = boto3.client('sns')
        
        # Function names
        self.connection_handler_function = f'AutoSpecAI-ConnectionHandler-{environment}'
        self.workflow_engine_function = f'AutoSpecAI-WorkflowEngine-{environment}'
        self.presence_manager_function = f'AutoSpecAI-PresenceManager-{environment}'
        self.comment_manager_function = f'AutoSpecAI-CommentManager-{environment}'
        self.version_control_function = f'AutoSpecAI-VersionControl-{environment}'
        self.collaboration_analytics_function = f'AutoSpecAI-CollaborationAnalytics-{environment}'
        
        # Resource names
        self.websocket_api_endpoint = self._get_websocket_endpoint()
        self.approval_workflow_arn = self._get_workflow_arn()
        self.collaboration_notifications_topic = self._get_notifications_topic()
        
        # Table names
        self.collaboration_sessions_table = f'autospec-ai-collaboration-sessions-{environment}'
        self.presence_table = f'autospec-ai-presence-{environment}'
        self.comments_table = f'autospec-ai-comments-{environment}'
        self.versions_table = f'autospec-ai-document-versions-{environment}'
        self.workflow_definitions_table = f'autospec-ai-workflow-definitions-{environment}'
        self.workflow_instances_table = f'autospec-ai-workflow-instances-{environment}'
        self.approval_tasks_table = f'autospec-ai-approval-tasks-{environment}'
        
        # Load configuration
        self.config = self._load_config()
        
        # WebSocket connection pool
        self.ws_connections = {}
        self.ws_lock = threading.Lock()
    
    def _get_websocket_endpoint(self) -> str:
        """Get WebSocket API endpoint."""
        try:
            # This would typically be retrieved from CloudFormation exports or parameter store
            return f'wss://collaboration-api-{self.environment}.autospec.ai'
        except Exception:
            return ''
    
    def _get_workflow_arn(self) -> str:
        """Get approval workflow ARN."""
        try:
            return f'arn:aws:states:us-east-1:123456789012:stateMachine:AutoSpecAI-ApprovalWorkflow-{self.environment}'
        except Exception:
            return ''
    
    def _get_notifications_topic(self) -> str:
        """Get collaboration notifications topic ARN."""
        try:
            return f'arn:aws:sns:us-east-1:123456789012:AutoSpecAI-CollaborationNotifications-{self.environment}'
        except Exception:
            return ''
    
    def _load_config(self) -> Dict[str, Any]:
        """Load collaboration configuration."""
        try:
            with open('config/environments/collaboration.json', 'r') as f:
                config = json.load(f)
                return config.get(self.environment, {})
        except Exception as e:
            logger.warning(f"Could not load collaboration config: {e}")
            return {}
    
    def start_collaboration_session(self, session_config: Dict[str, Any]) -> Dict[str, Any]:
        """Start a new collaboration session."""
        logger.info(f"Starting collaboration session for document: {session_config.get('document_id')}")
        
        try:
            session_id = str(uuid.uuid4())
            
            session_data = {
                'documentId': {'S': session_config['document_id']},
                'sessionId': {'S': session_id},
                'userId': {'S': session_config['user_id']},
                'status': {'S': 'active'},
                'startedAt': {'S': datetime.now(timezone.utc).isoformat()},
                'lastActivity': {'S': datetime.now(timezone.utc).isoformat()},
                'sessionType': {'S': session_config.get('session_type', 'edit')},
                'ttl': {'N': str(int((datetime.now(timezone.utc) + timedelta(hours=24)).timestamp()))}
            }
            
            if 'metadata' in session_config:
                session_data['metadata'] = {'S': json.dumps(session_config['metadata'])}
            
            self.dynamodb.put_item(
                TableName=self.collaboration_sessions_table,
                Item=session_data
            )
            
            # Initialize user presence
            self.update_user_presence(
                session_config['user_id'],
                session_config['document_id'],
                'online'
            )
            
            return {
                'session_id': session_id,
                'websocket_endpoint': self.websocket_api_endpoint,
                'status': 'started',
                'started_at': session_data['startedAt']['S']
            }
            
        except Exception as e:
            logger.error(f"Failed to start collaboration session: {str(e)}")
            return {'error': str(e)}
    
    def end_collaboration_session(self, session_id: str, user_id: str) -> Dict[str, Any]:
        """End a collaboration session."""
        logger.info(f"Ending collaboration session: {session_id}")
        
        try:
            # Update session status
            self.dynamodb.update_item(
                TableName=self.collaboration_sessions_table,
                Key={
                    'documentId': {'S': session_id},  # This would need the actual document_id
                    'sessionId': {'S': session_id}
                },
                UpdateExpression='SET #status = :status, endedAt = :timestamp',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':status': {'S': 'ended'},
                    ':timestamp': {'S': datetime.now(timezone.utc).isoformat()}
                }
            )
            
            return {'status': 'ended', 'session_id': session_id}
            
        except Exception as e:
            logger.error(f"Failed to end collaboration session: {str(e)}")
            return {'error': str(e)}
    
    def update_user_presence(self, user_id: str, document_id: str, status: str, 
                           cursor_position: Dict[str, Any] = None) -> Dict[str, Any]:
        """Update user presence status."""
        logger.info(f"Updating presence for user {user_id} in document {document_id}: {status}")
        
        try:
            payload = {
                'action': 'update_presence',
                'user_id': user_id,
                'document_id': document_id,
                'status': status
            }
            
            if cursor_position:
                payload['cursor_position'] = cursor_position
            
            response = self.lambda_client.invoke(
                FunctionName=self.presence_manager_function,
                Payload=json.dumps(payload)
            )
            
            result = json.loads(response['Payload'].read())
            
            if result['statusCode'] == 200:
                return json.loads(result['body'])
            else:
                return {'error': json.loads(result['body'])['error']}
                
        except Exception as e:
            logger.error(f"Failed to update user presence: {str(e)}")
            return {'error': str(e)}
    
    def get_document_presence(self, document_id: str) -> Dict[str, Any]:
        """Get active users in a document."""
        logger.info(f"Getting presence for document: {document_id}")
        
        try:
            payload = {
                'action': 'get_document_presence',
                'document_id': document_id
            }
            
            response = self.lambda_client.invoke(
                FunctionName=self.presence_manager_function,
                Payload=json.dumps(payload)
            )
            
            result = json.loads(response['Payload'].read())
            
            if result['statusCode'] == 200:
                return json.loads(result['body'])
            else:
                return {'error': json.loads(result['body'])['error']}
                
        except Exception as e:
            logger.error(f"Failed to get document presence: {str(e)}")
            return {'error': str(e)}
    
    def create_comment(self, comment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new comment or annotation."""
        logger.info(f"Creating comment in document: {comment_data.get('document_id')}")
        
        try:
            payload = {
                'action': 'create_comment',
                **comment_data
            }
            
            response = self.lambda_client.invoke(
                FunctionName=self.comment_manager_function,
                Payload=json.dumps(payload)
            )
            
            result = json.loads(response['Payload'].read())
            
            if result['statusCode'] == 200:
                return json.loads(result['body'])
            else:
                return {'error': json.loads(result['body'])['error']}
                
        except Exception as e:
            logger.error(f"Failed to create comment: {str(e)}")
            return {'error': str(e)}
    
    def reply_to_comment(self, reply_data: Dict[str, Any]) -> Dict[str, Any]:
        """Reply to an existing comment."""
        logger.info(f"Creating reply to comment: {reply_data.get('thread_id')}")
        
        try:
            payload = {
                'action': 'reply_to_comment',
                **reply_data
            }
            
            response = self.lambda_client.invoke(
                FunctionName=self.comment_manager_function,
                Payload=json.dumps(payload)
            )
            
            result = json.loads(response['Payload'].read())
            
            if result['statusCode'] == 200:
                return json.loads(result['body'])
            else:
                return {'error': json.loads(result['body'])['error']}
                
        except Exception as e:
            logger.error(f"Failed to create reply: {str(e)}")
            return {'error': str(e)}
    
    def get_document_comments(self, document_id: str, include_resolved: bool = False) -> Dict[str, Any]:
        """Get all comments for a document."""
        logger.info(f"Getting comments for document: {document_id}")
        
        try:
            payload = {
                'action': 'get_document_comments',
                'document_id': document_id,
                'include_resolved': include_resolved
            }
            
            response = self.lambda_client.invoke(
                FunctionName=self.comment_manager_function,
                Payload=json.dumps(payload)
            )
            
            result = json.loads(response['Payload'].read())
            
            if result['statusCode'] == 200:
                return json.loads(result['body'])
            else:
                return {'error': json.loads(result['body'])['error']}
                
        except Exception as e:
            logger.error(f"Failed to get document comments: {str(e)}")
            return {'error': str(e)}
    
    def resolve_comment(self, document_id: str, comment_id: str, user_id: str) -> Dict[str, Any]:
        """Resolve a comment thread."""
        logger.info(f"Resolving comment: {comment_id}")
        
        try:
            payload = {
                'action': 'resolve_comment',
                'document_id': document_id,
                'comment_id': comment_id,
                'user_id': user_id
            }
            
            response = self.lambda_client.invoke(
                FunctionName=self.comment_manager_function,
                Payload=json.dumps(payload)
            )
            
            result = json.loads(response['Payload'].read())
            
            if result['statusCode'] == 200:
                return json.loads(result['body'])
            else:
                return {'error': json.loads(result['body'])['error']}
                
        except Exception as e:
            logger.error(f"Failed to resolve comment: {str(e)}")
            return {'error': str(e)}
    
    def create_document_version(self, version_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new document version."""
        logger.info(f"Creating version for document: {version_data.get('document_id')}")
        
        try:
            payload = {
                'action': 'create_version',
                **version_data
            }
            
            response = self.lambda_client.invoke(
                FunctionName=self.version_control_function,
                Payload=json.dumps(payload)
            )
            
            result = json.loads(response['Payload'].read())
            
            if result['statusCode'] == 200:
                return json.loads(result['body'])
            else:
                return {'error': json.loads(result['body'])['error']}
                
        except Exception as e:
            logger.error(f"Failed to create document version: {str(e)}")
            return {'error': str(e)}
    
    def get_document_versions(self, document_id: str, limit: int = 20) -> Dict[str, Any]:
        """Get version history for a document."""
        logger.info(f"Getting versions for document: {document_id}")
        
        try:
            payload = {
                'action': 'get_versions',
                'document_id': document_id,
                'limit': limit
            }
            
            response = self.lambda_client.invoke(
                FunctionName=self.version_control_function,
                Payload=json.dumps(payload)
            )
            
            result = json.loads(response['Payload'].read())
            
            if result['statusCode'] == 200:
                return json.loads(result['body'])
            else:
                return {'error': json.loads(result['body'])['error']}
                
        except Exception as e:
            logger.error(f"Failed to get document versions: {str(e)}")
            return {'error': str(e)}
    
    def get_version_diff(self, document_id: str, version1: int, version2: int) -> Dict[str, Any]:
        """Get differences between two document versions."""
        logger.info(f"Getting diff between versions {version1} and {version2} for document: {document_id}")
        
        try:
            payload = {
                'action': 'get_version_diff',
                'document_id': document_id,
                'version1': version1,
                'version2': version2
            }
            
            response = self.lambda_client.invoke(
                FunctionName=self.version_control_function,
                Payload=json.dumps(payload)
            )
            
            result = json.loads(response['Payload'].read())
            
            if result['statusCode'] == 200:
                return json.loads(result['body'])
            else:
                return {'error': json.loads(result['body'])['error']}
                
        except Exception as e:
            logger.error(f"Failed to get version diff: {str(e)}")
            return {'error': str(e)}
    
    def restore_version(self, document_id: str, version_number: int, user_id: str) -> Dict[str, Any]:
        """Restore a document to a specific version."""
        logger.info(f"Restoring document {document_id} to version {version_number}")
        
        try:
            payload = {
                'action': 'restore_version',
                'document_id': document_id,
                'version_number': version_number,
                'user_id': user_id
            }
            
            response = self.lambda_client.invoke(
                FunctionName=self.version_control_function,
                Payload=json.dumps(payload)
            )
            
            result = json.loads(response['Payload'].read())
            
            if result['statusCode'] == 200:
                return json.loads(result['body'])
            else:
                return {'error': json.loads(result['body'])['error']}
                
        except Exception as e:
            logger.error(f"Failed to restore version: {str(e)}")
            return {'error': str(e)}
    
    def start_approval_workflow(self, workflow_config: Dict[str, Any]) -> Dict[str, Any]:
        """Start a document approval workflow."""
        logger.info(f"Starting approval workflow for document: {workflow_config.get('document_id')}")
        
        try:
            if not self.approval_workflow_arn:
                return {'error': 'Approval workflow not configured'}
            
            response = self.stepfunctions.start_execution(
                stateMachineArn=self.approval_workflow_arn,
                input=json.dumps(workflow_config)
            )
            
            execution_arn = response['executionArn']
            logger.info(f"Approval workflow started: {execution_arn}")
            
            return {
                'execution_arn': execution_arn,
                'start_date': response['startDate'].isoformat(),
                'status': 'started'
            }
            
        except Exception as e:
            logger.error(f"Failed to start approval workflow: {str(e)}")
            return {'error': str(e)}
    
    def get_workflow_status(self, execution_arn: str) -> Dict[str, Any]:
        """Get the status of an approval workflow."""
        logger.info(f"Getting workflow status: {execution_arn}")
        
        try:
            response = self.stepfunctions.describe_execution(
                executionArn=execution_arn
            )
            
            return {
                'execution_arn': execution_arn,
                'status': response['status'],
                'start_date': response['startDate'].isoformat(),
                'stop_date': response.get('stopDate', {}).isoformat() if response.get('stopDate') else None,
                'input': json.loads(response['input']) if response.get('input') else None,
                'output': json.loads(response['output']) if response.get('output') else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get workflow status: {str(e)}")
            return {'error': str(e)}
    
    def approve_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Approve a workflow task."""
        logger.info(f"Approving task: {task_data.get('task_id')}")
        
        try:
            payload = {
                'action': 'approve_task',
                **task_data
            }
            
            response = self.lambda_client.invoke(
                FunctionName=self.workflow_engine_function,
                Payload=json.dumps(payload)
            )
            
            result = json.loads(response['Payload'].read())
            
            if result['statusCode'] == 200:
                return json.loads(result['body'])
            else:
                return {'error': json.loads(result['body'])['error']}
                
        except Exception as e:
            logger.error(f"Failed to approve task: {str(e)}")
            return {'error': str(e)}
    
    def reject_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Reject a workflow task."""
        logger.info(f"Rejecting task: {task_data.get('task_id')}")
        
        try:
            payload = {
                'action': 'reject_task',
                **task_data
            }
            
            response = self.lambda_client.invoke(
                FunctionName=self.workflow_engine_function,
                Payload=json.dumps(payload)
            )
            
            result = json.loads(response['Payload'].read())
            
            if result['statusCode'] == 200:
                return json.loads(result['body'])
            else:
                return {'error': json.loads(result['body'])['error']}
                
        except Exception as e:
            logger.error(f"Failed to reject task: {str(e)}")
            return {'error': str(e)}
    
    def get_user_tasks(self, user_id: str) -> Dict[str, Any]:
        """Get pending approval tasks for a user."""
        logger.info(f"Getting tasks for user: {user_id}")
        
        try:
            payload = {
                'action': 'get_user_tasks',
                'user_id': user_id
            }
            
            response = self.lambda_client.invoke(
                FunctionName=self.workflow_engine_function,
                Payload=json.dumps(payload)
            )
            
            result = json.loads(response['Payload'].read())
            
            if result['statusCode'] == 200:
                return json.loads(result['body'])
            else:
                return {'error': json.loads(result['body'])['error']}
                
        except Exception as e:
            logger.error(f"Failed to get user tasks: {str(e)}")
            return {'error': str(e)}
    
    def connect_websocket(self, user_id: str, document_id: str) -> Optional[websocket.WebSocket]:
        """Connect to WebSocket for real-time collaboration."""
        logger.info(f"Connecting WebSocket for user {user_id} in document {document_id}")
        
        try:
            if not self.websocket_api_endpoint:
                logger.error("WebSocket endpoint not configured")
                return None
            
            ws_url = f"{self.websocket_api_endpoint}?userId={user_id}&documentId={document_id}"
            
            def on_message(ws, message):
                self._handle_websocket_message(ws, message, user_id, document_id)
            
            def on_error(ws, error):
                logger.error(f"WebSocket error: {error}")
            
            def on_close(ws, close_status_code, close_msg):
                logger.info(f"WebSocket connection closed for user {user_id}")
                with self.ws_lock:
                    if user_id in self.ws_connections:
                        del self.ws_connections[user_id]
            
            def on_open(ws):
                logger.info(f"WebSocket connection opened for user {user_id}")
                with self.ws_lock:
                    self.ws_connections[user_id] = ws
            
            ws = websocket.WebSocketApp(
                ws_url,
                on_open=on_open,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close
            )
            
            # Start WebSocket in a separate thread
            def run_websocket():
                ws.run_forever()
            
            ws_thread = threading.Thread(target=run_websocket)
            ws_thread.daemon = True
            ws_thread.start()
            
            return ws
            
        except Exception as e:
            logger.error(f"Failed to connect WebSocket: {str(e)}")
            return None
    
    def _handle_websocket_message(self, ws, message: str, user_id: str, document_id: str):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(message)
            message_type = data.get('type')
            
            if message_type == 'presence_update':
                logger.info(f"Received presence update from user {user_id}")
            elif message_type == 'document_change':
                logger.info(f"Received document change from user {user_id}")
                # Handle real-time document changes
            elif message_type == 'cursor_update':
                logger.debug(f"Received cursor update from user {user_id}")
                # Handle cursor position updates
            
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {str(e)}")
    
    def send_websocket_message(self, user_id: str, message: Dict[str, Any]) -> bool:
        """Send message to a specific user via WebSocket."""
        try:
            with self.ws_lock:
                if user_id in self.ws_connections:
                    ws = self.ws_connections[user_id]
                    ws.send(json.dumps(message))
                    return True
                else:
                    logger.warning(f"No WebSocket connection found for user {user_id}")
                    return False
        except Exception as e:
            logger.error(f"Failed to send WebSocket message: {str(e)}")
            return False
    
    def broadcast_to_document(self, document_id: str, message: Dict[str, Any], 
                            exclude_user: str = None) -> int:
        """Broadcast message to all users in a document."""
        logger.info(f"Broadcasting message to document {document_id}")
        
        try:
            # Get active users in document
            presence_data = self.get_document_presence(document_id)
            if 'error' in presence_data:
                logger.error(f"Failed to get document presence: {presence_data['error']}")
                return 0
            
            sent_count = 0
            for user_presence in presence_data.get('active_users', []):
                user_id = user_presence['user_id']
                if user_id != exclude_user:
                    if self.send_websocket_message(user_id, message):
                        sent_count += 1
            
            return sent_count
            
        except Exception as e:
            logger.error(f"Failed to broadcast to document: {str(e)}")
            return 0
    
    def get_collaboration_analytics(self, analytics_config: Dict[str, Any]) -> Dict[str, Any]:
        """Get collaboration analytics and metrics."""
        logger.info("Getting collaboration analytics")
        
        try:
            start_date = analytics_config.get('start_date', 
                (datetime.now() - timedelta(days=7)).date().isoformat())
            end_date = analytics_config.get('end_date', 
                datetime.now().date().isoformat())
            
            # Get collaboration metrics from CloudWatch
            metrics = self._get_collaboration_metrics(start_date, end_date)
            
            # Get session statistics
            session_stats = self._get_session_statistics(start_date, end_date)
            
            # Get comment statistics
            comment_stats = self._get_comment_statistics(start_date, end_date)
            
            # Get workflow statistics
            workflow_stats = self._get_workflow_statistics(start_date, end_date)
            
            return {
                'period': {
                    'start_date': start_date,
                    'end_date': end_date
                },
                'metrics': metrics,
                'session_statistics': session_stats,
                'comment_statistics': comment_stats,
                'workflow_statistics': workflow_stats,
                'generated_at': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get collaboration analytics: {str(e)}")
            return {'error': str(e)}
    
    def _get_collaboration_metrics(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Get collaboration metrics from CloudWatch."""
        try:
            end_time = datetime.fromisoformat(end_date + 'T23:59:59')
            start_time = datetime.fromisoformat(start_date + 'T00:00:00')
            
            response = self.cloudwatch.get_metric_statistics(
                Namespace='AutoSpecAI/Collaboration',
                MetricName='ActiveCollaborationSessions',
                Dimensions=[],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,  # 1 hour
                Statistics=['Average', 'Maximum']
            )
            
            return {
                'active_sessions': response['Datapoints'],
                'peak_concurrent_users': max([dp['Maximum'] for dp in response['Datapoints']] or [0])
            }
            
        except Exception as e:
            logger.error(f"Failed to get CloudWatch metrics: {str(e)}")
            return {}
    
    def _get_session_statistics(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Get collaboration session statistics."""
        try:
            # Query DynamoDB for session data
            response = self.dynamodb.scan(
                TableName=self.collaboration_sessions_table,
                FilterExpression='startedAt BETWEEN :start_date AND :end_date',
                ExpressionAttributeValues={
                    ':start_date': {'S': start_date},
                    ':end_date': {'S': end_date}
                }
            )
            
            sessions = response['Items']
            total_sessions = len(sessions)
            
            # Calculate average session duration
            total_duration = 0
            completed_sessions = 0
            
            for session in sessions:
                if 'endedAt' in session:
                    start_time = datetime.fromisoformat(session['startedAt']['S'])
                    end_time = datetime.fromisoformat(session['endedAt']['S'])
                    duration = (end_time - start_time).total_seconds()
                    total_duration += duration
                    completed_sessions += 1
            
            avg_duration = total_duration / completed_sessions if completed_sessions > 0 else 0
            
            return {
                'total_sessions': total_sessions,
                'completed_sessions': completed_sessions,
                'active_sessions': total_sessions - completed_sessions,
                'average_duration_seconds': avg_duration
            }
            
        except Exception as e:
            logger.error(f"Failed to get session statistics: {str(e)}")
            return {}
    
    def _get_comment_statistics(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Get comment statistics."""
        try:
            # Query DynamoDB for comment data
            response = self.dynamodb.scan(
                TableName=self.comments_table,
                FilterExpression='#timestamp BETWEEN :start_date AND :end_date',
                ExpressionAttributeNames={'#timestamp': 'timestamp'},
                ExpressionAttributeValues={
                    ':start_date': {'S': start_date},
                    ':end_date': {'S': end_date}
                }
            )
            
            comments = response['Items']
            total_comments = len(comments)
            
            # Count by type
            comment_count = 0
            reply_count = 0
            resolved_count = 0
            
            for comment in comments:
                comment_type = comment.get('type', {}).get('S', 'comment')
                status = comment.get('status', {}).get('S', 'active')
                
                if comment_type == 'comment':
                    comment_count += 1
                elif comment_type == 'reply':
                    reply_count += 1
                
                if status == 'resolved':
                    resolved_count += 1
            
            return {
                'total_comments': total_comments,
                'comments': comment_count,
                'replies': reply_count,
                'resolved_comments': resolved_count,
                'resolution_rate': resolved_count / total_comments if total_comments > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Failed to get comment statistics: {str(e)}")
            return {}
    
    def _get_workflow_statistics(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Get workflow statistics."""
        try:
            # Query DynamoDB for workflow data
            response = self.dynamodb.scan(
                TableName=self.workflow_instances_table,
                FilterExpression='createdAt BETWEEN :start_date AND :end_date',
                ExpressionAttributeValues={
                    ':start_date': {'S': start_date},
                    ':end_date': {'S': end_date}
                }
            )
            
            workflows = response['Items']
            total_workflows = len(workflows)
            
            # Count by status
            status_counts = {}
            for workflow in workflows:
                status = workflow.get('status', {}).get('S', 'unknown')
                status_counts[status] = status_counts.get(status, 0) + 1
            
            return {
                'total_workflows': total_workflows,
                'status_breakdown': status_counts,
                'completion_rate': status_counts.get('approved', 0) / total_workflows if total_workflows > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Failed to get workflow statistics: {str(e)}")
            return {}
    
    def cleanup_expired_sessions(self) -> Dict[str, Any]:
        """Clean up expired collaboration sessions."""
        logger.info("Cleaning up expired collaboration sessions")
        
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
            
            response = self.dynamodb.scan(
                TableName=self.collaboration_sessions_table,
                FilterExpression='lastActivity < :cutoff AND #status = :status',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':cutoff': {'S': cutoff_time.isoformat()},
                    ':status': {'S': 'active'}
                }
            )
            
            expired_sessions = response['Items']
            cleanup_count = 0
            
            for session in expired_sessions:
                # Update session to expired
                self.dynamodb.update_item(
                    TableName=self.collaboration_sessions_table,
                    Key={
                        'documentId': session['documentId'],
                        'sessionId': session['sessionId']
                    },
                    UpdateExpression='SET #status = :status, expiredAt = :timestamp',
                    ExpressionAttributeNames={'#status': 'status'},
                    ExpressionAttributeValues={
                        ':status': {'S': 'expired'},
                        ':timestamp': {'S': datetime.now(timezone.utc).isoformat()}
                    }
                )
                cleanup_count += 1
            
            return {
                'message': 'Expired sessions cleaned up',
                'cleanup_count': cleanup_count
            }
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {str(e)}")
            return {'error': str(e)}
    
    def validate_collaboration_setup(self) -> Dict[str, Any]:
        """Validate that collaboration infrastructure is properly configured."""
        logger.info("Validating collaboration setup")
        
        try:
            validation_results = {
                'overall_status': 'healthy',
                'components': {},
                'issues': []
            }
            
            # Check Lambda functions
            functions_to_check = [
                self.connection_handler_function,
                self.workflow_engine_function,
                self.presence_manager_function,
                self.comment_manager_function,
                self.version_control_function
            ]
            
            for function_name in functions_to_check:
                try:
                    response = self.lambda_client.get_function(FunctionName=function_name)
                    validation_results['components'][function_name] = 'healthy'
                except Exception as e:
                    validation_results['components'][function_name] = 'error'
                    validation_results['issues'].append(f"Function {function_name} not accessible: {str(e)}")
            
            # Check DynamoDB tables
            tables_to_check = [
                self.collaboration_sessions_table,
                self.presence_table,
                self.comments_table,
                self.versions_table,
                self.workflow_instances_table,
                self.approval_tasks_table
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
            
            # Check WebSocket API
            if self.websocket_api_endpoint:
                validation_results['components']['websocket_api'] = 'healthy'
            else:
                validation_results['components']['websocket_api'] = 'warning'
                validation_results['issues'].append("WebSocket API endpoint not configured")
            
            # Check Step Functions workflow
            if self.approval_workflow_arn:
                try:
                    response = self.stepfunctions.describe_state_machine(
                        stateMachineArn=self.approval_workflow_arn
                    )
                    if response['status'] == 'ACTIVE':
                        validation_results['components']['approval_workflow'] = 'healthy'
                    else:
                        validation_results['components']['approval_workflow'] = 'warning'
                        validation_results['issues'].append(f"Approval workflow status: {response['status']}")
                except Exception as e:
                    validation_results['components']['approval_workflow'] = 'error'
                    validation_results['issues'].append(f"Approval workflow not accessible: {str(e)}")
            else:
                validation_results['components']['approval_workflow'] = 'warning'
                validation_results['issues'].append("Approval workflow ARN not configured")
            
            # Determine overall status
            if any(status == 'error' for status in validation_results['components'].values()):
                validation_results['overall_status'] = 'error'
            elif any(status == 'warning' for status in validation_results['components'].values()):
                validation_results['overall_status'] = 'warning'
            
            return validation_results
            
        except Exception as e:
            logger.error(f"Collaboration setup validation failed: {str(e)}")
            return {'error': str(e)}

def main():
    parser = argparse.ArgumentParser(description='AutoSpec.AI Collaboration Management')
    parser.add_argument('--environment', required=True, choices=['dev', 'staging', 'prod'],
                       help='Environment to manage')
    parser.add_argument('--action', required=True,
                       choices=['start-session', 'end-session', 'update-presence', 'get-presence',
                               'create-comment', 'reply-comment', 'get-comments', 'resolve-comment',
                               'create-version', 'get-versions', 'get-diff', 'restore-version',
                               'start-workflow', 'get-workflow-status', 'approve-task', 'reject-task',
                               'get-user-tasks', 'connect-websocket', 'analytics-report',
                               'cleanup-sessions', 'validate-setup'],
                       help='Action to perform')
    parser.add_argument('--document-id', help='Document ID for operations')
    parser.add_argument('--user-id', help='User ID for operations')
    parser.add_argument('--config-file', help='JSON configuration file')
    parser.add_argument('--session-id', help='Collaboration session ID')
    parser.add_argument('--comment-id', help='Comment ID for operations')
    parser.add_argument('--thread-id', help='Comment thread ID')
    parser.add_argument('--version1', type=int, help='First version for diff')
    parser.add_argument('--version2', type=int, help='Second version for diff')
    parser.add_argument('--version-number', type=int, help='Version number to restore')
    parser.add_argument('--execution-arn', help='Step Functions execution ARN')
    parser.add_argument('--task-id', help='Workflow task ID')
    parser.add_argument('--output', help='Output file for results')
    
    args = parser.parse_args()
    
    collaboration_manager = CollaborationManager(args.environment)
    
    try:
        if args.action == 'start-session':
            if not args.config_file:
                print("Error: --config-file required for start-session")
                return 1
            
            with open(args.config_file, 'r') as f:
                session_config = json.load(f)
            
            result = collaboration_manager.start_collaboration_session(session_config)
            print(json.dumps(result, indent=2))
            
        elif args.action == 'end-session':
            if not args.session_id or not args.user_id:
                print("Error: --session-id and --user-id required for end-session")
                return 1
            
            result = collaboration_manager.end_collaboration_session(args.session_id, args.user_id)
            print(json.dumps(result, indent=2))
            
        elif args.action == 'update-presence':
            if not args.user_id or not args.document_id:
                print("Error: --user-id and --document-id required for update-presence")
                return 1
            
            result = collaboration_manager.update_user_presence(args.user_id, args.document_id, 'online')
            print(json.dumps(result, indent=2))
            
        elif args.action == 'get-presence':
            if not args.document_id:
                print("Error: --document-id required for get-presence")
                return 1
            
            result = collaboration_manager.get_document_presence(args.document_id)
            print(json.dumps(result, indent=2))
            
        elif args.action == 'create-comment':
            if not args.config_file:
                print("Error: --config-file required for create-comment")
                return 1
            
            with open(args.config_file, 'r') as f:
                comment_data = json.load(f)
            
            result = collaboration_manager.create_comment(comment_data)
            print(json.dumps(result, indent=2))
            
        elif args.action == 'reply-comment':
            if not args.config_file:
                print("Error: --config-file required for reply-comment")
                return 1
            
            with open(args.config_file, 'r') as f:
                reply_data = json.load(f)
            
            result = collaboration_manager.reply_to_comment(reply_data)
            print(json.dumps(result, indent=2))
            
        elif args.action == 'get-comments':
            if not args.document_id:
                print("Error: --document-id required for get-comments")
                return 1
            
            result = collaboration_manager.get_document_comments(args.document_id)
            print(json.dumps(result, indent=2))
            
        elif args.action == 'resolve-comment':
            if not args.document_id or not args.comment_id or not args.user_id:
                print("Error: --document-id, --comment-id, and --user-id required for resolve-comment")
                return 1
            
            result = collaboration_manager.resolve_comment(args.document_id, args.comment_id, args.user_id)
            print(json.dumps(result, indent=2))
            
        elif args.action == 'create-version':
            if not args.config_file:
                print("Error: --config-file required for create-version")
                return 1
            
            with open(args.config_file, 'r') as f:
                version_data = json.load(f)
            
            result = collaboration_manager.create_document_version(version_data)
            print(json.dumps(result, indent=2))
            
        elif args.action == 'get-versions':
            if not args.document_id:
                print("Error: --document-id required for get-versions")
                return 1
            
            result = collaboration_manager.get_document_versions(args.document_id)
            print(json.dumps(result, indent=2))
            
        elif args.action == 'get-diff':
            if not args.document_id or args.version1 is None or args.version2 is None:
                print("Error: --document-id, --version1, and --version2 required for get-diff")
                return 1
            
            result = collaboration_manager.get_version_diff(args.document_id, args.version1, args.version2)
            print(json.dumps(result, indent=2))
            
        elif args.action == 'restore-version':
            if not args.document_id or args.version_number is None or not args.user_id:
                print("Error: --document-id, --version-number, and --user-id required for restore-version")
                return 1
            
            result = collaboration_manager.restore_version(args.document_id, args.version_number, args.user_id)
            print(json.dumps(result, indent=2))
            
        elif args.action == 'start-workflow':
            if not args.config_file:
                print("Error: --config-file required for start-workflow")
                return 1
            
            with open(args.config_file, 'r') as f:
                workflow_config = json.load(f)
            
            result = collaboration_manager.start_approval_workflow(workflow_config)
            print(json.dumps(result, indent=2))
            
        elif args.action == 'get-workflow-status':
            if not args.execution_arn:
                print("Error: --execution-arn required for get-workflow-status")
                return 1
            
            result = collaboration_manager.get_workflow_status(args.execution_arn)
            print(json.dumps(result, indent=2))
            
        elif args.action == 'approve-task':
            if not args.config_file:
                print("Error: --config-file required for approve-task")
                return 1
            
            with open(args.config_file, 'r') as f:
                task_data = json.load(f)
            
            result = collaboration_manager.approve_task(task_data)
            print(json.dumps(result, indent=2))
            
        elif args.action == 'reject-task':
            if not args.config_file:
                print("Error: --config-file required for reject-task")
                return 1
            
            with open(args.config_file, 'r') as f:
                task_data = json.load(f)
            
            result = collaboration_manager.reject_task(task_data)
            print(json.dumps(result, indent=2))
            
        elif args.action == 'get-user-tasks':
            if not args.user_id:
                print("Error: --user-id required for get-user-tasks")
                return 1
            
            result = collaboration_manager.get_user_tasks(args.user_id)
            print(json.dumps(result, indent=2))
            
        elif args.action == 'connect-websocket':
            if not args.user_id or not args.document_id:
                print("Error: --user-id and --document-id required for connect-websocket")
                return 1
            
            ws = collaboration_manager.connect_websocket(args.user_id, args.document_id)
            if ws:
                print(f"WebSocket connected for user {args.user_id}")
                # Keep connection alive for testing
                try:
                    time.sleep(30)  # Keep connection for 30 seconds
                except KeyboardInterrupt:
                    print("WebSocket connection closed")
            else:
                print("Failed to connect WebSocket")
                return 1
                
        elif args.action == 'analytics-report':
            analytics_config = {}
            if args.config_file:
                with open(args.config_file, 'r') as f:
                    analytics_config = json.load(f)
            
            result = collaboration_manager.get_collaboration_analytics(analytics_config)
            
            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(result, f, indent=2)
                logger.info(f"Analytics report saved to {args.output}")
            else:
                print(json.dumps(result, indent=2))
                
        elif args.action == 'cleanup-sessions':
            result = collaboration_manager.cleanup_expired_sessions()
            print(json.dumps(result, indent=2))
            
        elif args.action == 'validate-setup':
            result = collaboration_manager.validate_collaboration_setup()
            print(json.dumps(result, indent=2))
    
    except Exception as e:
        logger.error(f"Collaboration management failed: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())