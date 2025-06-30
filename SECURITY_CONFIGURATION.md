# Security Configuration Guide

This document explains how to properly configure API keys and other sensitive information for AutoSpecAI.

## ⚠️ Important Security Notice

All hardcoded API keys and secrets have been removed from the codebase. You must now configure these values using environment variables or configuration files that are not tracked in git.

## Configuration Methods

### 1. Environment Variables (Recommended)

Set these environment variables before running any scripts or applications:

```bash
# API Configuration
export AUTOSPEC_API_URL="https://your-api-gateway-url.execute-api.us-east-1.amazonaws.com/prod"
export AUTOSPEC_API_KEY="your-api-key-here"

# Multiple API keys (if needed)
export AUTOSPEC_API_KEY_1="your-first-api-key"
export AUTOSPEC_API_KEY_2="your-second-api-key"
export AUTOSPEC_API_KEY_3="your-third-api-key"

# Third-party integrations
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
export JIRA_API_TOKEN="your-jira-api-token"
export GITHUB_TOKEN="ghp_your-github-token"
# ... etc (see .env.example for full list)
```

### 2. Configuration Files

#### Backend Configuration
1. Copy `.env.example` to `.env`
2. Fill in your actual values
3. The `.env` file is gitignored and won't be committed

#### Frontend Configuration
1. Copy `frontend/.env.example` to `frontend/.env.local`
2. Fill in your actual values
3. For production, set these in your deployment environment

#### Web UI Configuration
1. Copy `web-ui/config.js.example` to `web-ui/config.js`
2. Replace placeholder values with your actual configuration
3. The `config.js` file is gitignored

### 3. AWS Secrets Manager (Production)

For production deployments, use AWS Secrets Manager:

```bash
# Store API keys in Secrets Manager
aws secretsmanager create-secret \
  --name autospec-api-keys \
  --secret-string '{"api_keys":["key1","key2","key3"]}'

# Lambda functions can retrieve secrets at runtime
```

## Testing Your Configuration

### Shell Scripts
```bash
# Test scripts now require environment variables
export AUTOSPEC_API_KEY="your-api-key"
./test-upload.sh my-document.pdf
```

### Python Scripts
```bash
# Python scripts read from environment
export AUTOSPEC_API_KEY="your-api-key"
python3 scripts/test-dual-upload-system.py
```

### PowerShell Scripts
```powershell
# Set environment variable
$env:AUTOSPEC_API_KEY = "your-api-key"
.\scripts\test-production-system.ps1
```

### Frontend Development
```bash
cd frontend
# Create .env.local with your API key
npm start
```

## Security Best Practices

1. **Never commit real API keys** to version control
2. **Rotate keys regularly** - All previously exposed keys should be invalidated
3. **Use different keys** for development, staging, and production
4. **Limit key permissions** to only what's necessary
5. **Monitor key usage** through AWS CloudWatch

## Files That Need Configuration

- `.env` - Main environment configuration
- `frontend/.env.local` - Frontend development configuration
- `web-ui/config.js` - Web UI configuration
- `config/enterprise/*.json` - Enterprise integration configs (use .example files as templates)

## Troubleshooting

If you see errors like:
- "API key not configured!"
- "YOUR_API_KEY_HERE"
- "Environment variable not set"

This means you need to set the appropriate environment variables or create the necessary configuration files as described above.