import json
import boto3
import os
import logging
import hmac
import hashlib
import time
import urllib.parse
from datetime import datetime, timezone

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
s3_client = boto3.client('s3')
lambda_client = boto3.client('lambda')

# Environment variables
SLACK_SIGNING_SECRET = os.environ.get('SLACK_SIGNING_SECRET')
DOCUMENT_BUCKET = os.environ.get('DOCUMENT_BUCKET')
HISTORY_TABLE = os.environ.get('HISTORY_TABLE')
INGEST_FUNCTION_NAME = os.environ.get('INGEST_FUNCTION_NAME')

def handler(event, context):
    """
    Lambda handler for Slack integration.
    Handles slash commands and webhook responses.
    """
    try:
        logger.info(f"Slack integration received event: {json.dumps(event)}")
        
        # Parse the request
        headers = event.get('headers', {})
        body = event.get('body', '')
        
        # Verify Slack signature
        if not verify_slack_signature(headers, body):
            return {
                'statusCode': 401,
                'body': json.dumps({'error': 'Invalid signature'})
            }
        
        # Parse form data from Slack
        if event.get('isBase64Encoded'):
            import base64
            body = base64.b64decode(body).decode('utf-8')
        
        form_data = urllib.parse.parse_qs(body)
        
        # Handle different Slack events
        if 'command' in form_data:
            return handle_slash_command(form_data)
        elif 'payload' in form_data:
            return handle_interactive_component(form_data)
        else:
            return handle_webhook_response(form_data)
        
    except Exception as e:
        logger.error(f"Error in Slack handler: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal server error'})
        }

