# AutoSpec.AI Development Guide

Comprehensive guide for developers contributing to AutoSpec.AI, covering local development setup, coding standards, testing, and contribution workflow.

## Table of Contents

1. [Development Environment Setup](#development-environment-setup)
2. [Project Structure](#project-structure)
3. [Coding Standards](#coding-standards)
4. [Testing Framework](#testing-framework)
5. [Local Development Workflow](#local-development-workflow)
6. [Contributing Guidelines](#contributing-guidelines)
7. [Release Process](#release-process)

## Development Environment Setup

### Prerequisites

Install the required development tools:

```bash
# Node.js 18+ (using nvm)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install 18
nvm use 18

# Python 3.9+
pyenv install 3.9.18
pyenv local 3.9.18

# AWS CLI v2
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# AWS CDK
npm install -g aws-cdk

# Development tools
npm install -g typescript @types/node
pip install black pylint pytest
```

### Local Repository Setup

```bash
# Clone repository
git clone https://github.com/your-username/AutoSpecAI.git
cd AutoSpecAI

# Install dependencies
npm install
pip install -r requirements.txt

# Set up pre-commit hooks
pip install pre-commit
pre-commit install

# Create local environment configuration
cp config/environments/dev.env config/environments/local.env
```

### Environment Configuration

Edit `config/environments/local.env` for local development:

```bash
# Local Development Configuration
export AWS_REGION="us-east-1"
export CDK_STACK_NAME="AutoSpecAI-local-$(whoami)"
export ENVIRONMENT="local"

# Debug settings
export DEBUG_MODE=true
export VERBOSE_LOGGING=true
export MOCK_EXTERNAL_SERVICES=true

# Local overrides
export LAMBDA_MEMORY_SIZE=512
export LAMBDA_TIMEOUT=300
```

### IDE Configuration

#### VS Code Setup

Install recommended extensions:
- Python
- TypeScript and JavaScript
- AWS Toolkit
- GitLens
- Docker
- YAML

Configure workspace settings (`.vscode/settings.json`):

```json
{
  "python.defaultInterpreterPath": "./venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.formatting.provider": "black",
  "typescript.preferences.importModuleSpecifier": "relative",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  }
}
```

#### PyCharm Setup

Configure project settings:
1. Set Python interpreter to local environment
2. Enable Black code formatter
3. Configure pylint as code inspector
4. Set up AWS SDK
5. Configure TypeScript support

## Project Structure

### Directory Organization

```
AutoSpecAI/
├── 📁 lambdas/                 # AWS Lambda Functions
│   ├── 📁 ingest/              # Document ingestion
│   ├── 📁 process/             # AI processing
│   ├── 📁 format/              # Output formatting
│   ├── 📁 api/                 # REST API
│   ├── 📁 slack/               # Slack integration
│   ├── 📁 monitoring/          # System monitoring
│   └── 📁 shared/              # Shared utilities
├── 📁 frontend/                # React application
│   ├── 📁 src/                 # Source code
│   ├── 📁 public/              # Static assets
│   └── 📁 tests/               # Frontend tests
├── 📁 infra/                   # Infrastructure as Code
│   └── 📁 cdk/                 # AWS CDK code
├── 📁 testing/                 # Testing framework
│   ├── 📁 unit/                # Unit tests
│   ├── 📁 integration/         # Integration tests
│   └── 📁 e2e/                 # End-to-end tests
├── 📁 scripts/                 # Automation scripts
├── 📁 docs/                    # Documentation
└── 📁 config/                  # Configuration files
```

### Lambda Function Structure

Each Lambda function follows this structure:

```
lambdas/function-name/
├── handler.py              # Main handler function
├── requirements.txt        # Python dependencies
├── src/                    # Source code modules
│   ├── __init__.py
│   ├── service.py          # Business logic
│   ├── models.py           # Data models
│   └── utils.py            # Utility functions
├── tests/                  # Function tests
│   ├── test_handler.py
│   ├── test_service.py
│   └── fixtures/           # Test data
└── README.md               # Function documentation
```

### Frontend Structure

```
frontend/src/
├── components/             # Reusable components
│   ├── common/             # Common UI components
│   ├── forms/              # Form components
│   └── layout/             # Layout components
├── pages/                  # Page components
├── hooks/                  # Custom React hooks
├── services/               # API services
├── store/                  # Redux store
│   ├── slices/             # Redux slices
│   └── middleware/         # Custom middleware
├── utils/                  # Utility functions
├── types/                  # TypeScript types
└── styles/                 # CSS/SCSS styles
```

## Coding Standards

### Python Standards

#### Code Style

Follow PEP 8 with these specific guidelines:

```python
# File header
"""
AutoSpec.AI - Document Processing Service
Module for handling document ingestion and validation.
"""

# Imports organization
import os
import sys
from typing import Dict, List, Optional

import boto3
from aws_lambda_powertools import Logger, Tracer
from pydantic import BaseModel

# Local imports
from src.models import DocumentModel
from src.utils import validate_document

# Constants
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
SUPPORTED_FORMATS = ['pdf', 'docx', 'txt']

# Class definition
class DocumentProcessor:
    """Process documents for AI analysis."""
    
    def __init__(self, config: Dict[str, str]) -> None:
        """Initialize processor with configuration."""
        self.config = config
        self.logger = Logger()
        self.tracer = Tracer()
    
    @tracer.capture_method
    def process_document(self, document: DocumentModel) -> Dict[str, Any]:
        """Process a document and return results."""
        self.logger.info("Processing document", document_id=document.id)
        
        try:
            # Processing logic here
            result = self._analyze_content(document.content)
            return {"status": "success", "result": result}
        except Exception as e:
            self.logger.error("Processing failed", error=str(e))
            raise
```

#### Error Handling

```python
from aws_lambda_powertools import Logger
from src.exceptions import DocumentProcessingError, ValidationError

logger = Logger()

def process_document(document_id: str) -> Dict[str, Any]:
    """Process document with proper error handling."""
    try:
        # Validation
        if not document_id:
            raise ValidationError("Document ID is required")
        
        # Processing
        result = perform_processing(document_id)
        
        logger.info("Document processed successfully", 
                   document_id=document_id,
                   requirements_count=len(result.get('requirements', [])))
        
        return result
        
    except ValidationError as e:
        logger.warning("Validation error", error=str(e))
        raise
    except DocumentProcessingError as e:
        logger.error("Processing error", error=str(e))
        raise
    except Exception as e:
        logger.error("Unexpected error", error=str(e))
        raise DocumentProcessingError(f"Processing failed: {str(e)}")
```

#### Type Hints

```python
from typing import Dict, List, Optional, Union
from pydantic import BaseModel

class DocumentRequest(BaseModel):
    """Document processing request model."""
    title: str
    content: str
    file_type: str
    options: Optional[Dict[str, Any]] = None

def analyze_requirements(
    content: str,
    options: Optional[Dict[str, str]] = None
) -> List[Dict[str, Any]]:
    """Analyze document content and extract requirements."""
    pass

async def process_async(
    document: DocumentRequest
) -> Dict[str, Union[str, int, List[str]]]:
    """Asynchronously process document."""
    pass
```

### TypeScript Standards

#### React Components

```typescript
// Component with proper typing
interface DocumentCardProps {
  document: Document;
  onSelect: (id: string) => void;
  className?: string;
}

export const DocumentCard: React.FC<DocumentCardProps> = ({
  document,
  onSelect,
  className
}) => {
  const [isLoading, setIsLoading] = useState(false);
  
  const handleClick = useCallback(() => {
    onSelect(document.id);
  }, [document.id, onSelect]);
  
  return (
    <div className={`document-card ${className || ''}`}>
      <h3>{document.title}</h3>
      <p>{document.description}</p>
      <button onClick={handleClick} disabled={isLoading}>
        {isLoading ? 'Processing...' : 'Select'}
      </button>
    </div>
  );
};
```

#### Service Functions

```typescript
// API service with proper error handling
interface ApiResponse<T> {
  data: T;
  status: number;
  message: string;
}

interface DocumentUploadRequest {
  file: File;
  title: string;
  description?: string;
}

export class DocumentService {
  private baseUrl: string;
  private apiKey: string;
  
  constructor(baseUrl: string, apiKey: string) {
    this.baseUrl = baseUrl;
    this.apiKey = apiKey;
  }
  
  async uploadDocument(
    request: DocumentUploadRequest
  ): Promise<ApiResponse<Document>> {
    try {
      const formData = new FormData();
      formData.append('file', request.file);
      formData.append('title', request.title);
      if (request.description) {
        formData.append('description', request.description);
      }
      
      const response = await fetch(`${this.baseUrl}/documents`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.apiKey}`
        },
        body: formData
      });
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Document upload failed:', error);
      throw error;
    }
  }
}
```

### Infrastructure Code Standards

#### CDK Constructs

```typescript
import { Construct } from 'constructs';
import { Function, Runtime, Code } from 'aws-cdk-lib/aws-lambda';
import { Table, AttributeType } from 'aws-cdk-lib/aws-dynamodb';

interface DocumentProcessorProps {
  tableName: string;
  environment: string;
}

export class DocumentProcessor extends Construct {
  public readonly function: Function;
  public readonly table: Table;
  
  constructor(scope: Construct, id: string, props: DocumentProcessorProps) {
    super(scope, id);
    
    // DynamoDB table
    this.table = new Table(this, 'DocumentsTable', {
      tableName: props.tableName,
      partitionKey: {
        name: 'document_id',
        type: AttributeType.STRING
      },
      removalPolicy: props.environment === 'prod' 
        ? RemovalPolicy.RETAIN 
        : RemovalPolicy.DESTROY
    });
    
    // Lambda function
    this.function = new Function(this, 'ProcessorFunction', {
      runtime: Runtime.PYTHON_3_9,
      handler: 'handler.lambda_handler',
      code: Code.fromAsset('lambdas/process'),
      environment: {
        TABLE_NAME: this.table.tableName,
        ENVIRONMENT: props.environment
      },
      timeout: Duration.minutes(15),
      memorySize: 1024
    });
    
    // Grant permissions
    this.table.grantReadWriteData(this.function);
  }
}
```

## Testing Framework

### Unit Testing

#### Python Unit Tests

```python
import pytest
from unittest.mock import Mock, patch
from src.service import DocumentProcessor
from src.models import DocumentModel

class TestDocumentProcessor:
    """Test cases for DocumentProcessor."""
    
    @pytest.fixture
    def processor(self):
        """Create processor instance for testing."""
        config = {'region': 'us-east-1', 'table_name': 'test-table'}
        return DocumentProcessor(config)
    
    @pytest.fixture
    def sample_document(self):
        """Create sample document for testing."""
        return DocumentModel(
            id='doc-123',
            title='Test Document',
            content='This is a test document content.',
            file_type='txt'
        )
    
    def test_process_document_success(self, processor, sample_document):
        """Test successful document processing."""
        with patch.object(processor, '_analyze_content') as mock_analyze:
            mock_analyze.return_value = {'requirements': ['REQ-1', 'REQ-2']}
            
            result = processor.process_document(sample_document)
            
            assert result['status'] == 'success'
            assert len(result['result']['requirements']) == 2
            mock_analyze.assert_called_once_with(sample_document.content)
    
    def test_process_document_failure(self, processor, sample_document):
        """Test document processing failure."""
        with patch.object(processor, '_analyze_content') as mock_analyze:
            mock_analyze.side_effect = Exception('AI service error')
            
            with pytest.raises(Exception) as exc_info:
                processor.process_document(sample_document)
            
            assert 'AI service error' in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_async_processing(self, processor, sample_document):
        """Test asynchronous document processing."""
        with patch.object(processor, '_async_analyze') as mock_analyze:
            mock_analyze.return_value = {'requirements': ['REQ-1']}
            
            result = await processor.process_document_async(sample_document)
            
            assert result['status'] == 'success'
```

#### React Component Tests

```typescript
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { Provider } from 'react-redux';
import { DocumentCard } from '../DocumentCard';
import { mockDocument, createMockStore } from '../../test-utils';

describe('DocumentCard', () => {
  const mockOnSelect = jest.fn();
  const store = createMockStore();
  
  beforeEach(() => {
    mockOnSelect.mockClear();
  });
  
  const renderDocumentCard = (props = {}) => {
    const defaultProps = {
      document: mockDocument,
      onSelect: mockOnSelect,
      ...props
    };
    
    return render(
      <Provider store={store}>
        <DocumentCard {...defaultProps} />
      </Provider>
    );
  };
  
  it('renders document information correctly', () => {
    renderDocumentCard();
    
    expect(screen.getByText(mockDocument.title)).toBeInTheDocument();
    expect(screen.getByText(mockDocument.description)).toBeInTheDocument();
  });
  
  it('calls onSelect when clicked', async () => {
    renderDocumentCard();
    
    const selectButton = screen.getByText('Select');
    fireEvent.click(selectButton);
    
    await waitFor(() => {
      expect(mockOnSelect).toHaveBeenCalledWith(mockDocument.id);
    });
  });
  
  it('shows loading state during processing', async () => {
    renderDocumentCard({ isLoading: true });
    
    expect(screen.getByText('Processing...')).toBeInTheDocument();
    expect(screen.getByRole('button')).toBeDisabled();
  });
});
```

### Integration Testing

#### API Integration Tests

```python
import pytest
import requests
from testing.fixtures import TestEnvironment

class TestDocumentAPI:
    """Integration tests for document API."""
    
    @pytest.fixture(scope='class')
    def test_env(self):
        """Set up test environment."""
        return TestEnvironment()
    
    def test_document_upload_workflow(self, test_env):
        """Test complete document upload and processing workflow."""
        # Upload document
        with open('test-data/sample.pdf', 'rb') as f:
            response = requests.post(
                f"{test_env.api_url}/v1/documents",
                headers={'Authorization': f'Bearer {test_env.api_key}'},
                files={'file': f},
                data={'title': 'Test Document', 'description': 'Test'}
            )
        
        assert response.status_code == 201
        document = response.json()['document']
        document_id = document['id']
        
        # Poll for completion
        for _ in range(30):  # Wait up to 5 minutes
            response = requests.get(
                f"{test_env.api_url}/v1/documents/{document_id}",
                headers={'Authorization': f'Bearer {test_env.api_key}'}
            )
            
            status = response.json()['document']['status']
            if status == 'completed':
                break
            elif status == 'failed':
                pytest.fail("Document processing failed")
            
            time.sleep(10)
        else:
            pytest.fail("Document processing timed out")
        
        # Download results
        response = requests.get(
            f"{test_env.api_url}/v1/documents/{document_id}/download?format=json",
            headers={'Authorization': f'Bearer {test_env.api_key}'}
        )
        
        assert response.status_code == 200
        results = response.json()
        assert 'requirements' in results
        assert len(results['requirements']) > 0
```

### End-to-End Testing

#### Playwright E2E Tests

```typescript
import { test, expect } from '@playwright/test';

test.describe('Document Processing Workflow', () => {
  test('complete document upload and processing', async ({ page }) => {
    // Navigate to application
    await page.goto('/');
    
    // Login
    await page.fill('[data-testid=email-input]', 'test@example.com');
    await page.fill('[data-testid=password-input]', 'password123');
    await page.click('[data-testid=login-button]');
    
    // Wait for dashboard
    await expect(page.locator('[data-testid=dashboard]')).toBeVisible();
    
    // Upload document
    await page.click('[data-testid=upload-button]');
    await page.setInputFiles('[data-testid=file-input]', 'test-data/sample.pdf');
    await page.fill('[data-testid=title-input]', 'E2E Test Document');
    await page.click('[data-testid=submit-upload]');
    
    // Wait for processing to complete
    await expect(page.locator('[data-testid=processing-status]')).toContainText('Processing');
    await expect(page.locator('[data-testid=processing-status]')).toContainText('Completed', { timeout: 300000 });
    
    // Verify results
    await page.click('[data-testid=view-results]');
    await expect(page.locator('[data-testid=requirements-list]')).toBeVisible();
    
    const requirementCount = await page.locator('[data-testid=requirement-item]').count();
    expect(requirementCount).toBeGreaterThan(0);
  });
});
```

## Local Development Workflow

### Development Server

#### Backend Development

```bash
# Start local DynamoDB
docker run -p 8000:8000 amazon/dynamodb-local

# Set up local environment
export AWS_ACCESS_KEY_ID="local"
export AWS_SECRET_ACCESS_KEY="local"
export AWS_DEFAULT_REGION="us-east-1"
export DYNAMODB_ENDPOINT="http://localhost:8000"

# Run Lambda functions locally
sam local start-api --template template.yaml --env-vars env.json
```

#### Frontend Development

```bash
# Start React development server
cd frontend
npm start

# Run with specific environment
REACT_APP_API_URL=http://localhost:3001 npm start

# Run with mock API
REACT_APP_USE_MOCK_API=true npm start
```

### Testing Commands

```bash
# Run all tests
npm test

# Run specific test suites
npm run test:unit
npm run test:integration
npm run test:e2e

# Run tests with coverage
npm run test:coverage

# Run tests in watch mode
npm run test:watch

# Python tests
cd lambdas/process
python -m pytest tests/ -v --cov=src

# TypeScript tests
cd frontend
npm run test -- --coverage --watchAll=false
```

### Code Quality

#### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
  
  - repo: https://github.com/psf/black
    rev: 22.10.0
    hooks:
      - id: black
        language_version: python3.9
  
  - repo: https://github.com/PyCQA/pylint
    rev: v2.15.5
    hooks:
      - id: pylint
        args: [--disable=C0103,C0111]
  
  - repo: https://github.com/pre-commit/mirrors-eslint
    rev: v8.25.0
    hooks:
      - id: eslint
        files: \.(js|jsx|ts|tsx)$
        args: [--fix]
```

#### Linting Commands

```bash
# Python linting
black --check lambdas/
pylint lambdas/*/src/

# TypeScript linting
cd frontend
npm run lint
npm run lint:fix

# Infrastructure linting
cd infra/cdk
npm run lint
```

## Contributing Guidelines

### Git Workflow

#### Branch Strategy

```bash
# Main branches
main        # Production-ready code
develop     # Integration branch for features

# Feature branches
feature/document-comparison
feature/semantic-analysis
bugfix/lambda-timeout-issue
hotfix/security-patch
```

#### Commit Messages

Follow conventional commit format:

```
type(scope): description

[optional body]

[optional footer]
```

Examples:
```
feat(api): add document comparison endpoint
fix(lambda): resolve timeout issue in processing
docs(readme): update deployment instructions
test(integration): add API workflow tests
```

#### Pull Request Process

1. **Create feature branch** from `develop`
2. **Implement changes** with tests
3. **Run quality checks** locally
4. **Create pull request** with description
5. **Address review feedback**
6. **Merge after approval**

### Code Review Guidelines

#### Review Checklist

- [ ] Code follows project standards
- [ ] Tests cover new functionality
- [ ] Documentation is updated
- [ ] No security vulnerabilities
- [ ] Performance impact considered
- [ ] Error handling is robust
- [ ] Logging is appropriate

#### Review Process

1. **Automated checks** must pass
2. **At least one approval** required
3. **All conversations resolved**
4. **Up-to-date with target branch**

## Release Process

### Version Management

#### Semantic Versioning

- **MAJOR**: Breaking changes
- **MINOR**: New features, backward compatible
- **PATCH**: Bug fixes, backward compatible

#### Release Workflow

```bash
# Create release branch
git checkout develop
git pull origin develop
git checkout -b release/v1.2.0

# Update version numbers
npm version 1.2.0
git add .
git commit -m "chore: bump version to 1.2.0"

# Create pull request to main
# After merge, tag release
git checkout main
git pull origin main
git tag v1.2.0
git push origin v1.2.0

# Merge back to develop
git checkout develop
git merge main
git push origin develop
```

### Deployment Pipeline

#### Staging Deployment

```bash
# Automatic deployment from main branch
# Triggered by merge to main
# Runs full test suite
# Deploys to staging environment
```

#### Production Deployment

```bash
# Manual approval required
# Triggered by git tag creation
# Deploys to production environment
# Runs smoke tests
# Sends notifications
```

### Quality Gates

#### Automated Quality Checks

- [ ] All tests pass (unit, integration, E2E)
- [ ] Code coverage above 80%
- [ ] Security scan passes
- [ ] Performance tests pass
- [ ] Infrastructure validation passes

#### Manual Quality Checks

- [ ] Feature testing in staging
- [ ] User acceptance testing
- [ ] Performance validation
- [ ] Security review
- [ ] Documentation review