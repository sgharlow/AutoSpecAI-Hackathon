#!/bin/bash

# AutoSpec.AI Configuration Loader
# Loads environment-specific configuration

ENVIRONMENT=${1:-"dev"}
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

CONFIG_FILE="$PROJECT_ROOT/config/environments/$ENVIRONMENT.env"

if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
    echo "Configuration loaded for environment: $ENVIRONMENT"
    echo "Stack Name: $CDK_STACK_NAME"
    echo "Region: $AWS_REGION"
else
    echo "Configuration file not found: $CONFIG_FILE"
    exit 1
fi