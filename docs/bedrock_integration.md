# Amazon Bedrock Integration Documentation

## Overview

The AutoSpec.AI processing Lambda function integrates with Amazon Bedrock using Claude 3 Sonnet to analyze documents and generate structured system requirements.

## Model Configuration

- **Model ID**: `anthropic.claude-3-sonnet-20240229-v1:0`
- **Max Tokens**: 4,000
- **Temperature**: 0.1 (for consistent, focused output)
- **Top P**: 0.9

## System Analyst Prompt Strategy

The prompt instructs Claude to act as a skilled systems analyst and provides structured requirements for analysis:

### Analysis Criteria
1. Comprehensive and Clear Structure
2. Depth and Clarity of Functional Requirements
3. Role-Specific Responsibilities
4. Technical Transparency
5. Non-Functional Requirements Coverage
6. Cross-Referencing and Version Control
7. Balanced Narrative and Tabular Format

### Output Structure
The prompt requests structured Markdown output with these sections:

- **Executive Summary**: System purpose and scope
- **Functional Requirements**: What the system must do
- **Non-Functional Requirements**: Performance, security, usability attributes
- **Stakeholder Roles and Responsibilities**: Key roles and their duties
- **Technical Architecture Considerations**: High-level technical requirements
- **Integration Requirements**: External system integration needs
- **Data Requirements**: Data storage, processing, and management
- **Security and Compliance**: Security controls and regulatory requirements

## Processing Flow

1. **Document Extraction**: Text content extracted from PDF, DOCX, or TXT files
2. **Content Validation**: Verify text content exists and is processable
3. **Prompt Creation**: Generate system analyst prompt with document content
4. **Bedrock Invocation**: Call Claude model with structured request
5. **Response Processing**: Parse and structure the AI-generated requirements
6. **Section Extraction**: Break down response into organized sections
7. **Storage**: Save results to DynamoDB with metadata

## Error Handling

- **Empty Content**: Handles documents with no extractable text
- **Bedrock Failures**: Logs errors and updates processing status
- **Parsing Errors**: Captures partial results even if section parsing fails
- **Token Limits**: Truncates input to 8,000 characters to prevent overflow

## Response Structure

The function returns structured JSON containing:

```json
{
  "raw_response": "Full Bedrock response text",
  "generated_at": "2024-01-01T00:00:00Z",
  "model_used": "anthropic.claude-3-sonnet-20240229-v1:0",
  "processing_status": "completed",
  "requirements_sections": {
    "executive_summary": "...",
    "functional_requirements": "...",
    "non_functional_requirements": "...",
    "stakeholder_roles_and_responsibilities": "...",
    "technical_architecture_considerations": "...",
    "integration_requirements": "...",
    "data_requirements": "...",
    "security_and_compliance": "..."
  }
}
```

## Performance Considerations

- **Content Truncation**: Limits input to 8,000 characters for token efficiency
- **Async Processing**: Designed for S3 event-driven architecture
- **DynamoDB Updates**: Efficient record lookup and update patterns
- **Error Recovery**: Comprehensive error handling with status tracking

## Security

- **IAM Permissions**: Requires Bedrock invoke permissions for Claude models
- **Content Filtering**: Processes only supported document types
- **Logging**: Comprehensive logging without exposing sensitive content
- **Encryption**: Relies on AWS service-level encryption for data at rest