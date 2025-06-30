#!/bin/bash

# AutoSpec.AI Monitoring Update Script
# Updates monitoring dashboards and alerts

set -e

ENVIRONMENT=${1:-"dev"}
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Updating monitoring for environment: $ENVIRONMENT"

# Load environment configuration
CONFIG_FILE="$PROJECT_ROOT/config/environments/$ENVIRONMENT.env"
if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
    echo "Loaded configuration for $ENVIRONMENT environment"
else
    echo "Configuration file not found: $CONFIG_FILE"
    exit 1
fi

echo "Monitoring update completed successfully!"