"""
Standardized Error Handling Module for AutoSpec.AI Lambda Functions

This module provides consistent error handling, logging, and response formatting
across all Lambda functions in the AutoSpec.AI system.

Usage:
    from shared.error_handler import ErrorHandler, AutoSpecError
    
    error_handler = ErrorHandler(function_name='ingest')
    
    # Use as decorator
    @error_handler.lambda_handler
    def handler(event, context):
        # Your function logic
        pass
    
    # Or handle manually
    try:
        # risky operation
    except Exception as e:
        return error_handler.handle_error(e, event, context)
"""

import json
import logging
import traceback
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, Optional, Union
import boto3
from botocore.exceptions import ClientError, BotoCoreError

class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorCategory(Enum):
    """Error categories for classification."""
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    RATE_LIMIT = "rate_limit"
    EXTERNAL_SERVICE = "external_service"
    DATABASE = "database"
    FILE_PROCESSING = "file_processing"
    BUSINESS_LOGIC = "business_logic"
    SYSTEM = "system"
    UNKNOWN = "unknown"

class AutoSpecError(Exception):
    """Base exception class for AutoSpec.AI errors."""
    
    def __init__(self, message: str, error_code: str = None, 
                 category: ErrorCategory = ErrorCategory.UNKNOWN,
                 severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                 details: Dict[str, Any] = None,
                 http_status: int = 500):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.category = category
        self.severity = severity
        self.details = details or {}
        self.http_status = http_status
        self.timestamp = datetime.now(timezone.utc).isoformat()
        super().__init__(message)

class ValidationError(AutoSpecError):
    """Validation related errors."""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message, 
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW,
            http_status=400,
            **kwargs
        )

class AuthenticationError(AutoSpecError):
    """Authentication related errors."""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.AUTHENTICATION,
            severity=ErrorSeverity.HIGH,
            http_status=401,
            **kwargs
        )

class AuthorizationError(AutoSpecError):
    """Authorization related errors."""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.AUTHORIZATION,
            severity=ErrorSeverity.HIGH,
            http_status=403,
            **kwargs
        )

class RateLimitError(AutoSpecError):
    """Rate limiting errors."""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.RATE_LIMIT,
            severity=ErrorSeverity.MEDIUM,
            http_status=429,
            **kwargs
        )

class ExternalServiceError(AutoSpecError):
    """External service integration errors."""
    def __init__(self, message: str, service_name: str = None, **kwargs):
        details = kwargs.get('details', {})
        if service_name:
            details['service_name'] = service_name
        super().__init__(
            message,
            category=ErrorCategory.EXTERNAL_SERVICE,
            severity=ErrorSeverity.HIGH,
            details=details,
            **kwargs
        )

class DatabaseError(AutoSpecError):
    """Database operation errors."""
    def __init__(self, message: str, operation: str = None, **kwargs):
        details = kwargs.get('details', {})
        if operation:
            details['operation'] = operation
        super().__init__(
            message,
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.HIGH,
            details=details,
            **kwargs
        )

class FileProcessingError(AutoSpecError):
    """File processing errors."""
    def __init__(self, message: str, filename: str = None, file_type: str = None, **kwargs):
        details = kwargs.get('details', {})
        if filename:
            details['filename'] = filename
        if file_type:
            details['file_type'] = file_type
        super().__init__(
            message,
            category=ErrorCategory.FILE_PROCESSING,
            severity=ErrorSeverity.MEDIUM,
            details=details,
            **kwargs
        )

