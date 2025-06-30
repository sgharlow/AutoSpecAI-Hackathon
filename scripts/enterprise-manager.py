#!/usr/bin/env python3
"""
AutoSpec.AI Enterprise Integration Management

Comprehensive enterprise integration management for SSO, LDAP,
third-party connectors, and user provisioning.

Usage:
    python3 enterprise-manager.py --environment prod --action configure-sso
    python3 enterprise-manager.py --environment staging --action sync-ldap
    python3 enterprise-manager.py --environment dev --action provision-user
"""

import argparse
import boto3
import json
import time
import hashlib
import hmac
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import logging
import uuid
import base64

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class Organization:
    """Organization configuration."""
    organization_id: str
    name: str
    domain: str
    sso_enabled: bool
    ldap_enabled: bool
    integrations: List[str]
    user_count: int
    status: str

@dataclass
class EnterpriseUser:
    """Enterprise user structure."""
    user_id: str
    organization_id: str
    email: str
    first_name: str
    last_name: str
    department: str
    role: str
    permissions: List[str]
    status: str
    last_login: str

@dataclass
class SSOConfiguration:
    """SSO configuration structure."""
    organization_id: str
    provider_type: str  # 'SAML', 'OAuth_Google', etc.
    provider_name: str
    configuration: Dict[str, Any]
    status: str
    created_at: str

