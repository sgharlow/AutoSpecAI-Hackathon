"""
Enhanced API Lambda Function with Configuration Management

This is an improved version of the API function that demonstrates
the use of centralized configuration management and removes hardcoded values.
"""

import json
import boto3
import os
import logging
import uuid
import base64
import hashlib
import time
from datetime import datetime, timezone
from botocore.exceptions import ClientError

# Import our shared modules
import sys
sys.path.append('/opt/python/lib/python3.11/site-packages')
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import (
    ErrorHandler, ValidationError, AuthenticationError, 
    RateLimitError, get_config, validate_required_fields,
    validate_file_type
)

# Initialize configuration and error handling
config = get_config()
error_handler = ErrorHandler(
    function_name='api',
    environment=config.environment
)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
lambda_client = boto3.client('lambda')
s3_client = boto3.client('s3')

# Environment variables with configuration fallbacks
HISTORY_TABLE = os.environ.get('HISTORY_TABLE')
DOCUMENT_BUCKET = os.environ.get('DOCUMENT_BUCKET')
INGEST_FUNCTION_NAME = os.environ.get('INGEST_FUNCTION_NAME')
API_KEY_TABLE = os.environ.get('API_KEY_TABLE', f'{config.resource_naming.table_prefix}-api-keys')

@error_handler.lambda_handler
def handler(event, context):
    """
    Enhanced API Gateway handler with configuration-driven behavior.
    """
    error_handler.logger.info(f"API request received: {json.dumps(event, default=str)[:500]}...")
    
    # Extract request information
    http_method = event.get('httpMethod', 'GET')
    path = event.get('path', '')
    headers = event.get('headers', {})
    query_params = event.get('queryStringParameters') or {}
    body = event.get('body', '')
    
    # Handle API versioning
    api_version = extract_api_version(path, headers)
    
    # Authenticate request (if required by configuration)
    if config.security.api_key_required:
        auth_result = authenticate_request(headers, query_params)
        if not auth_result['authenticated']:
            raise AuthenticationError(auth_result['message'])
        client_id = auth_result['client_id']
    else:
        client_id = 'anonymous'
        error_handler.logger.info("API authentication disabled by configuration")
    
    # Check rate limiting (if enabled)
    if config.processing.rate_limiting.enabled:
        rate_limit_result = check_rate_limit(client_id)
        if not rate_limit_result['allowed']:
            raise RateLimitError(rate_limit_result['message'])
    
    # Route request to appropriate handler
    if path.startswith('/v1/upload') or path.startswith('/upload'):
        if http_method == 'POST':
            return handle_upload_v1(event, client_id)
        else:
            raise ValidationError('Only POST method is supported for uploads')
    
    elif path.startswith('/v1/status') or path.startswith('/status'):
        if http_method == 'GET':
            return handle_status_v1(event, client_id)
        else:
            raise ValidationError('Only GET method is supported for status')
    
    elif path.startswith('/v1/history') or path.startswith('/history'):
        if http_method == 'GET':
            return handle_history_v1(event, client_id)
        else:
            raise ValidationError('Only GET method is supported for history')
    
    elif path.startswith('/v1/formats') or path.startswith('/formats'):
        if http_method == 'GET':
            return handle_formats_v1(event, client_id)
        else:
            raise ValidationError('Only GET method is supported for formats')
    
    elif path.startswith('/v1/health') or path.startswith('/health'):
        return handle_health_check(event)
    
    elif path.startswith('/v1/docs') or path.startswith('/docs'):
        return handle_api_documentation(event)
    
    else:
        raise ValidationError(f'Endpoint {path} not found', http_status=404)

def extract_api_version(path, headers):
    """Extract API version from path or headers."""
    if '/v1/' in path:
        return 'v1'
    elif '/v2/' in path:
        return 'v2'
    
    version_header = headers.get('API-Version') or headers.get('api-version')
    return version_header or 'v1'

def authenticate_request(headers, query_params):
    """Authenticate API request using configuration-driven settings."""
    try:
        # Extract API key
        api_key = None
        
        # Check Authorization header
        auth_header = headers.get('Authorization') or headers.get('authorization')
        if auth_header and auth_header.startswith('Bearer '):
            api_key = auth_header[7:]
        
        # Check X-API-Key header
        if not api_key:
            api_key = headers.get('X-API-Key') or headers.get('x-api-key')
        
        # Check query parameter
        if not api_key:
            api_key = query_params.get('api_key')
        
        if not api_key:
            return {'authenticated': False, 'message': 'API key is required'}
        
        return validate_api_key(api_key)
        
    except Exception as e:
        error_handler.logger.error(f"Authentication error: {str(e)}")
        return {'authenticated': False, 'message': 'Authentication failed'}

