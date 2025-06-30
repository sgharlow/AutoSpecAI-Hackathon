"""
Shared utilities for AutoSpec.AI Lambda functions.

This package contains common functionality used across multiple Lambda functions
including error handling, logging, validation, and utility functions.
"""

from .error_handler import (
    ErrorHandler,
    AutoSpecError,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    RateLimitError,
    ExternalServiceError,
    DatabaseError,
    FileProcessingError,
    ErrorSeverity,
    ErrorCategory,
    validate_required_fields,
    validate_file_type,
    handle_aws_error
)

from .config import (
    get_config,
    get_config_manager,
    ConfigManager,
    AutoSpecConfig,
    ProcessingConfig,
    BedrockConfig,
    BrandingConfig,
    TemplatesConfig,
    IntegrationsConfig,
    SecurityConfig
)

from .logging_utils import (
    get_logger,
    StructuredLogger,
    LogContext,
    log_performance,
    log_aws_operation,
    configure_lambda_logging,
    init_lambda_logging,
    set_correlation_context,
    get_correlation_context,
    clear_correlation_context
)

from .health_checks import (
    HealthChecker,
    HealthStatus,
    HealthCheckResult,
    SystemHealthResult,
    AWSHealthChecks,
    create_lambda_health_checker
)

from .retry_utils import (
    retry_with_backoff,
    RetryConfig,
    RetryStrategy,
    CircuitBreaker,
    CircuitBreakerState,
    RetryExhaustedException,
    CircuitBreakerOpenException,
    AWSRetryUtils,
    retry_bedrock_call,
    retry_dynamodb_call,
    retry_s3_call,
    get_circuit_breaker_status
)

__all__ = [
    # Error handling
    'ErrorHandler',
    'AutoSpecError',
    'ValidationError', 
    'AuthenticationError',
    'AuthorizationError',
    'RateLimitError',
    'ExternalServiceError',
    'DatabaseError',
    'FileProcessingError',
    'ErrorSeverity',
    'ErrorCategory',
    'validate_required_fields',
    'validate_file_type',
    'handle_aws_error',
    # Configuration management
    'get_config',
    'get_config_manager',
    'ConfigManager',
    'AutoSpecConfig',
    'ProcessingConfig',
    'BedrockConfig',
    'BrandingConfig',
    'TemplatesConfig',
    'IntegrationsConfig',
    'SecurityConfig',
    # Logging utilities
    'get_logger',
    'StructuredLogger',
    'LogContext',
    'log_performance',
    'log_aws_operation',
    'configure_lambda_logging',
    'init_lambda_logging',
    'set_correlation_context',
    'get_correlation_context',
    'clear_correlation_context',
    # Health checks
    'HealthChecker',
    'HealthStatus',
    'HealthCheckResult',
    'SystemHealthResult',
    'AWSHealthChecks',
    'create_lambda_health_checker',
    # Retry utilities
    'retry_with_backoff',
    'RetryConfig',
    'RetryStrategy',
    'CircuitBreaker',
    'CircuitBreakerState',
    'RetryExhaustedException',
    'CircuitBreakerOpenException',
    'AWSRetryUtils',
    'retry_bedrock_call',
    'retry_dynamodb_call',
    'retry_s3_call',
    'get_circuit_breaker_status'
]