"""
Retry Logic with Exponential Backoff for AutoSpec.AI

This module provides robust retry mechanisms with exponential backoff for
external service calls, including AWS services, HTTP requests, and custom operations.

Usage:
    from shared.retry_utils import retry_with_backoff, RetryConfig, CircuitBreaker
    
    # Decorator usage
    @retry_with_backoff(max_attempts=3, backoff_factor=2.0)
    def call_external_api():
        # Your external service call
        pass
    
    # Context manager usage
    with CircuitBreaker('bedrock_service', failure_threshold=5) as cb:
        result = cb.call(lambda: bedrock_client.invoke_model(...))
"""

import time
import random
import functools
import logging
from typing import Callable, Any, Dict, List, Optional, Tuple, Type, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone, timedelta
import threading
from botocore.exceptions import ClientError, BotoCoreError
from botocore.client import BaseClient

from .logging_utils import get_logger

class RetryStrategy(Enum):
    """Retry strategy options."""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_DELAY = "fixed_delay"
    FIBONACCI_BACKOFF = "fibonacci_backoff"

class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"         # Failing, blocking calls
    HALF_OPEN = "half_open"  # Testing if service is back

@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    backoff_factor: float = 2.0
    jitter: bool = True
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    
    # Exception handling
    retryable_exceptions: Tuple[Type[Exception], ...] = field(
        default_factory=lambda: (ClientError, BotoCoreError, ConnectionError, TimeoutError)
    )
    non_retryable_error_codes: List[str] = field(
        default_factory=lambda: ['ValidationException', 'InvalidParameterException', 'AccessDenied']
    )
    
    # Circuit breaker integration
    enable_circuit_breaker: bool = False
    circuit_breaker_name: str = None

@dataclass
class RetryResult:
    """Result of a retry operation."""
    success: bool
    result: Any = None
    exception: Exception = None
    attempts_made: int = 0
    total_delay_seconds: float = 0.0
    final_delay_seconds: float = 0.0

class CircuitBreaker:
    """Circuit breaker implementation for external service calls."""
    
    _instances: Dict[str, 'CircuitBreaker'] = {}
    _lock = threading.Lock()
    
    def __init__(self, name: str, failure_threshold: int = 5, 
                 recovery_timeout_seconds: float = 60.0,
                 success_threshold: int = 2):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self.success_threshold = success_threshold
        
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.logger = get_logger(f"circuit_breaker.{name}")
        
        # Thread safety
        self._lock = threading.Lock()
    
    @classmethod
    def get_instance(cls, name: str, **kwargs) -> 'CircuitBreaker':
        """Get or create a circuit breaker instance."""
        if name not in cls._instances:
            with cls._lock:
                if name not in cls._instances:
                    cls._instances[name] = cls(name, **kwargs)
        return cls._instances[name]
    
    def _should_allow_request(self) -> bool:
        """Check if request should be allowed through the circuit breaker."""
        with self._lock:
            if self.state == CircuitBreakerState.CLOSED:
                return True
            elif self.state == CircuitBreakerState.OPEN:
                # Check if we should transition to half-open
                if (self.last_failure_time and 
                    time.time() - self.last_failure_time >= self.recovery_timeout_seconds):
                    self.state = CircuitBreakerState.HALF_OPEN
                    self.success_count = 0
                    self.logger.info(f"Circuit breaker {self.name} transitioning to HALF_OPEN")
                    return True
                return False
            elif self.state == CircuitBreakerState.HALF_OPEN:
                return True
            
        return False
    
    def _record_success(self):
        """Record a successful operation."""
        with self._lock:
            if self.state == CircuitBreakerState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.success_threshold:
                    self.state = CircuitBreakerState.CLOSED
                    self.failure_count = 0
                    self.logger.info(f"Circuit breaker {self.name} transitioning to CLOSED")
            elif self.state == CircuitBreakerState.CLOSED:
                self.failure_count = 0
    
    def _record_failure(self):
        """Record a failed operation."""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.state == CircuitBreakerState.HALF_OPEN:
                self.state = CircuitBreakerState.OPEN
                self.logger.warning(f"Circuit breaker {self.name} transitioning to OPEN (failure during half-open)")
            elif (self.state == CircuitBreakerState.CLOSED and 
                  self.failure_count >= self.failure_threshold):
                self.state = CircuitBreakerState.OPEN
                self.logger.warning(f"Circuit breaker {self.name} transitioning to OPEN (threshold reached)")
    
    def call(self, func: Callable[[], Any]) -> Any:
        """Execute a function through the circuit breaker."""
        if not self._should_allow_request():
            raise CircuitBreakerOpenException(f"Circuit breaker {self.name} is OPEN")
        
        try:
            result = func()
            self._record_success()
            return result
        except Exception as e:
            self._record_failure()
            raise
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Context manager cleanup if needed
        pass
    
    def get_state(self) -> Dict[str, Any]:
        """Get current circuit breaker state."""
        with self._lock:
            return {
                'name': self.name,
                'state': self.state.value,
                'failure_count': self.failure_count,
                'success_count': self.success_count,
                'failure_threshold': self.failure_threshold,
                'last_failure_time': self.last_failure_time,
                'recovery_timeout_seconds': self.recovery_timeout_seconds
            }

