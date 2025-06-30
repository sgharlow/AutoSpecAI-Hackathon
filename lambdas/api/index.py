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

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
lambda_client = boto3.client('lambda')
s3_client = boto3.client('s3')

# Environment variables
HISTORY_TABLE = os.environ.get('HISTORY_TABLE')
DOCUMENT_BUCKET = os.environ.get('DOCUMENT_BUCKET')
INGEST_FUNCTION_NAME = os.environ.get('INGEST_FUNCTION_NAME')
API_KEY_TABLE = os.environ.get('API_KEY_TABLE', 'autospec-ai-api-keys')

# Rate limiting configuration
RATE_LIMIT_REQUESTS = 100  # requests per hour
RATE_LIMIT_WINDOW = 3600   # 1 hour in seconds

# File upload configuration
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB for S3 direct upload
PRESIGNED_URL_EXPIRATION = 3600     # 1 hour
UPLOAD_PREFIX = 'uploads/'

class APIError(Exception):
    """Custom API error class."""
    def __init__(self, message, status_code=400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

def handler(event, context):
    """
    Enhanced API Gateway handler with versioning and advanced features.
    """
    try:
        logger.info(f"API request: {json.dumps(event, default=str)}")
        
        # Extract request information
        http_method = event.get('httpMethod', 'GET')
        path = event.get('path', '')
        headers = event.get('headers', {})
        query_params = event.get('queryStringParameters') or {}
        body = event.get('body', '')
        
        # Handle API versioning
        api_version = extract_api_version(path, headers)
        
        # Authenticate request
        auth_result = authenticate_request(headers, query_params)
        if not auth_result['authenticated']:
            return create_error_response(401, 'Unauthorized', auth_result['message'])
        
        # Check rate limiting
        rate_limit_result = check_rate_limit(auth_result['client_id'])
        if not rate_limit_result['allowed']:
            return create_error_response(429, 'Too Many Requests', rate_limit_result['message'])
        
        # Route request to appropriate handler
        if path.startswith('/v1/upload/initiate') or path.startswith('/upload/initiate'):
            if http_method == 'POST':
                return handle_upload_initiate_v1(event, auth_result['client_id'])
            else:
                return create_error_response(405, 'Method Not Allowed', 'Only POST method is supported')
        
        elif path.startswith('/v1/upload/complete') or path.startswith('/upload/complete'):
            if http_method == 'POST':
                return handle_upload_complete_v1(event, auth_result['client_id'])
            else:
                return create_error_response(405, 'Method Not Allowed', 'Only POST method is supported')
        
        elif path.startswith('/v1/upload') or path.startswith('/upload'):
            if http_method == 'POST':
                return handle_upload_v1(event, auth_result['client_id'])
            else:
                return create_error_response(405, 'Method Not Allowed', 'Only POST method is supported')
        
        elif path.startswith('/v1/status') or path.startswith('/status'):
            if http_method == 'GET':
                return handle_status_v1(event, auth_result['client_id'])
            else:
                return create_error_response(405, 'Method Not Allowed', 'Only GET method is supported')
        
        elif path.startswith('/v1/history') or path.startswith('/history'):
            if http_method == 'GET':
                return handle_history_v1(event, auth_result['client_id'])
            else:
                return create_error_response(405, 'Method Not Allowed', 'Only GET method is supported')
        
        elif path.startswith('/v1/formats') or path.startswith('/formats'):
            if http_method == 'GET':
                return handle_formats_v1(event, auth_result['client_id'])
            else:
                return create_error_response(405, 'Method Not Allowed', 'Only GET method is supported')
        
        elif path.startswith('/v1/health') or path.startswith('/health'):
            return handle_health_check(event)
        
        elif path.startswith('/v1/docs') or path.startswith('/docs'):
            return handle_api_documentation(event)
        
        else:
            return create_error_response(404, 'Not Found', f'Endpoint {path} not found')
        
    except APIError as e:
        return create_error_response(e.status_code, 'API Error', e.message)
    except Exception as e:
        logger.error(f"Unexpected error in API handler: {str(e)}")
        return create_error_response(500, 'Internal Server Error', 'An unexpected error occurred')

def extract_api_version(path, headers):
    """Extract API version from path or headers."""
    # Check path for version
    if '/v1/' in path:
        return 'v1'
    elif '/v2/' in path:
        return 'v2'
    
    # Check headers for version
    version_header = headers.get('API-Version') or headers.get('api-version')
    if version_header:
        return version_header
    
    # Default to v1
    return 'v1'

def authenticate_request(headers, query_params):
    """Authenticate API request using API keys."""
    try:
        # Extract API key from headers or query parameters
        api_key = None
        
        # Check Authorization header
        auth_header = headers.get('Authorization') or headers.get('authorization')
        if auth_header and auth_header.startswith('Bearer '):
            api_key = auth_header[7:]  # Remove 'Bearer ' prefix
        
        # Check X-API-Key header
        if not api_key:
            api_key = headers.get('X-API-Key') or headers.get('x-api-key')
        
        # Check query parameter
        if not api_key:
            api_key = query_params.get('api_key')
        
        # Check environment-based authentication requirements
        environment = os.environ.get('ENVIRONMENT', 'dev')
        require_auth = os.environ.get('REQUIRE_API_AUTH', 'true').lower() == 'true'
        
        # For development environments, optionally allow requests without API key
        if not api_key:
            if environment == 'dev' and not require_auth:
                logger.warning("No API key provided, allowing for development environment")
                return {
                    'authenticated': True,
                    'client_id': 'dev-client',
                    'rate_limit_tier': 'development',
                    'environment': 'development'
                }
            else:
                return {
                    'authenticated': False,
                    'message': 'API key is required'
                }
        
        # Validate API key
        return validate_api_key(api_key)
        
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        return {
            'authenticated': False,
            'message': 'Authentication failed'
        }

def validate_api_key(api_key):
    """Validate API key against DynamoDB table."""
    try:
        # Hash the API key for secure lookup
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        # Get API key table
        api_key_table_name = os.environ.get('API_KEY_TABLE', 'autospec-ai-api-keys')
        
        try:
            table = dynamodb.Table(api_key_table_name)
            
            # Look up the hashed API key
            response = table.get_item(
                Key={'keyHash': key_hash}
            )
            
            if 'Item' not in response:
                return {
                    'authenticated': False,
                    'message': 'Invalid API key'
                }
            
            item = response['Item']
            
            # Check if key is active
            if not item.get('isActive', False):
                return {
                    'authenticated': False,
                    'message': 'API key is disabled'
                }
            
            # Check expiration date
            expiry_date = item.get('expiryDate')
            if expiry_date and datetime.now(timezone.utc).isoformat() > expiry_date:
                return {
                    'authenticated': False,
                    'message': 'API key has expired'
                }
            
            # Update last used timestamp
            table.update_item(
                Key={'keyHash': key_hash},
                UpdateExpression='SET lastUsed = :timestamp, usageCount = usageCount + :inc',
                ExpressionAttributeValues={
                    ':timestamp': datetime.now(timezone.utc).isoformat(),
                    ':inc': 1
                }
            )
            
            return {
                'authenticated': True,
                'client_id': item.get('clientId', f"client-{key_hash[:8]}"),
                'rate_limit_tier': item.get('rateLimitTier', 'standard'),
                'client_name': item.get('clientName', 'Unknown'),
                'permissions': item.get('permissions', ['read', 'write'])
            }
            
        except Exception as dynamodb_error:
            logger.error(f"DynamoDB API key lookup failed: {str(dynamodb_error)}")
            # Fallback to basic validation for availability
            if len(api_key) >= 32:  # Minimum secure key length
                logger.warning("DynamoDB unavailable, using fallback API key validation")
                return {
                    'authenticated': True,
                    'client_id': f"fallback-{hashlib.sha256(api_key.encode()).hexdigest()[:8]}",
                    'rate_limit_tier': 'basic',
                    'fallback_mode': True
                }
            else:
                return {
                    'authenticated': False,
                    'message': 'Invalid API key format and database unavailable'
                }
        
    except Exception as e:
        logger.error(f"API key validation error: {str(e)}")
        return {
            'authenticated': False,
            'message': 'API key validation failed'
        }

def check_rate_limit(client_id):
    """Check rate limiting for client using DynamoDB."""
    try:
        current_time = int(time.time())
        window_start = current_time - RATE_LIMIT_WINDOW
        
        # Get rate limit table
        rate_limit_table_name = os.environ.get('RATE_LIMIT_TABLE', 'autospec-ai-rate-limits')
        
        logger.info(f"Using rate limit table: {rate_limit_table_name}")
        
        try:
            table = dynamodb.Table(rate_limit_table_name)
            
            # Get current usage for this client in the current window
            response = table.get_item(
                Key={'clientId': client_id}
            )
            
            if 'Item' in response:
                item = response['Item']
                
                # Check if the window has expired
                if item.get('windowStart', 0) < window_start:
                    # Reset the counter for new window
                    request_count = 1
                    window_start_time = current_time
                else:
                    # Increment counter in current window
                    request_count = item.get('requestCount', 0) + 1
                    window_start_time = item.get('windowStart', current_time)
                
                # Check if rate limit exceeded
                if request_count > RATE_LIMIT_REQUESTS:
                    return {
                        'allowed': False,
                        'remaining': 0,
                        'reset_time': window_start_time + RATE_LIMIT_WINDOW,
                        'message': 'Rate limit exceeded'
                    }
                
                # Update the counter
                table.put_item(
                    Item={
                        'clientId': client_id,
                        'requestCount': request_count,
                        'windowStart': window_start_time,
                        'lastRequest': current_time,
                        'ttl': current_time + RATE_LIMIT_WINDOW + 3600  # TTL for cleanup
                    }
                )
                
                return {
                    'allowed': True,
                    'remaining': max(0, RATE_LIMIT_REQUESTS - request_count),
                    'reset_time': window_start_time + RATE_LIMIT_WINDOW
                }
            else:
                # First request for this client
                table.put_item(
                    Item={
                        'clientId': client_id,
                        'requestCount': 1,
                        'windowStart': current_time,
                        'lastRequest': current_time,
                        'ttl': current_time + RATE_LIMIT_WINDOW + 3600
                    }
                )
                
                return {
                    'allowed': True,
                    'remaining': RATE_LIMIT_REQUESTS - 1,
                    'reset_time': current_time + RATE_LIMIT_WINDOW
                }
                
        except Exception as dynamodb_error:
            logger.warning(f"DynamoDB rate limiting failed: {str(dynamodb_error)}")
            # Fallback to allow request if DynamoDB fails
            return {
                'allowed': True,
                'remaining': RATE_LIMIT_REQUESTS,
                'reset_time': current_time + RATE_LIMIT_WINDOW,
                'message': 'Rate limiting unavailable - request allowed'
            }
        
    except Exception as e:
        logger.error(f"Rate limiting error: {str(e)}")
        return {
            'allowed': True,  # Allow on error for availability
            'remaining': RATE_LIMIT_REQUESTS,
            'reset_time': current_time + RATE_LIMIT_WINDOW,
            'message': 'Rate limiting check failed'
        }

def handle_upload_v1(event, client_id):
    """Handle document upload API v1."""
    try:
        # Parse request body
        body = event.get('body', '')
        if event.get('isBase64Encoded'):
            body = base64.b64decode(body).decode('utf-8')
        
        if not body:
            raise APIError('Request body is required', 400)
        
        try:
            request_data = json.loads(body)
        except json.JSONDecodeError:
            raise APIError('Invalid JSON in request body', 400)
        
        # Validate required fields
        required_fields = ['file_content', 'filename']
        for field in required_fields:
            if field not in request_data:
                raise APIError(f'Missing required field: {field}', 400)
        
        # Validate file content
        try:
            file_content = base64.b64decode(request_data['file_content'])
        except Exception:
            raise APIError('Invalid base64 file content', 400)
        
        # Validate file size (max 10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        if len(file_content) > max_size:
            raise APIError(f'File size exceeds maximum of {max_size} bytes', 413)
        
        # Validate file type
        filename = request_data['filename']
        allowed_extensions = ['.pdf', '.docx', '.doc', '.txt']
        if not any(filename.lower().endswith(ext) for ext in allowed_extensions):
            raise APIError('Unsupported file type. Allowed: PDF, DOCX, TXT', 400)
        
        # Generate request ID
        request_id = str(uuid.uuid4())
        
        # Add client information to request
        enhanced_request = request_data.copy()
        enhanced_request.update({
            'client_id': client_id,
            'request_id': request_id,
            'api_version': 'v1',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'use_existing_request_id': True  # Signal ingest function to use this ID
        })
        
        # Invoke ingest function
        lambda_response = lambda_client.invoke(
            FunctionName=INGEST_FUNCTION_NAME,
            InvocationType='Event',  # Async invocation
            Payload=json.dumps({
                'body': json.dumps(enhanced_request),
                'source': 'api_v1'
            })
        )
        
        # Return response
        response_data = {
            'request_id': request_id,
            'status': 'accepted',
            'message': 'Document uploaded and processing started',
            'filename': filename,
            'estimated_processing_time': '2-5 minutes'
        }
        
        return create_success_response(202, response_data)
        
    except APIError:
        raise
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        raise APIError('Upload processing failed', 500)

def handle_upload_initiate_v1(event, client_id):
    """Handle S3 pre-signed URL generation for large file uploads."""
    try:
        # Parse request body
        body = event.get('body', '')
        if event.get('isBase64Encoded'):
            body = base64.b64decode(body).decode('utf-8')
        
        if not body:
            raise APIError('Request body is required', 400)
        
        try:
            request_data = json.loads(body)
        except json.JSONDecodeError:
            raise APIError('Invalid JSON in request body', 400)
        
        # Validate required fields
        required_fields = ['filename', 'file_size']
        for field in required_fields:
            if field not in request_data:
                raise APIError(f'Missing required field: {field}', 400)
        
        filename = request_data['filename']
        file_size = int(request_data['file_size'])
        content_type = request_data.get('content_type', 'application/octet-stream')
        metadata = request_data.get('metadata', {})
        
        # Validate file size
        if file_size <= 0:
            raise APIError('File size must be greater than 0', 400)
        if file_size > MAX_FILE_SIZE:
            raise APIError(f'File size exceeds maximum of {MAX_FILE_SIZE // (1024*1024)}MB', 413)
        
        # Validate file type
        allowed_extensions = ['.pdf', '.docx', '.doc', '.txt']
        if not any(filename.lower().endswith(ext) for ext in allowed_extensions):
            raise APIError('Unsupported file type. Allowed: PDF, DOCX, TXT', 400)
        
        # Generate request ID and S3 key
        request_id = str(uuid.uuid4())
        s3_key = f"{UPLOAD_PREFIX}{request_id}/{filename}"
        
        # Generate pre-signed URL for S3 upload
        try:
            presigned_url = s3_client.generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': DOCUMENT_BUCKET,
                    'Key': s3_key,
                    'ContentType': content_type,
                    'ContentLength': file_size
                },
                ExpiresIn=PRESIGNED_URL_EXPIRATION,
                HttpMethod='PUT'
            )
        except Exception as s3_error:
            logger.error(f"S3 presigned URL generation failed: {str(s3_error)}")
            raise APIError('Failed to generate upload URL', 500)
        
        # Store upload tracking record in DynamoDB
        try:
            table = dynamodb.Table(HISTORY_TABLE)
            
            upload_record = {
                'requestId': request_id,
                'clientId': client_id,
                'filename': filename,
                'fileSize': file_size,
                'contentType': content_type,
                'uploadMethod': 'direct_s3',
                'uploadStatus': 'initiated',
                'status': 'upload_initiated',
                'processingStage': 'upload_pending',
                's3Key': s3_key,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'uploadInitiatedAt': datetime.now(timezone.utc).isoformat(),
                'metadata': metadata
            }
            
            table.put_item(Item=upload_record)
            
        except Exception as db_error:
            logger.error(f"DynamoDB upload record creation failed: {str(db_error)}")
            raise APIError('Failed to create upload tracking record', 500)
        
        # Return response with upload instructions
        response_data = {
            'request_id': request_id,
            'upload_url': presigned_url,
            'upload_method': 'PUT',
            'upload_headers': {
                'Content-Type': content_type,
                'Content-Length': str(file_size)
            },
            'expires_in': PRESIGNED_URL_EXPIRATION,
            'max_file_size': MAX_FILE_SIZE,
            'instructions': {
                'method': 'PUT',
                'url': presigned_url,
                'headers': {
                    'Content-Type': content_type,
                    'Content-Length': str(file_size)
                },
                'note': 'Upload file directly to this URL using PUT method'
            },
            'next_step': f'After upload, optionally call POST /v1/upload/complete with request_id to verify upload'
        }
        
        return create_success_response(200, response_data)
        
    except APIError:
        raise
    except Exception as e:
        logger.error(f"Upload initiate error: {str(e)}")
        raise APIError('Upload initiation failed', 500)

