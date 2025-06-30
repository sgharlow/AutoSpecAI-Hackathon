# AutoSpec.AI - Getting Started Guide

Welcome to **AutoSpec.AI**, your intelligent document processing system that converts documents into structured system requirements using advanced AI technology.

## 🌟 What is AutoSpec.AI?

AutoSpec.AI is a serverless AWS application that processes documents (PDF, DOCX, TXT) and generates professional system requirements using Amazon Bedrock's Claude 3.5 Sonnet v2. The system provides multiple ways to interact with it:

- **📧 Email Processing**: Send documents via email for processing
- **💬 Slack Integration**: Use Slack commands to process documents
- **🌐 Web API**: Integrate with web applications or use direct API calls
- **📊 Multi-Format Output**: Receive results in PDF, HTML, JSON, or Markdown

---

## 🚀 Quick Start Options

### Option 1: Email Processing (Simplest)
Send your documents directly via email and receive professional system requirements back.

### Option 2: Slack Integration  
Use Slack slash commands to process documents within your team workspace.

### Option 3: Web API
Integrate AutoSpec.AI into your applications or use direct API calls.

---

## 📧 Email Processing Guide

### How to Send Documents via Email

1. **Compose Email**
   - **To**: `documents@autospec-ai.com`
   - **Subject**: Brief description of your document
   - **Attachment**: Your document (PDF, DOCX, or TXT)
   - **Body**: Optional context or specific requirements

2. **Supported File Types**
   - **PDF**: Up to 200MB
   - **Microsoft Word**: `.docx` and `.doc` files
   - **Text Files**: `.txt` files
   - **File Size Limit**: 200MB per document

3. **Email Example**
   ```
   To: documents@autospec-ai.com
   Subject: E-commerce Platform Requirements
   
   Hi AutoSpec.AI,
   
   Please analyze the attached document for our new e-commerce platform.
   Focus on user authentication and payment processing requirements.
   
   Thanks!
   ```

### What Happens Next?

1. **Instant Confirmation**: You'll receive a confirmation email within minutes
2. **Processing Time**: 2-5 minutes for most documents
3. **Results Delivery**: Comprehensive system requirements sent to your email
4. **Multiple Formats**: Results include PDF report and structured analysis

### Email Response Format

You'll receive an email with:
- **📋 Executive Summary**: High-level overview
- **📋 Functional Requirements**: What the system must do
- **⚡ Non-Functional Requirements**: Performance, security, scalability
- **👥 Stakeholder Roles**: Key responsibilities 
- **🏗️ Technical Architecture**: System design considerations
- **🔌 Integration Requirements**: External system needs
- **💾 Data Requirements**: Storage and processing needs
- **🔒 Security & Compliance**: Controls and regulations

---

## 💬 Slack Integration Guide

### Setup Slack Integration

> **Note**: Contact your system administrator to enable Slack integration for your workspace.

### Using Slack Commands

Once integrated, use these commands in any Slack channel:

#### `/autospec upload [document-url]`
Process a document from a URL or previously uploaded file.

**Example:**
```
/autospec upload https://company.com/docs/requirements.pdf
```

#### `/autospec status [request-id]`
Check the processing status of your document.

**Example:**
```
/autospec status req_12345
```

#### `/autospec help`
Get help and available commands.

### Slack Workflow

1. **Upload Document**: Use `/autospec upload` command
2. **Get Request ID**: Slack responds with a tracking ID
3. **Wait for Processing**: Typically 2-5 minutes
4. **Receive Results**: AutoSpec.AI posts results directly to the channel
5. **Share with Team**: Results are visible to everyone in the channel

### Slack Features

- **🔄 Real-time Updates**: Get notified when processing completes
- **👥 Team Collaboration**: Share results with your team instantly
- **📎 File Attachments**: Results include downloadable reports
- **🔗 Direct Links**: Quick access to detailed analysis

---

## 🌐 Web API Guide

### API Endpoint
```
Base URL: https://nlkg4e7zo4.execute-api.us-east-1.amazonaws.com/prod/
```

### Authentication
API keys are required for production use. Contact your administrator for an API key.

### Available Endpoints

#### 1. Upload Document
```http
POST /v1/upload
Content-Type: multipart/form-data

Headers:
- x-api-key: YOUR_API_KEY
- Content-Type: multipart/form-data

Body:
- file: [document file]
- metadata: {"description": "Document description"}
```

**Example using curl:**
```bash
curl -X POST \
  https://nlkg4e7zo4.execute-api.us-east-1.amazonaws.com/prod/v1/upload \
  -H 'x-api-key: YOUR_API_KEY' \
  -F 'file=@requirements.pdf' \
  -F 'metadata={"description": "System requirements document"}'
```