class CircuitBreakerOpenException(Exception):
    """Exception raised when circuit breaker is open."""
    pass

class RetryExhaustedException(Exception):
    """Exception raised when all retry attempts are exhausted."""
    pass

def calculate_delay(attempt: int, config: RetryConfig) -> float:
    """Calculate delay for the given attempt number."""
    if config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
        delay = config.base_delay_seconds * (config.backoff_factor ** (attempt - 1))
    elif config.strategy == RetryStrategy.LINEAR_BACKOFF:
        delay = config.base_delay_seconds * attempt
    elif config.strategy == RetryStrategy.FIXED_DELAY:
        delay = config.base_delay_seconds
    elif config.strategy == RetryStrategy.FIBONACCI_BACKOFF:
        # Simple fibonacci sequence for delays
        if attempt <= 2:
            delay = config.base_delay_seconds
        else:
            # Calculate fibonacci number for attempt
            a, b = 1, 1
            for _ in range(attempt - 2):
                a, b = b, a + b
            delay = config.base_delay_seconds * b
    else:
        delay = config.base_delay_seconds
    
    # Apply maximum delay limit
    delay = min(delay, config.max_delay_seconds)
    
    # Add jitter to prevent thundering herd
    if config.jitter:
        jitter_amount = delay * 0.1  # 10% jitter
        delay += random.uniform(-jitter_amount, jitter_amount)
        delay = max(0, delay)  # Ensure non-negative
    
    return delay

def is_retryable_exception(exception: Exception, config: RetryConfig) -> bool:
    """Check if an exception is retryable based on configuration."""
    
    # Check if it's in the retryable exception types
    if not isinstance(exception, config.retryable_exceptions):
        return False
    
    # Special handling for AWS ClientError
    if isinstance(exception, ClientError):
        error_code = exception.response.get('Error', {}).get('Code', '')
        
        # Check for explicitly non-retryable error codes
        if error_code in config.non_retryable_error_codes:
            return False
        
        # HTTP status code checks
        http_status = exception.response.get('ResponseMetadata', {}).get('HTTPStatusCode', 0)
        
        # 4xx errors (except specific retryable ones) are generally not retryable
        if 400 <= http_status < 500:
            retryable_4xx = ['429', 'RequestLimitExceeded', 'Throttling', 'ThrottlingException']
            return error_code in retryable_4xx
        
        # 5xx errors are generally retryable
        if 500 <= http_status < 600:
            return True
    
    return True

