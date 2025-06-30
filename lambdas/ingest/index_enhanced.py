"""
Enhanced Ingest Lambda Function with Standardized Error Handling

This is an improved version of the ingest function that demonstrates
the use of standardized error handling, structured logging, and
better error classification.
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

# Import our standardized error handling
import sys
sys.path.append('/opt/python/lib/python3.11/site-packages')
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import (
    ErrorHandler, ValidationError, FileProcessingError, 
    ExternalServiceError, validate_required_fields, 
    validate_file_type, handle_aws_error
)
from format_preferences import extract_preferences_from_request, FormatPreferences

# Import X-Ray tracing
from aws_xray_sdk.core import xray_recorder, patch_all
patch_all()

# Initialize error handler
error_handler = ErrorHandler(
    function_name='ingest',
    environment=os.environ.get('ENVIRONMENT', 'dev')
)

# Initialize AWS clients
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

# Environment variables
DOCUMENT_BUCKET = os.environ.get('DOCUMENT_BUCKET')
HISTORY_TABLE = os.environ.get('HISTORY_TABLE')
EMAIL_BUCKET = os.environ.get('EMAIL_BUCKET')

# File processing configuration
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = ['.pdf', '.docx', '.doc', '.txt']
SUPPORTED_MIME_TYPES = {
    'application/pdf': '.pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
    'application/msword': '.doc',
    'text/plain': '.txt'
}

@error_handler.lambda_handler
@xray_recorder.capture('lambda_handler')
def handler(event, context):
    """
    Enhanced Lambda handler for document ingestion.
    Handles both SES email events and API Gateway uploads with
    standardized error handling and comprehensive validation.
    """
    request_id = str(uuid.uuid4())
    
    # Add tracing annotations
    xray_recorder.put_annotation('request_id', request_id)
    xray_recorder.put_annotation('function_name', 'ingest')
    
    error_handler.logger.info(f"Processing ingest request: {request_id}")
    
    # Validate environment configuration
    validate_environment_config()
    
    # Determine event source and process accordingly
    if 'Records' in event:
        xray_recorder.put_annotation('event_type', 'ses_email')
        return handle_ses_event(event, request_id)
    else:
        xray_recorder.put_annotation('event_type', 'api_upload')
        return handle_api_upload(event, request_id)

def validate_environment_config():
    """Validate that required environment variables are configured."""
    required_env_vars = ['DOCUMENT_BUCKET', 'HISTORY_TABLE', 'EMAIL_BUCKET']
    missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
    
    if missing_vars:
        raise ValidationError(
            f"Missing required environment variables: {', '.join(missing_vars)}",
            details={'missing_variables': missing_vars}
        )
    
    if not DOCUMENT_PROCESSING_AVAILABLE:
        error_handler.logger.warning(
            "Document processing libraries not available. "
            "Text extraction features will be limited."
        )

@xray_recorder.capture('handle_ses_event')
def handle_ses_event(event, request_id):
    """Handle SES email event with attached documents."""
    try:
        # Validate SES event structure
        if not event.get('Records'):
            raise ValidationError("No SES records found in event")
        
        ses_record = event['Records'][0]
        if ses_record.get('eventSource') != 'aws:ses':
            raise ValidationError("Event is not from SES")
        
        # Extract email data
        ses_mail = ses_record.get('ses', {}).get('mail', {})
        sender_email = extract_sender_email(ses_mail)
        
        # Get email message from S3 (SES stores large emails in S3)
        email_content = get_email_content_from_ses(ses_record)
        
        # Parse email and extract attachments
        email_message = email.message_from_string(email_content)
        attachments = extract_attachments_from_email(email_message)
        
        if not attachments:
            # Send response email indicating no attachments found
            send_no_attachments_response(sender_email, request_id)
            return create_success_response(f"No attachments found in email from {sender_email}")
        
        # Process each attachment
        results = []
        for attachment in attachments:
            try:
                result = process_document_attachment(attachment, sender_email, request_id)
                results.append(result)
            except Exception as attachment_error:
                error_handler.logger.error(
                    f"Failed to process attachment {attachment.get('filename')}: {attachment_error}"
                )
                # Continue processing other attachments
                continue
        
        if not results:
            raise FileProcessingError("Failed to process any attachments from email")
        
        return create_success_response(f"Processed {len(results)} documents from email")
        
    except Exception as e:
        if isinstance(e, (ValidationError, FileProcessingError)):
            raise
        else:
            handle_aws_error(e, 'SES') if hasattr(e, 'response') else None
            raise ExternalServiceError(f"SES event processing failed: {str(e)}", 'SES')

@xray_recorder.capture('handle_api_upload')
def handle_api_upload(event, request_id):
    """Handle API Gateway document upload."""
    try:
        # Parse request body
        body = event.get('body', '')
        if event.get('isBase64Encoded'):
            body = base64.b64decode(body).decode('utf-8')
        
        if not body:
            raise ValidationError("Request body is required")
        
        try:
            request_data = json.loads(body)
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON in request body: {str(e)}")
        
        # Check if this is a request ID reuse (from API function)
        if request_data.get('use_existing_request_id') and request_data.get('request_id'):
            request_id = request_data['request_id']
            xray_recorder.put_annotation('request_id_reused', True)
        
        # Validate required fields
        validate_required_fields(request_data, ['file_content', 'filename'])
        
        # Extract and validate file data
        filename = request_data['filename']
        validate_file_type(filename, ALLOWED_EXTENSIONS)
        
        # Decode file content
        try:
            file_content = base64.b64decode(request_data['file_content'])
        except Exception as e:
            raise ValidationError(f"Invalid base64 file content: {str(e)}")
        
        # Validate file size
        if len(file_content) > MAX_FILE_SIZE:
            raise ValidationError(
                f"File size ({len(file_content)} bytes) exceeds maximum allowed ({MAX_FILE_SIZE} bytes)",
                details={'file_size': len(file_content), 'max_size': MAX_FILE_SIZE}
            )
        
        # Extract additional metadata
        sender_email = request_data.get('sender_email', 'api-user@autospec.ai')\n        client_id = request_data.get('client_id', 'unknown')\n        
        # Create document info
        document_info = {
            'filename': filename,
            'content': file_content,
            'size': len(file_content),
            'mime_type': get_mime_type_from_filename(filename),
            'source': 'api'
        }
        
        # Process the document
        result = process_document(document_info, sender_email, request_id, client_id)
        
        return create_success_response(
            "Document uploaded and processing started",
            {'request_id': request_id, 'filename': filename}
        )
        
    except Exception as e:
        if isinstance(e, (ValidationError, FileProcessingError)):
            raise
        else:
            raise ExternalServiceError(f"API upload processing failed: {str(e)}")

@xray_recorder.capture('process_document')
def process_document(document_info, sender_email, request_id, client_id=None):
    """Process a document with enhanced error handling and validation."""
    
    filename = document_info['filename']
    file_content = document_info['content']
    file_size = document_info['size']
    
    error_handler.logger.info(
        f"Processing document: {filename} ({file_size} bytes) for request {request_id}"
    )
    
    try:
        # Generate S3 key
        file_extension = os.path.splitext(filename)[1].lower()
        timestamp = datetime.now(timezone.utc).strftime('%Y/%m/%d')
        s3_key = f"documents/{timestamp}/{request_id}/{filename}"
        
        # Extract format preferences
        try:
            preferences = extract_preferences_from_request({
                'sender_email': sender_email,
                'filename': filename
            })
        except Exception as pref_error:
            error_handler.logger.warning(f"Failed to extract preferences: {pref_error}")
            preferences = FormatPreferences()  # Use defaults
        
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
            preferences=preferences,
            client_id=client_id,
            source=document_info['source']
        )
        
        error_handler.logger.info(f"Successfully processed document {filename} for request {request_id}")
        
        return {
            'request_id': request_id,
            'filename': filename,
            's3_key': s3_key,
            'status': 'uploaded'
        }
        
    except Exception as e:
        if isinstance(e, FileProcessingError):
            raise
        else:
            raise FileProcessingError(
                f"Failed to process document {filename}: {str(e)}",
                filename=filename,
                details={'error_type': type(e).__name__}
            )

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
        error_handler.logger.info(f"Uploaded {filename} to S3: {s3_key}")
        
    except Exception as e:
        handle_aws_error(e, 'S3')

@xray_recorder.capture('store_document_metadata')
def store_document_metadata(request_id, filename, sender_email, s3_key, 
                          file_size, file_type, text_preview, preferences, 
                          client_id=None, source='unknown'):
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
            'preferences': preferences.to_dict(),
            'sourceType': source
        }
        
        if client_id:
            item['clientId'] = client_id
        
        table.put_item(Item=item)
        error_handler.logger.info(f"Stored metadata for request {request_id} in DynamoDB")
        
    except Exception as e:
        handle_aws_error(e, 'DynamoDB')

def extract_text_content(file_content, file_extension, filename):
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
                text += page.extract_text() + "\\n"
            return text.strip()
        
        elif file_extension in ['.docx', '.doc']:
            doc = Document(io.BytesIO(file_content))
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\\n"
            return text.strip()
        
        else:
            return f"Unsupported file type for text extraction: {file_extension}"
    
    except Exception as e:
        error_handler.logger.warning(f"Text extraction failed for {filename}: {e}")
        return f"Text extraction failed: {str(e)}"

def get_mime_type_from_filename(filename):
    """Get MIME type based on file extension."""
    extension = os.path.splitext(filename)[1].lower()
    mime_types = {
        '.pdf': 'application/pdf',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.doc': 'application/msword',
        '.txt': 'text/plain'
    }
    return mime_types.get(extension, 'application/octet-stream')

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
        
        raise ValidationError("Could not retrieve email content from SES record")
        
    except Exception as e:
        error_handler.logger.error(f"Failed to get email content: {e}")
        raise ExternalServiceError(f"Failed to retrieve email content: {str(e)}")

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
                                error_handler.logger.warning(
                                    f"Attachment {filename} is too large or empty"
                                )
                        else:
                            error_handler.logger.warning(
                                f"Attachment {filename} has unsupported file type"
                            )
        
        error_handler.logger.info(f"Extracted {len(attachments)} valid attachments")
        return attachments
        
    except Exception as e:
        error_handler.logger.error(f"Failed to extract attachments: {e}")
        raise FileProcessingError(f"Failed to extract email attachments: {str(e)}")

def process_document_attachment(attachment, sender_email, request_id):
    """Process a single email attachment."""
    try:
        # Use the same process_document function with attachment data
        return process_document(attachment, sender_email, request_id)
    except Exception as e:
        raise FileProcessingError(
            f"Failed to process email attachment {attachment.get('filename')}: {str(e)}"
        )

def send_no_attachments_response(sender_email, request_id):
    """Send response email when no attachments are found."""
    error_handler.logger.info(f"No attachments found for {sender_email}, request {request_id}")

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