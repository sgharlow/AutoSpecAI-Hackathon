# AutoSpec.AI Production Deployment Checklist

Complete checklist of all accounts, credentials, and configuration values required for production deployment.

## 🏢 Required Accounts and Services

### 1. AWS Account
- **AWS Account ID**: Production AWS account with billing enabled
- **Account Type**: Business or Enterprise support recommended
- **Region**: Primary region (recommended: `us-east-1`)
- **Billing**: Active billing with sufficient limits

### 2. Domain and DNS
- **Domain Name**: `autospec.ai` (or your chosen domain)
- **DNS Provider**: Route 53 or external DNS provider
- **SSL Certificate**: AWS Certificate Manager or external SSL

### 3. Third-Party Services (Optional)
- **Slack Workspace**: For notifications and integrations
- **PagerDuty Account**: For incident management
- **GitHub Account**: For CI/CD and source control

## 🔐 AWS Credentials and Permissions

### IAM User for Deployment
Create a dedicated IAM user with these policies:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudformation:*",
        "iam:*",
        "lambda:*",
        "apigateway:*",
        "s3:*",
        "dynamodb:*",
        "ses:*",
        "bedrock:*",
        "logs:*",
        "xray:*",
        "secretsmanager:*",
        "ssm:*",
        "sns:*",
        "sqs:*",
        "events:*",
        "application-autoscaling:*"
      ],
      "Resource": "*"
    }
  ]
}
```

### Required Credentials
- **AWS Access Key ID**: `AKIA...`
- **AWS Secret Access Key**: `...`
- **AWS Region**: `us-east-1`

## 📧 Email Configuration (Amazon SES)

### Verified Email Addresses
Required verified emails in SES:

1. **From Email**: `noreply@autospec.ai`
   ```bash
   aws ses verify-email-identity --email-address noreply@autospec.ai
   ```

2. **Support Email**: `support@autospec.ai`
   ```bash
   aws ses verify-email-identity --email-address support@autospec.ai
   ```

3. **Document Ingestion Email**: `documents@autospec.ai`
   ```bash
   aws ses verify-email-identity --email-address documents@autospec.ai
   ```

### Domain Verification (Recommended)
Verify entire domain for production:
```bash
aws ses verify-domain-identity --domain autospec.ai
```

### SES Configuration Requirements
- **Sending Limits**: Request production access (removes 200 email/day limit)
- **Dedicated IP**: Optional for high volume
- **Bounce/Complaint Handling**: Configure SNS topics

## 🤖 AI Service Access (Amazon Bedrock)

### Model Access Required
Request access to these models in AWS Bedrock console:

1. **Claude 3 Sonnet**: `anthropic.claude-3-sonnet-20240229-v1:0`
2. **Claude 3 Haiku**: `anthropic.claude-3-haiku-20240307-v1:0` (for backup)

### Steps to Enable:
1. Navigate to Amazon Bedrock console
2. Go to "Model access" in left sidebar
3. Click "Request model access"
4. Select "Anthropic Claude 3 Sonnet"
5. Accept terms and submit request
6. Wait for approval (usually immediate)

## 🔑 Secrets and Configuration Values

### Required Secrets in AWS Secrets Manager

Create these secrets before deployment:

#### 1. JWT Secret
```bash
aws secretsmanager create-secret \
  --name "autospec-ai/prod/jwt-secret" \
  --description "JWT signing secret for AutoSpec.AI production" \
  --secret-string "$(openssl rand -base64 64)" \
  --region us-east-1
```

#### 2. Encryption Key
```bash
aws secretsmanager create-secret \
  --name "autospec-ai/prod/encryption-key" \
  --description "Encryption key for AutoSpec.AI production" \
  --secret-string "$(openssl rand -base64 64)" \
  --region us-east-1
```

#### 3. Slack Webhook (Optional)
```bash
aws secretsmanager create-secret \
  --name "autospec-ai/prod/slack-webhook" \
  --description "Slack webhook URL for AutoSpec.AI production" \
  --secret-string "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK" \
  --region us-east-1
```

#### 4. PagerDuty Integration Key (Optional)
```bash
aws secretsmanager create-secret \
  --name "autospec-ai/prod/pagerduty-key" \
  --description "PagerDuty integration key for AutoSpec.AI production" \
  --secret-string "YOUR_PAGERDUTY_INTEGRATION_KEY" \
  --region us-east-1
```

## 🌐 Domain and SSL Configuration

### Domain Setup
1. **Purchase Domain**: Register `autospec.ai` or use existing domain
2. **DNS Configuration**: Point to AWS resources
3. **SSL Certificate**: Create in AWS Certificate Manager

### DNS Records Required
```
# Main application
app.autospec.ai     CNAME   -> CloudFront distribution
www.autospec.ai     CNAME   -> CloudFront distribution
autospec.ai         A       -> CloudFront distribution

# API endpoint
api.autospec.ai     CNAME   -> API Gateway custom domain

# Email ingestion
documents.autospec.ai MX 10 -> inbound-smtp.us-east-1.amazonaws.com

# Email authentication
autospec.ai         TXT     -> "v=spf1 include:amazonses.com ~all"
_dmarc.autospec.ai  TXT     -> "v=DMARC1; p=quarantine; rua=mailto:postmaster@autospec.ai"
```

### SSL Certificate
```bash
# Request certificate in AWS Certificate Manager
aws acm request-certificate \
  --domain-name autospec.ai \
  --subject-alternative-names "*.autospec.ai" \
  --validation-method DNS \
  --region us-east-1
```

## 📊 Monitoring and Alerting

### Required Notification Endpoints
- **Email Alerts**: `alerts@autospec.ai`
- **Slack Channel**: `#autospec-alerts`
- **PagerDuty Service**: AutoSpec.AI Production

