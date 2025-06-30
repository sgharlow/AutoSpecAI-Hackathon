import json
import boto3
import uuid
import email
import base64
import logging
import os
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
# Temporarily commented out for testing
# import PyPDF2
# from docx import Document
import io
from format_preferences import extract_preferences_from_request, FormatPreferences
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all
import time

# Enable X-Ray tracing for AWS SDK calls
patch_all()

# Configure structured logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.info("=== UPDATED INGEST FUNCTION - DEPENDENCIES TESTING ===")

# Import monitoring utilities
try:
    from monitoring.index import log_request_start, log_request_end, log_error, log_metric
except ImportError:
    # Fallback if monitoring module not available
    def log_request_start(request_id, function_name, **kwargs):
        logger.info(f"Request start: {request_id} in {function_name}")
    
    def log_request_end(request_id, function_name, duration, status, **kwargs):
        logger.info(f"Request end: {request_id} in {function_name} - {status} - {duration*1000:.2f}ms")
    
    def log_error(request_id, function_name, error, **kwargs):
        logger.error(f"Error in {function_name} for {request_id}: {str(error)}")
    
    def log_metric(metric_name, value, unit='Count', **kwargs):
        logger.info(f"Metric: {metric_name} = {value} {unit}")

# Initialize AWS clients
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

# Environment variables
DOCUMENT_BUCKET = os.environ.get('DOCUMENT_BUCKET')
HISTORY_TABLE = os.environ.get('HISTORY_TABLE')

@xray_recorder.capture('lambda_handler')
def handler(event, context):
    """
    Lambda handler for document ingestion.
    Handles both SES email events and API Gateway uploads.
    """
    request_id = str(uuid.uuid4())
    start_time = time.time()
    function_name = 'ingest'
    
    # Add request ID to X-Ray trace
    xray_recorder.put_annotation('request_id', request_id)
    xray_recorder.put_annotation('function_name', function_name)
    
    log_request_start(request_id, function_name, event_type='unknown')
    
    try:
        logger.info(f"Received event: {json.dumps(event, default=str)}")
        
        # Determine event source and add to trace
        if 'Records' in event:
            event_type = 'ses_email'
            xray_recorder.put_annotation('event_type', event_type)
            result = handle_ses_event(event, request_id)
        else:
            event_type = 'api_upload'
            xray_recorder.put_annotation('event_type', event_type)
            result = handle_api_upload(event, request_id)
        
        # Log successful completion
        duration = time.time() - start_time
        log_request_end(request_id, function_name, duration, 'success', event_type=event_type)
        log_metric('IngestRequestsSuccess', 1, dimensions={'EventType': event_type})
        
        return result
            
    except Exception as e:
        duration = time.time() - start_time
        log_error(request_id, function_name, e, event_type=event.get('source', 'unknown'))
        log_request_end(request_id, function_name, duration, 'error')
        log_metric('IngestRequestsError', 1)
        
        xray_recorder.put_annotation('error', True)
        xray_recorder.put_metadata('error_details', {
            'error_type': type(e).__name__,
            'error_message': str(e)
        })
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e),
                'request_id': request_id
            })
        }

def handle_ses_event(event, request_id):
    """Handle incoming SES email with document attachments."""
    for record in event['Records']:
        if record['eventSource'] == 'aws:ses':
            # Get the email from S3 (SES stores it there)
            message_id = record['ses']['mail']['messageId']
            
            # Process the email message
            email_data = extract_email_data(record)
            
            # Extract and store documents
            documents = extract_documents_from_email(email_data)
            
            # Store documents and trigger processing
            for doc in documents:
                try:
                    # Generate unique request ID for each document
                    request_id = str(uuid.uuid4())
                    
                    # Store document in S3
                    s3_key = f"uploads/{request_id}/{doc['filename']}"
                    s3_client.put_object(
                        Bucket=DOCUMENT_BUCKET,
                        Key=s3_key,
                        Body=doc['content'],
                        ContentType=get_content_type(doc['file_type'])
                    )
                    
                    # Store metadata in DynamoDB
                    doc_metadata = {
                        'filename': doc['filename'],
                        'file_type': doc['file_type'],
                        'size': doc['size'],
                        's3_key': s3_key
                    }
                    store_document_metadata(doc_metadata, email_data['sender'], 'email', request_id)
                    
                    logger.info(f"Stored document {doc['filename']} with request_id {request_id}")
                    
                except Exception as doc_error:
                    logger.error(f"Failed to store document {doc['filename']}: {str(doc_error)}")
    
    return {'statusCode': 200, 'body': 'Email processed successfully'}