def handle_upload_complete_v1(event, client_id):
    """Handle upload completion verification and trigger processing."""
    try:
        # Parse request body
        body = event.get('body', '')
        if event.get('isBase64Encoded'):
            body = base64.b64decode(body).decode('utf-8')
        
        if not body:
            raise APIError('Request body is required', 400)
        
        try:
            request_data = json.loads(body)
        except json.JSONDecodeError:
            raise APIError('Invalid JSON in request body', 400)
        
        # Validate required fields
        if 'request_id' not in request_data:
            raise APIError('Missing required field: request_id', 400)
        
        request_id = request_data['request_id']
        
        # Get upload tracking record
        try:
            table = dynamodb.Table(HISTORY_TABLE)
            response = table.get_item(Key={'requestId': request_id})
            
            if 'Item' not in response:
                raise APIError(f'Upload request {request_id} not found', 404)
            
            upload_record = response['Item']
            
            # Verify this request belongs to the client
            if upload_record.get('clientId') != client_id:
                raise APIError('Unauthorized access to upload request', 403)
            
        except APIError:
            raise
        except Exception as db_error:
            logger.error(f"DynamoDB lookup failed: {str(db_error)}")
            raise APIError('Failed to lookup upload request', 500)
        
        # Verify file was uploaded to S3
        s3_key = upload_record.get('s3Key')
        if not s3_key:
            raise APIError('Upload record missing S3 key', 500)
        
        try:
            # Check if object exists in S3
            s3_client.head_object(Bucket=DOCUMENT_BUCKET, Key=s3_key)
            
            # Get actual file size for verification
            s3_response = s3_client.head_object(Bucket=DOCUMENT_BUCKET, Key=s3_key)
            actual_file_size = s3_response['ContentLength']
            declared_file_size = upload_record.get('fileSize', 0)
            
            # Update upload status
            table.update_item(
                Key={'requestId': request_id},
                UpdateExpression='SET uploadStatus = :status, actualFileSize = :size, uploadCompletedAt = :timestamp, #status = :processing_status, processingStage = :stage',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':status': 'completed',
                    ':size': actual_file_size,
                    ':timestamp': datetime.now(timezone.utc).isoformat(),
                    ':processing_status': 'processing',
                    ':stage': 'file_uploaded'
                }
            )
            
            # Trigger processing by invoking ingest function
            enhanced_request = {
                'request_id': request_id,
                's3_bucket': DOCUMENT_BUCKET,
                's3_key': s3_key,
                'client_id': client_id,
                'api_version': 'v1',
                'upload_method': 'direct_s3',
                'metadata': upload_record.get('metadata', {}),
                'source': 'upload_complete_api'
            }
            
            lambda_response = lambda_client.invoke(
                FunctionName=INGEST_FUNCTION_NAME,
                InvocationType='Event',  # Async invocation
                Payload=json.dumps({
                    'Records': [{
                        'eventSource': 'aws:s3',
                        'eventName': 's3:ObjectCreated:Put',
                        's3': {
                            'bucket': {'name': DOCUMENT_BUCKET},
                            'object': {'key': s3_key}
                        }
                    }],
                    'uploadMetadata': enhanced_request
                })
            )
            
            # Return response
            response_data = {
                'request_id': request_id,
                'status': 'upload_verified',
                'message': 'Upload verified and processing started',
                'filename': upload_record.get('filename'),
                'declared_size': declared_file_size,
                'actual_size': actual_file_size,
                'size_match': declared_file_size == actual_file_size,
                'estimated_processing_time': '2-5 minutes'
            }
            
            return create_success_response(200, response_data)
            
        except ClientError as s3_error:
            if s3_error.response['Error']['Code'] == 'NoSuchKey':
                raise APIError('File not found in S3. Upload may have failed or not completed.', 404)
            else:
                logger.error(f"S3 verification failed: {str(s3_error)}")
                raise APIError('Failed to verify uploaded file', 500)
        
    except APIError:
        raise
    except Exception as e:
        logger.error(f"Upload complete error: {str(e)}")
        raise APIError('Upload completion verification failed', 500)

