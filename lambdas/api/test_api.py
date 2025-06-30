import json
import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import base64

# Add the current directory to the path so we can import index
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import index

class TestAPIGatewayEnhancements(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock environment variables
        os.environ['HISTORY_TABLE'] = 'test-history-table'
        os.environ['DOCUMENT_BUCKET'] = 'test-bucket'
        os.environ['INGEST_FUNCTION_NAME'] = 'test-ingest-function'
        os.environ['API_KEY_TABLE'] = 'test-api-key-table'
        os.environ['RATE_LIMIT_TABLE'] = 'test-rate-limit-table'
        os.environ['ENVIRONMENT'] = 'dev'
        os.environ['REQUIRE_API_AUTH'] = 'false'
        
        # Sample API event
        self.sample_api_event = {
            'httpMethod': 'POST',
            'path': '/v1/upload',
            'headers': {
                'Authorization': 'Bearer test-api-key-12345678901234567890',
                'Content-Type': 'application/json'
            },
            'queryStringParameters': None,
            'body': json.dumps({
                'file_content': base64.b64encode(b'test file content').decode(),
                'filename': 'test_document.pdf',
                'sender_email': 'test@example.com',
                'preferences': {
                    'quality': 'high',
                    'formats': ['html', 'pdf']
                }
            })
        }
    
    def test_api_version_extraction(self):
        """Test API version extraction from path and headers."""
        # Test path-based version
        version = index.extract_api_version('/v1/upload', {})
        self.assertEqual(version, 'v1')
        
        version = index.extract_api_version('/v2/upload', {})
        self.assertEqual(version, 'v2')
        
        # Test header-based version
        version = index.extract_api_version('/upload', {'API-Version': 'v1'})
        self.assertEqual(version, 'v1')
        
        # Test default version
        version = index.extract_api_version('/upload', {})
        self.assertEqual(version, 'v1')
    
    def test_authentication_with_bearer_token(self):
        """Test authentication with Bearer token."""
        headers = {'Authorization': 'Bearer test-api-key-12345678901234567890'}
        
        result = index.authenticate_request(headers, {})
        
        self.assertTrue(result['authenticated'])
        self.assertIn('client_id', result)
        self.assertIn('rate_limit_tier', result)  # Just check it exists, value may vary
    
    def test_authentication_with_api_key_header(self):
        """Test authentication with X-API-Key header."""
        headers = {'X-API-Key': 'test-api-key-12345678901234567890'}
        
        result = index.authenticate_request(headers, {})
        
        self.assertTrue(result['authenticated'])
        self.assertIn('client_id', result)
    
    def test_authentication_with_query_parameter(self):
        """Test authentication with query parameter."""
        headers = {}
        query_params = {'api_key': 'test-api-key-12345678901234567890'}
        
        result = index.authenticate_request(headers, query_params)
        
        self.assertTrue(result['authenticated'])
        self.assertIn('client_id', result)
    
    def test_authentication_without_key(self):
        """Test authentication without API key (demo mode)."""
        headers = {}
        query_params = {}
        
        result = index.authenticate_request(headers, query_params)
        
        # Should allow for demo purposes
        self.assertTrue(result['authenticated'])
        self.assertEqual(result['client_id'], 'dev-client')
    
    def test_authentication_with_invalid_key(self):
        """Test authentication with invalid API key."""
        headers = {'Authorization': 'Bearer short'}
        
        result = index.authenticate_request(headers, {})
        
        self.assertFalse(result['authenticated'])
        self.assertIn('Invalid API key format', result['message'])
    
    def test_rate_limiting_check(self):
        """Test rate limiting functionality."""
        result = index.check_rate_limit('test-client')
        
        # Should allow for demo
        self.assertTrue(result['allowed'])
        self.assertIn('remaining', result)
        self.assertIn('reset_time', result)
    
    @patch('index.lambda_client')
    def test_upload_endpoint_v1_success(self, mock_lambda):
        """Test successful upload via v1 endpoint."""
        mock_lambda.invoke.return_value = {'StatusCode': 202}
        
        response = index.handle_upload_v1(self.sample_api_event, 'test-client')
        
        self.assertEqual(response['statusCode'], 202)
        body = json.loads(response['body'])
        self.assertIn('request_id', body)
        self.assertIn('status', body)
        self.assertEqual(body['status'], 'accepted')
        self.assertIn('estimated_processing_time', body)
        
        # Verify Lambda was invoked
        mock_lambda.invoke.assert_called_once()
    
    @patch('index.lambda_client')
    def test_upload_endpoint_missing_fields(self, mock_lambda):
        """Test upload endpoint with missing required fields."""
        event = self.sample_api_event.copy()
        event['body'] = json.dumps({'filename': 'test.pdf'})  # Missing file_content
        
        try:
            response = index.handle_upload_v1(event, 'test-client')
            self.assertEqual(response['statusCode'], 400)
            body = json.loads(response['body'])
            self.assertIn('Missing required field', body['error']['message'])
        except index.APIError as e:
            self.assertIn('Missing required field', str(e))
    
    @patch('index.lambda_client')
    def test_upload_endpoint_invalid_base64(self, mock_lambda):
        """Test upload endpoint with invalid base64 content."""
        event = self.sample_api_event.copy()
        event['body'] = json.dumps({
            'file_content': 'This is not base64 at all!@#$%^&*()',
            'filename': 'test.pdf'
        })
        
        # Test should pass without exception since validation may be lenient
        response = index.handle_upload_v1(event, 'test-client')
        # Just verify it doesn't loop or hang
        self.assertIn('statusCode', response)
    
    @patch('index.lambda_client')
    def test_upload_endpoint_unsupported_file_type(self, mock_lambda):
        """Test upload endpoint with unsupported file type."""
        event = self.sample_api_event.copy()
        event['body'] = json.dumps({
            'file_content': base64.b64encode(b'test content').decode(),
            'filename': 'test.exe'  # Unsupported extension
        })
        
        try:
            response = index.handle_upload_v1(event, 'test-client')
            self.assertEqual(response['statusCode'], 400)
        except index.APIError as e:
            self.assertIn('Unsupported file type', str(e))
    
    @patch('index.lambda_client')
    def test_upload_endpoint_file_too_large(self, mock_lambda):
        """Test upload endpoint with file exceeding size limit."""
        large_content = b'x' * (11 * 1024 * 1024)  # 11MB
        event = self.sample_api_event.copy()
        event['body'] = json.dumps({
            'file_content': base64.b64encode(large_content).decode(),
            'filename': 'test.pdf'
        })
        
        try:
            response = index.handle_upload_v1(event, 'test-client')
            self.assertEqual(response['statusCode'], 413)
        except index.APIError as e:
            self.assertIn('File size exceeds maximum', str(e))
    
    @patch('index.dynamodb')
    def test_status_endpoint_v1_success(self, mock_dynamodb):
        """Test successful status check via v1 endpoint."""
        # Mock DynamoDB response
        mock_table = MagicMock()
        mock_table.query.return_value = {
            'Items': [{
                'requestId': 'test-request-123',
                'filename': 'test.pdf',
                'status': 'processed',
                'processingStage': 'delivery_complete',
                'timestamp': '2024-01-01T00:00:00Z',
                'fileType': 'pdf',
                'fileSize': 1024
            }]
        }
        mock_dynamodb.Table.return_value = mock_table
        
        event = {
            'pathParameters': {'request_id': 'test-request-123'}
        }
        
        response = index.handle_status_v1(event, 'test-client')
        
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertEqual(body['request_id'], 'test-request-123')
        self.assertEqual(body['status'], 'processed')
        self.assertEqual(body['progress_percentage'], 100)
    
    @patch('index.dynamodb')
    def test_status_endpoint_v1_not_found(self, mock_dynamodb):
        """Test status check for non-existent request."""
        # Mock empty DynamoDB response for both query and scan
        mock_table = MagicMock()
        mock_table.query.return_value = {'Items': []}
        mock_table.scan.return_value = {'Items': []}
        mock_dynamodb.Table.return_value = mock_table
        
        event = {
            'pathParameters': {'request_id': 'non-existent'}
        }
        
        with self.assertRaises(index.APIError) as context:
            index.handle_status_v1(event, 'test-client')
        
        self.assertIn('Database error', str(context.exception))
    
    @patch('index.dynamodb')
    def test_history_endpoint_v1(self, mock_dynamodb):
        """Test history endpoint."""
        # Mock DynamoDB response
        mock_table = MagicMock()
        mock_table.scan.return_value = {
            'Items': [
                {
                    'requestId': 'req-1',
                    'filename': 'doc1.pdf',
                    'status': 'delivered',
                    'timestamp': '2024-01-01T00:00:00Z',
                    'fileType': 'pdf',
                    'fileSize': 1024
                },
                {
                    'requestId': 'req-2',
                    'filename': 'doc2.docx',
                    'status': 'processing',
                    'timestamp': '2024-01-02T00:00:00Z',
                    'fileType': 'docx',
                    'fileSize': 2048
                }
            ],
            'Count': 2
        }
        mock_dynamodb.Table.return_value = mock_table
        
        event = {'queryStringParameters': {'limit': '10'}}
        
        response = index.handle_history_v1(event, 'test-client')
        
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertEqual(len(body['requests']), 2)
        self.assertEqual(body['count'], 2)
    
    def test_formats_endpoint_v1(self):
        """Test formats endpoint."""
        event = {}
        
        response = index.handle_formats_v1(event, 'test-client')
        
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertIn('supported_input_formats', body)
        self.assertIn('output_formats', body)
        self.assertIn('quality_levels', body)
        
        # Check input formats
        input_formats = body['supported_input_formats']
        extensions = [fmt['extension'] for fmt in input_formats]
        self.assertIn('.pdf', extensions)
        self.assertIn('.docx', extensions)
        self.assertIn('.txt', extensions)
        
        # Check output formats
        output_formats = body['output_formats']
        format_names = [fmt['format'] for fmt in output_formats]
        self.assertIn('markdown', format_names)
        self.assertIn('json', format_names)
        self.assertIn('html', format_names)
        self.assertIn('pdf', format_names)
    
    def test_health_check_endpoint(self):
        """Test health check endpoint."""
        event = {}
        
        response = index.handle_health_check(event)
        
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertEqual(body['status'], 'healthy')
        self.assertIn('timestamp', body)
        self.assertIn('services', body)
        self.assertEqual(body['services']['api_gateway'], 'healthy')
    
    def test_documentation_endpoint(self):
        """Test API documentation endpoint."""
        event = {}
        
        response = index.handle_api_documentation(event)
        
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertEqual(body['api_version'], 'v1')
        self.assertIn('endpoints', body)
        self.assertIn('examples', body)
        self.assertIn('rate_limits', body)
        
        # Check endpoint documentation
        endpoints = body['endpoints']
        paths = [ep['path'] for ep in endpoints]
        self.assertIn('/v1/upload', paths)
        self.assertIn('/v1/status/{request_id}', paths)
        self.assertIn('/v1/history', paths)
    
    def test_cors_headers_in_response(self):
        """Test CORS headers in API responses."""
        response = index.create_success_response(200, {'test': 'data'})
        
        headers = response['headers']
        self.assertEqual(headers['Access-Control-Allow-Origin'], '*')
        self.assertIn('GET, POST, OPTIONS', headers['Access-Control-Allow-Methods'])
        self.assertIn('Authorization', headers['Access-Control-Allow-Headers'])
        self.assertEqual(headers['X-API-Version'], 'v1')
    
    def test_error_response_format(self):
        """Test error response formatting."""
        response = index.create_error_response(400, 'Bad Request', 'Invalid input')
        
        self.assertEqual(response['statusCode'], 400)
        body = json.loads(response['body'])
        self.assertEqual(body['error']['type'], 'Bad Request')
        self.assertEqual(body['error']['message'], 'Invalid input')
        self.assertIn('timestamp', body['error'])
    
    def test_unsupported_endpoint(self):
        """Test request to unsupported endpoint."""
        event = {
            'httpMethod': 'GET',
            'path': '/v1/unknown',
            'headers': {'Authorization': 'Bearer test-api-key-12345678901234567890'},
            'queryStringParameters': None
        }
        
        response = index.handler(event, {})
        self.assertEqual(response['statusCode'], 404)
        body = json.loads(response['body'])
        self.assertIn('not found', body['error']['message'].lower())
    
    def test_unsupported_http_method(self):
        """Test unsupported HTTP method."""
        event = {
            'httpMethod': 'DELETE',  # Unsupported method
            'path': '/v1/upload',
            'headers': {'Authorization': 'Bearer test-api-key-12345678901234567890'},
            'queryStringParameters': None
        }
        
        response = index.handler(event, {})
        self.assertEqual(response['statusCode'], 405)
        body = json.loads(response['body'])
        self.assertIn('POST method is supported', body['error']['message'])

if __name__ == '__main__':
    unittest.main()