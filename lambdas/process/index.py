import json
import boto3
import os
import logging
import uuid
import time
from datetime import datetime, timezone
# Import document processing libraries with fallbacks for testing
try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False
    
try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
import io

# Optional X-Ray tracing
try:
    from aws_xray_sdk.core import xray_recorder
    from aws_xray_sdk.core import patch_all
    # Enable X-Ray tracing for AWS SDK calls
    patch_all()
    XRAY_AVAILABLE = True
except ImportError:
    XRAY_AVAILABLE = False
    # Create a mock xray_recorder for when X-Ray is not available
    class MockXRayRecorder:
        def capture(self, name):
            def decorator(func):
                return func
            return decorator
        def put_annotation(self, key, value):
            pass
        def put_metadata(self, key, value):
            pass
        def in_subsegment(self, name):
            from contextlib import nullcontext
            return nullcontext()
    
    xray_recorder = MockXRayRecorder()

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def log_metric(metric_name, value, unit='Count', dimensions=None):
    """Log custom metric to CloudWatch."""
    try:
        logger.info(f"METRIC: {metric_name}={value} {unit} {dimensions or {}}")
    except Exception as e:
        logger.warning(f"Failed to log metric {metric_name}: {e}")

# Initialize AWS clients
s3_client = boto3.client('s3')
bedrock_client = boto3.client('bedrock-runtime')
dynamodb = boto3.resource('dynamodb')

# Environment variables
DOCUMENT_BUCKET = os.environ.get('DOCUMENT_BUCKET')
HISTORY_TABLE = os.environ.get('HISTORY_TABLE')

# Bedrock model configuration
CLAUDE_MODEL_ID = "anthropic.claude-3-5-sonnet-20241022-v2:0"
MAX_TOKENS = 4000

def handler(event, context):
    """
    Lambda handler for AI processing with Amazon Bedrock.
    Triggered by S3 object creation events.
    """
    try:
        logger.info(f"Processing event: {json.dumps(event)}")
        
        # Process each record from S3 event
        for record in event['Records']:
            if record['eventSource'] == 'aws:s3':
                bucket_name = record['s3']['bucket']['name']
                object_key = record['s3']['object']['key']
                
                # Process the document
                process_document(bucket_name, object_key)
        
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Documents processed successfully'})
        }
        
    except Exception as e:
        logger.error(f"Error processing documents: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Processing failed',
                'message': str(e)
            })
        }

@xray_recorder.capture('process_document')
def process_document(bucket_name, object_key, request_id=None):
    """Process a single document from S3."""
    if not request_id:
        request_id = str(uuid.uuid4())
    
    xray_recorder.put_annotation('processing_document', True)
    xray_recorder.put_annotation('s3_bucket', bucket_name)
    xray_recorder.put_annotation('s3_object_key', object_key)
    
    try:
        logger.info(f"Processing document: s3://{bucket_name}/{object_key}")
        
        # Get document from S3
        with xray_recorder.in_subsegment('s3_get_object'):
            response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
            document_content = response['Body'].read()
            
        content_size = len(document_content)
        xray_recorder.put_annotation('document_size', content_size)
        log_metric('DocumentSize', content_size, 'Bytes')
        
        # Determine file type from key
        file_extension = object_key.lower().split('.')[-1]
        file_type = get_file_type(file_extension)
        
        # Extract text content
        with xray_recorder.in_subsegment('extract_text'):
            text_content = extract_text_content(document_content, file_type)
        
        if not text_content.strip():
            logger.warning(f"No text content extracted from {object_key}")
            update_processing_status(object_key, 'failed', 'No text content extracted')
            log_metric('TextExtractionFailed', 1, dimensions={'FileType': file_type})
            return
        
        text_length = len(text_content)
        xray_recorder.put_annotation('extracted_text_length', text_length)
        log_metric('ExtractedTextLength', text_length, 'Count', dimensions={'FileType': file_type})
        
        # Generate system requirements using Bedrock
        with xray_recorder.in_subsegment('bedrock_analysis'):
            requirements = generate_system_requirements(text_content, request_id)
        
        if not requirements:
            logger.error(f"Failed to generate requirements for {object_key}")
            update_processing_status(object_key, 'failed', 'AI processing failed')
            log_metric('BedrockProcessingFailed', 1)
            return
        
        # Store results
        with xray_recorder.in_subsegment('store_results'):
            store_processing_results(object_key, text_content, requirements, request_id)
        
        log_metric('DocumentProcessingSuccess', 1, dimensions={'FileType': file_type})
        logger.info(f"Successfully processed document: {object_key}")
        
    except Exception as e:
        logger.error(f"Error processing document {object_key}: {str(e)}")
        update_processing_status(object_key, 'failed', str(e))
        log_metric('DocumentProcessingError', 1)
        xray_recorder.put_annotation('processing_error', True)
        raise

