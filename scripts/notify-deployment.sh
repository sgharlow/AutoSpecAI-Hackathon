#!/bin/bash

# AutoSpec.AI Deployment Notification Script
# Usage: ./notify-deployment.sh <status> <environment> <api-url>

set -e

STATUS=${1}
ENVIRONMENT=${2}
API_URL=${3}

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Get deployment information
get_deployment_info() {
    TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "unknown")
    REGION=$(aws configure get region 2>/dev/null || echo "unknown")
    COMMIT_SHA=${GITHUB_SHA:-$(git rev-parse HEAD 2>/dev/null || echo "unknown")}
    COMMIT_MESSAGE=${GITHUB_EVENT_HEAD_COMMIT_MESSAGE:-$(git log -1 --pretty=%B 2>/dev/null || echo "Manual deployment")}
    ACTOR=${GITHUB_ACTOR:-$(whoami 2>/dev/null || echo "unknown")}
    
    # Get stack outputs if available
    STACK_NAME="AutoSpecAIStack-$ENVIRONMENT"
    if aws cloudformation describe-stacks --stack-name "$STACK_NAME" > /dev/null 2>&1; then
        STACK_STATUS=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --query 'Stacks[0].StackStatus' --output text)
        
        # Try to get outputs
        BUCKET_NAME=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --query 'Stacks[0].Outputs[?OutputKey==`DocumentBucketName`].OutputValue' --output text 2>/dev/null || echo "unknown")
        DASHBOARD_URL=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --query 'Stacks[0].Outputs[?OutputKey==`OperationalDashboardUrl`].OutputValue' --output text 2>/dev/null || echo "unknown")
    else
        STACK_STATUS="unknown"
        BUCKET_NAME="unknown"
        DASHBOARD_URL="unknown"
    fi
}

# Send Slack notification
send_slack_notification() {
    if [ -z "$SLACK_WEBHOOK_URL" ]; then
        log_info "No Slack webhook URL configured, skipping Slack notification"
        return 0
    fi
    
    log_info "Sending Slack notification..."
    
    # Set colors and emojis based on status
    case $STATUS in
        success)
            COLOR="good"
            EMOJI="✅"
            ;;
        failure)
            COLOR="danger"
            EMOJI="❌"
            ;;
        cancelled)
            COLOR="warning"
            EMOJI="⚠️"
            ;;
        *)
            COLOR="#36a64f"
            EMOJI="ℹ️"
            ;;
    esac
    
    # Create Slack payload
    local payload=$(cat << EOF
{
  "username": "AutoSpec.AI Deploy Bot",
  "icon_emoji": ":rocket:",
  "attachments": [
    {
      "color": "$COLOR",
      "title": "$EMOJI AutoSpec.AI Deployment $STATUS",
      "fields": [
        {
          "title": "Environment",
          "value": "$ENVIRONMENT",
          "short": true
        },
        {
          "title": "Status",
          "value": "$STATUS",
          "short": true
        },
        {
          "title": "Deployed By",
          "value": "$ACTOR",
          "short": true
        },
        {
          "title": "Timestamp",
          "value": "$TIMESTAMP",
          "short": true
        },
        {
          "title": "Commit",
          "value": "\`${COMMIT_SHA:0:8}\` - $COMMIT_MESSAGE",
          "short": false
        },
        {
          "title": "AWS Account",
          "value": "$ACCOUNT_ID",
          "short": true
        },
        {
          "title": "Region",
          "value": "$REGION",
          "short": true
        }
      ],
      "actions": []
    }
  ]
}
EOF
)
    
    # Add success-specific fields
    if [ "$STATUS" = "success" ]; then
        if [ "$API_URL" != "unknown" ] && [ -n "$API_URL" ]; then
            payload=$(echo "$payload" | jq --arg url "$API_URL" '.attachments[0].actions += [{"type": "button", "text": "API Endpoint", "url": $url}]')
        fi
        
        if [ "$DASHBOARD_URL" != "unknown" ] && [ -n "$DASHBOARD_URL" ]; then
            payload=$(echo "$payload" | jq --arg url "$DASHBOARD_URL" '.attachments[0].actions += [{"type": "button", "text": "Monitoring Dashboard", "url": $url}]')
        fi
    fi
    
    # Send to Slack
    if curl -s -X POST -H 'Content-type: application/json' --data "$payload" "$SLACK_WEBHOOK_URL" > /dev/null; then
        log_success "Slack notification sent successfully"
    else
        log_error "Failed to send Slack notification"
    fi
}

# Send email notification
send_email_notification() {
    if [ -z "$NOTIFICATION_EMAIL" ]; then
        log_info "No notification email configured, skipping email notification"
        return 0
    fi
    
    log_info "Sending email notification..."
    
    # Set subject based on status
    case $STATUS in
        success)
            SUBJECT="✅ AutoSpec.AI Deployment Successful - $ENVIRONMENT"
            ;;
        failure)
            SUBJECT="❌ AutoSpec.AI Deployment Failed - $ENVIRONMENT"
            ;;
        cancelled)
            SUBJECT="⚠️ AutoSpec.AI Deployment Cancelled - $ENVIRONMENT"
            ;;
        *)
            SUBJECT="ℹ️ AutoSpec.AI Deployment Update - $ENVIRONMENT"
            ;;
    esac
    
    # Create email body
    local email_body=$(cat << EOF
AutoSpec.AI Deployment Notification

Status: $STATUS
Environment: $ENVIRONMENT
Timestamp: $TIMESTAMP
Deployed By: $ACTOR
Commit: ${COMMIT_SHA:0:8} - $COMMIT_MESSAGE

AWS Details:
- Account: $ACCOUNT_ID
- Region: $REGION
- Stack Status: $STACK_STATUS

Resources:
EOF
)
    
    if [ "$API_URL" != "unknown" ] && [ -n "$API_URL" ]; then
        email_body="$email_body