**Response:**
```json
{
  "requestId": "req_abc123",
  "status": "processing",
  "message": "Document uploaded successfully",
  "estimatedCompletion": "2024-06-27T15:30:00Z"
}
```

#### 2. Check Processing Status
```http
GET /v1/status/{requestId}

Headers:
- x-api-key: YOUR_API_KEY
```

**Example:**
```bash
curl -X GET \
  https://nlkg4e7zo4.execute-api.us-east-1.amazonaws.com/prod/v1/status/req_abc123 \
  -H 'x-api-key: YOUR_API_KEY'
```

**Response:**
```json
{
  "requestId": "req_abc123",
  "status": "completed",
  "processingStage": "ai_processing_complete",
  "results": {
    "executiveSummary": "...",
    "functionalRequirements": "...",
    "nonFunctionalRequirements": "...",
    "downloadUrls": {
      "pdf": "https://...",
      "html": "https://...",
      "json": "https://..."
    }
  }
}
```

#### 3. Get Processing History
```http
GET /v1/history

Headers:
- x-api-key: YOUR_API_KEY

Query Parameters:
- limit: Number of results (default: 10)
- lastKey: For pagination
```

**Example:**
```bash
curl -X GET \
  https://nlkg4e7zo4.execute-api.us-east-1.amazonaws.com/prod/v1/history?limit=5 \
  -H 'x-api-key: YOUR_API_KEY'
```

#### 4. Health Check
```http
GET /v1/health
```

**Example:**
```bash
curl https://nlkg4e7zo4.execute-api.us-east-1.amazonaws.com/prod/v1/health
```

### API Response Codes

- **200**: Success
- **202**: Accepted (processing)
- **400**: Bad request
- **401**: Unauthorized (check API key)
- **413**: File too large
- **429**: Rate limit exceeded
- **500**: Internal server error

---

## 📊 Output Formats

AutoSpec.AI provides results in multiple formats to suit different needs:

### 1. PDF Report
- **Professional formatting** with company branding
- **Structured sections** with clear headings
- **Tables and diagrams** for complex requirements
- **Print-ready** for documentation packages

### 2. HTML Interactive Report
- **Web-friendly** format for online sharing
- **Interactive elements** and navigation
- **Responsive design** for mobile devices
- **Embedded charts** and visualizations

### 3. JSON Structured Data
- **Machine-readable** format for integrations
- **Structured hierarchy** of requirements
- **Metadata** and classification tags
- **API-friendly** for automated processing

### 4. Markdown Documentation
- **Developer-friendly** format
- **Version control** compatible
- **GitHub/GitLab** integration ready
- **Easy editing** and collaboration

---

## 🔧 Advanced Features

### 1. Document Comparison
Compare multiple versions of requirements documents to identify changes.

**Usage via API:**
```http
POST /v1/compare
Content-Type: application/json

{
  "documents": [
    {"requestId": "req_abc123", "version": "v1.0"},
    {"requestId": "req_def456", "version": "v2.0"}
  ]
}
```

### 2. Requirements Traceability
Track relationships between different requirements and their sources.

**Features:**
- **Requirement IDs** for tracking
- **Source mapping** to original documents
- **Change history** and versioning
- **Impact analysis** for modifications

### 3. Intelligent Routing
Automatically route different document types to specialized processing workflows.

**Document Types:**
- **Business Requirements**: User stories and business rules
- **Technical Specifications**: API docs and system architecture
- **Compliance Documents**: Regulatory and policy requirements
- **Test Plans**: QA and testing requirements

### 4. Semantic Analysis
Advanced AI analysis to understand context and relationships between requirements.

**Capabilities:**
- **Requirement clustering** by functionality
- **Dependency mapping** between components
- **Priority scoring** based on business impact
- **Gap analysis** for incomplete requirements

---

## 📈 Monitoring and Analytics

### System Health Dashboards

Monitor system performance and usage:

