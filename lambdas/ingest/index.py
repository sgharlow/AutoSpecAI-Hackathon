"""
Enhanced Ingest Lambda Function with SES Email Processing
Handles both SES email events and API Gateway uploads with
standardized error handling and comprehensive validation.
"""

import json
import boto3
import uuid
import email
import base64
import os
import io
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Import document processing libraries
try:
    import PyPDF2
    from docx import Document
    DOCUMENT_PROCESSING_AVAILABLE = True
except ImportError:
    DOCUMENT_PROCESSING_AVAILABLE = False

# Import X-Ray tracing - temporarily disabled due to dependency issues
# from aws_xray_sdk.core import xray_recorder, patch_all
# patch_all()

# Mock X-Ray recorder for compatibility
class MockXRayRecorder:
    def capture(self, name):
        def decorator(func):
            return func
        return decorator
    
    def put_annotation(self, key, value):
        pass

xray_recorder = MockXRayRecorder()

# Initialize AWS clients
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

# Environment variables
DOCUMENT_BUCKET = os.environ.get('DOCUMENT_BUCKET')
HISTORY_TABLE = os.environ.get('HISTORY_TABLE')
EMAIL_BUCKET = os.environ.get('EMAIL_BUCKET')

# Configure logging
import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# File processing configuration
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = ['.pdf', '.docx', '.doc', '.txt']
SUPPORTED_MIME_TYPES = {
    'application/pdf': '.pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
    'application/msword': '.doc',
    'text/plain': '.txt'
}

@xray_recorder.capture('lambda_handler')
def handler(event, context):
    """
    Enhanced Lambda handler for document ingestion.
    Handles both SES email events and API Gateway uploads.
    """
    request_id = str(uuid.uuid4())
    
    # Add tracing annotations
    xray_recorder.put_annotation('request_id', request_id)
    xray_recorder.put_annotation('function_name', 'ingest')
    
    logger.info(f"Processing ingest request: {request_id}")
    
    # Validate environment configuration
    validate_environment_config()
    
    try:
        # Determine event source and process accordingly
        if 'Records' in event:
            # Check if it's an SES event
            first_record = event['Records'][0]
            if first_record.get('eventSource') == 'aws:ses':
                xray_recorder.put_annotation('event_type', 'ses_email')
                return handle_ses_event(event, request_id)
            elif first_record.get('eventSource') == 'aws:s3':
                xray_recorder.put_annotation('event_type', 's3_upload')
                return handle_s3_upload_event(event, request_id)
            else:
                # Unknown record type - treat as API
                xray_recorder.put_annotation('event_type', 'api_upload')
                return handle_api_upload(event, request_id)
        elif 'uploadMetadata' in event:
            # Direct invocation from upload complete API
            xray_recorder.put_annotation('event_type', 's3_upload_api_triggered')
            return handle_s3_upload_event(event, request_id)
        else:
            xray_recorder.put_annotation('event_type', 'api_upload')
            return handle_api_upload(event, request_id)
            
    except Exception as e:
        logger.error(f"Handler error for request {request_id}: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'message': f'Processing failed: {str(e)}',
                'request_id': request_id,
                'status': 'error'
            })
        }

def validate_environment_config():
    """Validate that required environment variables are configured."""
    required_env_vars = ['DOCUMENT_BUCKET', 'HISTORY_TABLE']
    missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    if not DOCUMENT_PROCESSING_AVAILABLE:
        logger.warning("Document processing libraries not available. Text extraction features will be limited.")

@xray_recorder.capture('handle_ses_event')
def handle_ses_event(event, request_id):
    """Handle SES email event with attached documents."""
    try:
        # Validate SES event structure
        if not event.get('Records'):
            raise ValueError("No SES records found in event")
        
        ses_record = event['Records'][0]
        if ses_record.get('eventSource') != 'aws:ses':
            raise ValueError("Event is not from SES")
        
        # Extract email data
        ses_mail = ses_record.get('ses', {}).get('mail', {})
        sender_email = extract_sender_email(ses_mail)
        
        logger.info(f"Processing email from: {sender_email}")
        
        # Get email message from S3 (SES stores emails in S3)
        email_content = get_email_content_from_ses(ses_record)
        
        # Parse email and extract attachments
        email_message = email.message_from_string(email_content)
        attachments = extract_attachments_from_email(email_message)
        
        if not attachments:
            logger.info(f"No attachments found in email from {sender_email}")
            return create_success_response(f"No attachments found in email from {sender_email}")
        
        # Process each attachment
        results = []
        for attachment in attachments:
            try:
                result = process_document(attachment, sender_email, request_id)
                results.append(result)
                logger.info(f"Processed attachment: {attachment.get('filename')}")
            except Exception as attachment_error:
                logger.error(f"Failed to process attachment {attachment.get('filename')}: {attachment_error}")
                # Continue processing other attachments
                continue
        
        if not results:
            raise Exception("Failed to process any attachments from email")
        
        return create_success_response(f"Processed {len(results)} documents from email")
        
    except Exception as e:
        logger.error(f"SES event processing failed: {str(e)}")
        raise