### SNS Topics to Create
```bash
# Critical alerts
aws sns create-topic --name autospec-ai-prod-critical-alerts

# Warning alerts  
aws sns create-topic --name autospec-ai-prod-warning-alerts

# Business metrics
aws sns create-topic --name autospec-ai-prod-business-metrics
```

## 🔒 Security Configuration

### WAF Configuration
- **Rate Limiting**: 10,000 requests per 5 minutes per IP
- **Geographic Restrictions**: Block high-risk countries (optional)
- **SQL Injection Protection**: Enable
- **XSS Protection**: Enable

### Security Groups
- **ALB Security Group**: 
  - Inbound: 80, 443 from 0.0.0.0/0
  - Outbound: All to VPC
- **Lambda Security Group**:
  - Outbound: 443 to 0.0.0.0/0
  - Outbound: Database ports to RDS security group

## 💾 Backup and Disaster Recovery

### Cross-Region Backup
- **Backup Region**: `us-west-2`
- **S3 Cross-Region Replication**: Enable for critical buckets
- **DynamoDB Global Tables**: Enable for critical tables
- **RDS Automated Backups**: 30-day retention

## 💰 Cost Management

### Cost Budgets
Set up AWS Budgets for:
- **Monthly Spend**: $500 threshold with alerts
- **Service-specific**: Lambda, DynamoDB, S3, Bedrock
- **Cost Anomaly Detection**: Enable for unusual spending

### Reserved Capacity (After Stable Usage)
- **DynamoDB Reserved Capacity**: For predictable workloads
- **Lambda Provisioned Concurrency**: For consistent performance

## 🚀 Production Deployment Steps

### Pre-Deployment Checklist
- [ ] AWS account set up with billing
- [ ] IAM user created with deployment permissions
- [ ] Domain purchased and DNS configured
- [ ] SSL certificate issued and validated
- [ ] SES emails verified and production access requested
- [ ] Bedrock model access approved
- [ ] All secrets created in Secrets Manager
- [ ] Monitoring and alerting configured

### Environment Variables to Set
```bash
# Core AWS Configuration
export AWS_REGION="us-east-1"
export AWS_ACCOUNT_ID="123456789012"  # Your AWS account ID

# Domain Configuration
export DOMAIN_NAME="autospec.ai"
export API_DOMAIN="api.autospec.ai"
export APP_DOMAIN="app.autospec.ai"

# Email Configuration
export SES_FROM_EMAIL="noreply@autospec.ai"
export SES_REPLY_TO_EMAIL="support@autospec.ai"
export SES_DOCUMENTS_EMAIL="documents@autospec.ai"

# Security Configuration
export CORS_ALLOWED_ORIGINS="https://app.autospec.ai,https://www.autospec.ai"
export WAF_ENABLED=true
export SECURITY_HEADERS_ENABLED=true

# Performance Configuration
export LAMBDA_MEMORY_SIZE=2048
export LAMBDA_TIMEOUT=900
export API_THROTTLE_RATE_LIMIT=2000
export API_THROTTLE_BURST_LIMIT=5000

# Compliance Configuration
export GDPR_COMPLIANCE_ENABLED=true
export AUDIT_LOGGING_ENABLED=true
export DATA_RETENTION_POLICY_DAYS=2555
export ENCRYPTION_AT_REST_ENABLED=true
export ENCRYPTION_IN_TRANSIT_ENABLED=true
```

### Deployment Commands
```bash
# 1. Load production configuration
source ./scripts/load-config.sh prod

# 2. Bootstrap CDK (one-time)
cdk bootstrap aws://$AWS_ACCOUNT_ID/$AWS_REGION

# 3. Deploy to production
./scripts/deploy.sh prod

# 4. Validate deployment
./scripts/validate-deployment.sh prod

# 5. Run integration tests
./scripts/integration-tests.sh https://api.autospec.ai prod
```

## 📋 Post-Deployment Verification

### Health Checks
```bash
# API Health
curl https://api.autospec.ai/v1/health

# Application Health
curl https://app.autospec.ai

# Email Processing
echo "Test" | mail -s "Test Document" documents@autospec.ai
```

### Monitoring Verification
- [ ] CloudWatch dashboards showing data
- [ ] X-Ray traces appearing
- [ ] Log groups created and receiving logs
- [ ] Alarms in OK state
- [ ] SNS notifications working

### Security Verification
- [ ] SSL certificate valid
- [ ] WAF rules active
- [ ] Security headers present
- [ ] API authentication working
- [ ] CORS policy correct

## 🆘 Emergency Contacts and Procedures

### Key Personnel
- **DevOps Lead**: Contact for deployment issues
- **Security Team**: Contact for security incidents
- **Business Owner**: Contact for business decisions

### Emergency Procedures
- **Rollback**: `./scripts/rollback.sh prod`
- **Scale Down**: Update Lambda concurrency limits
- **Disable Features**: Update feature flags in environment config
- **Circuit Breaker**: Implement API Gateway throttling

## 📞 Support Information

### AWS Support
- **Account ID**: [Your AWS Account ID]
- **Support Plan**: Business or Enterprise
- **Primary Contact**: [Technical contact email]

### Service Limits to Monitor
- **Lambda Concurrent Executions**: 1000 (request increase if needed)
- **API Gateway Requests**: 10,000 per second
- **DynamoDB Read/Write Capacity**: Monitor and adjust
- **SES Sending Rate**: 200 emails/second (after production access)

This checklist ensures all required accounts, credentials, and configurations are in place for a successful production deployment of AutoSpec.AI.