def get_file_type(extension):
    """Determine file type from extension."""
    type_mapping = {
        'pdf': 'pdf',
        'docx': 'docx',
        'doc': 'docx',
        'txt': 'txt'
    }
    return type_mapping.get(extension, 'unknown')

def extract_text_content(file_content, file_type):
    """Extract text content from document based on file type."""
    try:
        if file_type == 'txt':
            return file_content.decode('utf-8')
        
        elif file_type == 'pdf':
            if not PYPDF2_AVAILABLE:
                return f"PDF processing not available - PyPDF2 not installed"
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text
        
        elif file_type == 'docx':
            if not DOCX_AVAILABLE:
                return f"DOCX processing not available - python-docx not installed"
            doc = Document(io.BytesIO(file_content))
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        
        else:
            logger.warning(f"Unsupported file type: {file_type}")
            return ""
            
    except Exception as e:
        logger.error(f"Error extracting text from {file_type}: {str(e)}")
        return ""

@xray_recorder.capture('generate_system_requirements')
def generate_system_requirements(document_text, request_id=None):
    """Generate system requirements using Amazon Bedrock."""
    xray_recorder.put_annotation('bedrock_processing', True)
    xray_recorder.put_annotation('input_text_length', len(document_text))
    xray_recorder.put_annotation('model_id', CLAUDE_MODEL_ID)
    
    start_time = time.time()
    
    try:
        # Create the system analyst prompt
        with xray_recorder.in_subsegment('create_prompt'):
            prompt = create_system_analyst_prompt(document_text)
            
        prompt_length = len(prompt)
        xray_recorder.put_annotation('prompt_length', prompt_length)
        
        # Prepare the request for Claude
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": MAX_TOKENS,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.1,
            "top_p": 0.9
        }
        
        # Call Bedrock
        with xray_recorder.in_subsegment('bedrock_invoke_model'):
            response = bedrock_client.invoke_model(
                modelId=CLAUDE_MODEL_ID,
                body=json.dumps(request_body),
                contentType='application/json',
                accept='application/json'
            )
        
        bedrock_duration = time.time() - start_time
        xray_recorder.put_annotation('bedrock_duration_seconds', bedrock_duration)
        log_metric('BedrockProcessingTime', bedrock_duration * 1000, 'Milliseconds')
        
        # Parse response
        with xray_recorder.in_subsegment('parse_response'):
            response_body = json.loads(response['body'].read())
            
            if 'content' in response_body and len(response_body['content']) > 0:
                requirements_text = response_body['content'][0]['text']
                response_length = len(requirements_text)
                
                xray_recorder.put_annotation('response_length', response_length)
                log_metric('BedrockResponseLength', response_length, 'Count')
                
                parsed_result = parse_requirements_response(requirements_text)
                log_metric('BedrockProcessingSuccess', 1)
                
                return parsed_result
            else:
                logger.error("No content in Bedrock response")
                log_metric('BedrockEmptyResponse', 1)
                return None
            
    except Exception as e:
        error_duration = time.time() - start_time
        logger.error(f"Error calling Bedrock: {str(e)}")
        log_metric('BedrockProcessingError', 1)
        log_metric('BedrockErrorDuration', error_duration * 1000, 'Milliseconds')
        
        xray_recorder.put_annotation('bedrock_error', True)
        xray_recorder.put_metadata('bedrock_error_details', {
            'error_type': type(e).__name__,
            'error_message': str(e)
        })
        
        return None