- **📊 Operational Dashboard**: [View Dashboard](https://us-east-1.console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=AutoSpecAI-Operational-Dashboard-prod)
- **⚡ Performance Dashboard**: [View Dashboard](https://us-east-1.console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=AutoSpecAI-Performance-Dashboard-prod)

### Key Metrics

- **📄 Documents Processed**: Total and daily counts
- **⏱️ Processing Time**: Average and percentile breakdowns
- **✅ Success Rate**: Processing completion percentage
- **💰 Cost Per Document**: Usage-based cost tracking
- **📊 Quality Scores**: AI analysis quality metrics

### Usage Analytics

Track your organization's usage:
- **Document types** processed
- **Department usage** patterns
- **Peak processing** times
- **Cost optimization** opportunities

---

## ❓ Troubleshooting & FAQ

### Common Issues

#### "File too large" Error
- **Cause**: Document exceeds 200MB limit
- **Solution**: 
  - Compress PDF files
  - Split large documents into sections
  - Convert to text format if possible

#### "Processing failed" Error
- **Cause**: Document format issues or corrupt files
- **Solution**:
  - Ensure document is not password-protected
  - Try converting to PDF format
  - Check file is not corrupted

#### "API key invalid" Error
- **Cause**: Missing or incorrect API key
- **Solution**:
  - Contact administrator for valid API key
  - Check header format: `x-api-key: YOUR_KEY`
  - Verify key has proper permissions

### Email Issues

#### "Email bounced back"
- **Cause**: SES configuration or invalid sender
- **Solution**: 
  - Verify email address: `documents@autospec-ai.com`
  - Check attachment size limits
  - Try sending from verified domain

#### "No response received"
- **Cause**: Processing queue backlog or system maintenance
- **Solution**:
  - Wait 10-15 minutes for response
  - Check spam/junk folders
  - Contact support if no response after 30 minutes

### Slack Issues

#### "Command not found"
- **Cause**: Slack integration not enabled
- **Solution**: Contact workspace administrator to install AutoSpec.AI app

#### "Permission denied"
- **Cause**: Insufficient Slack permissions
- **Solution**: Ensure bot has proper channel permissions

### Performance Optimization

#### Slow Processing Times
- **Smaller files** process faster
- **PDF format** is most efficient
- **Off-peak hours** have faster processing
- **Simple documents** complete quicker than complex ones

#### Rate Limiting
- **Email**: 50 documents per hour per sender
- **API**: 100 requests per hour per key
- **Slack**: 25 commands per hour per user

---

## 🔒 Security & Privacy

### Data Protection

- **🔐 Encryption**: All data encrypted in transit and at rest
- **🗂️ Retention**: Documents auto-deleted after 30 days
- **🔑 Access Control**: Role-based permissions and API keys
- **📝 Audit Logs**: Complete activity tracking
- **🛡️ Compliance**: SOC 2, GDPR, and CCPA compliant

### Privacy Guarantees

- **No Data Training**: Your documents are NOT used to train AI models
- **Confidential Processing**: Documents processed in isolated environments
- **Secure Deletion**: Automatic deletion after processing complete
- **Access Logging**: All access attempts logged and monitored

### Best Practices

1. **📧 Email**: Use business email addresses, not personal
2. **🔑 API Keys**: Rotate keys regularly, don't share in code
3. **📄 Documents**: Remove sensitive data before processing
4. **👥 Team Access**: Limit Slack integration to authorized channels

---

## 📞 Support & Help

### Getting Help

- **📧 Email Support**: support@autospec-ai.com
- **💬 Slack Support**: Use `/autospec help` command
- **📖 Documentation**: This guide and API docs
- **🔧 System Status**: Monitor dashboards for service health

### Response Times

- **🚨 Critical Issues**: 1 hour response
- **⚠️ General Support**: 4 hour response  
- **💡 Feature Requests**: 24 hour response
- **📚 Documentation**: Available 24/7

### What to Include in Support Requests

1. **Request ID** (if available)
2. **Error message** (exact text)
3. **Document type** and approximate size
4. **Processing method** (email/Slack/API)
5. **Expected vs actual** behavior
6. **Screenshots** (for UI issues)

---

## 🎯 Next Steps

### For Business Users
1. **Start Simple**: Try email processing with a test document
2. **Learn Slack**: Integrate with your team's Slack workspace
3. **Explore Outputs**: Try different format options
4. **Scale Usage**: Process multiple documents for complete projects

### For Developers
1. **Get API Key**: Contact administrator for development access
2. **Read API Docs**: Understand endpoints and responses
3. **Test Integration**: Start with health check and simple uploads
4. **Build Applications**: Integrate AutoSpec.AI into your workflows

### For Organizations
1. **Pilot Program**: Start with small team or department
2. **Training Sessions**: Educate users on all interaction methods
3. **Usage Analytics**: Monitor adoption and value delivery
4. **Scale Deployment**: Expand to enterprise-wide usage

---

## 📊 System Information

**Current System Details:**
- **Production URL**: https://nlkg4e7zo4.execute-api.us-east-1.amazonaws.com/prod/
- **Email Processing**: documents@autospec-ai.com
- **AI Model**: Claude 3.5 Sonnet v2 (latest)
- **Supported Regions**: US East (N. Virginia)
- **Max File Size**: 200MB
- **Processing SLA**: 95% within 5 minutes

**Service Limits:**
- **Concurrent Processing**: 50 documents
- **Daily Volume**: 10,000 documents per day
- **API Rate Limit**: 100 requests/hour per key
- **Storage Retention**: 30 days

---

*Last Updated: June 27, 2024*  
*Version: 1.0*  
*System Status: Production Ready* ✅

For the most up-to-date information, visit our [system status page](https://us-east-1.console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=AutoSpecAI-Operational-Dashboard-prod) or contact support.