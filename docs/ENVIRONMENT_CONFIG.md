# Environment Configuration Guide

This guide covers the environment configuration system for AutoSpec.AI, including all configuration options and environment-specific settings.

## Overview

AutoSpec.AI uses a multi-environment configuration system that supports:
- **Development (`dev`)**: Local development and testing
- **Staging (`staging`)**: Pre-production testing
- **Production (`prod`)**: Live production environment

## Configuration Files

Environment configurations are stored in `config/environments/`:

```
config/environments/
├── dev.env        # Development environment
├── staging.env    # Staging environment
└── prod.env       # Production environment
```

## Loading Configuration

```bash
# Load environment configuration
source ./scripts/load-config.sh <environment>

# Examples:
source ./scripts/load-config.sh dev
source ./scripts/load-config.sh staging
source ./scripts/load-config.sh prod
```

## Configuration Categories

### AWS Configuration

```bash
# AWS Configuration
export AWS_REGION="us-east-1"                    # AWS region
export AWS_ACCOUNT_ID=""                         # AWS account ID (auto-detected)
```

### Stack Configuration

```bash
# Stack Configuration
export CDK_STACK_NAME="AutoSpecAI-dev"          # CloudFormation stack name
export ENVIRONMENT="dev"                         # Environment identifier
export STAGE="dev"                              # Stage identifier
```

### API Configuration

```bash
# API Configuration
export API_STAGE="dev"                          # API Gateway stage
export API_THROTTLE_RATE_LIMIT=100             # Requests per second
export API_THROTTLE_BURST_LIMIT=200            # Burst limit
```

### Lambda Configuration

```bash
# Lambda Configuration
export LAMBDA_MEMORY_SIZE=512                   # Memory allocation (MB)
export LAMBDA_TIMEOUT=300                       # Timeout (seconds)
export LAMBDA_RUNTIME="python3.9"              # Runtime version
```

### Storage Configuration

```bash
# S3 Configuration
export S3_BUCKET_PREFIX="autospec-ai-dev"      # S3 bucket prefix
export S3_LIFECYCLE_DAYS=30                    # Object lifecycle (days)

# DynamoDB Configuration
export DYNAMODB_BILLING_MODE="PAY_PER_REQUEST" # Billing mode
export DYNAMODB_POINT_IN_TIME_RECOVERY=false   # PITR enabled
```

### Email Configuration

```bash
# SES Configuration
export SES_FROM_EMAIL="noreply-dev@autospec.ai"    # From email
export SES_REPLY_TO_EMAIL="dev-support@autospec.ai" # Reply-to email
```

### AI Configuration

```bash
# Bedrock Configuration
export BEDROCK_MODEL_ID="anthropic.claude-3-sonnet-20240229-v1:0"
export BEDROCK_MAX_TOKENS=4000
export BEDROCK_TEMPERATURE=0.1
```

### Security Configuration

```bash
# Security Configuration
export CORS_ALLOWED_ORIGINS="http://localhost:3000,https://dev.autospec.ai"
export JWT_SECRET_NAME="autospec-ai/dev/jwt-secret"
export ENCRYPTION_KEY_NAME="autospec-ai/dev/encryption-key"
```

### Monitoring Configuration

```bash
# Monitoring Configuration
export XRAY_TRACING_ENABLED=true               # X-Ray tracing
export CLOUDWATCH_LOG_RETENTION=7              # Log retention (days)
export CLOUDWATCH_DETAILED_MONITORING=false    # Detailed monitoring
```

### Feature Flags

```bash
# Feature Flags
export ENABLE_DOCUMENT_COMPARISON=true
export ENABLE_INTELLIGENT_ROUTING=true
export ENABLE_SEMANTIC_ANALYSIS=true
export ENABLE_REQUIREMENT_TRACEABILITY=true
export ENABLE_ADVANCED_ANALYTICS=true
```

## Environment-Specific Settings

### Development Environment

Development environment settings prioritize:
- Fast deployment and testing
- Detailed logging and debugging
- Cost optimization
- Relaxed security for development

```bash
# Development Specific
export DEBUG_MODE=true
export VERBOSE_LOGGING=true
export MOCK_EXTERNAL_SERVICES=false

# Cost Optimization
export LAMBDA_MEMORY_SIZE=512
export DYNAMODB_BILLING_MODE="PAY_PER_REQUEST"
export CLOUDWATCH_LOG_RETENTION=7
```

### Staging Environment

Staging environment settings focus on:
- Production-like configuration
- Performance testing
- Integration testing
- Security validation

```bash
# Staging Specific
export DEBUG_MODE=false
export VERBOSE_LOGGING=true
export MOCK_EXTERNAL_SERVICES=false

# Performance Settings
export LAMBDA_MEMORY_SIZE=1024
export API_THROTTLE_RATE_LIMIT=500
export CLOUDWATCH_LOG_RETENTION=14
```

### Production Environment

Production environment settings emphasize:
- High availability and performance
- Security and compliance
- Monitoring and alerting
- Cost optimization at scale

