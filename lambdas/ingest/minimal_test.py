import json
import boto3
import uuid
import logging
import os
from datetime import datetime, timezone

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')

# Environment variables
HISTORY_TABLE = os.environ.get('HISTORY_TABLE')

def handler(event, context):
    """Minimal test handler to verify DynamoDB connectivity."""
    logger.info("=== MINIMAL TEST HANDLER STARTED ===")
    
    try:
        request_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Test DynamoDB write
        table = dynamodb.Table(HISTORY_TABLE)
        
        item = {
            'requestId': request_id,
            'timestamp': timestamp,
            'senderEmail': 'test@example.com',
            'sourceType': 'minimal_test',
            'filename': 'test.txt',
            'fileType': 'txt',
            's3Key': 'test/test.txt',
            'fileSize': 100,
            'status': 'test',
            'processingStage': 'test_complete'
        }
        
        logger.info(f"Attempting to write to DynamoDB table: {HISTORY_TABLE}")
        table.put_item(Item=item)
        logger.info(f"✅ Successfully wrote test item to DynamoDB for request {request_id}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Minimal test successful',
                'request_id': request_id,
                'table': HISTORY_TABLE
            })
        }
        
    except Exception as e:
        logger.error(f"❌ Minimal test failed: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Minimal test failed',
                'message': str(e)
            })
        }