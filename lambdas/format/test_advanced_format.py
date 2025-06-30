import json
import unittest
from unittest.mock import patch, MagicMock, mock_open
import sys
import os

# Add the current directory to the path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import index
from pdf_generator import AdvancedPDFGenerator, generate_enhanced_html

class TestAdvancedFormatting(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock environment variables
        os.environ['DOCUMENT_BUCKET'] = 'test-bucket'
        os.environ['HISTORY_TABLE'] = 'test-table'
        os.environ['FROM_EMAIL'] = 'test@autospec.ai'
        
        # Sample request data with format preferences
        self.sample_request_data = {
            'requestId': 'test-request-123',
            'timestamp': '2024-01-01T00:00:00Z',
            'filename': 'advanced_test_document.pdf',
            'senderEmail': 'user@example.com',
            'fileType': 'pdf',
            'status': 'processed',
            'formatPreferences': {
                'formats': ['markdown', 'json', 'html', 'pdf'],
                'quality': 'premium',
                'charts': True,
                'interactive': True
            },
            'aiResponse': {
                'raw_response': '## Executive Summary\nAdvanced test system overview.\n\n## Functional Requirements\n- Advanced feature 1\n- Advanced feature 2\n\n## Non-Functional Requirements\n- Performance: 99.9% uptime\n- Security: Multi-factor authentication',
                'model_used': 'anthropic.claude-3-sonnet-20240229-v1:0',
                'generated_at': '2024-01-01T00:00:00Z',
                'processing_status': 'completed',
                'requirements_sections': {
                    'executive_summary': 'Advanced test system overview with comprehensive analysis.',
                    'functional_requirements': '- Advanced feature 1: Real-time processing\n- Advanced feature 2: Machine learning integration',
                    'non_functional_requirements': '- Performance: 99.9% uptime\n- Security: Multi-factor authentication\n- Scalability: Auto-scaling infrastructure',
                    'stakeholder_roles_and_responsibilities': '- Product Owner: Define requirements\n- Development Team: Implement features\n- QA Team: Ensure quality',
                    'technical_architecture_considerations': '- Microservices architecture\n- Cloud-native deployment\n- Container orchestration',
                    'security_and_compliance': '- GDPR compliance\n- SOC 2 certification\n- Regular security audits'
                }
            }
        }
    
    def test_advanced_pdf_generator_initialization(self):
        """Test PDF generator initialization."""
        pdf_generator = AdvancedPDFGenerator()
        
        self.assertIsNotNone(pdf_generator.styles)
        self.assertIsNotNone(pdf_generator.custom_styles)
        self.assertIn('CustomTitle', pdf_generator.custom_styles)
        self.assertIn('CustomHeading1', pdf_generator.custom_styles)
        self.assertIn('CustomBody', pdf_generator.custom_styles)
    
    @patch('matplotlib.pyplot.savefig')
    @patch('matplotlib.pyplot.subplots')
    def test_requirements_overview_chart_creation(self, mock_subplots, mock_savefig):
        """Test requirements overview chart generation."""
        # Mock matplotlib components
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_subplots.return_value = (mock_fig, mock_ax)
        
        pdf_generator = AdvancedPDFGenerator()
        requirements_sections = self.sample_request_data['aiResponse']['requirements_sections']
        
        # This would normally create a chart; we're testing the structure
        chart = pdf_generator._create_requirements_overview_chart(requirements_sections)
        
        # Verify matplotlib was called
        mock_subplots.assert_called_once()
        mock_ax.pie.assert_called_once()
        mock_ax.set_title.assert_called_once()
    
    def test_generate_enhanced_html_structure(self):
        """Test enhanced HTML generation structure."""
        markdown_content = "# Test Requirements\n\nThis is a test document."
        requirements_sections = self.sample_request_data['aiResponse']['requirements_sections']
        
        html_output = generate_enhanced_html(markdown_content, self.sample_request_data, requirements_sections)
        
        # Check for enhanced HTML features
        self.assertIn('<!DOCTYPE html>', html_output)
        self.assertIn('plotly', html_output.lower())  # Interactive charts
        self.assertIn('tabs', html_output.lower())    # Tabbed interface
        self.assertIn('chart-container', html_output) # Chart containers
        self.assertIn('advanced_test_document.pdf', html_output)
        self.assertIn('test-request-123', html_output)
    
    def test_enhanced_html_interactive_features(self):
        """Test interactive features in enhanced HTML."""
        markdown_content = "# Test"
        requirements_sections = self.sample_request_data['aiResponse']['requirements_sections']
        
        html_output = generate_enhanced_html(markdown_content, self.sample_request_data, requirements_sections)
        
        # Check for interactive JavaScript
        self.assertIn('openTab', html_output)
        self.assertIn('Plotly.newPlot', html_output)
        self.assertIn('overviewChart', html_output)
        self.assertIn('qualityChart', html_output)
        
        # Check for responsive design
        self.assertIn('@media print', html_output)
        self.assertIn('max-width', html_output)
    
    def test_format_preferences_integration(self):
        """Test format preferences integration in generation."""
        formatted_outputs = index.generate_formatted_outputs(self.sample_request_data)
        
        # Check all formats are generated
        self.assertIn('markdown', formatted_outputs)
        self.assertIn('json', formatted_outputs)
        self.assertIn('html', formatted_outputs)
        self.assertIn('pdf', formatted_outputs)
        
        # Check JSON structure includes preferences
        json_data = json.loads(formatted_outputs['json'])
        self.assertIn('metadata', json_data)
        self.assertIn('requirements', json_data)
        
        # Check HTML includes interactive features (based on preferences)
        html_content = formatted_outputs['html']
        if self.sample_request_data['formatPreferences']['interactive']:
            self.assertIn('plotly', html_content.lower())
    
    @patch('index.ses_client')
    def test_email_with_multiple_attachments(self, mock_ses):
        """Test email sending with multiple format attachments."""
        mock_ses.send_raw_email.return_value = {'MessageId': 'test-message-id'}
        
        formatted_outputs = {
            'markdown': '# Test Markdown Content',
            'json': '{"test": "json content"}',
            'html': '<html><body>Test HTML</body></html>',
            'pdf': b'mock pdf content'
        }
        
        # Test email sending
        index.send_email_response(self.sample_request_data, formatted_outputs)
        
        # Verify raw email was sent (with attachments)
        mock_ses.send_raw_email.assert_called_once()
        
        # Check call arguments
        call_args = mock_ses.send_raw_email.call_args[1]
        self.assertEqual(call_args['Source'], 'test@autospec.ai')
        self.assertIn('user@example.com', call_args['Destinations'])
        self.assertIn('Data', call_args['RawMessage'])
    
    def test_quality_metrics_chart_data(self):
        """Test quality metrics chart generation."""
        pdf_generator = AdvancedPDFGenerator()
        
        # Test that quality metrics are reasonable
        with patch('matplotlib.pyplot.subplots') as mock_subplots:
            mock_fig = MagicMock()
            mock_ax = MagicMock()
            mock_subplots.return_value = (mock_fig, mock_ax)
            
            chart = pdf_generator._create_quality_metrics_chart()
            
            # Verify bar chart was created
            mock_ax.bar.assert_called_once()
            
            # Check that metrics were used
            call_args = mock_ax.bar.call_args[0]
            categories = call_args[0]
            values = call_args[1]
            
            # Should have standard quality metrics
            expected_categories = ['Completeness', 'Clarity', 'Feasibility', 'Testability', 'Consistency']
            self.assertEqual(categories, expected_categories)
            
            # Values should be reasonable percentages
            for value in values:
                self.assertGreaterEqual(value, 0)
                self.assertLessEqual(value, 100)
    
    @patch('index.dynamodb')
    def test_preferences_storage_in_dynamodb(self, mock_dynamodb):
        """Test that format preferences are stored in DynamoDB."""
        mock_table = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        
        formatted_outputs = {
            'markdown': 'test',
            'json': '{"test": true}',
            'html': '<html></html>',
            'pdf': b'pdf content'
        }
        
        # Store final results
        index.store_final_results('test-request-123', formatted_outputs)
        
        # Verify DynamoDB update was called
        mock_table.update_item.assert_called_once()
        
        # Check that outputs metadata was stored
        call_args = mock_table.update_item.call_args[1]
        self.assertIn('formattedOutputs', str(call_args))
    
    def test_error_handling_in_advanced_generation(self):
        """Test error handling in advanced format generation."""
        # Test with invalid request data
        invalid_request = {
            'requestId': 'test',
            'aiResponse': {}  # Missing required fields
        }
        
        # Should not raise exception, should return None or fallback
        try:
            result = index.generate_formatted_outputs(invalid_request)
            # Should handle gracefully
            self.assertIsInstance(result, dict)
        except Exception as e:
            self.fail(f"Advanced formatting should handle errors gracefully: {str(e)}")
    
    def test_pdf_generation_fallback(self):
        """Test PDF generation fallback behavior."""
        # Test with missing dependencies or invalid data
        pdf_generator = AdvancedPDFGenerator()
        
        # Should handle missing data gracefully
        try:
            result = pdf_generator.generate_advanced_pdf({}, {})
            # Should return None or handle gracefully
            self.assertIsNone(result)
        except Exception as e:
            self.fail(f"PDF generation should handle missing data gracefully: {str(e)}")
    
    def test_chart_generation_with_empty_sections(self):
        """Test chart generation with empty requirements sections."""
        pdf_generator = AdvancedPDFGenerator()
        
        # Test with empty sections
        empty_sections = {}
        chart = pdf_generator._create_requirements_overview_chart(empty_sections)
        
        # Should return None for empty sections
        self.assertIsNone(chart)
    
    def test_html_responsive_design_elements(self):
        """Test HTML responsive design features."""
        markdown_content = "# Test"
        requirements_sections = {'executive_summary': 'Test summary'}
        
        html_output = generate_enhanced_html(markdown_content, self.sample_request_data, requirements_sections)
        
        # Check for responsive design elements
        self.assertIn('viewport', html_output)
        self.assertIn('max-width', html_output)
        self.assertIn('@media print', html_output)
        self.assertIn('margin: 0 auto', html_output)
        
        # Check for mobile-friendly features
        self.assertIn('border-radius', html_output)
        self.assertIn('box-shadow', html_output)

if __name__ == '__main__':
    unittest.main()