import json
import boto3
import os
import logging
import hashlib
from datetime import datetime, timezone
from jinja2 import Template
import markdown
from pdf_generator import AdvancedPDFGenerator, generate_enhanced_html

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
ses_client = boto3.client('ses')
dynamodb = boto3.resource('dynamodb')
s3_client = boto3.client('s3')

# Environment variables
DOCUMENT_BUCKET = os.environ.get('DOCUMENT_BUCKET')
HISTORY_TABLE = os.environ.get('HISTORY_TABLE')
FROM_EMAIL = os.environ.get('FROM_EMAIL', 'autospec-ai@example.com')
SLACK_WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL')

def handler(event, context):
    """
    Lambda handler for output formatting and delivery.
    Can be triggered by DynamoDB streams or direct invocation.
    """
    try:
        logger.info(f"Format function received event: {json.dumps(event)}")
        
        # Handle different event sources
        if 'Records' in event:
            # DynamoDB stream event
            for record in event['Records']:
                if record['eventName'] in ['INSERT', 'MODIFY']:
                    process_completed_analysis(record)
        else:
            # Direct invocation with request_id
            request_id = event.get('request_id')
            if request_id:
                process_request_by_id(request_id)
        
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Formatting completed successfully'})
        }
        
    except Exception as e:
        logger.error(f"Error in format function: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Formatting failed',
                'message': str(e)
            })
        }

def process_completed_analysis(dynamodb_record):
    """Process a completed analysis from DynamoDB stream."""
    try:
        # Extract request information from DynamoDB record
        if 'dynamodb' in dynamodb_record and 'NewImage' in dynamodb_record['dynamodb']:
            new_image = dynamodb_record['dynamodb']['NewImage']
            
            # Check if this is a completed AI processing record
            if (new_image.get('processingStage', {}).get('S') == 'ai_processing_complete' and 
                new_image.get('status', {}).get('S') == 'processed'):
                
                request_id = new_image['requestId']['S']
                process_request_by_id(request_id)
                
    except Exception as e:
        logger.error(f"Error processing DynamoDB record: {str(e)}")
        raise

def process_request_by_id(request_id):
    """Process a specific request by ID."""
    try:
        logger.info(f"Processing request: {request_id}")
        
        # Get request details from DynamoDB
        request_data = get_request_data(request_id)
        
        if not request_data:
            logger.error(f"No request data found for ID: {request_id}")
            return
        
        # Generate formatted outputs
        formatted_outputs = generate_formatted_outputs(request_data)
        
        # Send email response
        send_email_response(request_data, formatted_outputs)
        
        # Send Slack notification if configured
        send_slack_notification(request_data, formatted_outputs)
        
        # Store final results
        store_final_results(request_id, formatted_outputs)
        
        logger.info(f"Successfully processed and delivered request: {request_id}")
        
    except Exception as e:
        logger.error(f"Error processing request {request_id}: {str(e)}")
        update_processing_status(request_id, 'delivery_failed', str(e))
        raise

def get_request_data(request_id):
    """Retrieve request data from DynamoDB."""
    try:
        table = dynamodb.Table(HISTORY_TABLE)
        
        # Query for the request
        response = table.query(
            KeyConditionExpression='requestId = :id',
            ExpressionAttributeValues={':id': request_id}
        )
        
        if response['Items']:
            return response['Items'][0]  # Get the most recent record
        else:
            return None
            
    except Exception as e:
        logger.error(f"Error retrieving request data: {str(e)}")
        raise