- API Endpoint: $API_URL"
    fi
    
    if [ "$DASHBOARD_URL" != "unknown" ] && [ -n "$DASHBOARD_URL" ]; then
        email_body="$email_body
- Monitoring Dashboard: $DASHBOARD_URL"
    fi
    
    if [ "$BUCKET_NAME" != "unknown" ]; then
        email_body="$email_body
- Document Bucket: $BUCKET_NAME"
    fi
    
    email_body="$email_body

This is an automated notification from the AutoSpec.AI deployment pipeline.
"
    
    # Send email using AWS SES
    if [ "$REGION" != "unknown" ]; then
        aws ses send-email \
            --source "autospec-deployment@example.com" \
            --destination "ToAddresses=$NOTIFICATION_EMAIL" \
            --message "Subject={Data=\"$SUBJECT\"},Body={Text={Data=\"$email_body\"}}" \
            --region "$REGION" > /dev/null 2>&1 || log_warning "Failed to send email notification via SES"
    fi
}

# Create deployment record
create_deployment_record() {
    log_info "Creating deployment record..."
    
    local record_file="deployment-record-$ENVIRONMENT-$(date +%Y%m%d-%H%M%S).json"
    
    cat > "$record_file" << EOF
{
  "deployment": {
    "timestamp": "$TIMESTAMP",
    "status": "$STATUS",
    "environment": "$ENVIRONMENT",
    "aws_account": "$ACCOUNT_ID",
    "aws_region": "$REGION",
    "stack_name": "$STACK_NAME",
    "stack_status": "$STACK_STATUS",
    "commit_sha": "$COMMIT_SHA",
    "commit_message": "$COMMIT_MESSAGE",
    "deployed_by": "$ACTOR",
    "api_url": "$API_URL",
    "bucket_name": "$BUCKET_NAME",
    "dashboard_url": "$DASHBOARD_URL"
  },
  "github_context": {
    "workflow": "${GITHUB_WORKFLOW:-manual}",
    "run_id": "${GITHUB_RUN_ID:-unknown}",
    "run_number": "${GITHUB_RUN_NUMBER:-unknown}",
    "repository": "${GITHUB_REPOSITORY:-unknown}",
    "ref": "${GITHUB_REF:-unknown}"
  }
}
EOF
    
    log_success "Deployment record created: $record_file"
}

# Update deployment status in DynamoDB (if table exists)
update_deployment_status() {
    local table_name="autospec-ai-deployments"
    
    # Check if deployments table exists
    if aws dynamodb describe-table --table-name "$table_name" > /dev/null 2>&1; then
        log_info "Updating deployment status in DynamoDB..."
        
        aws dynamodb put-item \
            --table-name "$table_name" \
            --item '{
                "DeploymentId": {"S": "'$(uuidgen)'"},
                "Timestamp": {"S": "'$TIMESTAMP'"},
                "Environment": {"S": "'$ENVIRONMENT'"},
                "Status": {"S": "'$STATUS'"},
                "CommitSha": {"S": "'$COMMIT_SHA'"},
                "DeployedBy": {"S": "'$ACTOR'"},
                "ApiUrl": {"S": "'$API_URL'"},
                "StackStatus": {"S": "'$STACK_STATUS'"}
            }' > /dev/null 2>&1 || log_warning "Failed to update deployment status in DynamoDB"
    else
        log_info "Deployment tracking table not found, skipping DynamoDB update"
    fi
}

# Generate deployment summary
generate_deployment_summary() {
    echo ""
    echo "🚀 AutoSpec.AI Deployment Summary"
    echo "=================================="
    echo "Status: $STATUS"
    echo "Environment: $ENVIRONMENT"
    echo "Timestamp: $TIMESTAMP"
    echo "Deployed By: $ACTOR"
    echo "Commit: ${COMMIT_SHA:0:8}"
    echo "AWS Account: $ACCOUNT_ID"
    echo "Region: $REGION"
    
    if [ "$STATUS" = "success" ]; then
        echo ""
        echo "🔗 Important Links:"
        [ "$API_URL" != "unknown" ] && [ -n "$API_URL" ] && echo "- API Endpoint: $API_URL"
        [ "$DASHBOARD_URL" != "unknown" ] && [ -n "$DASHBOARD_URL" ] && echo "- Monitoring: $DASHBOARD_URL"
        echo "- X-Ray: https://${REGION}.console.aws.amazon.com/xray/home?region=${REGION}#/service-map"
        echo "- CloudWatch: https://${REGION}.console.aws.amazon.com/cloudwatch/home?region=${REGION}"
    fi
    echo "=================================="
}

# Main function
main() {
    log_info "Starting deployment notification process..."
    
    get_deployment_info
    send_slack_notification
    send_email_notification
    create_deployment_record
    update_deployment_status
    generate_deployment_summary
    
    log_success "Deployment notification process completed"
}

# Run main function
main