def handle_status_v1(event, client_id):
    """Handle status check API v1."""
    try:
        # Extract request ID from path or query parameters
        query_params = event.get('queryStringParameters') or {}
        path_params = event.get('pathParameters') or {}
        
        request_id = path_params.get('request_id') or query_params.get('request_id')
        
        if not request_id:
            raise APIError('Request ID is required', 400)
        
        # Get status from DynamoDB
        table = dynamodb.Table(HISTORY_TABLE)
        
        logger.info(f"Looking up request_id: {request_id} in table: {HISTORY_TABLE}")
        
        try:
            response = table.query(
                KeyConditionExpression='requestId = :id',
                ExpressionAttributeValues={':id': request_id},
                ScanIndexForward=False,  # Get latest first
                Limit=1
            )
            
            logger.info(f"DynamoDB query response: {response.get('Count', 0)} items found")
            
            if not response['Items']:
                # Try a fallback scan to debug
                logger.warning(f"Query failed, attempting scan for debugging...")
                scan_response = table.scan(
                    FilterExpression='requestId = :id',
                    ExpressionAttributeValues={':id': request_id},
                    Limit=1
                )
                logger.info(f"Scan response: {scan_response.get('Count', 0)} items found")
                
                if scan_response['Items']:
                    logger.warning(f"Found item via scan but not query - possible index issue")
                    response = scan_response
                else:
                    raise APIError(f'Request {request_id} not found in database', 404)
                    
        except Exception as db_error:
            logger.error(f"DynamoDB error: {str(db_error)}")
            raise APIError(f'Database error while looking up request {request_id}', 500)
        
        item = response['Items'][0]
        
        # Format status response
        status_data = {
            'request_id': request_id,
            'filename': item.get('filename'),
            'status': item.get('status'),
            'processing_stage': item.get('processingStage'),
            'created_at': item.get('timestamp'),
            'updated_at': item.get('processedAt') or item.get('deliveredAt'),
            'file_type': item.get('fileType'),
            'file_size': item.get('fileSize')
        }
        
        # Add progress information
        stage_progress = {
            'ingestion_complete': 25,
            'ai_processing_in_progress': 50,
            'ai_processing_complete': 75,
            'formatting_in_progress': 85,
            'delivery_complete': 100
        }
        
        current_stage = item.get('processingStage', 'unknown')
        status_data['progress_percentage'] = stage_progress.get(current_stage, 0)
        
        # Add error information if failed
        if item.get('status') == 'failed':
            status_data['error_message'] = item.get('errorMessage')
        
        # Add download links if completed
        if item.get('status') == 'delivered':
            status_data['download_links'] = {
                'note': 'Full results sent via email. API download endpoints coming soon.'
            }
        
        return create_success_response(200, status_data)
        
    except APIError:
        raise
    except Exception as e:
        logger.error(f"Status check error: {str(e)}")
        raise APIError('Status check failed', 500)