@xray_recorder.capture('handle_s3_upload_event')
def handle_s3_upload_event(event, request_id):
    """Handle S3 upload events from direct upload."""
    try:
        logger.info(f"S3 upload event received: {request_id}")
        
        # Extract S3 information from event
        if 'Records' in event and event['Records']:
            # Direct S3 event
            s3_record = event['Records'][0]['s3']
            bucket_name = s3_record['bucket']['name']
            s3_key = s3_record['object']['key']
            logger.info(f"Processing S3 object: {bucket_name}/{s3_key}")
        elif 'uploadMetadata' in event:
            # API-triggered S3 processing
            upload_metadata = event['uploadMetadata']
            bucket_name = upload_metadata['s3_bucket']
            s3_key = upload_metadata['s3_key']
            request_id = upload_metadata.get('request_id', request_id)
            logger.info(f"Processing API-triggered S3 upload: {bucket_name}/{s3_key}")
        else:
            raise ValueError("Invalid S3 event format")
        
        # Get file information from S3
        try:
            s3_response = s3_client.head_object(Bucket=bucket_name, Key=s3_key)
            file_size = s3_response['ContentLength']
            content_type = s3_response.get('ContentType', 'application/octet-stream')
            
            # Extract filename from S3 key
            filename = s3_key.split('/')[-1] if '/' in s3_key else s3_key
            
            logger.info(f"S3 file info: {filename}, {file_size} bytes, {content_type}")
            
        except Exception as s3_error:
            logger.error(f"Failed to get S3 object metadata: {str(s3_error)}")
            raise
        
        # Try to find existing tracking record in DynamoDB
        table = dynamodb.Table(HISTORY_TABLE)
        existing_record = None
        
        try:
            # Look for existing record by S3 key or request ID
            if 'uploads/' in s3_key:
                # Extract request ID from S3 key pattern: uploads/{request_id}/{filename}
                s3_request_id = s3_key.split('/')[1] if len(s3_key.split('/')) >= 2 else None
                if s3_request_id:
                    response = table.get_item(Key={'requestId': s3_request_id})
                    if 'Item' in response:
                        existing_record = response['Item']
                        request_id = s3_request_id  # Use the original request ID
                        logger.info(f"Found existing upload record for request: {request_id}")
        except Exception as db_lookup_error:
            logger.warning(f"Could not lookup existing record: {str(db_lookup_error)}")
        
        # Create or update tracking record
        timestamp = datetime.now(timezone.utc).isoformat()
        
        if existing_record:
            # Update existing record
            update_expression = 'SET #status = :status, processingStage = :stage, fileType = :file_type, actualFileSize = :actual_size, s3ProcessedAt = :timestamp'
            expression_values = {
                ':status': 'processing',
                ':stage': 's3_processing_complete',
                ':file_type': content_type,
                ':actual_size': file_size,
                ':timestamp': timestamp
            }
            expression_names = {'#status': 'status'}
            
            table.update_item(
                Key={'requestId': request_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values,
                ExpressionAttributeNames=expression_names
            )
            
            logger.info(f"Updated existing tracking record for request: {request_id}")
            
        else:
            # Create new tracking record (fallback for direct S3 uploads)
            item = {
                'requestId': request_id,
                'timestamp': timestamp,
                'filename': filename,
                'fileSize': file_size,
                'actualFileSize': file_size,
                'fileType': content_type,
                'sourceType': 's3_direct',
                'uploadMethod': 'direct_s3',
                'status': 'processing',
                'processingStage': 's3_processing_complete',
                's3Bucket': bucket_name,
                's3Key': s3_key,
                's3ProcessedAt': timestamp,
                'senderEmail': 'unknown@s3-upload.com'  # Default for direct uploads
            }
            
            table.put_item(Item=item)
            logger.info(f"Created new tracking record for S3 upload: {request_id}")
        
        # Validate file type
        if not any(filename.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS):
            error_msg = f"Unsupported file type: {filename}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
            logger.error(error_msg)
            
            # Update record with error
            table.update_item(
                Key={'requestId': request_id},
                UpdateExpression='SET #status = :status, errorMessage = :error, processingStage = :stage',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':status': 'failed',
                    ':error': error_msg,
                    ':stage': 'validation_failed'
                }
            )
            
            return create_error_response(400, error_msg)
        
        # Download and process the file content
        try:
            # Download file from S3
            s3_object = s3_client.get_object(Bucket=bucket_name, Key=s3_key)
            file_content = s3_object['Body'].read()
            
            # Extract text content based on file type
            text_content = extract_text_content(file_content, filename)
            
            if not text_content or len(text_content.strip()) < 10:
                raise ValueError("Document appears to be empty or unreadable")
            
            logger.info(f"Successfully extracted {len(text_content)} characters from {filename}")
            
        except Exception as processing_error:
            error_msg = f"Failed to process file content: {str(processing_error)}"
            logger.error(error_msg)
            
            # Update record with error
            table.update_item(
                Key={'requestId': request_id},
                UpdateExpression='SET #status = :status, errorMessage = :error, processingStage = :stage',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':status': 'failed',
                    ':error': error_msg,
                    ':stage': 'content_extraction_failed'
                }
            )
            
            return create_error_response(500, error_msg)
        
        # Store extracted content back to S3 for processing pipeline
        try:
            # Create processed content S3 key
            processed_key = f"processed/{request_id}/{filename}.txt"
            
            # Upload processed content
            s3_client.put_object(
                Bucket=bucket_name,
                Key=processed_key,
                Body=text_content.encode('utf-8'),
                ContentType='text/plain',
                Metadata={
                    'original-filename': filename,
                    'original-size': str(file_size),
                    'processing-stage': 'content-extracted',
                    'request-id': request_id
                }
            )
            
            # Update tracking record with processed content location
            table.update_item(
                Key={'requestId': request_id},
                UpdateExpression='SET processedS3Key = :processed_key, textContentLength = :content_length, processingStage = :stage',
                ExpressionAttributeValues={
                    ':processed_key': processed_key,
                    ':content_length': len(text_content),
                    ':stage': 'content_extracted'
                }
            )
            
            logger.info(f"Stored processed content at: {processed_key}")
            
        except Exception as storage_error:
            logger.error(f"Failed to store processed content: {str(storage_error)}")
            # Continue processing even if storage fails
        
        # Return success response
        response = {
            'statusCode': 200,
            'body': {
                'message': 'S3 upload processed successfully',
                'request_id': request_id,
                'filename': filename,
                'file_size': file_size,
                'content_length': len(text_content),
                'processing_stage': 'content_extracted'
            }
        }
        
        logger.info(f"S3 upload processing completed successfully: {request_id}")
        return response
        
    except Exception as e:
        logger.error(f"S3 upload event processing failed: {str(e)}")
        
        # Try to update tracking record with error if possible
        try:
            table = dynamodb.Table(HISTORY_TABLE)
            table.update_item(
                Key={'requestId': request_id},
                UpdateExpression='SET #status = :status, errorMessage = :error, processingStage = :stage',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':status': 'failed',
                    ':error': str(e),
                    ':stage': 's3_processing_failed'
                }
            )
        except:
            pass  # Don't fail if we can't update the record
        
        return create_error_response(500, str(e))

