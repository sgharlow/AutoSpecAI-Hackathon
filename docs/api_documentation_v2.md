# AutoSpec.AI API Documentation v2

Complete REST API reference for AutoSpec.AI with enhanced upload capabilities, supporting files up to 100MB through dual upload methods.

## Overview

The AutoSpec.AI API provides RESTful endpoints for intelligent document processing and requirements analysis. The API now supports two upload methods: JSON upload for smaller files and S3 direct upload for larger files.

### Key Features

- **Dual Upload Methods**: Automatic selection based on file size
- **Large File Support**: Files up to 100MB via S3 direct upload
- **Real-time Processing**: Status tracking and progress updates
- **AI-Powered Analysis**: Amazon Bedrock Claude 3 Sonnet
- **Multi-format Output**: JSON, Markdown, HTML, PDF

### API Versions

- **Current Version**: v1
- **Base URL**: `https://nlkg4e7zo4.execute-api.us-east-1.amazonaws.com/prod`
- **Versioning**: URI-based (`/v1/`)

## Authentication

All API endpoints require authentication using API keys.

```http
X-API-Key: YOUR_API_KEY
```

### Production API Keys

```
YOUR_API_KEY_HERE (AutoSpecAI-prod-test-key)
YOUR_API_KEY_HERE_2 (AutoSpecAI-prod-working-key-v2)
YOUR_API_KEY_HERE_3 (autospec-default-key-prod)
```

## Upload Methods

### Method Selection

The API automatically selects the appropriate upload method:

- **Files ≤ 5MB**: JSON Upload (single API call)
- **Files > 5MB**: S3 Direct Upload (3-step process)

### JSON Upload Method

For smaller files (≤ 5MB), use the traditional JSON upload method.

#### POST /v1/upload

```http
POST /v1/upload
Content-Type: application/json
X-API-Key: YOUR_API_KEY
```

**Request:**
```json
{
  "file_content": "base64_encoded_content",
  "filename": "requirements.pdf",
  "sender_email": "user@example.com",
  "preferences": {
    "quality": "high",
    "formats": ["html", "json", "markdown"]
  }
}
```

**Response:**
```json
{
  "request_id": "12345678-abcd-1234-efgh-123456789012",
  "status": "accepted",
  "message": "Document uploaded and processing started",
  "filename": "requirements.pdf",
  "estimated_processing_time": "2-5 minutes"
}
```

### S3 Direct Upload Method

For larger files (> 5MB), use the 3-step S3 direct upload process.

#### Step 1: POST /v1/upload/initiate

Generate a pre-signed S3 upload URL.

```http
POST /v1/upload/initiate
Content-Type: application/json
X-API-Key: YOUR_API_KEY
```

**Request:**
```json
{
  "filename": "large_requirements.pdf",
  "file_size": 52428800,
  "content_type": "application/pdf",
  "metadata": {
    "sender_email": "user@example.com",
    "preferences": {
      "quality": "premium",
      "formats": ["html", "pdf", "json"]
    }
  }
}
```

**Response:**
```json
{
  "request_id": "12345678-abcd-1234-efgh-123456789012",
  "upload_url": "https://s3.amazonaws.com/bucket/uploads/12345.../file.pdf?X-Amz-...",
  "upload_method": "PUT",
  "upload_headers": {
    "Content-Type": "application/pdf",
    "Content-Length": "52428800"
  },
  "expires_in": 3600,
  "max_file_size": 104857600,
  "instructions": {
    "method": "PUT",
    "url": "https://s3.amazonaws.com/...",
    "headers": {
      "Content-Type": "application/pdf",
      "Content-Length": "52428800"
    },
    "note": "Upload file directly to this URL using PUT method"
  },
  "next_step": "After upload, call POST /v1/upload/complete with request_id"
}
```

#### Step 2: Upload to S3

Upload the file directly to the pre-signed URL using PUT method.

```http
PUT https://s3.amazonaws.com/bucket/uploads/12345.../file.pdf?X-Amz-...
Content-Type: application/pdf
Content-Length: 52428800

[binary file data]
```

**Response:** HTTP 200 (no body)

#### Step 3: POST /v1/upload/complete

Verify the upload and trigger processing.

```http
POST /v1/upload/complete
Content-Type: application/json
X-API-Key: YOUR_API_KEY
```

**Request:**
```json
{
  "request_id": "12345678-abcd-1234-efgh-123456789012"
}
```

**Response:**
```json
{
  "request_id": "12345678-abcd-1234-efgh-123456789012",
  "status": "upload_verified",
  "message": "Upload verified and processing started",
  "filename": "large_requirements.pdf",
  "declared_size": 52428800,
  "actual_size": 52428800,
  "size_match": true,
  "estimated_processing_time": "2-5 minutes"
}
```

