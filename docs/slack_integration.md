# Slack Integration Documentation

## Overview

The AutoSpec.AI Slack integration provides a seamless way for teams to interact with the document analysis system directly from their Slack workspace. Users can upload documents, check processing status, and receive notifications when analysis is complete.

## Features

### Slash Commands
- `/autospec help` - Display help and usage information
- `/autospec upload <url>` - Instructions for document upload
- `/autospec status <request-id>` - Check processing status
- `/autospec list` - List recent requests (coming soon)

### Notifications
- Automatic notifications when document analysis is complete
- Rich message formatting with executive summary preview
- Interactive buttons for status checking
- Professional branding with AutoSpec.AI identity

## Architecture

### Components

#### 1. Slack Lambda Function (`lambdas/slack/`)
- **Purpose**: Handle Slack slash commands and interactive components
- **Triggers**: API Gateway requests from Slack
- **Functions**:
  - Command parsing and routing
  - Request status checking
  - Help and usage information
  - Security validation with signature verification

#### 2. Format Lambda Integration
- **Enhanced**: Added Slack notification capabilities
- **Functions**:
  - Send rich notifications when analysis completes
  - Format requirements summary for Slack display
  - Handle webhook delivery failures gracefully

#### 3. API Gateway Endpoint
- **Endpoint**: `/slack` (POST)
- **Purpose**: Receive Slack events and commands
- **Security**: Slack signature verification

## Slack App Setup

### 1. Create Slack App
1. Go to [api.slack.com](https://api.slack.com/apps)
2. Click "Create New App"
3. Choose "From scratch"
4. Enter app name: "AutoSpec.AI"
5. Select your workspace

### 2. Configure Slash Commands
Navigate to "Slash Commands" and create:
```
Command: /autospec
Request URL: https://your-api-gateway-url/prod/slack
Short Description: AutoSpec.AI document analysis
Usage Hint: help | upload <url> | status <request-id>
```

### 3. Configure Interactive Components
Enable interactive components:
```
Request URL: https://your-api-gateway-url/prod/slack
```

### 4. Configure Incoming Webhooks
Enable incoming webhooks for notifications:
1. Activate incoming webhooks
2. Add webhook to workspace
3. Copy webhook URL for configuration

### 5. Set Permissions
Required OAuth scopes:
- `commands` - Use slash commands
- `incoming-webhook` - Send messages
- `chat:write` - Send messages as app

## Configuration

### Environment Variables
Set in CDK deployment:

```javascript
environment: {
  SLACK_SIGNING_SECRET: 'your-slack-signing-secret',
  SLACK_WEBHOOK_URL: 'your-webhook-url',
  // ... other variables
}
```

### Slack App Settings
1. **Signing Secret**: Found in "Basic Information" → "App Credentials"
2. **Webhook URL**: Found in "Incoming Webhooks" after adding to workspace
3. **Bot Token**: Found in "OAuth & Permissions" (if needed for advanced features)

## Message Formats

### Slash Command Responses

#### Help Message
```
🤖 AutoSpec.AI Slack Integration

Available commands:
• /autospec help - Show this help message
• /autospec upload <url> - Upload document for analysis
• /autospec status <request-id> - Check processing status
• /autospec list - List your recent requests

How it works:
1. Upload documents via email or API
2. Get notified in Slack when analysis is complete
3. View structured system requirements
4. Download formatted reports

Supported formats: PDF, DOCX, TXT
```

#### Status Response
```
✅ Request Status

Request ID: `abc-123-def`
Filename: requirements_document.pdf
Status: Delivered
Stage: Delivery Complete
Last Updated: 2024-01-01T00:00:00Z

✅ Analysis complete! Check your email for detailed results.
```

### Rich Notifications

#### Analysis Complete Message
```json
{
  "text": "AutoSpec.AI Analysis Complete: document.pdf",
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
          "text": "*Document:*\ndocument.pdf"
        },
        {
          "type": "mrkdwn",  
          "text": "*Request ID:*\n`abc-123-def`"
        }
      ]
    },
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "*Executive Summary:*\nSystem overview and key requirements..."
      }
    },
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "*Analysis Includes:*\n• ⚙️ Functional Requirements\n• 📊 Non-Functional Requirements\n• 👥 Stakeholder Roles\n• 🏗️ Technical Architecture\n• 🔒 Security & Compliance"
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
          "value": "status_abc-123-def"
        }
      ]
    }
  ]
}
```

## Security

### Signature Verification
```python
def verify_slack_signature(headers, body):
    timestamp = headers.get('x-slack-request-timestamp')
    signature = headers.get('x-slack-signature')
    
    # Prevent replay attacks (5 minute window)
    if abs(time.time() - int(timestamp)) > 300:
        return False
    
    # Verify HMAC signature
    sig_basestring = f"v0:{timestamp}:{body}"
    my_signature = 'v0=' + hmac.new(
        SLACK_SIGNING_SECRET.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(my_signature, signature)
```

### Access Control
- Slack app permissions scope access appropriately
- Signing secret validation prevents unauthorized requests
- Ephemeral responses for sensitive information
- No sensitive data stored in Slack messages

## Usage Workflow

### 1. Document Upload
```
User: /autospec upload
Bot: 📄 Document Upload Instructions:

1. Use the AutoSpec.AI email: autospec@your-domain.com
2. Or use the API endpoint for direct uploads  
3. Supported formats: PDF, DOCX, TXT

Your analysis will be delivered back to this channel when complete!
```

### 2. Status Checking
```
User: /autospec status abc-123-def
Bot: ⚙️ Request Status

Request ID: `abc-123-def`
Filename: requirements.pdf
Status: Processing
Stage: AI Processing In Progress
Last Updated: 2024-01-01T12:00:00Z

⚙️ AI analysis in progress...
```

### 3. Completion Notification
```
AutoSpec.AI Bot: 🎉 Document Analysis Complete!

Document: requirements.pdf
Request ID: `abc-123-def`

Executive Summary:
The system provides comprehensive user management with role-based access control...

Analysis Includes:
• ⚙️ Functional Requirements
• 📊 Non-Functional Requirements  
• 👥 Stakeholder Roles
• 🏗️ Technical Architecture
• 🔒 Security & Compliance

📧 Full detailed report sent to your email!

[Check Status] (button)
```

## Error Handling

### Common Scenarios
- **Invalid Request ID**: Clear error message with format guidance
- **Webhook Failures**: Graceful degradation without blocking email delivery
- **Rate Limiting**: Appropriate response with retry guidance
- **Invalid Signatures**: Security-focused rejection with minimal information

### Monitoring
- CloudWatch logs for all Slack interactions
- Error tracking for webhook delivery failures
- Usage metrics for command popularity
- Response time monitoring for user experience

## Future Enhancements

### Planned Features
- **File Upload**: Direct file upload through Slack
- **Workspace Integration**: Multi-channel notifications
- **User Preferences**: Customizable notification settings
- **Advanced Commands**: Batch processing, format selection
- **Interactive Workflows**: Multi-step document submission

### Integration Opportunities
- **Jira Integration**: Create tickets from requirements
- **Confluence**: Export to documentation pages
- **GitHub**: Create issues from functional requirements
- **Microsoft Teams**: Cross-platform support