def generate_formatted_outputs(request_data):
    """Generate formatted outputs in multiple formats."""
    try:
        ai_response = request_data.get('aiResponse', {})
        
        if not ai_response:
            raise ValueError("No AI response data found")
        
        # Extract components
        raw_response = ai_response.get('raw_response', '')
        requirements_sections = ai_response.get('requirements_sections', {})
        
        # Generate Markdown output
        markdown_output = generate_markdown_output(raw_response, requirements_sections, request_data)
        
        # Generate JSON output
        json_output = generate_json_output(ai_response, request_data)
        
        # Generate enhanced HTML output
        html_output = generate_enhanced_html_output(markdown_output, request_data, requirements_sections)
        
        # Generate advanced PDF
        pdf_output = None
        try:
            pdf_output = generate_advanced_pdf_output(request_data, {
                'markdown': markdown_output,
                'json': json_output,
                'html': html_output
            })
        except Exception as e:
            logger.warning(f"Advanced PDF generation failed: {str(e)}")
        
        return {
            'markdown': markdown_output,
            'json': json_output,
            'html': html_output,
            'pdf': pdf_output
        }
        
    except Exception as e:
        logger.error(f"Error generating formatted outputs: {str(e)}")
        raise

def generate_markdown_output(raw_response, sections, request_data):
    """Generate formatted Markdown output."""
    template_str = """# System Requirements Analysis

**Document:** {{ filename }}  
**Processed:** {{ processed_date }}  
**Generated by:** AutoSpec.AI

---

{{ raw_response }}

---

## Processing Summary

- **Request ID:** {{ request_id }}
- **Processing Status:** {{ status }}
- **AI Model:** {{ model_used }}
- **Sections Extracted:** {{ section_count }}

## Sections Overview

{% for section_name, section_content in sections.items() %}
### {{ section_name.replace('_', ' ').title() }}
{{ section_content }}

{% endfor %}

---

*Generated by AutoSpec.AI - Smart Document-to-System Requirements Analyzer*
"""
    
    template = Template(template_str)
    
    return template.render(
        filename=request_data.get('filename', 'Unknown'),
        processed_date=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
        raw_response=raw_response,
        request_id=request_data.get('requestId'),
        status=request_data.get('status'),
        model_used=request_data.get('aiResponse', {}).get('model_used', 'Unknown'),
        section_count=len(sections),
        sections=sections
    )

def generate_json_output(ai_response, request_data):
    """Generate structured JSON output."""
    json_structure = {
        'metadata': {
            'request_id': request_data.get('requestId'),
            'filename': request_data.get('filename'),
            'processed_at': request_data.get('processedAt'),
            'sender_email': request_data.get('senderEmail'),
            'file_type': request_data.get('fileType'),
            'processing_status': request_data.get('status')
        },
        'ai_analysis': {
            'model_used': ai_response.get('model_used'),
            'generated_at': ai_response.get('generated_at'),
            'processing_status': ai_response.get('processing_status')
        },
        'requirements': ai_response.get('requirements_sections', {}),
        'raw_response': ai_response.get('raw_response', ''),
        'generated_by': 'AutoSpec.AI',
        'format_version': '1.0'
    }
    
    return json.dumps(json_structure, indent=2, ensure_ascii=False)

def generate_enhanced_html_output(markdown_content, request_data, requirements_sections):
    """Generate enhanced HTML output with interactive features."""
    try:
        return generate_enhanced_html(markdown_content, request_data, requirements_sections)
        
    except Exception as e:
        logger.error(f"Error generating enhanced HTML: {str(e)}")
        # Fallback to simple HTML
        return generate_simple_html_output(markdown_content, request_data)