def handle_api_upload(event, request_id):
    """Handle direct API Gateway document upload."""
    try:
        # Parse request body
        logger.info(f"Processing API upload event: {json.dumps(event, default=str)}")
        
        if event.get('isBase64Encoded'):
            body = base64.b64decode(event['body'])
        else:
            body = json.loads(event['body'])
        
        logger.info(f"Parsed body: {json.dumps(body, default=str)}")
        
        # Extract file data
        file_content = base64.b64decode(body['file_content'])
        filename = body['filename']
        sender_email = body.get('sender_email', 'api-user@autospec.ai')
        
        # Use the request_id passed from the main handler
        logger.info(f"Using request_id from handler: {request_id}")
        
        # Extract format preferences
        preferences = extract_preferences_from_request('api', body)
        preference_summary = FormatPreferences.create_preference_summary(preferences)
        
        # Determine file type
        file_type = get_file_type(filename)
        
        # Store document - use request_id in S3 key for consistency
        document_key = f"uploads/{request_id}/{filename}"
        s3_client.put_object(
            Bucket=DOCUMENT_BUCKET,
            Key=document_key,
            Body=file_content,
            ContentType=get_content_type(file_type)
        )
        
        # Store metadata with preferences
        doc_metadata = {
            'filename': filename,
            'file_type': file_type,
            's3_key': document_key,
            'size': len(file_content),
            'format_preferences': preferences
        }
        
        # Store document metadata with the consistent request_id
        store_document_metadata(doc_metadata, sender_email, 'api', request_id)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Document uploaded successfully',
                'request_id': request_id,
                'filename': filename,
                'preferences': preference_summary
            })
        }
        
    except Exception as e:
        logger.error(f"Error handling API upload: {str(e)}")
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'Invalid request',
                'message': str(e)
            })
        }

def extract_email_data(ses_record):
    """Extract email data from SES record."""
    mail_data = ses_record['ses']['mail']
    
    return {
        'message_id': mail_data['messageId'],
        'sender': mail_data['commonHeaders']['from'][0],
        'subject': mail_data['commonHeaders'].get('subject', 'No Subject'),
        'timestamp': mail_data['timestamp']
    }

def extract_documents_from_email(email_data):
    """Extract document attachments from email."""
    import email
    from email.mime.multipart import MIMEMultipart
    from email.mime.base import MIMEBase
    
    documents = []
    
    try:
        # Get the email content from S3 (SES stores email content in S3)
        message_id = email_data['message_id']
        
        # Construct S3 key where SES stores the email
        # Format: prefix/{messageId}
        email_bucket = os.environ.get('EMAIL_BUCKET', DOCUMENT_BUCKET)
        email_key = f"emails/{message_id}"
        
        logger.info(f"Fetching email from s3://{email_bucket}/{email_key}")
        
        try:
            # Get email content from S3
            response = s3_client.get_object(Bucket=email_bucket, Key=email_key)
            email_content = response['Body'].read()
            
            # Parse the email
            msg = email.message_from_bytes(email_content)
            
            # Process multipart message
            if msg.is_multipart():
                for part in msg.walk():
                    # Check if this part has an attachment
                    disposition = part.get('Content-Disposition')
                    if disposition and 'attachment' in disposition:
                        filename = part.get_filename()
                        if filename:
                            # Check if it's a supported file type
                            file_type = get_file_type(filename)
                            if file_type in ['pdf', 'docx', 'txt']:
                                # Extract attachment content
                                attachment_content = part.get_payload(decode=True)
                                
                                if attachment_content:
                                    documents.append({
                                        'filename': filename,
                                        'content': attachment_content,
                                        'file_type': file_type,
                                        'size': len(attachment_content)
                                    })
                                    logger.info(f"Extracted attachment: {filename} ({file_type}, {len(attachment_content)} bytes)")
            else:
                # Single part message - check if it's a supported document type
                filename = msg.get_filename() or f"email_content_{message_id}.txt"
                if get_file_type(filename) in ['pdf', 'docx', 'txt']:
                    content = msg.get_payload(decode=True)
                    if content:
                        documents.append({
                            'filename': filename,
                            'content': content,
                            'file_type': get_file_type(filename),
                            'size': len(content)
                        })
                        
        except Exception as s3_error:
            logger.warning(f"Could not fetch email from S3: {str(s3_error)}")
            # Fallback: create a text document from the email body if available
            if 'body' in email_data:
                content = email_data['body'].encode('utf-8')
                documents.append({
                    'filename': f"email_body_{message_id}.txt",
                    'content': content,
                    'file_type': 'txt',
                    'size': len(content)
                })
                logger.info(f"Created text document from email body ({len(content)} bytes)")
        
        logger.info(f"Extracted {len(documents)} documents from email from {email_data['sender']}")
        
    except Exception as e:
        logger.error(f"Error extracting documents from email: {str(e)}")
        # Create a fallback document if possible
        if email_data.get('subject'):
            content = f"Subject: {email_data['subject']}\nFrom: {email_data['sender']}\nTimestamp: {email_data['timestamp']}\n\nEmail processing failed, but metadata preserved.".encode('utf-8')
            documents.append({
                'filename': f"email_metadata_{email_data['message_id']}.txt",
                'content': content,
                'file_type': 'txt',
                'size': len(content)
            })
    
    return documents