def handle_history_v1(event, client_id):
    """Handle request history API v1."""
    try:
        query_params = event.get('queryStringParameters') or {}
        
        # Get pagination parameters
        limit = min(int(query_params.get('limit', 10)), 100)  # Max 100 items
        last_evaluated_key = query_params.get('next_token')
        
        # Get client's requests (simplified - would need GSI in production)
        table = dynamodb.Table(HISTORY_TABLE)
        
        logger.info(f"Scanning history table: {HISTORY_TABLE} with limit: {limit}")
        
        # For demo, return all recent requests
        scan_kwargs = {
            'Limit': limit
        }
        
        if last_evaluated_key:
            try:
                scan_kwargs['ExclusiveStartKey'] = json.loads(base64.b64decode(last_evaluated_key))
            except Exception:
                raise APIError('Invalid next_token', 400)
        
        try:
            response = table.scan(**scan_kwargs)
            logger.info(f"History scan returned {response.get('Count', 0)} items")
        except Exception as scan_error:
            logger.error(f"History scan failed: {str(scan_error)}")
            raise APIError(f'Failed to retrieve history: {str(scan_error)}', 500)
        
        # Sort items by timestamp in descending order (newest first)
        if 'Items' in response:
            response['Items'] = sorted(response['Items'], 
                                     key=lambda x: x.get('timestamp', ''), 
                                     reverse=True)
        
        # Format response
        items = []
        for item in response['Items']:
            items.append({
                'request_id': item.get('requestId'),
                'filename': item.get('filename'),
                'status': item.get('status'),
                'created_at': item.get('timestamp'),
                'file_type': item.get('fileType'),
                'file_size': item.get('fileSize')
            })
        
        history_data = {
            'requests': items,
            'count': len(items),
            'total_count': response.get('Count', 0)
        }
        
        # Add pagination token if more results available
        if 'LastEvaluatedKey' in response:
            next_token = base64.b64encode(
                json.dumps(response['LastEvaluatedKey']).encode()
            ).decode()
            history_data['next_token'] = next_token
        
        return create_success_response(200, history_data)
        
    except APIError:
        raise
    except Exception as e:
        logger.error(f"History error: {str(e)}")
        raise APIError('History retrieval failed', 500)