```bash
# Production Specific
export DEBUG_MODE=false
export VERBOSE_LOGGING=false
export MOCK_EXTERNAL_SERVICES=false
export PERFORMANCE_MONITORING_ENABLED=true

# High Performance
export LAMBDA_MEMORY_SIZE=2048
export LAMBDA_TIMEOUT=900
export API_THROTTLE_RATE_LIMIT=2000
export API_THROTTLE_BURST_LIMIT=5000

# High Availability
export MULTI_AZ_ENABLED=true
export AUTO_SCALING_ENABLED=true
export DISASTER_RECOVERY_ENABLED=true

# Compliance
export GDPR_COMPLIANCE_ENABLED=true
export AUDIT_LOGGING_ENABLED=true
export DATA_RETENTION_POLICY_DAYS=2555  # 7 years
export ENCRYPTION_AT_REST_ENABLED=true
export ENCRYPTION_IN_TRANSIT_ENABLED=true
```

## Customizing Configuration

### 1. Create Local Configuration

```bash
# Copy environment configuration
cp config/environments/dev.env config/environments/dev.local.env

# Edit local configuration
nano config/environments/dev.local.env
```

### 2. Override Specific Settings

```bash
# Load base configuration
source config/environments/dev.env

# Override specific settings
export LAMBDA_MEMORY_SIZE=1024
export DEBUG_MODE=false
```

### 3. Environment Variables

Set environment variables to override configuration:

```bash
# Override via environment variables
export AUTOSPEC_LAMBDA_MEMORY_SIZE=1024
export AUTOSPEC_DEBUG_MODE=false

# Load configuration
source ./scripts/load-config.sh dev
```

## Secrets Management

Sensitive configuration is stored in AWS Secrets Manager:

### Creating Secrets

```bash
# JWT signing secret
aws secretsmanager create-secret \
  --name "autospec-ai/dev/jwt-secret" \
  --description "JWT signing secret" \
  --secret-string "$(openssl rand -base64 32)"

# Encryption key
aws secretsmanager create-secret \
  --name "autospec-ai/dev/encryption-key" \
  --description "Encryption key" \
  --secret-string "$(openssl rand -base64 32)"

# Slack webhook URL
aws secretsmanager create-secret \
  --name "autospec-ai/dev/slack-webhook" \
  --description "Slack webhook URL" \
  --secret-string "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
```

### Updating Secrets

```bash
# Update existing secret
aws secretsmanager update-secret \
  --secret-id "autospec-ai/dev/jwt-secret" \
  --secret-string "$(openssl rand -base64 32)"
```

### Retrieving Secrets

```bash
# Get secret value
aws secretsmanager get-secret-value \
  --secret-id "autospec-ai/dev/jwt-secret" \
  --query 'SecretString' \
  --output text
```

## Validation

### Configuration Validation

```bash
# Validate configuration
./scripts/validate-config.sh dev

# Check required variables
./scripts/check-config.sh dev
```

### Environment Health Check

```bash
# Health check for environment
./scripts/health-check.sh dev

# Comprehensive validation
./scripts/validate-deployment.sh dev
```

## Best Practices

### 1. Security

- Never commit secrets to version control
- Use AWS Secrets Manager for sensitive data
- Rotate secrets regularly
- Use least privilege access policies

### 2. Environment Isolation

- Use separate AWS accounts for production
- Implement proper RBAC
- Monitor cross-environment access
- Audit configuration changes

### 3. Configuration Management

- Document all configuration changes
- Use infrastructure as code (CDK)
- Version configuration files
- Test configuration changes in staging first

### 4. Monitoring

- Monitor configuration drift
- Alert on unauthorized changes
- Log configuration access
- Regular configuration audits

## Troubleshooting

### Common Issues

#### 1. Missing Environment Variables

```bash
# Error: Required environment variable not set
# Solution: Check configuration loading
source ./scripts/load-config.sh dev
echo $CDK_STACK_NAME
```

#### 2. Invalid AWS Credentials

```bash
# Error: Invalid AWS credentials
# Solution: Verify AWS configuration
aws sts get-caller-identity
aws configure list
```

#### 3. Secret Not Found

```bash
# Error: Secret not found in Secrets Manager
# Solution: Create missing secret
aws secretsmanager create-secret \
  --name "autospec-ai/dev/jwt-secret" \
  --secret-string "$(openssl rand -base64 32)"
```

#### 4. Region Mismatch

```bash
# Error: Resource not found in region
# Solution: Verify AWS region
echo $AWS_REGION
aws configure get region
```

### Debug Commands

```bash
# Check environment variables
env | grep AUTOSPEC

# Validate AWS access
aws sts get-caller-identity

# Check secrets
aws secretsmanager list-secrets \
  --query 'SecretList[?contains(Name, `autospec-ai`)].Name'

# Test configuration
./scripts/load-config.sh dev && echo "Configuration loaded successfully"
```

## Migration Guide

### Upgrading Configuration

When upgrading AutoSpec.AI versions:

1. **Backup Current Configuration**
   ```bash
   cp config/environments/prod.env config/environments/prod.env.backup
   ```

2. **Review New Configuration Options**
   ```bash
   diff config/environments/prod.env.backup config/environments/prod.env
   ```

3. **Update Configuration**
   ```bash
   # Apply new settings
   nano config/environments/prod.env
   ```

4. **Test in Staging**
   ```bash
   ./scripts/deploy.sh staging
   ./scripts/validate-deployment.sh staging
   ```

5. **Deploy to Production**
   ```bash
   ./scripts/deploy.sh prod
   ```

### Environment Migration

To migrate between environments:

1. **Export Current Configuration**
   ```bash
   ./scripts/export-config.sh dev > dev-config.json
   ```

2. **Import to New Environment**
   ```bash
   ./scripts/import-config.sh staging < dev-config.json
   ```

3. **Validate Migration**
   ```bash
   ./scripts/validate-config.sh staging
   ```