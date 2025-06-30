#!/bin/bash

# AutoSpec.AI Deployment Validation Script

set -e

ENVIRONMENT=${1:-"dev"}
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Starting deployment validation for environment: $ENVIRONMENT"

# Load environment configuration
CONFIG_FILE="$PROJECT_ROOT/config/environments/$ENVIRONMENT.env"
if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
    echo "Loaded configuration for $ENVIRONMENT environment"
else
    echo "Configuration file not found: $CONFIG_FILE"
    exit 1
fi

# Check CloudFormation stack
if aws cloudformation describe-stacks --stack-name "$CDK_STACK_NAME" --region "$AWS_REGION" > /dev/null 2>&1; then
    echo "CloudFormation stack exists: $CDK_STACK_NAME"
else
    echo "CloudFormation stack not found: $CDK_STACK_NAME"
    exit 1
fi

echo "Deployment validation completed successfully!"