def create_system_analyst_prompt(document_text):
    """Create the system analyst prompt for Bedrock."""
    prompt = f"""Review this document with the mindset of a skilled systems analyst and break down the contents into an organized list of system requirements that meet these criteria:

1. Comprehensive and Clear Structure  
2. Depth and Clarity of Functional Requirements  
3. Role-Specific Responsibilities  
4. Technical Transparency  
5. Non-Functional Requirements Are Not Forgotten  
6. Cross-Referencing and Version Control  
7. Balanced Use of Narrative and Tabular Format  

Return your output in structured Markdown with headings for each requirement category.

Document Content:
---
{document_text[:8000]}  # Limit to prevent token overflow
---

Please provide a comprehensive analysis including:

## Executive Summary
Brief overview of the system purpose and scope.

## Functional Requirements
Detailed list of what the system must do.

## Non-Functional Requirements
Performance, security, usability, and other quality attributes.

## Stakeholder Roles and Responsibilities
Key roles and their specific responsibilities.

## Technical Architecture Considerations
High-level technical requirements and constraints.

## Integration Requirements
External system integration needs.

## Data Requirements
Data storage, processing, and management needs.

## Security and Compliance
Security controls and regulatory compliance requirements.

Format each section with clear, actionable requirements using both narrative descriptions and structured lists where appropriate."""

    return prompt

def parse_requirements_response(requirements_text):
    """Parse and structure the Bedrock response."""
    try:
        # Create structured response
        structured_requirements = {
            'raw_response': requirements_text,
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'model_used': CLAUDE_MODEL_ID,
            'processing_status': 'completed',
            'requirements_sections': extract_sections(requirements_text)
        }
        
        return structured_requirements
        
    except Exception as e:
        logger.error(f"Error parsing requirements response: {str(e)}")
        return {
            'raw_response': requirements_text,
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'model_used': CLAUDE_MODEL_ID,
            'processing_status': 'partial',
            'parse_error': str(e)
        }

def extract_sections(requirements_text):
    """Extract different sections from the requirements text."""
    sections = {}
    current_section = None
    current_content = []
    
    for line in requirements_text.split('\n'):
        if line.startswith('## '):
            # Save previous section
            if current_section:
                sections[current_section] = '\n'.join(current_content)
            
            # Start new section
            current_section = line[3:].strip().lower().replace(' ', '_')
            current_content = []
        elif current_section:
            current_content.append(line)
    
    # Save last section
    if current_section:
        sections[current_section] = '\n'.join(current_content)
    
    return sections

@xray_recorder.capture('store_processing_results')
def store_processing_results(object_key, original_text, requirements, request_id=None):
    """Store processing results in DynamoDB."""
    try:
        table = dynamodb.Table(HISTORY_TABLE)
        
        # Find the corresponding record by S3 key
        # This is a simplified approach - in production, you'd use better indexing
        response = table.scan(
            FilterExpression='s3Key = :key',
            ExpressionAttributeValues={':key': object_key}
        )
        
        if response['Items']:
            # Update existing record
            item = response['Items'][0]
            request_id = item['requestId']
            timestamp = item['timestamp']
            
            table.update_item(
                Key={
                    'requestId': request_id,
                    'timestamp': timestamp
                },
                UpdateExpression='SET processingStage = :stage, #status = :status, aiResponse = :response, processedAt = :processed_at, extractedText = :text',
                ExpressionAttributeNames={
                    '#status': 'status'
                },
                ExpressionAttributeValues={
                    ':stage': 'ai_processing_complete',
                    ':status': 'processed',
                    ':response': requirements,
                    ':processed_at': datetime.now(timezone.utc).isoformat(),
                    ':text': original_text[:1000]  # Store first 1000 chars of extracted text
                }
            )
            
            logger.info(f"Stored processing results for request {request_id}")
        else:
            logger.warning(f"No record found for S3 key: {object_key}")
        
    except Exception as e:
        logger.error(f"Error storing processing results: {str(e)}")
        raise

@xray_recorder.capture('update_processing_status')
def update_processing_status(object_key, status, error_message=None):
    """Update processing status in DynamoDB."""
    try:
        table = dynamodb.Table(HISTORY_TABLE)
        
        # Find the corresponding record
        response = table.scan(
            FilterExpression='s3Key = :key',
            ExpressionAttributeValues={':key': object_key}
        )
        
        if response['Items']:
            item = response['Items'][0]
            request_id = item['requestId']
            timestamp = item['timestamp']
            
            update_expression = 'SET #status = :status, processingStage = :stage'
            expression_values = {
                ':status': status,
                ':stage': f'ai_processing_{status}'
            }
            
            if error_message:
                update_expression += ', errorMessage = :error'
                expression_values[':error'] = error_message
            
            table.update_item(
                Key={
                    'requestId': request_id,
                    'timestamp': timestamp
                },
                UpdateExpression=update_expression,
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues=expression_values
            )
            
    except Exception as e:
        logger.error(f"Error updating processing status: {str(e)}")