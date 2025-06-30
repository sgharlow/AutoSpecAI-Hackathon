import json
import unittest
from unittest.mock import patch, MagicMock, mock_open
import sys
import os

# Add the current directory to the path so we can import index
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import index

class TestProcessFunction(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock environment variables
        os.environ['DOCUMENT_BUCKET'] = 'test-bucket'
        os.environ['HISTORY_TABLE'] = 'test-table'
    
    def test_get_file_type(self):
        """Test file type detection."""
        self.assertEqual(index.get_file_type('pdf'), 'pdf')
        self.assertEqual(index.get_file_type('docx'), 'docx')
        self.assertEqual(index.get_file_type('doc'), 'docx')
        self.assertEqual(index.get_file_type('txt'), 'txt')
        self.assertEqual(index.get_file_type('unknown'), 'unknown')
    
    def test_extract_text_content_txt(self):
        """Test text extraction from TXT content."""
        test_content = "This is a test document with requirements."
        content_bytes = test_content.encode('utf-8')
        
        result = index.extract_text_content(content_bytes, 'txt')
        self.assertEqual(result, test_content)
    
    def test_create_system_analyst_prompt(self):
        """Test prompt creation for system analysis."""
        document_text = "User login system requirements document"
        
        prompt = index.create_system_analyst_prompt(document_text)
        
        # Check that prompt contains expected elements
        self.assertIn("systems analyst", prompt.lower())
        self.assertIn("functional requirements", prompt.lower())
        self.assertIn("non-functional requirements", prompt.lower())
        self.assertIn("stakeholder roles", prompt.lower())
        self.assertIn(document_text, prompt)
    
    def test_extract_sections(self):
        """Test section extraction from requirements text."""
        requirements_text = """## Executive Summary
This is the summary.

## Functional Requirements
- Login functionality
- User management

## Non-Functional Requirements
- Performance: 99.9% uptime
- Security: HTTPS encryption"""
        
        sections = index.extract_sections(requirements_text)
        
        self.assertIn('executive_summary', sections)
        self.assertIn('functional_requirements', sections)
        self.assertIn('non-functional_requirements', sections)
        
        self.assertIn('This is the summary', sections['executive_summary'])
        self.assertIn('Login functionality', sections['functional_requirements'])
        self.assertIn('99.9% uptime', sections['non-functional_requirements'])
    
    def test_parse_requirements_response(self):
        """Test parsing of Bedrock response."""
        requirements_text = """## Executive Summary
Test system overview.

## Functional Requirements
- Feature 1
- Feature 2"""
        
        result = index.parse_requirements_response(requirements_text)
        
        self.assertEqual(result['raw_response'], requirements_text)
        self.assertEqual(result['model_used'], index.CLAUDE_MODEL_ID)
        self.assertEqual(result['processing_status'], 'completed')
        self.assertIn('requirements_sections', result)
        self.assertIn('generated_at', result)
    
    @patch('index.s3_client')
    @patch('index.bedrock_client')
    @patch('index.dynamodb')
    def test_s3_event_processing(self, mock_dynamodb, mock_bedrock, mock_s3):
        """Test S3 event processing workflow."""
        # Mock S3 response
        mock_s3.get_object.return_value = {
            'Body': MagicMock(read=lambda: b"Test document content for analysis")
        }
        
        # Mock Bedrock response
        mock_bedrock_response = {
            'body': MagicMock(read=lambda: json.dumps({
                'content': [{'text': '## Executive Summary\nTest requirements analysis'}]
            }).encode())
        }
        mock_bedrock.invoke_model.return_value = mock_bedrock_response
        
        # Mock DynamoDB
        mock_table = MagicMock()
        mock_table.scan.return_value = {
            'Items': [{
                'requestId': 'test-request-id',
                'timestamp': '2024-01-01T00:00:00Z'
            }]
        }
        mock_dynamodb.Table.return_value = mock_table
        
        # Create test S3 event
        event = {
            'Records': [{
                'eventSource': 'aws:s3',
                's3': {
                    'bucket': {'name': 'test-bucket'},
                    'object': {'key': 'uploads/test-doc.txt'}
                }
            }]
        }
        
        context = {}
        
        # Call the handler
        response = index.handler(event, context)
        
        # Assertions
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertEqual(body['message'], 'Documents processed successfully')
        
        # Verify S3 was called
        mock_s3.get_object.assert_called_once()
        
        # Verify Bedrock was called
        mock_bedrock.invoke_model.assert_called_once()
        
        # Verify DynamoDB was updated
        mock_table.update_item.assert_called_once()
    
    @patch('index.logger')
    def test_error_handling(self, mock_logger):
        """Test error handling in main handler."""
        # Create invalid event that will cause an error
        event = {'invalid': 'event'}
        context = {}
        
        response = index.handler(event, context)
        
        self.assertEqual(response['statusCode'], 500)
        body = json.loads(response['body'])
        self.assertEqual(body['error'], 'Processing failed')
        
        # Verify error was logged
        mock_logger.error.assert_called()
    
    def test_bedrock_request_format(self):
        """Test Bedrock request formatting."""
        document_text = "Test requirements document"
        
        # This tests the internal structure that would be sent to Bedrock
        prompt = index.create_system_analyst_prompt(document_text)
        
        # Verify prompt structure matches expected Bedrock format
        self.assertIsInstance(prompt, str)
        self.assertTrue(len(prompt) > 100)  # Should be substantial
        self.assertIn("## Executive Summary", prompt)
        self.assertIn("## Functional Requirements", prompt)

if __name__ == '__main__':
    unittest.main()