def handle_formats_v1(event, client_id):
    """Handle supported formats API v1."""
    try:
        formats_data = {
            'supported_input_formats': [
                {
                    'extension': '.pdf',
                    'mime_type': 'application/pdf',
                    'description': 'Portable Document Format',
                    'max_size_mb': 10
                },
                {
                    'extension': '.docx',
                    'mime_type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    'description': 'Microsoft Word Document',
                    'max_size_mb': 10
                },
                {
                    'extension': '.doc',
                    'mime_type': 'application/msword',
                    'description': 'Microsoft Word Document (Legacy)',
                    'max_size_mb': 10
                },
                {
                    'extension': '.txt',
                    'mime_type': 'text/plain',
                    'description': 'Plain Text File',
                    'max_size_mb': 10
                }
            ],
            'output_formats': [
                {
                    'format': 'markdown',
                    'description': 'Human-readable markdown format',
                    'availability': 'always'
                },
                {
                    'format': 'json',
                    'description': 'Structured JSON format',
                    'availability': 'always'
                },
                {
                    'format': 'html',
                    'description': 'Interactive HTML format with charts',
                    'availability': 'always'
                },
                {
                    'format': 'pdf',
                    'description': 'Professional PDF report',
                    'availability': 'when_enabled'
                }
            ],
            'quality_levels': [
                {
                    'level': 'standard',
                    'description': 'Basic formatting, minimal charts',
                    'features': ['markdown', 'json', 'html']
                },
                {
                    'level': 'high',
                    'description': 'Enhanced formatting with charts',
                    'features': ['markdown', 'json', 'html', 'charts', 'detailed_analysis']
                },
                {
                    'level': 'premium',
                    'description': 'Full feature set with advanced visualizations',
                    'features': ['markdown', 'json', 'html', 'pdf', 'charts', 'interactive', 'detailed_analysis']
                }
            ]
        }
        
        return create_success_response(200, formats_data)
        
    except Exception as e:
        logger.error(f"Formats endpoint error: {str(e)}")
        raise APIError('Formats retrieval failed', 500)