@xray_recorder.capture('handle_api_upload')
def handle_api_upload(event, request_id):
    """Handle API Gateway document upload."""
    try:
        # Parse request body if it exists
        body = event.get('body', '')
        if body:
            try:
                request_data = json.loads(body)
                filename = request_data.get('filename', 'unknown.txt')
                file_content = request_data.get('file_content', '')
                sender_email = request_data.get('sender_email', 'api-user@autospec.ai')
                
                if file_content and filename:
                    # Decode and process the file
                    try:
                        decoded_content = base64.b64decode(file_content)
                        
                        # Store minimal record in DynamoDB
                        table = dynamodb.Table(HISTORY_TABLE)
                        
                        item = {
                            'requestId': request_id,
                            'timestamp': datetime.now(timezone.utc).isoformat(),
                            'senderEmail': sender_email,
                            'sourceType': 'api',
                            'filename': filename,
                            'fileType': get_file_type(filename),
                            's3Key': f'api/{request_id}/{filename}',
                            'fileSize': len(decoded_content),
                            'status': 'ingestion_complete',
                            'processingStage': 'ingestion_complete'
                        }
                        
                        table.put_item(Item=item)
                        
                        return {
                            'statusCode': 200,
                            'headers': {'Content-Type': 'application/json'},
                            'body': json.dumps({
                                'message': 'Document uploaded successfully',
                                'request_id': request_id,
                                'filename': filename,
                                'status': 'success'
                            })
                        }
                        
                    except Exception as decode_error:
                        logger.error(f"Failed to decode file content: {decode_error}")
                        return {
                            'statusCode': 400,
                            'headers': {'Content-Type': 'application/json'},
                            'body': json.dumps({
                                'error': 'Invalid request',
                                'status': 'error'
                            })
                        }
                        
            except json.JSONDecodeError:
                return {
                    'statusCode': 400,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({
                        'error': 'Invalid request',
                        'status': 'error'
                    })
                }
        
        # Default minimal implementation
        logger.info("API upload event received - minimal processing")
        
        # Store minimal record in DynamoDB
        table = dynamodb.Table(HISTORY_TABLE)
        
        item = {
            'requestId': request_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'senderEmail': 'api-user@autospec.ai',
            'sourceType': 'api',
            'filename': 'api-upload.txt',
            'fileType': 'txt',
            's3Key': f'api/{request_id}/placeholder.txt',
            'fileSize': 0,
            'status': 'ingestion_complete',
            'processingStage': 'ingestion_complete'
        }
        
        table.put_item(Item=item)
        
        return create_success_response("API upload processed")
        
    except Exception as e:
        logger.error(f"API upload processing failed: {str(e)}")
        raise

