"""
Comprehensive Health Check System for AutoSpec.AI Lambda Functions

This module provides standardized health checking capabilities for all Lambda functions,
including dependency checks, performance monitoring, and system status reporting.

Usage:
    from shared.health_checks import HealthChecker, HealthStatus
    
    health_checker = HealthChecker('my_function')
    
    # Add dependency checks
    health_checker.add_dependency_check('s3', check_s3_connectivity)
    health_checker.add_dependency_check('dynamodb', check_dynamodb_connectivity)
    
    # Perform health check
    health_result = health_checker.check_health()
"""

import os
import time
import boto3
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Callable, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field
from botocore.exceptions import ClientError, BotoCoreError

from .config import get_config
from .logging_utils import get_logger

class HealthStatus(Enum):
    """Health check status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

@dataclass
class HealthCheckResult:
    """Result of a single health check."""
    name: str
    status: HealthStatus
    duration_ms: float
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

@dataclass
class SystemHealthResult:
    """Overall system health result."""
    status: HealthStatus
    timestamp: str
    function_name: str
    environment: str
    checks: List[HealthCheckResult] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    uptime_ms: float = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'status': self.status.value,
            'timestamp': self.timestamp,
            'function_name': self.function_name,
            'environment': self.environment,
            'uptime_ms': self.uptime_ms,
            'checks': [
                {
                    'name': check.name,
                    'status': check.status.value,
                    'duration_ms': check.duration_ms,
                    'message': check.message,
                    'details': check.details,
                    'timestamp': check.timestamp
                }
                for check in self.checks
            ],
            'metrics': self.metrics
        }

class HealthChecker:
    """Comprehensive health checker for Lambda functions."""
    
    def __init__(self, function_name: str, environment: str = None):
        self.function_name = function_name
        self.config = get_config()
        self.environment = environment or self.config.environment
        self.logger = get_logger(f"{function_name}.health", function_name, self.environment)
        self.dependency_checks: Dict[str, Callable[[], HealthCheckResult]] = {}
        self.start_time = time.time()
        
        # Add default system checks
        self._add_default_checks()
    
    def _add_default_checks(self):
        """Add default system health checks."""
        self.add_dependency_check('memory', self._check_memory_usage)
        self.add_dependency_check('disk_space', self._check_disk_space)
        self.add_dependency_check('environment', self._check_environment_config)
    
    def add_dependency_check(self, name: str, check_function: Callable[[], HealthCheckResult]):
        """Add a dependency health check."""
        self.dependency_checks[name] = check_function
    
    def check_health(self) -> SystemHealthResult:
        """Perform comprehensive health check."""
        self.logger.info("Starting health check", operation="health_check")
        
        start_time = time.time()
        checks = []
        overall_status = HealthStatus.HEALTHY
        
        # Run all dependency checks
        for name, check_function in self.dependency_checks.items():
            try:
                result = check_function()
                checks.append(result)
                
                # Update overall status based on worst individual status
                if result.status == HealthStatus.UNHEALTHY:
                    overall_status = HealthStatus.UNHEALTHY
                elif result.status == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                    overall_status = HealthStatus.DEGRADED
                    
            except Exception as e:
                self.logger.error(f"Health check failed for {name}", error=str(e))
                checks.append(HealthCheckResult(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    duration_ms=0,
                    message=f"Health check failed: {str(e)}"
                ))
                overall_status = HealthStatus.UNHEALTHY
        
        # Calculate metrics
        uptime_ms = (time.time() - self.start_time) * 1000
        total_duration_ms = (time.time() - start_time) * 1000
        
        metrics = {
            'total_checks': len(checks),
            'healthy_checks': len([c for c in checks if c.status == HealthStatus.HEALTHY]),
            'degraded_checks': len([c for c in checks if c.status == HealthStatus.DEGRADED]),
            'unhealthy_checks': len([c for c in checks if c.status == HealthStatus.UNHEALTHY]),
            'total_check_duration_ms': total_duration_ms
        }
        
        result = SystemHealthResult(
            status=overall_status,
            timestamp=datetime.now(timezone.utc).isoformat(),
            function_name=self.function_name,
            environment=self.environment,
            checks=checks,
            metrics=metrics,
            uptime_ms=uptime_ms
        )
        
        self.logger.info("Health check completed", 
                        status=overall_status.value,
                        duration_ms=total_duration_ms,
                        total_checks=len(checks))
        
        return result
    
    def _check_memory_usage(self) -> HealthCheckResult:
        """Check memory usage."""
        start_time = time.time()
        
        try:
            import psutil
            memory = psutil.virtual_memory()
            usage_percent = memory.percent
            
            if usage_percent > 90:
                status = HealthStatus.UNHEALTHY
                message = f"High memory usage: {usage_percent:.1f}%"
            elif usage_percent > 80:
                status = HealthStatus.DEGRADED
                message = f"Elevated memory usage: {usage_percent:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"Memory usage normal: {usage_percent:.1f}%"
            
            details = {
                'usage_percent': usage_percent,
                'available_mb': memory.available / (1024 * 1024),
                'total_mb': memory.total / (1024 * 1024)
            }
            
        except ImportError:
            # psutil not available, use basic check
            status = HealthStatus.HEALTHY
            message = "Memory check not available (psutil not installed)"
            details = {}
        except Exception as e:
            status = HealthStatus.UNKNOWN
            message = f"Memory check failed: {str(e)}"
            details = {}
        
        duration_ms = (time.time() - start_time) * 1000
        return HealthCheckResult(
            name='memory',
            status=status,
            duration_ms=duration_ms,
            message=message,
            details=details
        )
    
    def _check_disk_space(self) -> HealthCheckResult:
        """Check disk space (primarily /tmp in Lambda)."""
        start_time = time.time()
        
        try:\n            import shutil\n            disk_usage = shutil.disk_usage('/tmp')\n            total_mb = disk_usage.total / (1024 * 1024)\n            free_mb = disk_usage.free / (1024 * 1024)\n            usage_percent = ((total_mb - free_mb) / total_mb) * 100\n            \n            if usage_percent > 90:\n                status = HealthStatus.UNHEALTHY\n                message = f\"Low disk space: {usage_percent:.1f}% used\"\n            elif usage_percent > 80:\n                status = HealthStatus.DEGRADED\n                message = f\"Elevated disk usage: {usage_percent:.1f}% used\"\n            else:\n                status = HealthStatus.HEALTHY\n                message = f\"Disk space normal: {usage_percent:.1f}% used\"\n            \n            details = {\n                'usage_percent': usage_percent,\n                'free_mb': free_mb,\n                'total_mb': total_mb\n            }\n            \n        except Exception as e:\n            status = HealthStatus.UNKNOWN\n            message = f\"Disk space check failed: {str(e)}\"\n            details = {}\n        \n        duration_ms = (time.time() - start_time) * 1000\n        return HealthCheckResult(\n            name='disk_space',\n            status=status,\n            duration_ms=duration_ms,\n            message=message,\n            details=details\n        )\n    \n    def _check_environment_config(self) -> HealthCheckResult:\n        \"\"\"Check environment configuration validity.\"\"\"\n        start_time = time.time()\n        \n        try:\n            # Check required environment variables\n            required_vars = ['ENVIRONMENT', 'AWS_REGION']\n            missing_vars = []\n            \n            for var in required_vars:\n                if not os.environ.get(var):\n                    missing_vars.append(var)\n            \n            # Check configuration loading\n            config_valid = True\n            config_issues = []\n            \n            try:\n                config = get_config()\n                # Basic validation of config structure\n                if not hasattr(config, 'environment'):\n                    config_issues.append(\"Missing environment in config\")\n                if not hasattr(config, 'processing'):\n                    config_issues.append(\"Missing processing config\")\n            except Exception as e:\n                config_valid = False\n                config_issues.append(f\"Config loading failed: {str(e)}\")\n            \n            if missing_vars or not config_valid:\n                status = HealthStatus.UNHEALTHY\n                issues = missing_vars + config_issues\n                message = f\"Environment issues: {'; '.join(issues)}\"\n            elif config_issues:\n                status = HealthStatus.DEGRADED\n                message = f\"Config warnings: {'; '.join(config_issues)}\"\n            else:\n                status = HealthStatus.HEALTHY\n                message = \"Environment configuration valid\"\n            \n            details = {\n                'missing_env_vars': missing_vars,\n                'config_valid': config_valid,\n                'config_issues': config_issues,\n                'environment': self.environment\n            }\n            \n        except Exception as e:\n            status = HealthStatus.UNKNOWN\n            message = f\"Environment check failed: {str(e)}\"\n            details = {}\n        \n        duration_ms = (time.time() - start_time) * 1000\n        return HealthCheckResult(\n            name='environment',\n            status=status,\n            duration_ms=duration_ms,\n            message=message,\n            details=details\n        )\n\n# AWS Service Health Checks\nclass AWSHealthChecks:\n    \"\"\"Collection of AWS service health checks.\"\"\"\n    \n    @staticmethod\n    def create_s3_check(bucket_name: str) -> Callable[[], HealthCheckResult]:\n        \"\"\"Create S3 connectivity health check.\"\"\"\n        def check_s3() -> HealthCheckResult:\n            start_time = time.time()\n            \n            try:\n                s3_client = boto3.client('s3')\n                \n                # Test bucket access\n                s3_client.head_bucket(Bucket=bucket_name)\n                \n                # Test object operations (create a small test object)\n                test_key = f\"health-check/{datetime.now().strftime('%Y%m%d')}/test.txt\"\n                s3_client.put_object(\n                    Bucket=bucket_name,\n                    Key=test_key,\n                    Body=b'health check test',\n                    ServerSideEncryption='AES256'\n                )\n                \n                # Clean up test object\n                s3_client.delete_object(Bucket=bucket_name, Key=test_key)\n                \n                duration_ms = (time.time() - start_time) * 1000\n                return HealthCheckResult(\n                    name='s3',\n                    status=HealthStatus.HEALTHY,\n                    duration_ms=duration_ms,\n                    message=f\"S3 bucket {bucket_name} accessible\",\n                    details={'bucket_name': bucket_name, 'operations_tested': ['head_bucket', 'put_object', 'delete_object']}\n                )\n                \n            except ClientError as e:\n                duration_ms = (time.time() - start_time) * 1000\n                error_code = e.response.get('Error', {}).get('Code', 'Unknown')\n                \n                if error_code in ['NoSuchBucket', 'AccessDenied']:\n                    status = HealthStatus.UNHEALTHY\n                else:\n                    status = HealthStatus.DEGRADED\n                \n                return HealthCheckResult(\n                    name='s3',\n                    status=status,\n                    duration_ms=duration_ms,\n                    message=f\"S3 error: {error_code}\",\n                    details={'bucket_name': bucket_name, 'error_code': error_code, 'error_message': str(e)}\n                )\n                \n            except Exception as e:\n                duration_ms = (time.time() - start_time) * 1000\n                return HealthCheckResult(\n                    name='s3',\n                    status=HealthStatus.UNHEALTHY,\n                    duration_ms=duration_ms,\n                    message=f\"S3 check failed: {str(e)}\",\n                    details={'bucket_name': bucket_name, 'error_type': type(e).__name__}\n                )\n        \n        return check_s3\n    \n    @staticmethod\n    def create_dynamodb_check(table_name: str) -> Callable[[], HealthCheckResult]:\n        \"\"\"Create DynamoDB connectivity health check.\"\"\"\n        def check_dynamodb() -> HealthCheckResult:\n            start_time = time.time()\n            \n            try:\n                dynamodb = boto3.resource('dynamodb')\n                table = dynamodb.Table(table_name)\n                \n                # Test table access\n                table.load()\n                \n                # Test basic operations\n                response = table.describe_table()\n                table_status = response['Table']['TableStatus']\n                \n                if table_status != 'ACTIVE':\n                    status = HealthStatus.DEGRADED\n                    message = f\"DynamoDB table {table_name} status: {table_status}\"\n                else:\n                    status = HealthStatus.HEALTHY\n                    message = f\"DynamoDB table {table_name} active\"\n                \n                duration_ms = (time.time() - start_time) * 1000\n                return HealthCheckResult(\n                    name='dynamodb',\n                    status=status,\n                    duration_ms=duration_ms,\n                    message=message,\n                    details={\n                        'table_name': table_name,\n                        'table_status': table_status,\n                        'item_count': response['Table'].get('ItemCount', 0),\n                        'table_size_bytes': response['Table'].get('TableSizeBytes', 0)\n                    }\n                )\n                \n            except ClientError as e:\n                duration_ms = (time.time() - start_time) * 1000\n                error_code = e.response.get('Error', {}).get('Code', 'Unknown')\n                \n                return HealthCheckResult(\n                    name='dynamodb',\n                    status=HealthStatus.UNHEALTHY,\n                    duration_ms=duration_ms,\n                    message=f\"DynamoDB error: {error_code}\",\n                    details={'table_name': table_name, 'error_code': error_code, 'error_message': str(e)}\n                )\n                \n            except Exception as e:\n                duration_ms = (time.time() - start_time) * 1000\n                return HealthCheckResult(\n                    name='dynamodb',\n                    status=HealthStatus.UNHEALTHY,\n                    duration_ms=duration_ms,\n                    message=f\"DynamoDB check failed: {str(e)}\",\n                    details={'table_name': table_name, 'error_type': type(e).__name__}\n                )\n        \n        return check_dynamodb\n    \n    @staticmethod\n    def create_bedrock_check(model_id: str = None) -> Callable[[], HealthCheckResult]:\n        \"\"\"Create Amazon Bedrock connectivity health check.\"\"\"\n        def check_bedrock() -> HealthCheckResult:\n            start_time = time.time()\n            \n            try:\n                config = get_config()\n                test_model_id = model_id or config.bedrock.model_id\n                \n                bedrock_client = boto3.client('bedrock-runtime')\n                \n                # Test model availability with a simple prompt\n                test_prompt = \"Hello\"\n                body = json.dumps({\n                    \"prompt\": f\"\\n\\nHuman: {test_prompt}\\n\\nAssistant:\",\n                    \"max_tokens_to_sample\": 10,\n                    \"temperature\": 0.1\n                })\n                \n                response = bedrock_client.invoke_model(\n                    body=body,\n                    modelId=test_model_id,\n                    accept='application/json',\n                    contentType='application/json'\n                )\n                \n                duration_ms = (time.time() - start_time) * 1000\n                \n                return HealthCheckResult(\n                    name='bedrock',\n                    status=HealthStatus.HEALTHY,\n                    duration_ms=duration_ms,\n                    message=f\"Bedrock model {test_model_id} accessible\",\n                    details={'model_id': test_model_id, 'response_size': len(response['body'].read())}\n                )\n                \n            except ClientError as e:\n                duration_ms = (time.time() - start_time) * 1000\n                error_code = e.response.get('Error', {}).get('Code', 'Unknown')\n                \n                # Determine severity based on error type\n                if error_code in ['ValidationException', 'AccessDeniedException']:\n                    status = HealthStatus.UNHEALTHY\n                else:\n                    status = HealthStatus.DEGRADED\n                \n                return HealthCheckResult(\n                    name='bedrock',\n                    status=status,\n                    duration_ms=duration_ms,\n                    message=f\"Bedrock error: {error_code}\",\n                    details={'model_id': test_model_id, 'error_code': error_code, 'error_message': str(e)}\n                )\n                \n            except Exception as e:\n                duration_ms = (time.time() - start_time) * 1000\n                return HealthCheckResult(\n                    name='bedrock',\n                    status=HealthStatus.UNHEALTHY,\n                    duration_ms=duration_ms,\n                    message=f\"Bedrock check failed: {str(e)}\",\n                    details={'model_id': test_model_id, 'error_type': type(e).__name__}\n                )\n        \n        return check_bedrock\n    \n    @staticmethod\n    def create_ses_check(from_email: str = None) -> Callable[[], HealthCheckResult]:\n        \"\"\"Create SES connectivity health check.\"\"\"\n        def check_ses() -> HealthCheckResult:\n            start_time = time.time()\n            \n            try:\n                config = get_config()\n                test_from_email = from_email or config.templates.email.default_sender\n                \n                ses_client = boto3.client('ses')\n                \n                # Check sending quota and statistics\n                quota_response = ses_client.get_send_quota()\n                stats_response = ses_client.get_send_statistics()\n                \n                # Check if we have sending capacity\n                sent_last_24h = quota_response.get('SentLast24Hours', 0)\n                max_24h_send = quota_response.get('Max24HourSend', 0)\n                \n                if sent_last_24h >= max_24h_send * 0.9:  # 90% of quota used\n                    status = HealthStatus.DEGRADED\n                    message = f\"SES quota nearly exhausted: {sent_last_24h}/{max_24h_send}\"\n                else:\n                    status = HealthStatus.HEALTHY\n                    message = f\"SES service accessible, quota: {sent_last_24h}/{max_24h_send}\"\n                \n                duration_ms = (time.time() - start_time) * 1000\n                \n                return HealthCheckResult(\n                    name='ses',\n                    status=status,\n                    duration_ms=duration_ms,\n                    message=message,\n                    details={\n                        'from_email': test_from_email,\n                        'sent_last_24h': sent_last_24h,\n                        'max_24h_send': max_24h_send,\n                        'max_send_rate': quota_response.get('MaxSendRate', 0)\n                    }\n                )\n                \n            except ClientError as e:\n                duration_ms = (time.time() - start_time) * 1000\n                error_code = e.response.get('Error', {}).get('Code', 'Unknown')\n                \n                return HealthCheckResult(\n                    name='ses',\n                    status=HealthStatus.UNHEALTHY,\n                    duration_ms=duration_ms,\n                    message=f\"SES error: {error_code}\",\n                    details={'from_email': test_from_email, 'error_code': error_code, 'error_message': str(e)}\n                )\n                \n            except Exception as e:\n                duration_ms = (time.time() - start_time) * 1000\n                return HealthCheckResult(\n                    name='ses',\n                    status=HealthStatus.UNHEALTHY,\n                    duration_ms=duration_ms,\n                    message=f\"SES check failed: {str(e)}\",\n                    details={'from_email': test_from_email, 'error_type': type(e).__name__}\n                )\n        \n        return check_ses\n\n# Convenience function to create a standard health checker for Lambda functions\ndef create_lambda_health_checker(function_name: str, \n                                 bucket_name: str = None,\n                                 table_name: str = None,\n                                 include_bedrock: bool = False,\n                                 include_ses: bool = False) -> HealthChecker:\n    \"\"\"Create a pre-configured health checker for Lambda functions.\"\"\"\n    \n    health_checker = HealthChecker(function_name)\n    \n    # Add AWS service checks based on parameters\n    if bucket_name:\n        health_checker.add_dependency_check('s3', AWSHealthChecks.create_s3_check(bucket_name))\n    \n    if table_name:\n        health_checker.add_dependency_check('dynamodb', AWSHealthChecks.create_dynamodb_check(table_name))\n    \n    if include_bedrock:\n        health_checker.add_dependency_check('bedrock', AWSHealthChecks.create_bedrock_check())\n    \n    if include_ses:\n        health_checker.add_dependency_check('ses', AWSHealthChecks.create_ses_check())\n    \n    return health_checker