@xray_recorder.capture('get_file_type')
def get_file_type(filename):
    """Determine file type from filename."""
    extension = filename.lower().split('.')[-1]
    xray_recorder.put_annotation('file_extension', extension)
    
    type_mapping = {
        'pdf': 'pdf',
        'docx': 'docx',
        'doc': 'docx',  # Treat .doc as .docx for simplicity
        'txt': 'txt'
    }
    file_type = type_mapping.get(extension, 'unknown')
    xray_recorder.put_annotation('detected_file_type', file_type)
    
    return file_type

def get_content_type(file_type):
    """Get MIME type for file type."""
    content_types = {
        'pdf': 'application/pdf',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'txt': 'text/plain'
    }
    return content_types.get(file_type, 'application/octet-stream')

@xray_recorder.capture('store_document_metadata')
def store_document_metadata(doc_metadata, sender_email, source_type, existing_request_id=None):
    """Store document metadata in DynamoDB."""
    request_id = existing_request_id or str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()
    
    xray_recorder.put_annotation('storing_metadata', True)
    xray_recorder.put_annotation('source_type', source_type)
    
    with xray_recorder.in_subsegment('dynamodb_put'):
        table = dynamodb.Table(HISTORY_TABLE)
        
        # Simplify formatPreferences to avoid serialization issues
        default_prefs = {'formats': ['markdown', 'json', 'html'], 'quality': 'standard'}
        format_prefs = doc_metadata.get('format_preferences', default_prefs)
        
        item = {
            'requestId': request_id,
            'timestamp': timestamp,
            'senderEmail': sender_email,
            'sourceType': source_type,
            'filename': doc_metadata['filename'],
            'fileType': doc_metadata['file_type'],
            's3Key': doc_metadata['s3_key'],
            'fileSize': doc_metadata['size'],
            'status': 'uploaded',
            'processingStage': 'ingestion_complete',
            'formatPreferences': format_prefs
        }
        
        try:
            logger.info(f"Environment variable HISTORY_TABLE: {HISTORY_TABLE}")
            logger.info(f"DynamoDB table object: {table}")
            logger.info(f"Attempting to write to DynamoDB table: {HISTORY_TABLE}")
            logger.info(f"Item to be written: {json.dumps(item, default=str)}")
            table.put_item(Item=item)
            logger.info(f"✅ Successfully stored metadata to DynamoDB for request {request_id}")
        except Exception as dynamodb_error:
            logger.error(f"❌ DynamoDB put_item failed: {str(dynamodb_error)}")
            logger.error(f"Table name: {HISTORY_TABLE}")
            logger.error(f"Table object: {table}")
            logger.error(f"AWS Region from boto3: {dynamodb.meta.client.meta.region_name}")
            logger.error(f"Item: {json.dumps(item, default=str)}")
            raise dynamodb_error
    
    try:
        log_metric('DocumentsStored', 1, dimensions={'SourceType': source_type, 'FileType': doc_metadata['file_type']})
    except Exception as metric_error:
        logger.warning(f"Failed to log metric: {str(metric_error)}")
    
    logger.info(f"✅ Stored metadata for request {request_id}")
    return request_id

# Temporarily disabled text extraction for testing
@xray_recorder.capture('extract_text_content')
def extract_text_content(file_content, file_type):
    """Extract text content from document based on file type."""
    logger.info(f"Text extraction temporarily disabled for testing - {file_type}")
    return "Text extraction temporarily disabled for dependency testing"