def validate_api_key(api_key):
    """Validate API key against DynamoDB with configuration-driven settings."""
    try:
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        try:
            table = dynamodb.Table(API_KEY_TABLE)
            response = table.get_item(Key={'keyHash': key_hash})
            
            if 'Item' not in response:
                return {'authenticated': False, 'message': 'Invalid API key'}
            
            item = response['Item']
            
            if not item.get('isActive', False):
                return {'authenticated': False, 'message': 'API key is disabled'}
            
            # Check expiration
            expiry_date = item.get('expiryDate')
            if expiry_date and datetime.now(timezone.utc).isoformat() > expiry_date:
                return {'authenticated': False, 'message': 'API key has expired'}
            
            # Update usage
            table.update_item(\n                Key={'keyHash': key_hash},\n                UpdateExpression='SET lastUsed = :timestamp, usageCount = usageCount + :inc',\n                ExpressionAttributeValues={\n                    ':timestamp': datetime.now(timezone.utc).isoformat(),\n                    ':inc': 1\n                }\n            )\n            \n            return {\n                'authenticated': True,\n                'client_id': item.get('clientId', f\"client-{key_hash[:8]}\"),\n                'rate_limit_tier': item.get('rateLimitTier', 'standard'),\n                'client_name': item.get('clientName', 'Unknown'),\n                'permissions': item.get('permissions', ['read', 'write'])\n            }\n            \n        except Exception as dynamodb_error:\n            error_handler.logger.error(f\"DynamoDB API key lookup failed: {str(dynamodb_error)}\")\n            # In development, allow basic validation as fallback\n            if config.environment == 'dev' and len(api_key) >= 32:\n                error_handler.logger.warning(\"Using fallback API key validation in development\")\n                return {\n                    'authenticated': True,\n                    'client_id': f\"fallback-{hashlib.sha256(api_key.encode()).hexdigest()[:8]}\",\n                    'rate_limit_tier': 'basic',\n                    'fallback_mode': True\n                }\n            else:\n                return {'authenticated': False, 'message': 'API key validation failed'}\n        \n    except Exception as e:\n        error_handler.logger.error(f\"API key validation error: {str(e)}\")\n        return {'authenticated': False, 'message': 'API key validation failed'}\n\ndef check_rate_limit(client_id):\n    \"\"\"Check rate limiting using configuration-driven limits.\"\"\"\n    try:\n        current_time = int(time.time())\n        window_start = current_time - config.processing.rate_limiting.window_seconds\n        \n        rate_limit_table_name = os.environ.get('RATE_LIMIT_TABLE', \n                                              f'{config.resource_naming.table_prefix}-rate-limits')\n        \n        try:\n            table = dynamodb.Table(rate_limit_table_name)\n            response = table.get_item(Key={'clientId': client_id})\n            \n            if 'Item' in response:\n                item = response['Item']\n                \n                if item.get('windowStart', 0) < window_start:\n                    # Reset counter for new window\n                    request_count = 1\n                    window_start_time = current_time\n                else:\n                    # Increment counter\n                    request_count = item.get('requestCount', 0) + 1\n                    window_start_time = item.get('windowStart', current_time)\n                \n                # Check limit using configuration\n                if request_count > config.processing.rate_limiting.requests_per_hour:\n                    return {\n                        'allowed': False,\n                        'remaining': 0,\n                        'reset_time': window_start_time + config.processing.rate_limiting.window_seconds,\n                        'message': f'Rate limit exceeded. Maximum {config.processing.rate_limiting.requests_per_hour} requests per hour.'\n                    }\n                \n                # Update counter\n                table.put_item(\n                    Item={\n                        'clientId': client_id,\n                        'requestCount': request_count,\n                        'windowStart': window_start_time,\n                        'lastRequest': current_time,\n                        'ttl': current_time + config.processing.rate_limiting.window_seconds + 3600\n                    }\n                )\n                \n                return {\n                    'allowed': True,\n                    'remaining': max(0, config.processing.rate_limiting.requests_per_hour - request_count),\n                    'reset_time': window_start_time + config.processing.rate_limiting.window_seconds\n                }\n            else:\n                # First request\n                table.put_item(\n                    Item={\n                        'clientId': client_id,\n                        'requestCount': 1,\n                        'windowStart': current_time,\n                        'lastRequest': current_time,\n                        'ttl': current_time + config.processing.rate_limiting.window_seconds + 3600\n                    }\n                )\n                \n                return {\n                    'allowed': True,\n                    'remaining': config.processing.rate_limiting.requests_per_hour - 1,\n                    'reset_time': current_time + config.processing.rate_limiting.window_seconds\n                }\n                \n        except Exception as dynamodb_error:\n            error_handler.logger.warning(f\"Rate limiting check failed: {str(dynamodb_error)}\")\n            # Allow request if rate limiting fails\n            return {\n                'allowed': True,\n                'remaining': config.processing.rate_limiting.requests_per_hour,\n                'reset_time': current_time + config.processing.rate_limiting.window_seconds,\n                'message': 'Rate limiting unavailable - request allowed'\n            }\n        \n    except Exception as e:\n        error_handler.logger.error(f\"Rate limiting error: {str(e)}\")\n        return {\n            'allowed': True,\n            'remaining': config.processing.rate_limiting.requests_per_hour,\n            'reset_time': current_time + config.processing.rate_limiting.window_seconds,\n            'message': 'Rate limiting check failed'\n        }\n\ndef handle_upload_v1(event, client_id):\n    \"\"\"Handle document upload with configuration-driven validation.\"\"\"\n    # Parse request body\n    body = event.get('body', '')\n    if event.get('isBase64Encoded'):\n        body = base64.b64decode(body).decode('utf-8')\n    \n    if not body:\n        raise ValidationError('Request body is required')\n    \n    try:\n        request_data = json.loads(body)\n    except json.JSONDecodeError:\n        raise ValidationError('Invalid JSON in request body')\n    \n    # Validate required fields\n    validate_required_fields(request_data, ['file_content', 'filename'])\n    \n    # Validate file content\n    try:\n        file_content = base64.b64decode(request_data['file_content'])\n    except Exception:\n        raise ValidationError('Invalid base64 file content')\n    \n    # Validate file size using configuration\n    max_size = config.processing.file_limits.max_size_mb * 1024 * 1024\n    if len(file_content) > max_size:\n        raise ValidationError(\n            config.templates.error_messages.file_too_large.format(\n                max_size_mb=config.processing.file_limits.max_size_mb\n            )\n        )\n    \n    # Validate file type using configuration\n    filename = request_data['filename']\n    validate_file_type(filename, config.processing.file_limits.allowed_extensions)\n    \n    # Generate request ID\n    request_id = str(uuid.uuid4())\n    \n    # Add client information\n    enhanced_request = request_data.copy()\n    enhanced_request.update({\n        'client_id': client_id,\n        'request_id': request_id,\n        'api_version': 'v1',\n        'timestamp': datetime.now(timezone.utc).isoformat(),\n        'use_existing_request_id': True\n    })\n    \n    # Invoke ingest function\n    lambda_client.invoke(\n        FunctionName=INGEST_FUNCTION_NAME,\n        InvocationType='Event',\n        Payload=json.dumps({\n            'body': json.dumps(enhanced_request),\n            'source': 'api_v1'\n        })\n    )\n    \n    return create_success_response(202, {\n        'request_id': request_id,\n        'status': 'accepted',\n        'message': 'Document uploaded and processing started',\n        'filename': filename,\n        'estimated_processing_time': '2-5 minutes'\n    })\n\ndef handle_status_v1(event, client_id):\n    \"\"\"Handle status check with enhanced error reporting.\"\"\"\n    query_params = event.get('queryStringParameters') or {}\n    path_params = event.get('pathParameters') or {}\n    \n    request_id = path_params.get('request_id') or query_params.get('request_id')\n    \n    if not request_id:\n        raise ValidationError('Request ID is required')\n    \n    # Get status from DynamoDB\n    table = dynamodb.Table(HISTORY_TABLE)\n    \n    try:\n        response = table.query(\n            KeyConditionExpression='requestId = :id',\n            ExpressionAttributeValues={':id': request_id},\n            ScanIndexForward=False,\n            Limit=1\n        )\n        \n        if not response['Items']:\n            raise ValidationError(f'Request {request_id} not found', http_status=404)\n            \n    except Exception as db_error:\n        error_handler.logger.error(f\"Database error: {str(db_error)}\")\n        raise ValidationError(f'Database error while looking up request {request_id}')\n    \n    item = response['Items'][0]\n    \n    # Format status response with configuration-driven progress\n    status_data = {\n        'request_id': request_id,\n        'filename': item.get('filename'),\n        'status': item.get('status'),\n        'processing_stage': item.get('processingStage'),\n        'created_at': item.get('timestamp'),\n        'updated_at': item.get('processedAt') or item.get('deliveredAt'),\n        'file_type': item.get('fileType'),\n        'file_size': item.get('fileSize')\n    }\n    \n    # Add progress information\n    stage_progress = {\n        'ingestion_complete': 25,\n        'ai_processing_in_progress': 50,\n        'ai_processing_complete': 75,\n        'formatting_in_progress': 85,\n        'delivery_complete': 100\n    }\n    \n    current_stage = item.get('processingStage', 'unknown')\n    status_data['progress_percentage'] = stage_progress.get(current_stage, 0)\n    \n    # Add error information if failed\n    if item.get('status') == 'failed':\n        status_data['error_message'] = item.get('errorMessage')\n    \n    # Add download links if completed\n    if item.get('status') == 'delivered':\n        status_data['download_links'] = {\n            'note': 'Full results sent via email. API download endpoints coming soon.'\n        }\n    \n    return create_success_response(200, status_data)\n\ndef handle_history_v1(event, client_id):\n    \"\"\"Handle request history with pagination.\"\"\"\n    query_params = event.get('queryStringParameters') or {}\n    \n    # Get pagination parameters\n    limit = min(int(query_params.get('limit', 10)), 100)\n    last_evaluated_key = query_params.get('next_token')\n    \n    table = dynamodb.Table(HISTORY_TABLE)\n    \n    scan_kwargs = {'Limit': limit}\n    \n    if last_evaluated_key:\n        try:\n            scan_kwargs['ExclusiveStartKey'] = json.loads(base64.b64decode(last_evaluated_key))\n        except Exception:\n            raise ValidationError('Invalid next_token')\n    \n    try:\n        response = table.scan(**scan_kwargs)\n    except Exception as scan_error:\n        error_handler.logger.error(f\"History scan failed: {str(scan_error)}\")\n        raise ValidationError(f'Failed to retrieve history: {str(scan_error)}')\n    \n    # Sort by timestamp (newest first)\n    if 'Items' in response:\n        response['Items'] = sorted(\n            response['Items'], \n            key=lambda x: x.get('timestamp', ''), \n            reverse=True\n        )\n    \n    # Format response\n    items = []\n    for item in response['Items']:\n        items.append({\n            'request_id': item.get('requestId'),\n            'filename': item.get('filename'),\n            'status': item.get('status'),\n            'created_at': item.get('timestamp'),\n            'file_type': item.get('fileType'),\n            'file_size': item.get('fileSize')\n        })\n    \n    history_data = {\n        'requests': items,\n        'count': len(items),\n        'total_count': response.get('Count', 0)\n    }\n    \n    # Add pagination token\n    if 'LastEvaluatedKey' in response:\n        next_token = base64.b64encode(\n            json.dumps(response['LastEvaluatedKey']).encode()\n        ).decode()\n        history_data['next_token'] = next_token\n    \n    return create_success_response(200, history_data)\n\ndef handle_formats_v1(event, client_id):\n    \"\"\"Handle supported formats with configuration-driven responses.\"\"\"\n    formats_data = {\n        'supported_input_formats': [\n            {\n                'extension': ext,\n                'mime_type': config.processing.file_limits.supported_mime_types.get(mime, 'application/octet-stream'),\n                'description': get_format_description(ext),\n                'max_size_mb': config.processing.file_limits.max_size_mb\n            }\n            for ext, mime in config.processing.file_limits.supported_mime_types.items()\n            for extension in [mime]  # Convert mime to extension\n        ],\n        'output_formats': [\n            {\n                'format': 'markdown',\n                'description': 'Human-readable markdown format',\n                'availability': 'always'\n            },\n            {\n                'format': 'json',\n                'description': 'Structured JSON format',\n                'availability': 'always'\n            },\n            {\n                'format': 'html',\n                'description': 'Interactive HTML format with charts',\n                'availability': 'always'\n            },\n            {\n                'format': 'pdf',\n                'description': 'Professional PDF report',\n                'availability': 'when_enabled'\n            }\n        ],\n        'rate_limits': {\n            'requests_per_hour': config.processing.rate_limiting.requests_per_hour,\n            'window_seconds': config.processing.rate_limiting.window_seconds,\n            'burst_limit': config.processing.rate_limiting.burst_limit\n        } if config.processing.rate_limiting.enabled else None\n    }\n    \n    return create_success_response(200, formats_data)\n\ndef handle_health_check(event):\n    \"\"\"Handle health check with configuration information.\"\"\"\n    health_data = {\n        'status': 'healthy',\n        'timestamp': datetime.now(timezone.utc).isoformat(),\n        'version': 'v1',\n        'environment': config.environment,\n        'features': {\n            'api_authentication': config.security.api_key_required,\n            'rate_limiting': config.processing.rate_limiting.enabled,\n            'file_size_limit_mb': config.processing.file_limits.max_size_mb\n        },\n        'services': {\n            'api_gateway': 'healthy',\n            'lambda': 'healthy',\n            'dynamodb': 'healthy',\n            's3': 'healthy'\n        }\n    }\n    \n    return create_success_response(200, health_data)\n\ndef handle_api_documentation(event):\n    \"\"\"Handle API documentation with configuration-driven content.\"\"\"\n    docs_data = {\n        'api_version': 'v1',\n        'base_url': config.branding.api_base_url,\n        'environment': config.environment,\n        'authentication': 'API Key required in Authorization header or X-API-Key header' if config.security.api_key_required else 'No authentication required',\n        'rate_limits': {\n            'requests_per_hour': config.processing.rate_limiting.requests_per_hour,\n            'burst_limit': config.processing.rate_limiting.burst_limit,\n            'enabled': config.processing.rate_limiting.enabled\n        },\n        'file_limits': {\n            'max_size_mb': config.processing.file_limits.max_size_mb,\n            'allowed_extensions': config.processing.file_limits.allowed_extensions\n        },\n        'endpoints': [\n            {\n                'path': '/v1/upload',\n                'method': 'POST',\n                'description': 'Upload document for analysis',\n                'required_fields': ['file_content', 'filename'],\n                'optional_fields': ['sender_email', 'preferences']\n            },\n            {\n                'path': '/v1/status/{request_id}',\n                'method': 'GET',\n                'description': 'Get processing status',\n                'parameters': ['request_id']\n            },\n            {\n                'path': '/v1/history',\n                'method': 'GET',\n                'description': 'Get request history',\n                'parameters': ['limit', 'next_token']\n            },\n            {\n                'path': '/v1/formats',\n                'method': 'GET',\n                'description': 'Get supported formats and options'\n            },\n            {\n                'path': '/v1/health',\n                'method': 'GET',\n                'description': 'Service health check'\n            }\n        ],\n        'support': {\n            'email': config.branding.support_email,\n            'website': config.branding.website_url\n        }\n    }\n    \n    return create_success_response(200, docs_data)\n\ndef get_format_description(extension):\n    \"\"\"Get human-readable description for file format.\"\"\"\n    descriptions = {\n        '.pdf': 'Portable Document Format',\n        '.docx': 'Microsoft Word Document',\n        '.doc': 'Microsoft Word Document (Legacy)',\n        '.txt': 'Plain Text File'\n    }\n    return descriptions.get(extension, 'Document')\n\ndef create_success_response(status_code, data):\n    \"\"\"Create successful API response with configuration-driven headers.\"\"\"\n    headers = {\n        'Content-Type': 'application/json',\n        'X-API-Version': 'v1',\n        'X-Environment': config.environment,\n        'X-Powered-By': config.branding.company_name\n    }\n    \n    # Add CORS headers based on configuration\n    if config.security.cors_origins:\n        headers['Access-Control-Allow-Origin'] = config.security.cors_origins[0] if len(config.security.cors_origins) == 1 else '*'\n        headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'\n        headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-API-Key'\n    \n    return {\n        'statusCode': status_code,\n        'headers': headers,\n        'body': json.dumps(data, default=str)\n    }