class ErrorHandler:
    """Centralized error handling for Lambda functions."""
    
    def __init__(self, function_name: str, environment: str = None):
        self.function_name = function_name
        self.environment = environment or 'unknown'
        self.logger = self._setup_logger()
        self.cloudwatch = boto3.client('cloudwatch')
        
    def _setup_logger(self) -> logging.Logger:
        """Set up structured logging."""
        logger = logging.getLogger(self.function_name)
        
        # Remove any existing handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # Create new handler
        handler = logging.StreamHandler()
        
        # JSON formatter for structured logging
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
            '"function": "' + self.function_name + '", '
            '"environment": "' + self.environment + '", '
            '"message": "%(message)s", "module": "%(name)s"}'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        return logger
    
    def lambda_handler(self, func):
        """Decorator for Lambda handler functions."""
        def wrapper(event, context):
            start_time = time.time()
            request_id = context.aws_request_id if context else 'unknown'
            
            # Log function start
            self.logger.info(
                f"Function started - RequestId: {request_id}, "
                f"Event: {json.dumps(event, default=str)[:500]}..."
            )
            
            try:
                # Execute the function
                result = func(event, context)
                
                # Log successful completion
                duration = time.time() - start_time
                self.logger.info(
                    f"Function completed successfully - RequestId: {request_id}, "
                    f"Duration: {duration:.2f}s"
                )
                
                # Send success metric
                self._send_metric('Success', 1)
                self._send_metric('Duration', duration * 1000)  # milliseconds
                
                return result
                
            except Exception as e:
                # Handle the error
                duration = time.time() - start_time
                return self.handle_error(e, event, context, duration)
        
        return wrapper
    
    def handle_error(self, error: Exception, event: Dict[str, Any] = None, 
                    context: Any = None, duration: float = None) -> Dict[str, Any]:
        """Handle and format errors consistently."""
        
        request_id = context.aws_request_id if context else 'unknown'
        
        # Classify the error
        if isinstance(error, AutoSpecError):
            # Custom application error
            error_data = {
                'error_code': error.error_code,
                'message': error.message,
                'category': error.category.value,
                'severity': error.severity.value,
                'details': error.details,
                'timestamp': error.timestamp,
                'http_status': error.http_status
            }
        else:
            # System or unexpected error
            error_data = self._classify_system_error(error)
        
        # Add context information
        error_data.update({
            'request_id': request_id,
            'function_name': self.function_name,
            'environment': self.environment
        })
        
        # Log the error
        self._log_error(error, error_data, event, duration)
        
        # Send error metrics
        self._send_error_metrics(error_data)
        
        # Return formatted response
        return self._format_error_response(error_data)
    
    def _classify_system_error(self, error: Exception) -> Dict[str, Any]:
        """Classify system/unexpected errors."""
        
        if isinstance(error, ClientError):
            # AWS service error
            service_name = error.response.get('Error', {}).get('Code', 'AWS')
            error_code = error.response.get('Error', {}).get('Code', 'ServiceError')
            
            return {
                'error_code': f"AWS_{error_code}",
                'message': str(error),
                'category': ErrorCategory.EXTERNAL_SERVICE.value,
                'severity': ErrorSeverity.HIGH.value,
                'details': {
                    'service_name': service_name,
                    'aws_error_code': error_code
                },
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'http_status': 502
            }
        
        elif isinstance(error, BotoCoreError):
            # Boto3 error
            return {
                'error_code': 'BotoCoreError',
                'message': str(error),
                'category': ErrorCategory.EXTERNAL_SERVICE.value,
                'severity': ErrorSeverity.HIGH.value,
                'details': {'error_type': error.__class__.__name__},
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'http_status': 502
            }
        
        elif isinstance(error, (ValueError, TypeError)):
            # Data/validation error
            return {
                'error_code': error.__class__.__name__,
                'message': str(error),
                'category': ErrorCategory.VALIDATION.value,
                'severity': ErrorSeverity.MEDIUM.value,
                'details': {},
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'http_status': 400
            }
        
        else:
            # Unknown system error
            return {
                'error_code': 'SystemError',
                'message': 'An unexpected error occurred',
                'category': ErrorCategory.SYSTEM.value,
                'severity': ErrorSeverity.CRITICAL.value,
                'details': {
                    'error_type': error.__class__.__name__,
                    'original_message': str(error)
                },
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'http_status': 500
            }
    
    def _log_error(self, error: Exception, error_data: Dict[str, Any], 
                  event: Dict[str, Any] = None, duration: float = None):
        """Log error with full context."""
        
        log_data = {
            'error_details': error_data,
            'stack_trace': traceback.format_exc(),
            'event_sample': json.dumps(event, default=str)[:1000] if event else None,
            'duration_seconds': duration
        }
        
        # Log at appropriate level based on severity
        severity = error_data.get('severity', 'medium')
        if severity in ['critical', 'high']:
            self.logger.error(f"Error occurred: {json.dumps(log_data, default=str)}")
        else:
            self.logger.warning(f"Error occurred: {json.dumps(log_data, default=str)}")
    
    def _send_error_metrics(self, error_data: Dict[str, Any]):
        """Send error metrics to CloudWatch."""
        try:
            category = error_data.get('category', 'unknown')
            severity = error_data.get('severity', 'medium')
            
            # Send error count metric
            self._send_metric('Errors', 1, {
                'Category': category,
                'Severity': severity
            })
            
            # Send specific error code metric
            self._send_metric('ErrorsByCode', 1, {
                'ErrorCode': error_data.get('error_code', 'Unknown')
            })
            
        except Exception as metric_error:
            self.logger.warning(f"Failed to send error metrics: {metric_error}")
    
    def _send_metric(self, metric_name: str, value: float, dimensions: Dict[str, str] = None):
        """Send custom metric to CloudWatch."""
        try:
            metric_dimensions = [
                {'Name': 'FunctionName', 'Value': self.function_name},
                {'Name': 'Environment', 'Value': self.environment}
            ]
            
            if dimensions:
                for key, val in dimensions.items():
                    metric_dimensions.append({'Name': key, 'Value': val})
            
            self.cloudwatch.put_metric_data(
                Namespace='AutoSpecAI/Lambda',
                MetricData=[{
                    'MetricName': metric_name,
                    'Value': value,
                    'Unit': 'Count' if metric_name != 'Duration' else 'Milliseconds',
                    'Dimensions': metric_dimensions,
                    'Timestamp': datetime.now(timezone.utc)
                }]
            )
        except Exception as e:
            self.logger.warning(f"Failed to send metric {metric_name}: {e}")
    
    def _format_error_response(self, error_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format error response for different contexts."""
        
        # Determine if this is an API Gateway response
        http_status = error_data.get('http_status', 500)
        
        # Create error response body
        response_body = {
            'error': {
                'code': error_data.get('error_code'),
                'message': error_data.get('message'),
                'category': error_data.get('category'),
                'timestamp': error_data.get('timestamp'),
                'request_id': error_data.get('request_id')
            }
        }
        
        # Add details for non-production environments
        if self.environment != 'prod':
            response_body['error']['details'] = error_data.get('details', {})
        
        # Return API Gateway response format if HTTP status is provided
        if http_status:
            return {
                'statusCode': http_status,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'X-Request-ID': error_data.get('request_id')
                },
                'body': json.dumps(response_body)
            }
        else:
            # Return Lambda response format
            return response_body

# Convenience functions for common error scenarios
def validate_required_fields(data: Dict[str, Any], required_fields: list) -> None:
    """Validate that required fields are present in data."""
    missing_fields = [field for field in required_fields if field not in data or data[field] is None]
    
    if missing_fields:
        raise ValidationError(
            f"Missing required fields: {', '.join(missing_fields)}",
            details={'missing_fields': missing_fields}
        )

def validate_file_type(filename: str, allowed_extensions: list) -> None:
    """Validate file type based on extension."""
    if not any(filename.lower().endswith(ext) for ext in allowed_extensions):
        raise FileProcessingError(
            f"Unsupported file type. Allowed extensions: {', '.join(allowed_extensions)}",
            filename=filename,
            details={'allowed_extensions': allowed_extensions}
        )

def handle_aws_error(error: ClientError, service_name: str) -> None:
    """Convert AWS ClientError to appropriate AutoSpecError."""
    error_code = error.response.get('Error', {}).get('Code', 'Unknown')
    
    if error_code in ['AccessDenied', 'UnauthorizedOperation']:
        raise AuthorizationError(
            f"Access denied to {service_name}",
            details={'aws_error_code': error_code, 'service': service_name}
        )
    elif error_code in ['ThrottlingException', 'RequestLimitExceeded']:
        raise RateLimitError(
            f"Rate limit exceeded for {service_name}",
            details={'aws_error_code': error_code, 'service': service_name}
        )
    else:
        raise ExternalServiceError(
            f"Error from {service_name}: {str(error)}",
            service_name=service_name,
            details={'aws_error_code': error_code}
        )