def generate_simple_html_output(markdown_content, request_data):
    """Generate simple HTML output as fallback."""
    try:
        # Convert Markdown to HTML
        html_content = markdown.markdown(markdown_content, extensions=['tables', 'fenced_code'])
        
        # Wrap in a complete HTML document
        html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>System Requirements - {{ filename }}</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }
        h1, h2, h3 { color: #2c3e50; }
        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
        th { background-color: #f8f9fa; }
        .metadata { background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0; }
        .footer { text-align: center; color: #666; margin-top: 40px; font-style: italic; }
    </style>
</head>
<body>
    {{ content }}
    <div class="footer">
        Generated by AutoSpec.AI<br>
        Smart Document-to-System Requirements Analyzer
    </div>
</body>
</html>"""
        
        template = Template(html_template)
        return template.render(
            filename=request_data.get('filename', 'Unknown'),
            content=html_content
        )
        
    except Exception as e:
        logger.error(f"Error generating simple HTML: {str(e)}")
        return markdown_content  # Fallback to plain markdown

def generate_advanced_pdf_output(request_data, formatted_outputs):
    """Generate advanced PDF output with charts and professional formatting."""
    try:
        pdf_generator = AdvancedPDFGenerator()
        pdf_bytes = pdf_generator.generate_advanced_pdf(request_data, formatted_outputs)
        
        if pdf_bytes:
            logger.info("Advanced PDF generated successfully")
            return pdf_bytes
        else:
            logger.warning("Advanced PDF generation returned None")
            return None
        
    except Exception as e:
        logger.error(f"Error generating advanced PDF: {str(e)}")
        return None

def send_email_response(request_data, formatted_outputs):
    """Send formatted requirements via email."""
    try:
        recipient_email = request_data.get('senderEmail')
        filename = request_data.get('filename', 'document')
        request_id = request_data.get('requestId')
        
        if not recipient_email:
            logger.error("No recipient email found")
            return
        
        # Create email subject
        subject = f"AutoSpec.AI - System Requirements for {filename}"
        
        # Create email body
        email_body = create_email_body(request_data, formatted_outputs)
        
        # Send email with attachments
        send_ses_email(
            recipient_email,
            subject,
            email_body,
            formatted_outputs,
            request_id
        )
        
        logger.info(f"Email sent successfully to {recipient_email}")
        
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        raise

def create_email_body(request_data, formatted_outputs):
    """Create email body content."""
    email_template = """Dear User,

Your document analysis is complete! AutoSpec.AI has generated comprehensive system requirements based on your uploaded document.

Document Details:
- Filename: {{ filename }}
- Processed: {{ processed_date }}
- Request ID: {{ request_id }}

The analysis includes:
- Executive Summary
- Functional Requirements
- Non-Functional Requirements
- Stakeholder Roles and Responsibilities
- Technical Architecture Considerations
- Integration Requirements
- Data Requirements
- Security and Compliance

Please find the detailed requirements attached in multiple formats:
- Markdown (.md) - Human-readable text format
- JSON (.json) - Structured data format
- HTML (.html) - Web-viewable format

If you have any questions about the analysis or need clarification on any requirements, please feel free to reach out.

Best regards,
AutoSpec.AI Team

---
This is an automated message from AutoSpec.AI
Smart Document-to-System Requirements Analyzer
"""
    
    template = Template(email_template)
    return template.render(
        filename=request_data.get('filename', 'Unknown'),
        processed_date=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
        request_id=request_data.get('requestId')
    )

def send_ses_email(recipient, subject, body, attachments, request_id):
    """Send email via Amazon SES with PDF attachment."""
    try:
        import email.mime.multipart
        import email.mime.text
        import email.mime.base
        import email.encoders
        import base64
        
        # Create multipart message
        msg = email.mime.multipart.MIMEMultipart('mixed')
        msg['Subject'] = subject
        msg['From'] = FROM_EMAIL
        msg['To'] = recipient
        
        # Create multipart alternative for text and HTML
        msg_body = email.mime.multipart.MIMEMultipart('alternative')
        
        # Add text version
        text_part = email.mime.text.MIMEText(body, 'plain', 'utf-8')
        msg_body.attach(text_part)
        
        # Add HTML version
        html_content = attachments.get('html', body)
        html_part = email.mime.text.MIMEText(html_content, 'html', 'utf-8')
        msg_body.attach(html_part)
        
        msg.attach(msg_body)
        
        # Add PDF attachment if available
        pdf_content = attachments.get('pdf')
        if pdf_content:
            try:
                pdf_attachment = email.mime.base.MIMEBase('application', 'pdf')
                pdf_attachment.set_payload(pdf_content)
                email.encoders.encode_base64(pdf_attachment)
                pdf_attachment.add_header(
                    'Content-Disposition',
                    f'attachment; filename="requirements_analysis_{request_id}.pdf"'
                )
                msg.attach(pdf_attachment)
                logger.info("PDF attachment added to email")
            except Exception as e:
                logger.warning(f"Failed to attach PDF: {str(e)}")
        
        # Add Markdown attachment
        markdown_content = attachments.get('markdown', '')
        if markdown_content:
            try:
                md_attachment = email.mime.text.MIMEText(markdown_content, 'plain', 'utf-8')
                md_attachment.add_header(
                    'Content-Disposition',
                    f'attachment; filename="requirements_analysis_{request_id}.md"'
                )
                msg.attach(md_attachment)
                logger.info("Markdown attachment added to email")
            except Exception as e:
                logger.warning(f"Failed to attach Markdown: {str(e)}")
        
        # Add JSON attachment
        json_content = attachments.get('json', '')
        if json_content:
            try:
                json_attachment = email.mime.text.MIMEText(json_content, 'plain', 'utf-8')
                json_attachment.add_header(
                    'Content-Disposition',
                    f'attachment; filename="requirements_analysis_{request_id}.json"'
                )
                msg.attach(json_attachment)
                logger.info("JSON attachment added to email")
            except Exception as e:
                logger.warning(f"Failed to attach JSON: {str(e)}")
        
        # Send email
        response = ses_client.send_raw_email(
            Source=FROM_EMAIL,
            Destinations=[recipient],
            RawMessage={'Data': msg.as_string()}
        )
        
        logger.info(f"SES email with attachments sent, MessageId: {response['MessageId']}")
        
    except Exception as e:
        logger.error(f"Error sending SES email with attachments: {str(e)}")
        # Fallback to simple email
        try:
            response = ses_client.send_email(
                Source=FROM_EMAIL,
                Destination={'ToAddresses': [recipient]},
                Message={
                    'Subject': {'Data': subject},
                    'Body': {
                        'Text': {'Data': body},
                        'Html': {'Data': attachments.get('html', body)}
                    }
                }
            )
            logger.info(f"Fallback SES email sent, MessageId: {response['MessageId']}")
        except Exception as fallback_error:
            logger.error(f"Fallback email also failed: {str(fallback_error)}")
            raise

def store_final_results(request_id, formatted_outputs):
    """Store final formatted results in DynamoDB."""
    try:
        table = dynamodb.Table(HISTORY_TABLE)
        
        # Create hash of the response for versioning
        response_hash = hashlib.md5(
            formatted_outputs['json'].encode('utf-8')
        ).hexdigest()
        
        # Update the record with final results
        table.update_item(
            Key={
                'requestId': request_id,
                'timestamp': get_latest_timestamp(request_id)
            },
            UpdateExpression='SET processingStage = :stage, #status = :status, formattedOutputs = :outputs, responseHash = :hash, deliveredAt = :delivered',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':stage': 'delivery_complete',
                ':status': 'delivered',
                ':outputs': {
                    'markdown_length': len(formatted_outputs['markdown']),
                    'json_length': len(formatted_outputs['json']),
                    'html_length': len(formatted_outputs['html']),
                    'pdf_generated': formatted_outputs['pdf'] is not None
                },
                ':hash': response_hash,
                ':delivered': datetime.now(timezone.utc).isoformat()
            }
        )
        
        logger.info(f"Final results stored for request {request_id}")
        
    except Exception as e:
        logger.error(f"Error storing final results: {str(e)}")
        raise

def get_latest_timestamp(request_id):
    """Get the latest timestamp for a request ID."""
    try:
        table = dynamodb.Table(HISTORY_TABLE)
        response = table.query(
            KeyConditionExpression='requestId = :id',
            ExpressionAttributeValues={':id': request_id},
            ScanIndexForward=False,  # Get latest first
            Limit=1
        )
        
        if response['Items']:
            return response['Items'][0]['timestamp']
        else:
            return None
            
    except Exception as e:
        logger.error(f"Error getting latest timestamp: {str(e)}")
        raise

def update_processing_status(request_id, status, error_message=None):
    """Update processing status in DynamoDB."""
    try:
        table = dynamodb.Table(HISTORY_TABLE)
        timestamp = get_latest_timestamp(request_id)
        
        if not timestamp:
            logger.error(f"No timestamp found for request {request_id}")
            return
        
        update_expression = 'SET #status = :status, processingStage = :stage'
        expression_values = {
            ':status': status,
            ':stage': f'formatting_{status}'
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

def send_slack_notification(request_data, formatted_outputs):
    """Send Slack notification if webhook URL is configured."""
    try:
        if not SLACK_WEBHOOK_URL:
            logger.info("No Slack webhook configured, skipping Slack notification")
            return
        
        # Extract relevant data
        filename = request_data.get('filename', 'Unknown')
        request_id = request_data.get('requestId')
        sender_email = request_data.get('senderEmail', 'Unknown')
        
        # Get Slack channel/user from request metadata if available
        slack_channel = request_data.get('slackChannel')
        slack_user = request_data.get('slackUser')
        
        # Create Slack message
        slack_message = create_slack_message(request_data, formatted_outputs)
        
        # Send to webhook
        send_slack_webhook(slack_message, slack_channel)
        
        logger.info(f"Slack notification sent for request {request_id}")
        
    except Exception as e:
        logger.error(f"Error sending Slack notification: {str(e)}")
        # Don't fail the entire process if Slack fails

def create_slack_message(request_data, formatted_outputs):
    """Create formatted Slack message."""
    try:
        filename = request_data.get('filename', 'Unknown')
        request_id = request_data.get('requestId')
        ai_response = request_data.get('aiResponse', {})
        requirements_sections = ai_response.get('requirements_sections', {})
        
        # Create rich Slack message with blocks
        message = {
            "text": f"AutoSpec.AI Analysis Complete: {filename}",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "🎉 Document Analysis Complete!"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Document:*\n{filename}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Request ID:*\n`{request_id}`"
                        }
                    ]
                },
                {
                    "type": "divider"
                }
            ]
        }
        
        # Add executive summary if available
        exec_summary = requirements_sections.get('executive_summary', '')
        if exec_summary:
            # Truncate for Slack display
            summary = exec_summary[:300] + "..." if len(exec_summary) > 300 else exec_summary
            message["blocks"].append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Executive Summary:*\n{summary}"
                }
            })
        
        # Add sections overview
        sections_found = []
        section_mapping = {
            'functional_requirements': '⚙️ Functional Requirements',
            'non_functional_requirements': '📊 Non-Functional Requirements',
            'stakeholder_roles_and_responsibilities': '👥 Stakeholder Roles',
            'technical_architecture_considerations': '🏗️ Technical Architecture',
            'integration_requirements': '🔗 Integration Requirements',
            'data_requirements': '💾 Data Requirements',
            'security_and_compliance': '🔒 Security & Compliance'
        }
        
        for section_key, section_name in section_mapping.items():
            if section_key in requirements_sections and requirements_sections[section_key].strip():
                sections_found.append(section_name)
        
        if sections_found:
            sections_text = "\n".join([f"• {section}" for section in sections_found])
            message["blocks"].append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Analysis Includes:*\n{sections_text}"
                }
            })
        
        # Add action buttons
        message["blocks"].extend([
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "📧 *Full detailed report sent to your email!*"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Check Status"
                        },
                        "style": "primary",
                        "value": f"status_{request_id}",
                        "action_id": "check_status"
                    }
                ]
            }
        ])
        
        return message
        
    except Exception as e:
        logger.error(f"Error creating Slack message: {str(e)}")
        # Fallback to simple message
        return {
            "text": f"AutoSpec.AI analysis complete for {request_data.get('filename', 'document')}! Check your email for detailed results."
        }

def send_slack_webhook(message, channel=None):
    """Send message to Slack webhook."""
    try:
        import urllib.request
        
        # Add channel if specified
        if channel:
            message["channel"] = channel
        
        # Add username and icon
        message.update({
            "username": "AutoSpec.AI",
            "icon_emoji": ":robot_face:"
        })
        
        # Send webhook request
        req = urllib.request.Request(
            SLACK_WEBHOOK_URL,
            data=json.dumps(message).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        
        response = urllib.request.urlopen(req)
        
        if response.status == 200:
            logger.info("Slack webhook sent successfully")
        else:
            logger.warning(f"Slack webhook returned status {response.status}")
        
    except Exception as e:
        logger.error(f"Error sending Slack webhook: {str(e)}")
        raise