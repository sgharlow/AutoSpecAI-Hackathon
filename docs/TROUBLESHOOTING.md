# AutoSpec.AI Troubleshooting Guide

Comprehensive troubleshooting guide for AutoSpec.AI deployment, configuration, and operational issues.

## Table of Contents

1. [Deployment Issues](#deployment-issues)
2. [Configuration Problems](#configuration-problems)
3. [Runtime Errors](#runtime-errors)
4. [Performance Issues](#performance-issues)
5. [API Problems](#api-problems)
6. [Security Issues](#security-issues)
7. [Monitoring and Debugging](#monitoring-and-debugging)
8. [Getting Help](#getting-help)

## Deployment Issues

### CDK Bootstrap Failures

#### Error: Need to perform AWS CDK bootstrap

**Symptoms**:
```
Error: This stack uses assets, so the toolkit stack must be deployed to the environment
```

**Cause**: CDK environment not bootstrapped

**Solution**:
```bash
# Bootstrap CDK with specific account and region
cdk bootstrap aws://123456789012/us-east-1

# Or auto-detect account
cdk bootstrap
```

#### Error: Bootstrap stack version mismatch

**Symptoms**:
```
Error: The bootstrap stack version 'X' does not match the required version 'Y'
```

**Solution**:
```bash
# Update bootstrap stack
cdk bootstrap --force

# Or specify version
cdk bootstrap --bootstrap-stack-version-ssm-parameter /cdk-bootstrap/hnb659fds/version
```

### CloudFormation Stack Issues

#### Error: Stack already exists

**Symptoms**:
```
Error: Stack [AutoSpecAI-dev] already exists
```

**Solutions**:
```bash
# Option 1: Use force flag
./scripts/deploy.sh dev --force

# Option 2: Delete existing stack
aws cloudformation delete-stack --stack-name AutoSpecAI-dev

# Option 3: Update existing stack
cdk deploy --require-approval never
```

#### Error: Resource limit exceeded

**Symptoms**:
```
Error: Limit Exceeded (Service: AmazonCloudFormation; Status Code: 400)
```

**Solutions**:
1. Check AWS service limits in console
2. Request limit increases if needed
3. Optimize resource usage
4. Use nested stacks for complex deployments

### Lambda Deployment Issues

#### Error: Code storage limit exceeded

**Symptoms**:
```
Error: CodeStorageExceededException
```

**Solutions**:
```bash
# Clean up old function versions
aws lambda list-versions-by-function --function-name AutoSpecAI-dev-process
aws lambda delete-function --function-name AutoSpecAI-dev-process --qualifier 1

# Use Lambda layers for dependencies
# Optimize package size
```

#### Error: Function size too large

**Symptoms**:
```
Error: Unzipped size must be smaller than 262144000 bytes
```

**Solutions**:
1. Remove unnecessary files from package
2. Use Lambda layers for large dependencies
3. Optimize Python packages
4. Use container images for large functions

## Configuration Problems

### Environment Variables

#### Error: Required environment variable not set

**Symptoms**:
```
KeyError: 'CDK_STACK_NAME'
```

**Solutions**:
```bash
# Load environment configuration
source ./scripts/load-config.sh dev

# Verify variables are set
echo $CDK_STACK_NAME
echo $AWS_REGION

# Check configuration file
cat config/environments/dev.env
```

#### Error: Invalid configuration values

**Symptoms**:
- Functions failing with configuration errors
- Invalid AWS service calls

**Solutions**:
```bash
# Validate configuration
./scripts/validate-config.sh dev

# Check AWS credentials
aws sts get-caller-identity

# Verify region settings
aws configure list
```

### AWS Credentials

#### Error: Invalid AWS credentials

**Symptoms**:
```
Error: The security token included in the request is invalid
```

**Solutions**:
```bash
# Refresh AWS credentials
aws configure

# Check credential chain
aws sts get-caller-identity

# For temporary credentials
aws sts assume-role --role-arn arn:aws:iam::123456789012:role/MyRole --role-session-name MySession
```

#### Error: Permission denied

**Symptoms**:
```
Error: User is not authorized to perform action
```

**Solutions**:
1. Verify IAM permissions
2. Check resource-based policies
3. Review service-linked roles
4. Add required permissions to user/role

### Secrets Management

#### Error: Secret not found

**Symptoms**:
```
Error: ResourceNotFoundException: Secret not found
```

**Solutions**:
```bash
# Create missing secret
aws secretsmanager create-secret \
  --name "autospec-ai/dev/jwt-secret" \
  --secret-string "$(openssl rand -base64 32)"

# Verify secret exists
aws secretsmanager describe-secret --secret-id "autospec-ai/dev/jwt-secret"

# Check region
aws secretsmanager list-secrets --region us-east-1
```

## Runtime Errors

### Lambda Function Errors

#### Error: Function timeout

**Symptoms**:
```
Task timed out after 300.00 seconds
```

**Solutions**:
```bash
# Increase timeout in configuration
export LAMBDA_TIMEOUT=900  # 15 minutes

# Optimize function performance
# Check for infinite loops
# Review external API calls
```

#### Error: Out of memory

**Symptoms**:
```
Runtime exited with error: signal: killed
```

**Solutions**:
```bash
# Increase memory allocation
export LAMBDA_MEMORY_SIZE=2048

# Optimize memory usage
# Profile memory consumption
# Use streaming for large files
```

#### Error: Import module error

**Symptoms**:
```
Unable to import module 'handler': No module named 'module_name'
```

**Solutions**:
1. Check requirements.txt includes all dependencies
2. Verify package installation in deployment
3. Check Python path in Lambda
4. Use Lambda layers for common dependencies

### DynamoDB Errors

#### Error: Provisioned throughput exceeded

**Symptoms**:
```
ProvisionedThroughputExceededException
```

**Solutions**:
```bash
# Enable auto-scaling
aws application-autoscaling register-scalable-target \
  --service-namespace dynamodb \
  --scalable-dimension dynamodb:table:WriteCapacityUnits \
  --resource-id table/AutoSpecAI-Documents \
  --min-capacity 5 \
  --max-capacity 40

# Or switch to on-demand billing
aws dynamodb modify-table \
  --table-name AutoSpecAI-Documents \
  --billing-mode PAY_PER_REQUEST
```

#### Error: Item size too large

**Symptoms**:
```
ValidationException: Item size has exceeded 400KB
```

**Solutions**:
1. Store large data in S3, reference in DynamoDB
2. Compress data before storage
3. Split large items into multiple records
4. Use GSI for large attributes

### Bedrock API Errors

#### Error: Model access denied

**Symptoms**:
```
AccessDeniedException: Your request was denied access to the model
```

**Solutions**:
1. Request model access in Bedrock console
2. Wait for approval (usually immediate)
3. Check region availability
4. Verify IAM permissions for Bedrock

#### Error: Throttling errors

**Symptoms**:
```
ThrottlingException: Rate exceeded
```

**Solutions**:
1. Implement exponential backoff
2. Add retry logic
3. Request rate limit increase
4. Optimize prompt length

## Performance Issues

### Slow Processing

#### Issue: Documents take too long to process

**Diagnosis**:
```bash
# Check CloudWatch logs
aws logs tail "/aws/lambda/AutoSpecAI-dev-process" --since 1h

# Check X-Ray traces
aws xray get-trace-summaries \
  --time-range-type TimeRangeByStartTime \
  --start-time $(date -d '1 hour ago' -u +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S)
```

**Solutions**:
1. Optimize Lambda memory allocation
2. Implement connection pooling
3. Cache frequently accessed data
4. Parallelize processing where possible

### High Latency

#### Issue: API responses are slow

**Diagnosis**:
```bash
# Test API latency
curl -w "%{time_total}" -o /dev/null -s "$API_URL/health"

# Check API Gateway metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApiGateway \
  --metric-name Latency \
  --dimensions Name=ApiName,Value=AutoSpecAI-dev \
  --start-time $(date -d '1 hour ago' -u +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average
```

**Solutions**:
1. Enable API Gateway caching
2. Optimize Lambda cold starts
3. Use provisioned concurrency
4. Implement CDN for static assets

## API Problems

### Authentication Issues

#### Error: Invalid API key

**Symptoms**:
```json
{
  "error": {
    "code": "AUTHENTICATION_ERROR",
    "message": "Invalid API key"
  }
}
```

**Solutions**:
```bash
# Generate new API key
aws apigateway create-api-key \
  --name "AutoSpecAI-dev-key" \
  --description "API key for AutoSpecAI development"

# Verify API key is active
aws apigateway get-api-key --api-key YOUR_API_KEY_ID --include-value
```

#### Error: JWT token expired

**Symptoms**:
```json
{
  "error": {
    "code": "AUTHENTICATION_ERROR",
    "message": "Token has expired"
  }
}
```

**Solutions**:
1. Refresh JWT token
2. Check token expiration time
3. Implement automatic token refresh
4. Verify system clock accuracy

### Rate Limiting

#### Error: Rate limit exceeded

**Symptoms**:
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Try again in 60 seconds."
  }
}
```

**Solutions**:
1. Implement exponential backoff
2. Reduce request frequency
3. Request rate limit increase
4. Use multiple API keys if needed

### CORS Issues

#### Error: CORS policy blocks request

**Symptoms**:
```
Access to fetch at 'https://api.autospec.ai' from origin 'https://app.autospec.ai' has been blocked by CORS policy
```

**Solutions**:
```bash
# Update CORS configuration
export CORS_ALLOWED_ORIGINS="https://app.autospec.ai,http://localhost:3000"

# Redeploy API Gateway
./scripts/deploy.sh dev
```

## Security Issues

### SSL/TLS Problems

#### Error: SSL certificate verification failed

**Symptoms**:
```
SSL: CERTIFICATE_VERIFY_FAILED
```

**Solutions**:
1. Check certificate validity
2. Update certificate if expired
3. Verify certificate chain
4. Check system trust store

### IAM Permission Issues

#### Error: Access denied for service

**Symptoms**:
```
AccessDenied: User is not authorized to perform action
```

**Solutions**:
```bash
# Check current permissions
aws iam get-user-policy --user-name autospec-ai-deployer --policy-name AutoSpecAIPolicy

# Simulate policy
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::123456789012:user/autospec-ai-deployer \
  --action-names s3:GetObject \
  --resource-arns arn:aws:s3:::autospec-ai-dev-documents/*
```

## Monitoring and Debugging

### CloudWatch Logs

#### Access function logs

```bash
# List log groups
aws logs describe-log-groups \
  --log-group-name-prefix "/aws/lambda/AutoSpecAI-dev"

# Tail specific function logs
aws logs tail "/aws/lambda/AutoSpecAI-dev-process" \
  --follow \
  --format short

# Search logs
aws logs filter-log-events \
  --log-group-name "/aws/lambda/AutoSpecAI-dev-process" \
  --filter-pattern "ERROR" \
  --start-time $(date -d '1 hour ago' +%s)000
```

### X-Ray Tracing

#### Analyze traces

```bash
# Get trace summaries
aws xray get-trace-summaries \
  --time-range-type TimeRangeByStartTime \
  --start-time $(date -d '1 hour ago' -u +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --filter-expression "service(\"AutoSpecAI-dev-process\")"

# Get specific trace
aws xray batch-get-traces --trace-ids TRACE_ID
```

### Custom Metrics

#### Check application metrics

```bash
# Get custom metrics
aws cloudwatch get-metric-statistics \
  --namespace AutoSpecAI \
  --metric-name DocumentsProcessed \
  --dimensions Name=Environment,Value=dev \
  --start-time $(date -d '1 hour ago' -u +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum
```

### Health Checks

#### Automated health monitoring

```bash
# Health check script
#!/bin/bash
API_URL="https://api.autospec.ai"

# Check API health
if curl -f -s "$API_URL/v1/health" > /dev/null; then
  echo "API is healthy"
else
  echo "API health check failed"
  exit 1
fi

# Check database
if aws dynamodb describe-table --table-name AutoSpecAI-Documents > /dev/null 2>&1; then
  echo "Database is accessible"
else
  echo "Database check failed"
  exit 1
fi
```

## Getting Help

### Diagnostic Information

When seeking help, provide:

1. **Environment**: dev/staging/prod
2. **Error messages**: Complete error text
3. **Request ID**: From API responses
4. **Timestamps**: When issue occurred
5. **Steps to reproduce**: What actions led to the issue

### Support Channels

#### Internal Support

```bash
# Generate diagnostic report
./scripts/diagnostic-report.sh dev > diagnostic-report.txt

# Check system status
./scripts/system-status.sh dev

# Validate deployment
./scripts/validate-deployment.sh dev
```

#### AWS Support

For AWS-related issues:

1. **AWS Support Center**: Submit support case
2. **AWS Forums**: Community support
3. **AWS Documentation**: Service-specific guides
4. **AWS Status Page**: Service status updates

### Community Resources

- **GitHub Issues**: Report bugs and feature requests
- **Stack Overflow**: Tag questions with `autospec-ai`
- **Discord Community**: Real-time chat support
- **Documentation Wiki**: Community-maintained guides

### Best Practices for Troubleshooting

1. **Start with logs**: Always check CloudWatch logs first
2. **Use correlation IDs**: Track requests across services
3. **Monitor metrics**: Watch for patterns and anomalies
4. **Test incrementally**: Isolate issues by testing components
5. **Document solutions**: Keep record of fixes for future reference