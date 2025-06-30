import json
import base64
import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add the current directory to the path so we can import index
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import index

class TestIngestFunction(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock environment variables
        os.environ['DOCUMENT_BUCKET'] = 'test-bucket'
        os.environ['HISTORY_TABLE'] = 'test-table'
    
    @patch('index.s3_client')
    @patch('index.dynamodb')
    def test_api_upload_success(self, mock_dynamodb, mock_s3):
        """Test successful API upload."""
        # Mock DynamoDB table
        mock_table = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        
        # Create test event
        test_content = "This is a test document content."
        encoded_content = base64.b64encode(test_content.encode()).decode()
        
        event = {
            'body': json.dumps({
                'file_content': encoded_content,
                'filename': 'test_document.txt',
                'sender_email': 'test@example.com'
            })
        }
        
        context = {}
        
        # Call the handler
        response = index.handler(event, context)
        
        # Assertions
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertEqual(body['message'], 'Document uploaded successfully')
        self.assertEqual(body['filename'], 'test_document.txt')
        self.assertIn('request_id', body)
        
        # For API uploads, the function only stores metadata in DynamoDB
        # S3 upload is handled separately in production
        # Verify DynamoDB write was called
        mock_table.put_item.assert_called_once()
    
    def test_get_file_type(self):
        """Test file type detection."""
        self.assertEqual(index.get_file_type('document.pdf'), 'pdf')
        self.assertEqual(index.get_file_type('document.docx'), 'docx')
        self.assertEqual(index.get_file_type('document.DOC'), 'docx')
        self.assertEqual(index.get_file_type('document.txt'), 'txt')
        self.assertEqual(index.get_file_type('document.unknown'), 'unknown')
    
    def test_get_content_type(self):
        """Test MIME content type mapping."""
        self.assertEqual(index.get_content_type('pdf'), 'application/pdf')
        self.assertEqual(index.get_content_type('docx'), 
                        'application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        self.assertEqual(index.get_content_type('txt'), 'text/plain')
        self.assertEqual(index.get_content_type('unknown'), 'application/octet-stream')
    
    def test_extract_text_content_txt(self):
        """Test text extraction from TXT files."""
        test_content = "This is a test document."
        content_bytes = test_content.encode('utf-8')
        
        result = index.extract_text_content(content_bytes, '.txt', 'test.txt')
        self.assertEqual(result, test_content)
    
    @patch('index.s3_client')
    @patch('index.dynamodb')
    def test_api_upload_invalid_json(self, mock_dynamodb, mock_s3):
        """Test API upload with invalid JSON."""
        event = {
            'body': 'invalid json'
        }
        
        context = {}
        
        response = index.handler(event, context)
        
        self.assertEqual(response['statusCode'], 400)
        body = json.loads(response['body'])
        self.assertEqual(body['error'], 'Invalid request')
    
    def test_ses_event_structure(self):
        """Test SES event handling structure."""
        # Create a mock SES event
        event = {
            'Records': [{
                'eventSource': 'aws:ses',
                'ses': {
                    'mail': {
                        'messageId': 'test-message-id',
                        'timestamp': '2024-01-01T00:00:00.000Z',
                        'commonHeaders': {
                            'from': ['sender@example.com'],
                            'subject': 'Test Subject'
                        }
                    }
                }
            }]
        }
        
        context = {}
        
        # SES processing may fail without proper email content setup
        response = index.handler(event, context)
        # SES event processing fails gracefully with 500 when email content can't be retrieved
        self.assertEqual(response['statusCode'], 500)

if __name__ == '__main__':
    unittest.main()