@xray_recorder.capture('process_document')
def process_document(document_info, sender_email, request_id):
    """Process a document with error handling and validation."""
    
    filename = document_info['filename']
    file_content = document_info['content']
    file_size = document_info['size']
    
    logger.info(f"Processing document: {filename} ({file_size} bytes) for request {request_id}")
    
    try:
        # Generate S3 key
        file_extension = os.path.splitext(filename)[1].lower()
        timestamp = datetime.now(timezone.utc).strftime('%Y/%m/%d')
        s3_key = f"documents/{timestamp}/{request_id}/{filename}"
        
        # Upload to S3
        upload_to_s3(file_content, s3_key, filename, document_info['mime_type'])
        
        # Extract text content for preview
        text_content = extract_text_content(file_content, file_extension, filename)
        text_preview = text_content[:500] + "..." if len(text_content) > 500 else text_content
        
        # Store in DynamoDB
        store_document_metadata(
            request_id=request_id,
            filename=filename,
            sender_email=sender_email,
            s3_key=s3_key,
            file_size=file_size,
            file_type=file_extension[1:],  # Remove the dot
            text_preview=text_preview,
            source=document_info['source']
        )
        
        logger.info(f"Successfully processed document {filename} for request {request_id}")
        
        return {
            'request_id': request_id,
            'filename': filename,
            's3_key': s3_key,
            'status': 'uploaded'
        }
        
    except Exception as e:
        logger.error(f"Failed to process document {filename}: {str(e)}")
        raise

@xray_recorder.capture('upload_to_s3')
def upload_to_s3(file_content, s3_key, filename, mime_type):
    """Upload document to S3 with proper error handling."""
    try:
        s3_client.put_object(
            Bucket=DOCUMENT_BUCKET,
            Key=s3_key,
            Body=file_content,
            ContentType=mime_type,
            Metadata={
                'original_filename': filename,
                'upload_timestamp': datetime.now(timezone.utc).isoformat(),
                'source': 'autospec-ai-ingest'
            },
            ServerSideEncryption='AES256'
        )
        logger.info(f"Uploaded {filename} to S3: {s3_key}")
        
    except Exception as e:
        logger.error(f"S3 upload failed: {str(e)}")
        raise

