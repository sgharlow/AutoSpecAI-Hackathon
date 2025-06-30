# AutoSpec.AI Configuration Guide

## Overview

This guide explains how to configure AutoSpec.AI for different deployment environments, including setting up required AWS services and external integrations.

## Required Configurations

### 1. Amazon SES (Simple Email Service)

**Purpose**: Email-based document submission and result delivery

**Setup Steps**:
1. **Verify Domain**:
   ```bash
   aws ses verify-domain-identity --domain your-domain.com
   ```

2. **Configure DNS Records**: Add the verification TXT record to your domain's DNS

3. **Request Production Access**: If using for production, request to move out of SES sandbox

4. **Update Configuration**:
   ```json
   {
     "notifications": {
       "ses_verified_domain": "your-domain.com",
       "ses_from_email": "autospec-ai@your-domain.com"
     }
   }
   ```

5. **Update CDK Stack**: Edit `infra/cdk/lib/autospec-ai-stack.js`:
   ```javascript
   environment: {
     FROM_EMAIL: 'autospec-ai@your-domain.com',
   }
   ```

### 2. Slack Integration (Optional)

**Purpose**: Team notifications and document processing via Slack

**Setup Steps**:
1. **Create Slack App**: Go to https://api.slack.com/apps

2. **Configure Slash Commands**:
   - Command: `/autospec`
   - Request URL: `https://your-api-url.amazonaws.com/v1/slack/command`

3. **Set Up Incoming Webhooks**:
   - Create webhook URL for your channel
   - Copy webhook URL

4. **Configure App Permissions**:
   - `chat:write`
   - `commands`
   - `files:read`

5. **Update Configuration**:
   ```json
   {
     "notifications": {
       "slack_webhook_url": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
     }
   }
   ```

6. **Update CDK Stack**: Edit `infra/cdk/lib/autospec-ai-stack.js`:
   ```javascript
   environment: {
     SLACK_WEBHOOK_URL: 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL',
     SLACK_SIGNING_SECRET: 'your-slack-signing-secret',
   }
   ```

### 3. Amazon Bedrock Model Access

**Purpose**: AI-powered document analysis

**Setup Steps**:
1. **Request Model Access**:
   - Go to AWS Bedrock console
   - Request access to Claude 3 Sonnet model
   - Wait for approval (usually immediate)

2. **Verify Access**:
   ```bash
   aws bedrock list-foundation-models --region us-east-1
   ```

3. **Test Model**:
   ```bash
   aws bedrock-runtime invoke-model \
     --model-id anthropic.claude-3-sonnet-20240229-v1:0 \
     --body '{"anthropic_version":"bedrock-2023-05-31","max_tokens":100,"messages":[{"role":"user","content":"Hello"}]}' \
     --cli-binary-format raw-in-base64-out \
     output.json
   ```

### 4. API Authentication

**Purpose**: Secure API access with rate limiting

**Setup Steps**:
1. **Generate API Keys**: After deployment, use the API to create keys:
   ```bash
   # This will be available via AWS CLI or custom script
   aws dynamodb put-item \
     --table-name autospec-ai-api-keys \
     --item '{
       "keyHash": {"S": "hash-of-your-api-key"},
       "keyName": {"S": "dev-key-1"},
       "enabled": {"BOOL": true},
       "rateLimit": {"N": "100"}
     }'
   ```

2. **Update Environment Variables**: Configure rate limiting table access in CDK

## Environment-Specific Configuration

### Development Environment

**File**: `config/environments/dev.json`

**Key Settings**:
- Lower resource allocation
- Relaxed rate limiting
- Optional Slack integration
- Basic monitoring

**Required Updates**:
```json
{
  "notifications": {
    "ses_from_email": "autospec-ai-dev@your-domain.com"
  }
}
```

### Staging Environment

**File**: `config/environments/staging.json`

**Key Settings**:
- Production-like resource allocation
- Full feature testing
- Comprehensive monitoring

### Production Environment

**File**: `config/environments/prod.json`

**Key Settings**:
- High availability configuration
- Strict rate limiting
- Enhanced security
- Comprehensive monitoring and alerting