def retry_with_backoff(max_attempts: int = 3,\n                      base_delay_seconds: float = 1.0,\n                      max_delay_seconds: float = 60.0,\n                      backoff_factor: float = 2.0,\n                      strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF,\n                      jitter: bool = True,\n                      retryable_exceptions: Tuple[Type[Exception], ...] = None,\n                      circuit_breaker_name: str = None,\n                      logger_name: str = None):\n    \"\"\"Decorator to add retry logic with exponential backoff to a function.\"\"\"\n    \n    def decorator(func: Callable) -> Callable:\n        @functools.wraps(func)\n        def wrapper(*args, **kwargs):\n            # Create retry configuration\n            config = RetryConfig(\n                max_attempts=max_attempts,\n                base_delay_seconds=base_delay_seconds,\n                max_delay_seconds=max_delay_seconds,\n                backoff_factor=backoff_factor,\n                strategy=strategy,\n                jitter=jitter,\n                retryable_exceptions=retryable_exceptions or (ClientError, BotoCoreError, ConnectionError, TimeoutError),\n                enable_circuit_breaker=circuit_breaker_name is not None,\n                circuit_breaker_name=circuit_breaker_name\n            )\n            \n            logger = get_logger(logger_name or func.__module__)\n            \n            return execute_with_retry(func, args, kwargs, config, logger)\n        \n        return wrapper\n    return decorator\n\ndef execute_with_retry(func: Callable, args: tuple, kwargs: dict, \n                      config: RetryConfig, logger) -> Any:\n    \"\"\"Execute a function with retry logic.\"\"\"\n    \n    circuit_breaker = None\n    if config.enable_circuit_breaker and config.circuit_breaker_name:\n        circuit_breaker = CircuitBreaker.get_instance(config.circuit_breaker_name)\n    \n    last_exception = None\n    total_delay = 0.0\n    \n    for attempt in range(1, config.max_attempts + 1):\n        try:\n            # Execute through circuit breaker if configured\n            if circuit_breaker:\n                return circuit_breaker.call(lambda: func(*args, **kwargs))\n            else:\n                return func(*args, **kwargs)\n                \n        except Exception as e:\n            last_exception = e\n            \n            # Check if this exception is retryable\n            if not is_retryable_exception(e, config):\n                logger.error(\n                    f\"Non-retryable exception in {func.__name__}\",\n                    error_type=type(e).__name__,\n                    error_message=str(e),\n                    attempt=attempt\n                )\n                raise\n            \n            # Don't retry on the last attempt\n            if attempt == config.max_attempts:\n                logger.error(\n                    f\"All retry attempts exhausted for {func.__name__}\",\n                    total_attempts=attempt,\n                    total_delay_seconds=total_delay,\n                    final_error=str(e)\n                )\n                raise RetryExhaustedException(\n                    f\"Function {func.__name__} failed after {attempt} attempts. Last error: {str(e)}\"\n                ) from e\n            \n            # Calculate delay for next attempt\n            delay = calculate_delay(attempt, config)\n            total_delay += delay\n            \n            logger.warning(\n                f\"Attempt {attempt} failed for {func.__name__}, retrying in {delay:.2f}s\",\n                error_type=type(e).__name__,\n                error_message=str(e),\n                delay_seconds=delay,\n                remaining_attempts=config.max_attempts - attempt\n            )\n            \n            # Wait before next attempt\n            time.sleep(delay)\n    \n    # This should never be reached, but just in case\n    raise last_exception\n\ndef retry_async_with_backoff(max_attempts: int = 3,\n                            base_delay_seconds: float = 1.0,\n                            max_delay_seconds: float = 60.0,\n                            backoff_factor: float = 2.0):\n    \"\"\"Async version of retry decorator (for future async operations).\"\"\"\n    \n    def decorator(func: Callable) -> Callable:\n        @functools.wraps(func)\n        async def wrapper(*args, **kwargs):\n            import asyncio\n            \n            config = RetryConfig(\n                max_attempts=max_attempts,\n                base_delay_seconds=base_delay_seconds,\n                max_delay_seconds=max_delay_seconds,\n                backoff_factor=backoff_factor\n            )\n            \n            logger = get_logger(func.__module__)\n            last_exception = None\n            \n            for attempt in range(1, config.max_attempts + 1):\n                try:\n                    return await func(*args, **kwargs)\n                except Exception as e:\n                    last_exception = e\n                    \n                    if not is_retryable_exception(e, config) or attempt == config.max_attempts:\n                        raise\n                    \n                    delay = calculate_delay(attempt, config)\n                    logger.warning(\n                        f\"Async attempt {attempt} failed for {func.__name__}, retrying in {delay:.2f}s\",\n                        error_type=type(e).__name__,\n                        error_message=str(e)\n                    )\n                    \n                    await asyncio.sleep(delay)\n            \n            raise last_exception\n        \n        return wrapper\n    return decorator\n\n# AWS-specific retry utilities\nclass AWSRetryUtils:\n    \"\"\"Utilities for AWS service retry patterns.\"\"\"\n    \n    @staticmethod\n    def create_bedrock_client_with_retry() -> BaseClient:\n        \"\"\"Create a Bedrock client with built-in retry configuration.\"\"\"\n        import boto3\n        from botocore.config import Config\n        \n        # Configure boto3 retry settings\n        retry_config = Config(\n            retries={\n                'max_attempts': 3,\n                'mode': 'adaptive'  # adaptive, legacy, or standard\n            }\n        )\n        \n        return boto3.client('bedrock-runtime', config=retry_config)\n    \n    @staticmethod\n    def create_dynamodb_client_with_retry() -> BaseClient:\n        \"\"\"Create a DynamoDB client with built-in retry configuration.\"\"\"\n        import boto3\n        from botocore.config import Config\n        \n        retry_config = Config(\n            retries={\n                'max_attempts': 5,  # DynamoDB can handle more retries\n                'mode': 'adaptive'\n            }\n        )\n        \n        return boto3.client('dynamodb', config=retry_config)\n    \n    @staticmethod\n    def create_s3_client_with_retry() -> BaseClient:\n        \"\"\"Create an S3 client with built-in retry configuration.\"\"\"\n        import boto3\n        from botocore.config import Config\n        \n        retry_config = Config(\n            retries={\n                'max_attempts': 3,\n                'mode': 'standard'\n            }\n        )\n        \n        return boto3.client('s3', config=retry_config)\n\n# Convenience functions for common retry patterns\ndef retry_bedrock_call(func: Callable, *args, **kwargs) -> Any:\n    \"\"\"Retry a Bedrock API call with appropriate configuration.\"\"\"\n    config = RetryConfig(\n        max_attempts=3,\n        base_delay_seconds=1.0,\n        max_delay_seconds=30.0,\n        backoff_factor=2.0,\n        non_retryable_error_codes=['ValidationException', 'AccessDeniedException']\n    )\n    \n    logger = get_logger('bedrock_retry')\n    return execute_with_retry(func, args, kwargs, config, logger)\n\ndef retry_dynamodb_call(func: Callable, *args, **kwargs) -> Any:\n    \"\"\"Retry a DynamoDB API call with appropriate configuration.\"\"\"\n    config = RetryConfig(\n        max_attempts=5,  # DynamoDB can benefit from more retries\n        base_delay_seconds=0.5,\n        max_delay_seconds=20.0,\n        backoff_factor=2.0,\n        non_retryable_error_codes=['ValidationException', 'ConditionalCheckFailedException']\n    )\n    \n    logger = get_logger('dynamodb_retry')\n    return execute_with_retry(func, args, kwargs, config, logger)\n\ndef retry_s3_call(func: Callable, *args, **kwargs) -> Any:\n    \"\"\"Retry an S3 API call with appropriate configuration.\"\"\"\n    config = RetryConfig(\n        max_attempts=3,\n        base_delay_seconds=1.0,\n        max_delay_seconds=30.0,\n        backoff_factor=2.0,\n        non_retryable_error_codes=['NoSuchBucket', 'NoSuchKey', 'AccessDenied']\n    )\n    \n    logger = get_logger('s3_retry')\n    return execute_with_retry(func, args, kwargs, config, logger)\n\n# Health check for retry utilities\ndef get_circuit_breaker_status() -> Dict[str, Any]:\n    \"\"\"Get status of all circuit breakers.\"\"\"\n    return {\n        name: cb.get_state()\n        for name, cb in CircuitBreaker._instances.items()\n    }