## Status and Monitoring

#### GET /v1/status/{request_id}

Check processing status for any upload method.

```http
GET /v1/status/12345678-abcd-1234-efgh-123456789012
X-API-Key: YOUR_API_KEY
```

**Response:**
```json
{
  "request_id": "12345678-abcd-1234-efgh-123456789012",
  "filename": "requirements.pdf",
  "status": "processing",
  "processing_stage": "ai_processing_in_progress",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:31:30Z",
  "file_type": "application/pdf",
  "file_size": 52428800,
  "progress_percentage": 75,
  "upload_method": "direct_s3"
}
```

### Processing Stages

1. **upload_initiated** - S3 upload URL generated
2. **uploading** - File being uploaded to S3
3. **upload_complete** - File successfully uploaded
4. **processing** - AI analysis in progress
5. **ai_processing_complete** - Analysis finished
6. **formatting_in_progress** - Generating output formats
7. **delivery_complete** - Results delivered

## Additional Endpoints

#### GET /v1/health

System health check.

```http
GET /v1/health
X-API-Key: YOUR_API_KEY
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "version": "v1",
  "services": {
    "api_gateway": "healthy",
    "lambda": "healthy",
    "dynamodb": "healthy",
    "s3": "healthy"
  }
}
```

#### GET /v1/history

Get processing history.

```http
GET /v1/history?limit=10
X-API-Key: YOUR_API_KEY
```

**Response:**
```json
{
  "requests": [
    {
      "request_id": "12345678-abcd-1234-efgh-123456789012",
      "filename": "requirements.pdf",
      "status": "delivered",
      "created_at": "2024-01-15T10:30:00Z",
      "file_type": "application/pdf",
      "file_size": 52428800
    }
  ],
  "count": 1,
  "total_count": 1
}
```

#### GET /v1/formats

Get supported input and output formats.

```http
GET /v1/formats
X-API-Key: YOUR_API_KEY
```

**Response:**
```json
{
  "supported_input_formats": [
    {
      "extension": ".pdf",
      "mime_type": "application/pdf",
      "description": "Portable Document Format",
      "max_size_mb": 100
    },
    {
      "extension": ".docx",
      "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      "description": "Microsoft Word Document",
      "max_size_mb": 100
    },
    {
      "extension": ".txt",
      "mime_type": "text/plain",
      "description": "Plain Text File",
      "max_size_mb": 100
    }
  ],
  "output_formats": [
    {
      "format": "json",
      "description": "Structured JSON format",
      "availability": "always"
    },
    {
      "format": "html",
      "description": "Interactive HTML format",
      "availability": "always"
    },
    {
      "format": "pdf",
      "description": "Professional PDF report",
      "availability": "when_enabled"
    }
  ]
}
```

## Error Handling

### Error Response Format

```json
{
  "error": {
    "type": "ValidationError",
    "message": "File size exceeds maximum of 100MB",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

### Common Error Codes

| Code | Description |
|------|-------------|
| 400 | Bad Request - Invalid request format |
| 401 | Unauthorized - Invalid API key |
| 403 | Forbidden - Access denied |
| 413 | Payload Too Large - File exceeds size limit |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error - Server error |

## Rate Limiting

- **Requests per hour**: 100
- **Burst limit**: 10 requests
- **Headers included in response**:
  - `X-RateLimit-Remaining`
  - `X-RateLimit-Reset`

## Client Examples

### JavaScript/TypeScript

```typescript
// Small file - JSON upload
async function uploadSmallFile(file: File) {
  const base64 = await fileToBase64(file);
  
  const response = await fetch('/v1/upload', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': 'YOUR_API_KEY'
    },
    body: JSON.stringify({
      file_content: base64,
      filename: file.name,
      sender_email: 'user@example.com'
    })
  });
  
  return response.json();
}

// Large file - S3 direct upload
async function uploadLargeFile(file: File) {
  // Step 1: Initiate upload
  const initiateResponse = await fetch('/v1/upload/initiate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': 'YOUR_API_KEY'
    },
    body: JSON.stringify({
      filename: file.name,
      file_size: file.size,
      content_type: file.type,
      metadata: {
        sender_email: 'user@example.com'
      }
    })
  });
  
  const { upload_url, request_id } = await initiateResponse.json();
  
  // Step 2: Upload to S3
  await fetch(upload_url, {
    method: 'PUT',
    headers: {
      'Content-Type': file.type,
      'Content-Length': file.size.toString()
    },
    body: file
  });
  
  // Step 3: Complete upload
  const completeResponse = await fetch('/v1/upload/complete', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': 'YOUR_API_KEY'
    },
    body: JSON.stringify({
      request_id: request_id
    })
  });
  
  return completeResponse.json();
}
```

### Python

```python
import requests
import base64

