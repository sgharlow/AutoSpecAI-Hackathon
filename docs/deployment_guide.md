# AutoSpec.AI Complete Deployment Guide

This comprehensive guide covers everything needed to deploy AutoSpec.AI from development to production, including all configuration requirements, dependencies, and deployment steps.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [AWS Account Setup](#aws-account-setup)
3. [Local Environment Setup](#local-environment-setup)
4. [Environment Configuration](#environment-configuration)
5. [Infrastructure Deployment](#infrastructure-deployment)
6. [Application Deployment](#application-deployment)
7. [Post-Deployment Configuration](#post-deployment-configuration)
8. [Validation and Testing](#validation-and-testing)
9. [Monitoring Setup](#monitoring-setup)
10. [Production Checklist](#production-checklist)
11. [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Software

Install the following tools before beginning deployment:

```bash
# 1. AWS CLI v2
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# 2. Node.js 18+ (using nvm)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install 18
nvm use 18

# 3. AWS CDK v2
npm install -g aws-cdk

# 4. Python 3.9+
sudo apt-get update
sudo apt-get install python3.9 python3-pip

# 5. Git
sudo apt-get install git

# 6. jq (JSON processor)
sudo apt-get install jq
```

### Verify Installation

```bash
aws --version          # Should show AWS CLI 2.x
node --version          # Should show Node.js 18+
npm --version           # Should show npm 8+
cdk --version           # Should show AWS CDK 2.x
python3 --version       # Should show Python 3.9+
git --version           # Should show Git 2.x+
jq --version            # Should show jq 1.6+
```

## AWS Account Setup

### 1. AWS Account Requirements

- **AWS Account**: Active AWS account with billing enabled
- **AWS Regions**: Recommended regions with Bedrock support:
  - `us-east-1` (N. Virginia) - Primary recommendation
  - `us-west-2` (Oregon)
  - `eu-west-1` (Ireland)

### 2. IAM User Creation

Create an IAM user with programmatic access and required policies.

### 3. Configure AWS CLI

```bash
# Configure AWS CLI with your credentials
aws configure

# Verify configuration
aws sts get-caller-identity
```

### 4. Enable Required AWS Services

Enable Amazon Bedrock and request access to Claude 3 Sonnet model through the AWS Console.

## Local Environment Setup

### 1. Clone Repository

```bash
git clone https://github.com/your-username/AutoSpecAI.git
cd AutoSpecAI
```

### 2. Install Dependencies

```bash
# Install Node.js dependencies for CDK
cd infra/cdk
npm install
cd ../..

# Install Python dependencies for Lambda functions
pip3 install -r requirements.txt

# Make scripts executable
chmod +x scripts/*.sh
```

## Environment Configuration

### 1. Environment Overview

AutoSpec.AI supports three environments:
- **Development (`dev`)**: Local development and testing
- **Staging (`staging`)**: Pre-production testing
- **Production (`prod`)**: Live production environment

### 2. Configure Development Environment

```bash
# Load environment configuration
source ./scripts/load-config.sh dev

# Review and customize settings
nano config/environments/dev.env
```

**Required Configuration Updates:**

```bash
# AWS Configuration
export AWS_REGION="us-east-1"
export AWS_ACCOUNT_ID="123456789012"

# SES Configuration (must be verified emails)
export SES_FROM_EMAIL="noreply@yourdomain.com"
export SES_REPLY_TO_EMAIL="support@yourdomain.com"

# Security Configuration
export CORS_ALLOWED_ORIGINS="http://localhost:3000,https://yourdomain.com"
```

### 3. Set Up Secrets

AutoSpec.AI uses AWS Secrets Manager for sensitive configuration:

```bash
# Create JWT secret
aws secretsmanager create-secret \
  --name "autospec-ai/dev/jwt-secret" \
  --description "JWT signing secret for AutoSpec.AI dev environment" \
  --secret-string "$(openssl rand -base64 32)" \
  --region us-east-1

# Create encryption key
aws secretsmanager create-secret \
  --name "autospec-ai/dev/encryption-key" \
  --description "Encryption key for AutoSpec.AI dev environment" \
  --secret-string "$(openssl rand -base64 32)" \
  --region us-east-1
```

## Infrastructure Deployment

### 1. CDK Bootstrap

Bootstrap CDK in your AWS account (one-time setup):

```bash
# Load environment configuration
source ./scripts/load-config.sh dev

# Bootstrap CDK
cdk bootstrap aws://$AWS_ACCOUNT_ID/$AWS_REGION
```

### 2. Deploy Using Scripts

The recommended deployment method uses the provided scripts:

```bash
# Deploy to development environment
./scripts/deploy.sh dev

# Deploy with options
./scripts/deploy.sh dev --skip-tests --region us-east-1
```

### 3. Verify Infrastructure Deployment

```bash
# Check CloudFormation stack
aws cloudformation describe-stacks \
  --stack-name AutoSpecAI-dev \
  --region us-east-1
```

## Application Deployment

The deployment script handles building and deploying Lambda functions automatically.

## Post-Deployment Configuration

### 1. Configure API Gateway

```bash
# Get API Gateway URL
API_URL=$(aws cloudformation describe-stacks \
  --stack-name AutoSpecAI-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' \
  --output text \
  --region us-east-1)

echo "API URL: $API_URL"

# Test API endpoint
curl -s "$API_URL/health" | jq .
```

### 2. Configure Monitoring

```bash
# Update monitoring dashboards
./scripts/update-monitoring.sh dev
```

## Validation and Testing

### 1. Run Deployment Validation

```bash
# Validate deployment
./scripts/validate-deployment.sh dev
```

### 2. Run Integration Tests

```bash
# Run integration tests
./scripts/integration-tests.sh "$API_URL" dev
```

## Monitoring Setup

### 1. CloudWatch Dashboards

Access the operational dashboard through the AWS Console.

### 2. X-Ray Tracing

View X-Ray traces and service maps through the AWS Console.

## Production Checklist

Before deploying to production, ensure:

### Security Checklist

- [ ] **IAM Roles**: Principle of least privilege applied
- [ ] **Secrets Management**: All secrets in AWS Secrets Manager
- [ ] **Encryption**: At-rest and in-transit encryption enabled
- [ ] **Security Headers**: CORS, CSP, and security headers configured

### Performance Checklist

- [ ] **Lambda Memory**: Optimized memory allocation for functions
- [ ] **DynamoDB**: Provisioned capacity or on-demand configured
- [ ] **API Gateway**: Caching and throttling configured

### Monitoring Checklist

- [ ] **CloudWatch Alarms**: Critical metrics monitored
- [ ] **X-Ray Tracing**: Distributed tracing enabled
- [ ] **Log Retention**: Appropriate log retention periods set
- [ ] **Health Checks**: API health checks implemented

## Troubleshooting

### Common Issues

#### 1. CDK Bootstrap Fails

```bash
# Solution: Bootstrap with specific account and region
cdk bootstrap aws://123456789012/us-east-1
```

#### 2. Lambda Function Timeout

```bash
# Solution: Increase timeout in environment configuration
export LAMBDA_TIMEOUT=600  # 10 minutes
```

#### 3. Bedrock Access Denied

Ensure model access is granted in Bedrock console.

### Debug Commands

```bash
# Check stack status
aws cloudformation describe-stacks --stack-name AutoSpecAI-dev

# View recent Lambda logs
aws logs tail "/aws/lambda/AutoSpecAI-dev-process" --since 1h

# Test API connectivity
curl -v "$API_URL/health"
```

## Next Steps

After successful deployment:

1. **Configure Production Environment**: Follow this guide for staging and production
2. **Set Up CI/CD Pipeline**: Configure GitHub Actions for automated deployment
3. **Load Testing**: Perform load testing with realistic data volumes
4. **User Training**: Train end users on the application features
5. **Documentation**: Keep deployment documentation updated