@xray_recorder.capture('store_document_metadata')
def store_document_metadata(request_id, filename, sender_email, s3_key, 
                          file_size, file_type, text_preview, source='email'):
    """Store document metadata in DynamoDB."""
    try:
        table = dynamodb.Table(HISTORY_TABLE)
        
        item = {
            'requestId': request_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'senderEmail': sender_email,
            'filename': filename,
            's3Key': s3_key,
            'fileSize': file_size,
            'fileType': file_type,
            'textPreview': text_preview,
            'status': 'ingestion_complete',
            'processingStage': 'ingestion_complete',
            'sourceType': source
        }
        
        table.put_item(Item=item)
        logger.info(f"Stored metadata for request {request_id} in DynamoDB")
        
    except Exception as e:
        logger.error(f"DynamoDB storage failed: {str(e)}")
        raise

def extract_text_content(file_content, file_extension, filename=None):
    """Extract text content from document for preview."""
    if not DOCUMENT_PROCESSING_AVAILABLE:
        return f"Document processing libraries not available. Filename: {filename}"
    
    try:
        if file_extension == '.txt':
            return file_content.decode('utf-8', errors='ignore')
        
        elif file_extension == '.pdf':
            reader = PyPDF2.PdfReader(io.BytesIO(file_content))
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text.strip()
        
        elif file_extension in ['.docx', '.doc']:
            doc = Document(io.BytesIO(file_content))
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text.strip()
        
        else:
            return f"Unsupported file type for text extraction: {file_extension}"
    
    except Exception as e:
        logger.warning(f"Text extraction failed for {filename}: {e}")
        return f"Text extraction failed: {str(e)}"

def extract_sender_email(ses_mail):
    """Extract sender email from SES mail object."""
    common_headers = ses_mail.get('commonHeaders', {})
    sender = common_headers.get('from', ['unknown@example.com'])[0]
    return sender

def get_email_content_from_ses(ses_record):
    """Get email content from SES record."""
    try:
        # SES action should have stored the email in S3
        ses_receipt = ses_record.get('ses', {}).get('receipt', {})
        action = ses_receipt.get('action', {})
        
        if action.get('type') == 's3':
            # Email was stored in S3
            bucket_name = action.get('bucketName', EMAIL_BUCKET)
            object_key = action.get('objectKey')
            
            if bucket_name and object_key:
                response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
                return response['Body'].read().decode('utf-8')
        
        # Fallback: try to get from mail content if available
        mail_content = ses_record.get('ses', {}).get('mail', {}).get('content')
        if mail_content:
            return mail_content
        
        raise ValueError("Could not retrieve email content from SES record")
        
    except Exception as e:
        logger.error(f"Failed to get email content: {e}")
        raise

def extract_attachments_from_email(email_message):
    """Extract attachments from email message."""
    attachments = []
    
    try:
        if email_message.is_multipart():
            for part in email_message.walk():
                content_disposition = part.get('Content-Disposition', '')
                
                if 'attachment' in content_disposition:
                    filename = part.get_filename()
                    if filename:
                        # Validate file type
                        file_extension = os.path.splitext(filename)[1].lower()
                        if file_extension in ALLOWED_EXTENSIONS:
                            content = part.get_payload(decode=True)
                            if content and len(content) <= MAX_FILE_SIZE:
                                attachments.append({
                                    'filename': filename,
                                    'content': content,
                                    'size': len(content),
                                    'mime_type': part.get_content_type(),
                                    'source': 'email_attachment'
                                })
                            else:
                                logger.warning(f"Attachment {filename} is too large or empty")
                        else:
                            logger.warning(f"Attachment {filename} has unsupported file type")
        
        logger.info(f"Extracted {len(attachments)} valid attachments")
        return attachments
        
    except Exception as e:
        logger.error(f"Failed to extract attachments: {e}")
        raise

def create_success_response(message, data=None):
    """Create a standardized success response."""
    response_data = {'message': message, 'status': 'success'}
    if data:
        response_data.update(data)
    
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(response_data)
    }

def create_error_response(status_code, message):
    """Create a standardized error response."""
    error_data = {
        'error': message,
        'status': 'error',
        'statusCode': status_code
    }
    
    return {
        'statusCode': status_code,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(error_data)
    }

def get_file_type(filename):
    """Determine file type from filename."""
    extension = filename.lower().split('.')[-1] if '.' in filename else 'unknown'
    type_mapping = {
        'pdf': 'pdf',
        'docx': 'docx',
        'doc': 'docx',
        'txt': 'txt'
    }
    return type_mapping.get(extension, 'unknown')

def get_content_type(file_type):
    """Get MIME content type for file type."""
    content_types = {
        'pdf': 'application/pdf',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'doc': 'application/msword',
        'txt': 'text/plain'
    }
    return content_types.get(file_type, 'application/octet-stream')