**Required Updates**:
```json
{
  "notifications": {
    "slack_webhook_url": "CONFIGURE_SLACK_WEBHOOK_URL",
    "notification_email": "alerts@your-domain.com",
    "escalation_email": "ops-team@your-domain.com",
    "ses_from_email": "autospec-ai@your-domain.com"
  }
}
```

## Deployment Commands with Configuration

### Quick Setup for Development

```bash
# 1. Configure SES domain (required)
export SES_DOMAIN="your-domain.com"

# 2. Update dev configuration
sed -i "s/CONFIGURE_SES_DOMAIN/$SES_DOMAIN/g" config/environments/dev.json

# 3. Deploy with updated configuration
./deploy.sh dev
```

### Production Deployment

```bash
# 1. Update all configuration placeholders
export SES_DOMAIN="your-domain.com"
export SLACK_WEBHOOK="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
export NOTIFICATION_EMAIL="alerts@your-domain.com"

# 2. Update production configuration
sed -i "s/CONFIGURE_SES_DOMAIN/$SES_DOMAIN/g" config/environments/prod.json
sed -i "s|CONFIGURE_SLACK_WEBHOOK_URL|$SLACK_WEBHOOK|g" config/environments/prod.json
sed -i "s/CONFIGURE_SES_VERIFIED_EMAIL/$NOTIFICATION_EMAIL/g" config/environments/prod.json

# 3. Deploy to production
./deploy.sh prod
```

## Validation Steps

### 1. Test SES Configuration

```bash
# Send test email
aws ses send-email \
  --source "autospec-ai@your-domain.com" \
  --destination "ToAddresses=test@example.com" \
  --message '{
    "Subject": {"Data": "AutoSpec.AI Test"},
    "Body": {"Text": {"Data": "Configuration test successful"}}
  }'
```

### 2. Test Bedrock Access

```bash
# Test model access
curl -X POST https://your-api-url.amazonaws.com/v1/upload \
  -H "Content-Type: application/json" \
  -d '{
    "file_content": "VGVzdCBkb2N1bWVudCBmb3IgQXV0b1NwZWMuQUk=",
    "filename": "test.txt",
    "sender_email": "test@example.com"
  }'
```

### 3. Test Slack Integration

```bash
# Test webhook
curl -X POST $SLACK_WEBHOOK \
  -H "Content-Type: application/json" \
  -d '{
    "text": "AutoSpec.AI configuration test successful!"
  }'
```

## Troubleshooting

### Common Issues

1. **SES Email Bounces**:
   - Verify domain ownership
   - Check DNS configuration
   - Ensure sender email is verified

2. **Bedrock Access Denied**:
   - Request model access in Bedrock console
   - Check IAM permissions
   - Verify region availability

3. **Slack Integration Fails**:
   - Verify webhook URL format
   - Check Slack app permissions
   - Validate signing secret

4. **Rate Limiting Not Working**:
   - Verify DynamoDB table creation
   - Check Lambda permissions
   - Review CloudWatch logs

### Getting Help

1. **AWS Support**: For service-specific issues
2. **GitHub Issues**: For application bugs
3. **Documentation**: Check comprehensive guides in `docs/` directory

## Security Considerations

### Production Checklist

- [ ] SES domain verified and configured
- [ ] Slack webhook URL secured
- [ ] API keys properly managed
- [ ] Rate limiting enabled
- [ ] Monitoring and alerting configured
- [ ] Access logging enabled
- [ ] Encryption at rest and in transit
- [ ] IAM roles follow least privilege
- [ ] VPC configuration (if required)

### Secret Management

**Never commit secrets to version control**:
- Use environment variables for deployment
- Use AWS Secrets Manager for production
- Rotate keys regularly
- Monitor for exposed credentials

## Advanced Configuration

### Custom Domains

Set up custom domain for API Gateway:
```bash
# Create certificate in ACM
aws acm request-certificate \
  --domain-name api.autospec.ai \
  --validation-method DNS

# Configure custom domain in API Gateway
# Update Route 53 records
```

### Multi-Region Deployment

For high availability:
1. Deploy to multiple AWS regions
2. Configure cross-region replication
3. Set up Route 53 health checks
4. Configure disaster recovery procedures

---

**Next Steps**: After configuration, proceed with deployment using `./deploy.sh <environment>`