# Small file - JSON upload
def upload_small_file(file_path, api_key):
    with open(file_path, 'rb') as f:
        file_content = base64.b64encode(f.read()).decode('utf-8')
    
    response = requests.post(
        'https://nlkg4e7zo4.execute-api.us-east-1.amazonaws.com/prod/v1/upload',
        headers={
            'Content-Type': 'application/json',
            'X-API-Key': api_key
        },
        json={
            'file_content': file_content,
            'filename': os.path.basename(file_path),
            'sender_email': 'user@example.com'
        }
    )
    return response.json()

# Large file - S3 direct upload
def upload_large_file(file_path, api_key):
    filename = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    
    # Step 1: Initiate upload
    initiate_response = requests.post(
        'https://nlkg4e7zo4.execute-api.us-east-1.amazonaws.com/prod/v1/upload/initiate',
        headers={
            'Content-Type': 'application/json',
            'X-API-Key': api_key
        },
        json={
            'filename': filename,
            'file_size': file_size,
            'content_type': 'application/pdf',
            'metadata': {
                'sender_email': 'user@example.com'
            }
        }
    )
    
    initiate_data = initiate_response.json()
    upload_url = initiate_data['upload_url']
    request_id = initiate_data['request_id']
    
    # Step 2: Upload to S3
    with open(file_path, 'rb') as f:
        requests.put(
            upload_url,
            headers={
                'Content-Type': 'application/pdf',
                'Content-Length': str(file_size)
            },
            data=f
        )
    
    # Step 3: Complete upload
    complete_response = requests.post(
        'https://nlkg4e7zo4.execute-api.us-east-1.amazonaws.com/prod/v1/upload/complete',
        headers={
            'Content-Type': 'application/json',
            'X-API-Key': api_key
        },
        json={
            'request_id': request_id
        }
    )
    
    return complete_response.json()
```

### cURL

```bash
# Small file - JSON upload
curl -X POST "https://nlkg4e7zo4.execute-api.us-east-1.amazonaws.com/prod/v1/upload" \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "file_content": "'"$(base64 -w 0 document.pdf)"'",
    "filename": "document.pdf",
    "sender_email": "user@example.com"
  }'

# Large file - S3 direct upload
# Step 1: Initiate
RESPONSE=$(curl -X POST "https://nlkg4e7zo4.execute-api.us-east-1.amazonaws.com/prod/v1/upload/initiate" \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "large_document.pdf",
    "file_size": 52428800,
    "content_type": "application/pdf"
  }')

UPLOAD_URL=$(echo "$RESPONSE" | jq -r '.upload_url')
REQUEST_ID=$(echo "$RESPONSE" | jq -r '.request_id')

# Step 2: Upload to S3
curl -X PUT "$UPLOAD_URL" \
  -H "Content-Type: application/pdf" \
  -H "Content-Length: 52428800" \
  --data-binary "@large_document.pdf"

# Step 3: Complete
curl -X POST "https://nlkg4e7zo4.execute-api.us-east-1.amazonaws.com/prod/v1/upload/complete" \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"request_id\": \"$REQUEST_ID\"}"
```

## Best Practices

### File Size Optimization

1. **Automatic Method Selection**: Let the client automatically choose upload method based on file size
2. **Progress Tracking**: Implement progress callbacks for large file uploads
3. **Error Handling**: Handle network interruptions gracefully with retry logic
4. **File Validation**: Validate file types and sizes on the client side

### Performance Tips

1. **Parallel Processing**: Use concurrent uploads for multiple files
2. **Compression**: Consider compressing large files before upload
3. **Chunked Upload**: For very large files, consider implementing chunked uploads
4. **Caching**: Cache API responses where appropriate

### Security Considerations

1. **API Key Protection**: Never expose API keys in client-side code
2. **File Validation**: Validate file contents on both client and server
3. **HTTPS Only**: Always use HTTPS for API communication
4. **Rate Limiting**: Implement client-side rate limiting to avoid 429 errors

## Support

- **Documentation**: [docs.autospec.ai](https://docs.autospec.ai)
- **Status Page**: [status.autospec.ai](https://status.autospec.ai)
- **Support Email**: support@autospec.ai
- **GitHub Issues**: [github.com/autospec-ai/issues](https://github.com/autospec-ai/issues)