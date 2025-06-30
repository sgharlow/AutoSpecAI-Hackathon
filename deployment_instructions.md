# AutoSpec.AI Deployment Instructions

This document provides comprehensive instructions for deploying AutoSpec.AI to AWS using the provided deployment scripts and CI/CD pipeline.

## Prerequisites

### Required Tools

1. **AWS CLI v2** - [Installation Guide](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html)
2. **AWS CDK v2** - Install with `npm install -g aws-cdk`
3. **Node.js 18+** - [Download](https://nodejs.org/)
4. **Python 3.9+** - [Download](https://python.org/)
5. **Git** - [Installation Guide](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)

### AWS Account Setup

1. **AWS Account** with appropriate permissions
2. **IAM User** with required policies
3. **Configure AWS CLI**: `aws configure`

## Environment Configuration

The project supports three environments: `dev`, `staging`, and `prod`. Each environment has its own configuration file in `config/environments/`.

## Manual Deployment

### Quick Start Deployment

```bash
# Make scripts executable
chmod +x scripts/*.sh

# Deploy to development
./scripts/deploy.sh dev
```

### Advanced Options

```bash
# Deploy with options
./scripts/deploy.sh <environment> [--skip-tests] [--force] [--region REGION]
```

## CI/CD Pipeline Deployment

Configure GitHub Secrets:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`

Automatic deployments:
- **Develop branch** → Development environment
- **Main branch** → Staging environment

## Post-Deployment Validation

```bash
# Validate deployment
./scripts/validate-deployment.sh <environment>

# Run integration tests
./scripts/integration-tests.sh <api-url> <environment>
```

## Environment Management

```bash
# Load environment configuration
source ./scripts/load-config.sh <environment>
```

## Rollback Procedures

```bash
# Rollback to previous version
./scripts/rollback.sh <environment>
```

For detailed instructions and troubleshooting, see the full documentation in the repository.