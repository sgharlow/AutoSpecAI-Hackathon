import json
import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add the current directory to the path so we can import index
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import index

class TestSlackIntegration(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock environment variables
        os.environ['DOCUMENT_BUCKET'] = 'test-bucket'
        os.environ['HISTORY_TABLE'] = 'test-table'
        os.environ['INGEST_FUNCTION_NAME'] = 'test-ingest-function'
        os.environ['SLACK_SIGNING_SECRET'] = 'test-secret'
        
        # Sample request data
        self.sample_request_data = {
            'requestId': 'test-request-123',
            'timestamp': '2024-01-01T00:00:00Z',
            'filename': 'test_document.pdf',
            'status': 'delivered',
            'processingStage': 'delivery_complete'
        }
    
    def test_get_help_message(self):
        """Test help message generation."""
        help_text = index.get_help_message()
        
        self.assertIn('AutoSpec.AI', help_text)
        self.assertIn('/autospec help', help_text)
        self.assertIn('/autospec upload', help_text)
        self.assertIn('/autospec status', help_text)
        self.assertIn('PDF, DOCX, TXT', help_text)
    
    def test_format_status_message(self):
        """Test status message formatting."""
        status_message = index.format_status_message(self.sample_request_data)
        
        self.assertIn('test-request-123', status_message)
        self.assertIn('test_document.pdf', status_message)
        self.assertIn('Delivered', status_message)
        self.assertIn('✅', status_message)  # Success emoji for delivered status
    
    def test_format_status_message_failed(self):
        """Test status message for failed request."""
        failed_request = self.sample_request_data.copy()
        failed_request['status'] = 'failed'
        failed_request['errorMessage'] = 'Processing error'
        
        status_message = index.format_status_message(failed_request)
        
        self.assertIn('❌', status_message)  # Error emoji
        self.assertIn('Processing error', status_message)
    
    @patch('index.dynamodb')
    def test_get_request_status(self, mock_dynamodb):
        """Test request status retrieval."""
        # Mock DynamoDB response
        mock_table = MagicMock()
        mock_table.query.return_value = {
            'Items': [self.sample_request_data]
        }
        mock_dynamodb.Table.return_value = mock_table
        
        result = index.get_request_status('test-request-123')
        
        self.assertEqual(result, self.sample_request_data)
        mock_table.query.assert_called_once()
    
    def test_slack_response_ephemeral(self):
        """Test ephemeral Slack response creation."""
        response = index.slack_response("Test message", ephemeral=True)
        
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertEqual(body['text'], "Test message")
        self.assertEqual(body['response_type'], 'ephemeral')
    
    def test_slack_response_public(self):
        """Test public Slack response creation."""
        response = index.slack_response("Test message", ephemeral=False)
        
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertEqual(body['text'], "Test message")
        self.assertEqual(body['response_type'], 'in_channel')
    
    def test_handle_autospec_command_help(self):
        """Test help command handling."""
        response = index.handle_autospec_command('help', 'U123', 'C123', 'http://response.url')
        
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertIn('AutoSpec.AI', body['text'])
        self.assertEqual(body['response_type'], 'ephemeral')
    
    def test_handle_autospec_command_upload(self):
        """Test upload command handling."""
        response = index.handle_upload_command([], 'U123', 'C123', 'http://response.url')
        
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertIn('document URL or use file upload', body['text'])
    
    @patch('index.get_request_status')
    def test_handle_status_command_found(self, mock_get_status):
        """Test status command with existing request."""
        mock_get_status.return_value = self.sample_request_data
        
        response = index.handle_status_command(['test-request-123'], 'U123', 'C123')
        
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertIn('test-request-123', body['text'])
        self.assertIn('test_document.pdf', body['text'])
    
    @patch('index.get_request_status')
    def test_handle_status_command_not_found(self, mock_get_status):
        """Test status command with non-existing request."""
        mock_get_status.return_value = None
        
        response = index.handle_status_command(['invalid-id'], 'U123', 'C123')
        
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertIn('not found', body['text'])
    
    def test_handle_status_command_no_args(self):
        """Test status command without arguments."""
        response = index.handle_status_command([], 'U123', 'C123')
        
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertIn('provide a request ID', body['text'])
    
    def test_format_requirements_for_slack(self):
        """Test requirements formatting for Slack."""
        requirements_data = {
            'metadata': {
                'filename': 'test.pdf',
                'request_id': 'req-123'
            },
            'requirements': {
                'executive_summary': 'This is a test system summary.',
                'functional_requirements': '- Login\n- Dashboard',
                'security_and_compliance': '- HTTPS\n- Authentication'
            }
        }
        
        message = index.format_requirements_for_slack(requirements_data)
        
        self.assertIn('Analysis Complete', message)
        self.assertIn('test.pdf', message)
        self.assertIn('req-123', message)
        self.assertIn('This is a test system', message)  # Executive summary
        self.assertIn('⚙️ Functional Requirements', message)
        self.assertIn('🔒 Security & Compliance', message)
    
    @patch('index.verify_slack_signature')
    def test_handler_with_slash_command(self, mock_verify):
        """Test handler with slash command event."""
        mock_verify.return_value = True
        
        event = {
            'headers': {},
            'body': 'command=%2Fautospec&text=help&user_id=U123&channel_id=C123&response_url=http%3A%2F%2Fresponse.url'
        }
        
        response = index.handler(event, {})
        
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertIn('AutoSpec.AI', body['text'])
    
    @patch('index.verify_slack_signature')
    def test_handler_invalid_signature(self, mock_verify):
        """Test handler with invalid signature."""
        mock_verify.return_value = False
        
        event = {
            'headers': {},
            'body': 'command=%2Fautospec&text=help'
        }
        
        response = index.handler(event, {})
        
        self.assertEqual(response['statusCode'], 401)
        body = json.loads(response['body'])
        self.assertEqual(body['error'], 'Invalid signature')
    
    @patch('urllib.request.urlopen')
    def test_send_slack_notification(self, mock_urlopen):
        """Test Slack notification sending."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_urlopen.return_value = mock_response
        
        # This would be called from the format lambda
        index.send_slack_notification('http://webhook.url', 'Test message')
        
        # Verify urllib.request was called
        mock_urlopen.assert_called_once()

if __name__ == '__main__':
    unittest.main()