def verify_slack_signature(headers, body):
    """Verify that the request came from Slack."""
    if not SLACK_SIGNING_SECRET:
        logger.warning("SLACK_SIGNING_SECRET not configured")
        return True  # Skip verification in development
    
    timestamp = headers.get('x-slack-request-timestamp', [''])[0]
    signature = headers.get('x-slack-signature', [''])[0]
    
    if not timestamp or not signature:
        return False
    
    # Check timestamp to prevent replay attacks
    if abs(time.time() - int(timestamp)) > 60 * 5:  # 5 minutes
        return False
    
    # Verify signature
    sig_basestring = f"v0:{timestamp}:{body}"
    my_signature = 'v0=' + hmac.new(
        SLACK_SIGNING_SECRET.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(my_signature, signature)

def handle_slash_command(form_data):
    """Handle Slack slash commands."""
    try:
        command = form_data.get('command', [''])[0]
        text = form_data.get('text', [''])[0]
        user_id = form_data.get('user_id', [''])[0]
        channel_id = form_data.get('channel_id', [''])[0]
        response_url = form_data.get('response_url', [''])[0]
        
        logger.info(f"Slash command: {command}, text: {text}, user: {user_id}")
        
        if command == '/autospec':
            return handle_autospec_command(text, user_id, channel_id, response_url)
        else:
            return slack_response("Unknown command", ephemeral=True)
            
    except Exception as e:
        logger.error(f"Error handling slash command: {str(e)}")
        return slack_response("Error processing command", ephemeral=True)

def handle_autospec_command(text, user_id, channel_id, response_url):
    """Handle the /autospec slash command."""
    try:
        # Parse command arguments
        args = text.strip().split() if text.strip() else []
        
        if not args:
            return slack_response(get_help_message(), ephemeral=True)
        
        subcommand = args[0].lower()
        
        if subcommand == 'help':
            return slack_response(get_help_message(), ephemeral=True)
        
        elif subcommand == 'upload':
            return handle_upload_command(args[1:], user_id, channel_id, response_url)
        
        elif subcommand == 'status':
            return handle_status_command(args[1:], user_id, channel_id)
        
        elif subcommand == 'list':
            return handle_list_command(user_id, channel_id)
        
        else:
            return slack_response(f"Unknown subcommand: {subcommand}\n\n{get_help_message()}", ephemeral=True)
            
    except Exception as e:
        logger.error(f"Error handling autospec command: {str(e)}")
        return slack_response("Error processing autospec command", ephemeral=True)

def handle_upload_command(args, user_id, channel_id, response_url):
    """Handle document upload command."""
    if not args:
        return slack_response(
            "Please provide a document URL or use file upload.\n"
            "Usage: `/autospec upload <url>` or attach a file to your message.",
            ephemeral=True
        )
    
    # For now, return instructions for file upload
    # In production, you would handle URL downloads or file attachments
    return slack_response(
        "📄 Document Upload Instructions:\n\n"
        "1. Use the AutoSpec.AI email: `autospec@your-domain.com`\n"
        "2. Or use the API endpoint for direct uploads\n"
        "3. Supported formats: PDF, DOCX, TXT\n\n"
        "Your analysis will be delivered back to this channel when complete!",
        ephemeral=True
    )

def handle_status_command(args, user_id, channel_id):
    """Handle status check command."""
    if not args:
        return slack_response(
            "Please provide a request ID.\n"
            "Usage: `/autospec status <request-id>`",
            ephemeral=True
        )
    
    request_id = args[0]
    
    try:
        # Get request status from DynamoDB
        status_info = get_request_status(request_id)
        
        if not status_info:
            return slack_response(f"Request ID `{request_id}` not found.", ephemeral=True)
        
        # Format status response
        status_message = format_status_message(status_info)
        return slack_response(status_message, ephemeral=True)
        
    except Exception as e:
        logger.error(f"Error checking status: {str(e)}")
        return slack_response("Error checking request status", ephemeral=True)

def handle_list_command(user_id, channel_id):
    """Handle list recent requests command."""
    try:
        # This would require a GSI on senderEmail or a different approach
        # For now, return a placeholder
        return slack_response(
            "📋 Recent Requests:\n\n"
            "This feature is coming soon! For now, use `/autospec status <request-id>` "
            "to check specific request status.",
            ephemeral=True
        )
        
    except Exception as e:
        logger.error(f"Error listing requests: {str(e)}")
        return slack_response("Error listing requests", ephemeral=True)

def get_help_message():
    """Get help message for Slack commands."""
    return """🤖 **AutoSpec.AI Slack Integration**

Available commands:
• `/autospec help` - Show this help message
• `/autospec upload <url>` - Upload document for analysis
• `/autospec status <request-id>` - Check processing status
• `/autospec list` - List your recent requests

**How it works:**
1. Upload documents via email or API
2. Get notified in Slack when analysis is complete
3. View structured system requirements
4. Download formatted reports

**Supported formats:** PDF, DOCX, TXT

For more info, visit: https://autospec.ai"""

def get_request_status(request_id):
    """Get request status from DynamoDB."""
    try:
        table = dynamodb.Table(HISTORY_TABLE)
        
        response = table.query(
            KeyConditionExpression='requestId = :id',
            ExpressionAttributeValues={':id': request_id},
            ScanIndexForward=False,  # Get latest first
            Limit=1
        )
        
        if response['Items']:
            return response['Items'][0]
        else:
            return None
            
    except Exception as e:
        logger.error(f"Error getting request status: {str(e)}")
        return None

def format_status_message(status_info):
    """Format status information for Slack."""
    request_id = status_info.get('requestId', 'Unknown')
    filename = status_info.get('filename', 'Unknown')
    status = status_info.get('status', 'Unknown')
    processing_stage = status_info.get('processingStage', 'Unknown')
    timestamp = status_info.get('timestamp', 'Unknown')
    
    # Status emoji mapping
    status_emoji = {
        'uploaded': '📤',
        'processing': '⚙️',
        'processed': '✅',
        'delivered': '📧',
        'failed': '❌'
    }
    
    emoji = status_emoji.get(status, '📋')
    
    message = f"{emoji} **Request Status**\n\n"
    message += f"**Request ID:** `{request_id}`\n"
    message += f"**Filename:** {filename}\n"
    message += f"**Status:** {status.title()}\n"
    message += f"**Stage:** {processing_stage.replace('_', ' ').title()}\n"
    message += f"**Last Updated:** {timestamp}\n"
    
    if status == 'delivered':
        message += "\n✅ Analysis complete! Check your email for detailed results."
    elif status == 'failed':
        error_msg = status_info.get('errorMessage', 'Unknown error')
        message += f"\n❌ **Error:** {error_msg}"
    elif status == 'processing' or processing_stage.startswith('ai_processing'):
        message += "\n⚙️ AI analysis in progress..."
    
    return message

def slack_response(text, ephemeral=False):
    """Create a Slack response."""
    response = {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({
            'text': text,
            'response_type': 'ephemeral' if ephemeral else 'in_channel'
        })
    }
    
    return response

def handle_interactive_component(form_data):
    """Handle interactive Slack components (buttons, menus, etc.)."""
    try:
        payload = json.loads(form_data['payload'][0])
        
        # Handle different interaction types
        if payload.get('type') == 'block_actions':
            return handle_block_actions(payload)
        else:
            return slack_response("Unknown interaction type", ephemeral=True)
            
    except Exception as e:
        logger.error(f"Error handling interactive component: {str(e)}")
        return slack_response("Error processing interaction", ephemeral=True)

def handle_block_actions(payload):
    """Handle block action interactions."""
    # Placeholder for interactive components
    return slack_response("Interactive components coming soon!", ephemeral=True)

def handle_webhook_response(form_data):
    """Handle incoming webhook responses."""
    # This would be used for file uploads or other webhook integrations
    return slack_response("Webhook received", ephemeral=True)

def send_slack_notification(webhook_url, message):
    """Send a notification to Slack webhook."""
    try:
        import urllib.request
        
        payload = {
            'text': message,
            'username': 'AutoSpec.AI',
            'icon_emoji': ':robot_face:'
        }
        
        req = urllib.request.Request(
            webhook_url,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        
        response = urllib.request.urlopen(req)
        logger.info(f"Slack notification sent: {response.status}")
        
    except Exception as e:
        logger.error(f"Error sending Slack notification: {str(e)}")

def format_requirements_for_slack(requirements_data):
    """Format AI-generated requirements for Slack display."""
    try:
        metadata = requirements_data.get('metadata', {})
        requirements = requirements_data.get('requirements', {})
        
        # Create formatted message
        message = f"🎉 **Analysis Complete!**\n\n"
        message += f"**Document:** {metadata.get('filename', 'Unknown')}\n"
        message += f"**Request ID:** `{metadata.get('request_id', 'Unknown')}`\n\n"
        
        # Add executive summary if available
        exec_summary = requirements.get('executive_summary', '')
        if exec_summary:
            # Truncate for Slack
            summary = exec_summary[:200] + "..." if len(exec_summary) > 200 else exec_summary
            message += f"**Executive Summary:**\n{summary}\n\n"
        
        # Add sections overview
        sections = [
            ('functional_requirements', '⚙️ Functional Requirements'),
            ('non_functional_requirements', '📊 Non-Functional Requirements'),
            ('stakeholder_roles_and_responsibilities', '👥 Stakeholder Roles'),
            ('technical_architecture_considerations', '🏗️ Technical Architecture'),
            ('security_and_compliance', '🔒 Security & Compliance')
        ]
        
        message += "**Analysis Includes:**\n"
        for section_key, section_name in sections:
            if section_key in requirements and requirements[section_key].strip():
                message += f"• {section_name}\n"
        
        message += "\n📧 **Full detailed report sent to your email!**"
        
        return message
        
    except Exception as e:
        logger.error(f"Error formatting requirements for Slack: {str(e)}")
        return "Analysis complete! Check your email for detailed results."