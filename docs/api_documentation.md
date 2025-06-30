# AutoSpec.AI API Documentation

Complete REST API reference for AutoSpec.AI, including all endpoints, request/response formats, authentication, and integration examples.

## Overview

The AutoSpec.AI API provides RESTful endpoints for document processing, requirements analysis, and system management. The API supports multiple input formats, real-time processing status, and various output formats.

### API Features

- **Document Upload**: Support for PDF, DOCX, TXT files up to 100MB
- **Dual Upload Methods**: JSON upload (<5MB) and S3 direct upload (5MB+)
- **AI Processing**: Amazon Bedrock-powered requirements analysis
- **Real-time Status**: WebSocket and polling-based status updates
- **Multi-format Output**: JSON, Markdown, HTML, PDF outputs
- **Advanced Features**: Document comparison, semantic analysis, traceability

### API Versions

- **Current Version**: v1
- **Base Path**: `/v1`
- **Versioning**: URI-based versioning (`/v1/`, `/v2/`)

## Authentication

### API Key Authentication

```http
Authorization: Bearer YOUR_API_KEY
```

### JWT Token Authentication

```http
Authorization: Bearer YOUR_JWT_TOKEN
```

## Base URLs

### Environment URLs

- **Development**: `https://api-dev.autospec.ai`
- **Staging**: `https://api-staging.autospec.ai`
- **Production**: `https://api.autospec.ai`

## Error Handling

### Error Response Format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid file format. Supported formats: PDF, DOCX, TXT",
    "details": {
      "field": "file",
      "value": "image.jpg",
      "supported_formats": ["pdf", "docx", "txt"]
    },
    "request_id": "req_1234567890",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

### HTTP Status Codes

| Code | Status | Description |
|------|--------|-------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created successfully |
| 400 | Bad Request | Invalid request parameters |
| 401 | Unauthorized | Invalid or missing authentication |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource not found |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |

## API Endpoints

### Health and Status

#### GET /health

System health check endpoint.

```http
GET /v1/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "version": "1.0.0",
  "environment": "production"
}
```

### Document Management

#### POST /documents

Upload a document for processing.

```http
POST /v1/documents
Content-Type: multipart/form-data
Authorization: Bearer YOUR_TOKEN
```

**Request:**
```
file: [binary file data]
title: "Project Requirements Document"
description: "Requirements for new e-commerce platform"
```

**Response:**
```json
{
  "document": {
    "id": "doc_1234567890",
    "title": "Project Requirements Document",
    "description": "Requirements for new e-commerce platform",
    "filename": "requirements.pdf",
    "size": 2048576,
    "type": "application/pdf",
    "status": "uploaded",
    "created_at": "2024-01-15T10:30:00Z"
  },
  "processing": {
    "job_id": "job_1234567890",
    "status": "queued",
    "estimated_completion": "2024-01-15T10:32:00Z"
  }
}
```

#### GET /documents

List documents with filtering and pagination.

```http
GET /v1/documents?status=completed&limit=20&offset=0
Authorization: Bearer YOUR_TOKEN
```

**Response:**
```json
{
  "documents": [
    {
      "id": "doc_1234567890",
      "title": "Project Requirements Document",
      "filename": "requirements.pdf",
      "status": "completed",
      "created_at": "2024-01-15T10:30:00Z",
      "requirements_count": 45
    }
  ],
  "pagination": {
    "total": 150,
    "limit": 20,
    "offset": 0,
    "has_more": true
  }
}
```

#### GET /documents/{id}

Get detailed information about a specific document.

```http
GET /v1/documents/doc_1234567890
Authorization: Bearer YOUR_TOKEN
```

**Response:**
```json
{
  "document": {
    "id": "doc_1234567890",
    "title": "Project Requirements Document",
    "status": "completed",
    "created_at": "2024-01-15T10:30:00Z",
    "processing_completed_at": "2024-01-15T10:32:15Z"
  },
  "results": {
    "requirements_count": 45,
    "functional_requirements": 32,
    "non_functional_requirements": 13,
    "confidence_score": 0.95
  }
}
```

#### GET /documents/{id}/download

Download processed document in specified format.

```http
GET /v1/documents/doc_1234567890/download?format=json
Authorization: Bearer YOUR_TOKEN
```

**Query Parameters:**
- `format`: Output format (`json`, `markdown`, `html`, `pdf`)

## Examples

### Complete Document Processing Workflow

```javascript
// 1. Upload document
const uploadResponse = await fetch('/v1/documents', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer YOUR_TOKEN'
  },
  body: formData
});
const document = await uploadResponse.json();

// 2. Poll for completion
const pollStatus = async (documentId) => {
  while (true) {
    const response = await fetch(`/v1/documents/${documentId}`, {
      headers: { 'Authorization': 'Bearer YOUR_TOKEN' }
    });
    const doc = await response.json();
    
    if (doc.document.status === 'completed') {
      return doc;
    }
    
    await new Promise(resolve => setTimeout(resolve, 5000));
  }
};

// 3. Download results
const completedDoc = await pollStatus(document.document.id);
const resultsResponse = await fetch(
  `/v1/documents/${document.document.id}/download?format=json`,
  {
    headers: { 'Authorization': 'Bearer YOUR_TOKEN' }
  }
);
const results = await resultsResponse.json();
```