def handle_health_check(event):
    """Handle health check endpoint."""
    try:
        health_data = {
            'status': 'healthy',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'version': 'v1',
            'services': {
                'api_gateway': 'healthy',
                'lambda': 'healthy',
                'dynamodb': 'healthy',
                's3': 'healthy'
            }
        }
        
        return create_success_response(200, health_data)
        
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return create_error_response(503, 'Service Unavailable', 'Health check failed')

def handle_api_documentation(event):
    """Handle API documentation endpoint."""
    try:
        docs_data = {
            'api_version': 'v1',
            'base_url': 'https://api.autospec.ai/v1',
            'authentication': 'API Key required in Authorization header or X-API-Key header',
            'rate_limits': {
                'requests_per_hour': RATE_LIMIT_REQUESTS,
                'burst_limit': 10
            },
            'endpoints': [
                {
                    'path': '/v1/upload',
                    'method': 'POST',
                    'description': 'Upload document for analysis',
                    'required_fields': ['file_content', 'filename'],
                    'optional_fields': ['sender_email', 'preferences']
                },
                {
                    'path': '/v1/status/{request_id}',
                    'method': 'GET',
                    'description': 'Get processing status',
                    'parameters': ['request_id']
                },
                {
                    'path': '/v1/history',
                    'method': 'GET',
                    'description': 'Get request history',
                    'parameters': ['limit', 'next_token']
                },
                {
                    'path': '/v1/formats',
                    'method': 'GET',
                    'description': 'Get supported formats and options'
                },
                {
                    'path': '/v1/health',
                    'method': 'GET',
                    'description': 'Service health check'
                }
            ],
            'examples': {
                'upload_curl': '''curl -X POST https://api.autospec.ai/v1/upload \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "file_content": "base64_encoded_content",
    "filename": "requirements.pdf",
    "sender_email": "user@example.com",
    "preferences": {
      "quality": "premium",
      "formats": ["html", "pdf"]
    }
  }'
''',
                'status_curl': '''curl -X GET https://api.autospec.ai/v1/status/your-request-id \\
  -H "Authorization: Bearer YOUR_API_KEY"
'''
            }
        }
        
        return create_success_response(200, docs_data)
        
    except Exception as e:
        logger.error(f"Documentation error: {str(e)}")
        raise APIError('Documentation retrieval failed', 500)

def create_success_response(status_code, data):
    """Create successful API response."""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-API-Key',
            'X-API-Version': 'v1'
        },
        'body': json.dumps(data, default=str)
    }

def create_error_response(status_code, error_type, message):
    """Create error API response."""
    error_data = {
        'error': {
            'type': error_type,
            'message': message,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    }
    
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-API-Key',
            'X-API-Version': 'v1'
        },
        'body': json.dumps(error_data)
    }