class EnterpriseManager:
    """Manages enterprise integrations for AutoSpec.AI."""
    
    def __init__(self, environment: str):
        self.environment = environment
        
        # AWS clients
        self.lambda_client = boto3.client('lambda')
        self.dynamodb = boto3.client('dynamodb')
        self.cognito_idp = boto3.client('cognito-idp')
        self.secretsmanager = boto3.client('secretsmanager')
        self.events = boto3.client('events')
        
        # Function names
        self.sso_configuration_function = f'AutoSpecAI-SSOConfiguration-{environment}'
        self.ldap_connector_function = f'AutoSpecAI-LDAPConnector-{environment}'
        self.third_party_connector_function = f'AutoSpecAI-ThirdPartyConnector-{environment}'
        self.user_provisioning_function = f'AutoSpecAI-UserProvisioning-{environment}'
        self.audit_logging_function = f'AutoSpecAI-AuditLogging-{environment}'
        
        # Table names
        self.organizations_table = f'autospec-ai-organizations-{environment}'
        self.enterprise_users_table = f'autospec-ai-enterprise-users-{environment}'
        self.integration_configs_table = f'autospec-ai-integration-configs-{environment}'
        self.api_configs_table = f'autospec-ai-api-configs-{environment}'
        self.audit_logs_table = f'autospec-ai-audit-logs-{environment}'
        
        # User pool
        self.user_pool_id = self._get_user_pool_id()
        
        # Load configuration
        self.config = self._load_config()
    
    def _get_user_pool_id(self) -> str:
        """Get enterprise user pool ID."""
        try:
            # This would typically be retrieved from CloudFormation outputs
            return f'us-east-1_EXAMPLE{self.environment.upper()}'
        except Exception:
            return ''
    
    def _load_config(self) -> Dict[str, Any]:
        """Load enterprise configuration."""
        try:
            with open('config/environments/enterprise.json', 'r') as f:
                config = json.load(f)
                return config.get(self.environment, {})
        except Exception as e:
            logger.warning(f"Could not load enterprise config: {e}")
            return {}
    
    def create_organization(self, org_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new enterprise organization."""
        logger.info(f"Creating organization: {org_config.get('name')}")
        
        try:
            organization_id = org_config.get('organizationId') or str(uuid.uuid4())
            
            # Store organization in DynamoDB
            org_item = {
                'organizationId': {'S': organization_id},
                'name': {'S': org_config['name']},
                'domain': {'S': org_config['domain']},
                'ssoEnabled': {'BOOL': org_config.get('ssoEnabled', False)},
                'ldapEnabled': {'BOOL': org_config.get('ldapEnabled', False)},
                'integrations': {'SS': org_config.get('integrations', [])},
                'userCount': {'N': '0'},
                'status': {'S': 'active'},
                'createdAt': {'S': datetime.now(timezone.utc).isoformat()},
                'updatedAt': {'S': datetime.now(timezone.utc).isoformat()},
                'settings': {'S': json.dumps(org_config.get('settings', {}))},
                'billing': {'S': json.dumps(org_config.get('billing', {}))},
            }
            
            self.dynamodb.put_item(TableName=self.organizations_table, Item=org_item)
            
            # Log audit event
            self._log_audit_event({
                'organizationId': organization_id,
                'userId': 'system',
                'action': 'organization_created',
                'resource': f'organization/{organization_id}',
                'result': 'success',
                'details': {'name': org_config['name'], 'domain': org_config['domain']}
            })
            
            logger.info(f"Organization created successfully: {organization_id}")
            return {
                'message': 'Organization created successfully',
                'organizationId': organization_id,
                'name': org_config['name']
            }
            
        except Exception as e:
            logger.error(f"Organization creation failed: {str(e)}")
            return {'error': str(e)}
    
    def configure_sso(self, organization_id: str, sso_config: Dict[str, Any]) -> Dict[str, Any]:
        """Configure SSO for an organization."""
        logger.info(f"Configuring SSO for organization: {organization_id}")
        
        try:
            sso_type = sso_config['type']  # 'SAML' or 'OAuth'
            
            if sso_type == 'SAML':
                payload = {
                    'action': 'configure_saml',
                    'organizationId': organization_id,
                    'samlConfig': sso_config['config']
                }
            elif sso_type.startswith('OAuth'):
                payload = {
                    'action': 'configure_oauth',
                    'organizationId': organization_id,
                    'oauthConfig': sso_config['config']
                }
            else:
                return {'error': f'Unsupported SSO type: {sso_type}'}
            
            # Invoke SSO configuration function
            response = self.lambda_client.invoke(
                FunctionName=self.sso_configuration_function,
                Payload=json.dumps(payload)
            )
            
            result = json.loads(response['Payload'].read())
            
            if result['statusCode'] == 200:
                # Log audit event
                self._log_audit_event({
                    'organizationId': organization_id,
                    'userId': 'admin',
                    'action': 'sso_configured',
                    'resource': f'sso/{sso_type}',
                    'result': 'success',
                    'details': {'sso_type': sso_type}
                })
                
                logger.info("SSO configured successfully")
                return json.loads(result['body'])
            else:
                logger.error(f"SSO configuration failed: {result['body']}")
                return {'error': json.loads(result['body'])['error']}
                
        except Exception as e:
            logger.error(f"SSO configuration failed: {str(e)}")
            return {'error': str(e)}
    
    def test_sso_connection(self, organization_id: str, integration_type: str) -> Dict[str, Any]:
        """Test SSO connection for an organization."""
        logger.info(f"Testing SSO connection for {organization_id}: {integration_type}")
        
        try:
            payload = {
                'action': 'test_connection',
                'organizationId': organization_id,
                'integrationType': integration_type
            }
            
            response = self.lambda_client.invoke(
                FunctionName=self.sso_configuration_function,
                Payload=json.dumps(payload)
            )
            
            result = json.loads(response['Payload'].read())
            
            if result['statusCode'] == 200:
                return json.loads(result['body'])
            else:
                return {'error': json.loads(result['body'])['error']}
                
        except Exception as e:
            logger.error(f"SSO connection test failed: {str(e)}")
            return {'error': str(e)}
    
    def configure_ldap(self, organization_id: str, ldap_config: Dict[str, Any]) -> Dict[str, Any]:
        """Configure LDAP for an organization."""
        logger.info(f"Configuring LDAP for organization: {organization_id}")
        
        try:
            # Store LDAP credentials in Secrets Manager
            secret_name = f"autospec-ai-ldap-config-{self.environment}/{organization_id}"
            
            secret_value = {
                'server': ldap_config['server'],
                'port': ldap_config.get('port', 389),
                'username': ldap_config['username'],
                'password': ldap_config['password'],
                'base_dn': ldap_config['base_dn'],
                'user_search_filter': ldap_config.get('user_search_filter', '(objectClass=user)'),
                'group_search_filter': ldap_config.get('group_search_filter', '(objectClass=group)'),
                'use_ssl': ldap_config.get('use_ssl', True),
            }
            
            try:
                self.secretsmanager.create_secret(
                    Name=secret_name,
                    Description=f'LDAP configuration for organization {organization_id}',
                    SecretString=json.dumps(secret_value)
                )
            except self.secretsmanager.exceptions.ResourceExistsException:
                # Update existing secret
                self.secretsmanager.update_secret(
                    SecretId=secret_name,
                    SecretString=json.dumps(secret_value)
                )
            
            # Store configuration reference
            config_item = {
                'organizationId': {'S': organization_id},
                'integrationType': {'S': 'LDAP'},
                'configuration': {'S': json.dumps({
                    'secret_arn': secret_name,
                    'server': ldap_config['server'],
                    'base_dn': ldap_config['base_dn'],
                    'sync_schedule': ldap_config.get('sync_schedule', '0 */6 * * *'),  # Every 6 hours
                })},
                'status': {'S': 'active'},
                'createdAt': {'S': datetime.now(timezone.utc).isoformat()},
                'updatedAt': {'S': datetime.now(timezone.utc).isoformat()},
            }
            
            self.dynamodb.put_item(TableName=self.integration_configs_table, Item=config_item)
            
            # Log audit event
            self._log_audit_event({
                'organizationId': organization_id,
                'userId': 'admin',
                'action': 'ldap_configured',
                'resource': f'ldap/{organization_id}',
                'result': 'success',
                'details': {'server': ldap_config['server'], 'base_dn': ldap_config['base_dn']}
            })
            
            logger.info("LDAP configured successfully")
            return {
                'message': 'LDAP configured successfully',
                'organizationId': organization_id,
                'server': ldap_config['server']
            }
            
        except Exception as e:
            logger.error(f"LDAP configuration failed: {str(e)}")
            return {'error': str(e)}
    
    def sync_ldap_users(self, organization_id: str, force_sync: bool = False) -> Dict[str, Any]:
        """Synchronize users from LDAP."""
        logger.info(f"Synchronizing LDAP users for organization: {organization_id}")
        
        try:
            # Get LDAP configuration
            response = self.dynamodb.get_item(
                TableName=self.integration_configs_table,
                Key={
                    'organizationId': {'S': organization_id},
                    'integrationType': {'S': 'LDAP'}
                }
            )
            
            if 'Item' not in response:
                return {'error': 'LDAP not configured for this organization'}
            
            ldap_config = json.loads(response['Item']['configuration']['S'])
            
            # Invoke LDAP sync function
            payload = {
                'action': 'sync_users',
                'organizationId': organization_id,
                'ldapConfig': ldap_config,
                'forceSync': force_sync
            }
            
            response = self.lambda_client.invoke(
                FunctionName=self.ldap_connector_function,
                Payload=json.dumps(payload)
            )
            
            result = json.loads(response['Payload'].read())
            
            if result['statusCode'] == 200:
                # Log audit event
                sync_result = json.loads(result['body'])
                self._log_audit_event({
                    'organizationId': organization_id,
                    'userId': 'system',
                    'action': 'ldap_sync',
                    'resource': f'ldap/{organization_id}',
                    'result': 'success',
                    'details': {
                        'users_synced': sync_result.get('users_synced', 0),
                        'users_updated': sync_result.get('users_updated', 0),
                        'force_sync': force_sync
                    }
                })
                
                logger.info("LDAP sync completed successfully")
                return sync_result
            else:
                logger.error(f"LDAP sync failed: {result['body']}")
                return {'error': json.loads(result['body'])['error']}
                
        except Exception as e:
            logger.error(f"LDAP sync failed: {str(e)}")
            return {'error': str(e)}
    
    def configure_third_party_integration(self, organization_id: str, provider: str, 
                                        config: Dict[str, Any]) -> Dict[str, Any]:
        """Configure third-party integration."""
        logger.info(f"Configuring {provider} integration for organization: {organization_id}")
        
        try:
            # Invoke third-party connector function
            payload = {
                'action': 'configure',
                'organizationId': organization_id,
                'provider': provider,
                'config': config
            }
            
            response = self.lambda_client.invoke(
                FunctionName=self.third_party_connector_function,
                Payload=json.dumps(payload)
            )
            
            result = json.loads(response['Payload'].read())
            
            if result['statusCode'] == 200:
                # Log audit event
                self._log_audit_event({
                    'organizationId': organization_id,
                    'userId': 'admin',
                    'action': 'third_party_integration_configured',
                    'resource': f'integration/{provider}',
                    'result': 'success',
                    'details': {'provider': provider}
                })
                
                logger.info(f"{provider} integration configured successfully")
                return json.loads(result['body'])
            else:
                logger.error(f"{provider} integration failed: {result['body']}")
                return {'error': json.loads(result['body'])['error']}
                
        except Exception as e:
            logger.error(f"Third-party integration failed: {str(e)}")
            return {'error': str(e)}
    
    def send_third_party_notification(self, organization_id: str, provider: str, 
                                    notification_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send notification via third-party integration."""
        logger.info(f"Sending {provider} notification for organization: {organization_id}")
        
        try:
            payload = {
                'action': 'send_notification',
                'organizationId': organization_id,
                'provider': provider,
                'notification_data': notification_data
            }
            
            response = self.lambda_client.invoke(
                FunctionName=self.third_party_connector_function,
                Payload=json.dumps(payload)
            )
            
            result = json.loads(response['Payload'].read())
            
            if result['statusCode'] == 200:
                return json.loads(result['body'])
            else:
                return {'error': json.loads(result['body'])['error']}
                
        except Exception as e:
            logger.error(f"Third-party notification failed: {str(e)}")
            return {'error': str(e)}
    
    def provision_user(self, organization_id: str, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Provision a new enterprise user."""
        logger.info(f"Provisioning user: {user_data.get('email')} for organization: {organization_id}")
        
        try:
            payload = {
                'action': 'provision',
                'organizationId': organization_id,
                'userData': user_data
            }
            
            response = self.lambda_client.invoke(
                FunctionName=self.user_provisioning_function,
                Payload=json.dumps(payload)
            )
            
            result = json.loads(response['Payload'].read())
            
            if result['statusCode'] == 200:
                # Log audit event
                self._log_audit_event({
                    'organizationId': organization_id,
                    'userId': 'admin',
                    'action': 'user_provisioned',
                    'resource': f"user/{user_data.get('email')}",
                    'result': 'success',
                    'details': {
                        'email': user_data.get('email'),
                        'department': user_data.get('department'),
                        'role': user_data.get('role')
                    }
                })
                
                logger.info("User provisioned successfully")
                return json.loads(result['body'])
            else:
                logger.error(f"User provisioning failed: {result['body']}")
                return {'error': json.loads(result['body'])['error']}
                
        except Exception as e:
            logger.error(f"User provisioning failed: {str(e)}")
            return {'error': str(e)}
    
    def deprovision_user(self, email: str) -> Dict[str, Any]:
        """Deprovision an enterprise user."""
        logger.info(f"Deprovisioning user: {email}")
        
        try:
            payload = {
                'action': 'deprovision',
                'userData': {'email': email}
            }
            
            response = self.lambda_client.invoke(
                FunctionName=self.user_provisioning_function,
                Payload=json.dumps(payload)
            )
            
            result = json.loads(response['Payload'].read())
            
            if result['statusCode'] == 200:
                # Log audit event
                self._log_audit_event({
                    'organizationId': 'unknown',  # Would get from user record
                    'userId': 'admin',
                    'action': 'user_deprovisioned',
                    'resource': f"user/{email}",
                    'result': 'success',
                    'details': {'email': email}
                })
                
                logger.info("User deprovisioned successfully")
                return json.loads(result['body'])
            else:
                logger.error(f"User deprovisioning failed: {result['body']}")
                return {'error': json.loads(result['body'])['error']}
                
        except Exception as e:
            logger.error(f"User deprovisioning failed: {str(e)}")
            return {'error': str(e)}
    
    def get_organization_users(self, organization_id: str) -> Dict[str, Any]:
        """Get all users for an organization."""
        logger.info(f"Getting users for organization: {organization_id}")
        
        try:
            # Query enterprise users table
            response = self.dynamodb.query(
                TableName=self.enterprise_users_table,
                IndexName='OrganizationIndex',
                KeyConditionExpression='organizationId = :org_id',
                ExpressionAttributeValues={
                    ':org_id': {'S': organization_id}
                }
            )
            
            users = []
            for item in response['Items']:
                user = {
                    'userId': item['userId']['S'],
                    'organizationId': item['organizationId']['S'],
                    'firstName': item.get('firstName', {}).get('S', ''),
                    'lastName': item.get('lastName', {}).get('S', ''),
                    'department': item.get('department', {}).get('S', ''),
                    'role': item.get('role', {}).get('S', ''),
                    'status': item.get('status', {}).get('S', ''),
                    'createdAt': item.get('createdAt', {}).get('S', ''),
                    'lastLoginAt': item.get('lastLoginAt', {}).get('S', ''),
                }
                users.append(user)
            
            return {
                'organizationId': organization_id,
                'userCount': len(users),
                'users': users
            }
            
        except Exception as e:
            logger.error(f"Failed to get organization users: {str(e)}")
            return {'error': str(e)}
    
    def get_organization_integrations(self, organization_id: str) -> Dict[str, Any]:
        """Get all integrations for an organization."""
        logger.info(f"Getting integrations for organization: {organization_id}")
        
        try:
            # Query integration configs
            response = self.dynamodb.query(
                TableName=self.integration_configs_table,
                KeyConditionExpression='organizationId = :org_id',
                ExpressionAttributeValues={
                    ':org_id': {'S': organization_id}
                }
            )
            
            integrations = []
            for item in response['Items']:
                integration = {
                    'organizationId': item['organizationId']['S'],
                    'integrationType': item['integrationType']['S'],
                    'configuration': json.loads(item['configuration']['S']),
                    'status': item['status']['S'],
                    'createdAt': item['createdAt']['S'],
                    'updatedAt': item['updatedAt']['S'],
                }
                integrations.append(integration)
            
            # Query API configs
            api_response = self.dynamodb.query(
                TableName=self.api_configs_table,
                KeyConditionExpression='organizationId = :org_id',
                ExpressionAttributeValues={
                    ':org_id': {'S': organization_id}
                }
            )
            
            api_integrations = []
            for item in api_response['Items']:
                api_integration = {
                    'organizationId': item['organizationId']['S'],
                    'apiProvider': item['apiProvider']['S'],
                    'configuration': json.loads(item['configuration']['S']),
                    'status': item['status']['S'],
                    'createdAt': item['createdAt']['S'],
                    'updatedAt': item['updatedAt']['S'],
                }
                api_integrations.append(api_integration)
            
            return {
                'organizationId': organization_id,
                'ssoIntegrations': integrations,
                'apiIntegrations': api_integrations,
                'totalIntegrations': len(integrations) + len(api_integrations)
            }
            
        except Exception as e:
            logger.error(f"Failed to get organization integrations: {str(e)}")
            return {'error': str(e)}
    
    def generate_audit_report(self, organization_id: str, start_date: str = None, 
                            end_date: str = None) -> Dict[str, Any]:
        """Generate audit report for an organization."""
        logger.info(f"Generating audit report for organization: {organization_id}")
        
        try:
            if not start_date:
                start_date = (datetime.now() - timedelta(days=30)).date().isoformat()
            if not end_date:
                end_date = datetime.now().date().isoformat()
            
            # Query audit logs
            response = self.dynamodb.query(
                TableName=self.audit_logs_table,
                IndexName='OrganizationTimestampIndex',
                KeyConditionExpression='organizationId = :org_id AND #timestamp BETWEEN :start_date AND :end_date',
                ExpressionAttributeNames={'#timestamp': 'timestamp'},
                ExpressionAttributeValues={
                    ':org_id': {'S': organization_id},
                    ':start_date': {'S': start_date},
                    ':end_date': {'S': end_date}
                }
            )
            
            # Process audit logs
            audit_events = []
            action_counts = {}
            user_activity = {}
            
            for item in response['Items']:
                event = {
                    'logId': item['logId']['S'],
                    'timestamp': item['timestamp']['S'],
                    'userId': item['userId']['S'],
                    'action': item['action']['S'],
                    'resource': item['resource']['S'],
                    'result': item['result']['S'],
                    'details': json.loads(item['details']['S']),
                }
                audit_events.append(event)
                
                # Count actions
                action = event['action']
                action_counts[action] = action_counts.get(action, 0) + 1
                
                # Track user activity
                user_id = event['userId']
                if user_id not in user_activity:
                    user_activity[user_id] = {'total_actions': 0, 'actions': {}}
                user_activity[user_id]['total_actions'] += 1
                user_activity[user_id]['actions'][action] = user_activity[user_id]['actions'].get(action, 0) + 1
            
            return {
                'organizationId': organization_id,
                'reportPeriod': {'start': start_date, 'end': end_date},
                'summary': {
                    'totalEvents': len(audit_events),
                    'actionCounts': action_counts,
                    'activeUsers': len(user_activity),
                    'topActions': sorted(action_counts.items(), key=lambda x: x[1], reverse=True)[:10]
                },
                'userActivity': user_activity,
                'events': audit_events[-100:]  # Return last 100 events
            }
            
        except Exception as e:
            logger.error(f"Audit report generation failed: {str(e)}")
            return {'error': str(e)}
    
    def _log_audit_event(self, event_data: Dict[str, Any]):
        """Log an audit event."""
        try:
            # Add metadata
            event_data.update({
                'sourceIp': event_data.get('sourceIp', 'unknown'),
                'userAgent': event_data.get('userAgent', 'enterprise-manager'),
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            # Invoke audit logging function
            self.lambda_client.invoke(
                FunctionName=self.audit_logging_function,
                InvocationType='Event',  # Async
                Payload=json.dumps(event_data)
            )
            
        except Exception as e:
            logger.warning(f"Failed to log audit event: {str(e)}")
    
    def test_enterprise_system(self) -> Dict[str, Any]:
        """Test the enterprise integration system."""
        logger.info("Testing enterprise integration system")
        
        try:
            test_results = []
            
            # Test 1: Create test organization
            test_org_config = {
                'name': 'Test Organization',
                'domain': 'test.example.com',
                'ssoEnabled': True,
                'ldapEnabled': False,
                'integrations': ['slack'],
                'settings': {'test_mode': True}
            }
            
            org_result = self.create_organization(test_org_config)
            test_results.append({
                'test': 'create_organization',
                'success': 'error' not in org_result,
                'result': org_result
            })
            
            if 'error' not in org_result:
                test_org_id = org_result['organizationId']
                
                # Test 2: Configure Slack integration
                slack_config = {
                    'webhook_url': 'https://hooks.slack.com/test',
                    'channel': '#test-channel'
                }
                
                integration_result = self.configure_third_party_integration(
                    test_org_id, 'slack', slack_config
                )
                test_results.append({
                    'test': 'configure_slack_integration',
                    'success': 'error' not in integration_result,
                    'result': integration_result
                })
                
                # Test 3: Provision test user
                test_user = {
                    'email': 'testuser@test.example.com',
                    'firstName': 'Test',
                    'lastName': 'User',
                    'department': 'Engineering',
                    'role': 'Developer',
                    'permissions': ['read', 'write'],
                    'sendWelcomeEmail': False
                }
                
                user_result = self.provision_user(test_org_id, test_user)
                test_results.append({
                    'test': 'provision_user',
                    'success': 'error' not in user_result,
                    'result': user_result
                })
                
                # Test 4: Get organization data
                users_result = self.get_organization_users(test_org_id)
                test_results.append({
                    'test': 'get_organization_users',
                    'success': 'error' not in users_result,
                    'result': users_result
                })
                
                integrations_result = self.get_organization_integrations(test_org_id)
                test_results.append({
                    'test': 'get_organization_integrations',
                    'success': 'error' not in integrations_result,
                    'result': integrations_result
                })
            
            # Summary
            successful_tests = sum(1 for test in test_results if test['success'])
            total_tests = len(test_results)
            
            return {
                'message': 'Enterprise system test completed',
                'successful_tests': successful_tests,
                'total_tests': total_tests,
                'success_rate': f"{successful_tests/total_tests*100:.1f}%",
                'test_results': test_results
            }
            
        except Exception as e:
            logger.error(f"System test failed: {str(e)}")
            return {'error': str(e)}

def main():
    parser = argparse.ArgumentParser(description='AutoSpec.AI Enterprise Management')
    parser.add_argument('--environment', required=True, choices=['dev', 'staging', 'prod'],
                       help='Environment to manage')
    parser.add_argument('--action', required=True,
                       choices=['create-organization', 'configure-sso', 'test-sso',
                               'configure-ldap', 'sync-ldap', 'configure-integration',
                               'send-notification', 'provision-user', 'deprovision-user',
                               'get-users', 'get-integrations', 'audit-report', 'test-system'],
                       help='Action to perform')
    parser.add_argument('--organization-id', help='Organization ID')
    parser.add_argument('--config-file', help='JSON configuration file')
    parser.add_argument('--user-email', help='User email for operations')
    parser.add_argument('--provider', help='Integration provider (slack, jira, etc.)')
    parser.add_argument('--sso-type', help='SSO integration type')
    parser.add_argument('--output', help='Output file for reports')
    parser.add_argument('--start-date', help='Start date for reports (YYYY-MM-DD)')
    parser.add_argument('--end-date', help='End date for reports (YYYY-MM-DD)')
    parser.add_argument('--force', action='store_true', help='Force operation')
    
    args = parser.parse_args()
    
    enterprise_manager = EnterpriseManager(args.environment)
    
    try:
        if args.action == 'create-organization':
            if not args.config_file:
                print("Error: --config-file required for create-organization")
                return 1
            
            with open(args.config_file, 'r') as f:
                org_config = json.load(f)
            
            result = enterprise_manager.create_organization(org_config)
            print(json.dumps(result, indent=2))
            
        elif args.action == 'configure-sso':
            if not all([args.organization_id, args.config_file]):
                print("Error: --organization-id and --config-file required")
                return 1
            
            with open(args.config_file, 'r') as f:
                sso_config = json.load(f)
            
            result = enterprise_manager.configure_sso(args.organization_id, sso_config)
            print(json.dumps(result, indent=2))
            
        elif args.action == 'test-sso':
            if not all([args.organization_id, args.sso_type]):
                print("Error: --organization-id and --sso-type required")
                return 1
            
            result = enterprise_manager.test_sso_connection(args.organization_id, args.sso_type)
            print(json.dumps(result, indent=2))
            
        elif args.action == 'configure-ldap':
            if not all([args.organization_id, args.config_file]):
                print("Error: --organization-id and --config-file required")
                return 1
            
            with open(args.config_file, 'r') as f:
                ldap_config = json.load(f)
            
            result = enterprise_manager.configure_ldap(args.organization_id, ldap_config)
            print(json.dumps(result, indent=2))
            
        elif args.action == 'sync-ldap':
            if not args.organization_id:
                print("Error: --organization-id required")
                return 1
            
            result = enterprise_manager.sync_ldap_users(args.organization_id, args.force)
            print(json.dumps(result, indent=2))
            
        elif args.action == 'configure-integration':
            if not all([args.organization_id, args.provider, args.config_file]):
                print("Error: --organization-id, --provider, and --config-file required")
                return 1
            
            with open(args.config_file, 'r') as f:
                integration_config = json.load(f)
            
            result = enterprise_manager.configure_third_party_integration(
                args.organization_id, args.provider, integration_config
            )
            print(json.dumps(result, indent=2))
            
        elif args.action == 'send-notification':
            if not all([args.organization_id, args.provider, args.config_file]):
                print("Error: --organization-id, --provider, and --config-file required")
                return 1
            
            with open(args.config_file, 'r') as f:
                notification_data = json.load(f)
            
            result = enterprise_manager.send_third_party_notification(
                args.organization_id, args.provider, notification_data
            )
            print(json.dumps(result, indent=2))
            
        elif args.action == 'provision-user':
            if not all([args.organization_id, args.config_file]):
                print("Error: --organization-id and --config-file required")
                return 1
            
            with open(args.config_file, 'r') as f:
                user_data = json.load(f)
            
            result = enterprise_manager.provision_user(args.organization_id, user_data)
            print(json.dumps(result, indent=2))
            
        elif args.action == 'deprovision-user':
            if not args.user_email:
                print("Error: --user-email required")
                return 1
            
            result = enterprise_manager.deprovision_user(args.user_email)
            print(json.dumps(result, indent=2))
            
        elif args.action == 'get-users':
            if not args.organization_id:
                print("Error: --organization-id required")
                return 1
            
            result = enterprise_manager.get_organization_users(args.organization_id)
            print(json.dumps(result, indent=2))
            
        elif args.action == 'get-integrations':
            if not args.organization_id:
                print("Error: --organization-id required")
                return 1
            
            result = enterprise_manager.get_organization_integrations(args.organization_id)
            print(json.dumps(result, indent=2))
            
        elif args.action == 'audit-report':
            if not args.organization_id:
                print("Error: --organization-id required")
                return 1
            
            result = enterprise_manager.generate_audit_report(
                args.organization_id, args.start_date, args.end_date
            )
            
            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(result, f, indent=2)
                logger.info(f"Audit report saved to {args.output}")
            else:
                print(json.dumps(result, indent=2))
                
        elif args.action == 'test-system':
            result = enterprise_manager.test_enterprise_system()
            print(json.dumps(result, indent=2))
    
    except Exception as e:
        logger.error(f"Enterprise management failed: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())