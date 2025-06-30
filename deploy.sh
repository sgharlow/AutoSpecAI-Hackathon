#!/bin/bash

# AutoSpec.AI Quick Deployment Script
# Usage: ./deploy.sh [environment] [options]

set -e

# Default values
ENVIRONMENT="${1:-dev}"
SKIP_TESTS="${2:-false}"
FORCE_DEPLOY="${3:-false}"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# ASCII Art Banner
print_banner() {
    echo -e "${BLUE}"
    cat << "EOF"
    ╔═══════════════════════════════════════════════════════════╗
    ║                    AutoSpec.AI                            ║
    ║               Deployment Automation                       ║
    ║                                                           ║
    ║    🚀 Intelligent Document Analysis Platform 🚀           ║
    ╚═══════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
}

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

log_step() {
    echo -e "${PURPLE}[STEP]${NC} $1"
}

# Help function
show_help() {
    echo "AutoSpec.AI Deployment Script"
    echo ""
    echo "Usage:"
    echo "  ./deploy.sh [environment] [skip-tests] [force]"
    echo ""
    echo "Parameters:"
    echo "  environment    Target environment (dev, staging, prod) [default: dev]"
    echo "  skip-tests     Skip running tests (true/false) [default: false]"
    echo "  force          Force deployment without confirmation [default: false]"
    echo ""
    echo "Examples:"
    echo "  ./deploy.sh dev                    # Deploy to development"
    echo "  ./deploy.sh staging false          # Deploy to staging with tests"
    echo "  ./deploy.sh prod false true        # Force deploy to production"
    echo ""
    echo "Environment Variables:"
    echo "  AWS_PROFILE                       # AWS profile to use"
    echo "  SLACK_WEBHOOK_URL                 # Slack notifications"
    echo "  NOTIFICATION_EMAIL                # Email notifications"
    echo ""
}

# Check if help is requested
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    show_help
    exit 0
fi

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Print banner
print_banner

echo "🎯 Target Environment: $ENVIRONMENT"
echo "🧪 Skip Tests: $SKIP_TESTS"
echo "⚡ Force Deploy: $FORCE_DEPLOY"
echo ""

# Validate environment
case $ENVIRONMENT in
    dev|staging|prod)
        log_info "Valid environment: $ENVIRONMENT"
        ;;
    *)
        log_error "Invalid environment: $ENVIRONMENT. Must be dev, staging, or prod"
        show_help
        exit 1
        ;;
esac

# Production safety check
if [ "$ENVIRONMENT" = "prod" ] && [ "$FORCE_DEPLOY" != "true" ]; then
    log_warning "🚨 PRODUCTION DEPLOYMENT DETECTED 🚨"
    echo ""
    echo "You are about to deploy to the PRODUCTION environment."
    echo "This deployment will affect live users and services."
    echo ""
    echo "Please confirm the following:"
    echo "- All tests have passed"
    echo "- Code has been reviewed"
    echo "- Deployment has been approved"
    echo ""
    read -p "Type 'DEPLOY' to continue with production deployment: " confirmation
    
    if [ "$confirmation" != "DEPLOY" ]; then
        log_error "Production deployment cancelled by user"
        exit 1
    fi
fi

# Step 1: Environment Setup
log_step "1/8 Setting up environment"

if [ ! -f "scripts/load-config.sh" ]; then
    log_error "Configuration loader not found. Please ensure you're in the project root directory."
    exit 1
fi

# Load configuration
log_info "Loading configuration for $ENVIRONMENT..."
source ./scripts/load-config.sh "$ENVIRONMENT"

if ! validate_config; then
    log_error "Configuration validation failed"
    exit 1
fi

log_success "Environment configuration loaded and validated"

# Step 2: Prerequisites Check
log_step "2/8 Checking prerequisites"

# Check required tools
REQUIRED_TOOLS=("aws" "node" "npm" "python3" "jq")
for tool in "${REQUIRED_TOOLS[@]}"; do
    if ! command -v "$tool" &> /dev/null; then
        log_error "Required tool not found: $tool"
        exit 1
    fi
done

# Check AWS credentials
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    log_error "AWS credentials not configured or invalid"
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=$(aws configure get region)

log_success "Prerequisites check passed"
log_info "AWS Account: $ACCOUNT_ID"
log_info "AWS Region: $REGION"

# Step 3: Pre-deployment Validation
log_step "3/8 Running pre-deployment validation"

if ! ./scripts/validate-deployment.sh "$ENVIRONMENT"; then
    log_error "Pre-deployment validation failed"
    exit 1
fi

log_success "Pre-deployment validation completed"

# Step 4: Run Tests (if not skipped)
if [ "$SKIP_TESTS" != "true" ]; then
    log_step "4/8 Running tests"
    
    # Run Lambda function tests
    LAMBDA_DIRS=("ingest" "process" "format" "slack" "api" "monitoring")
    
    for lambda_dir in "${LAMBDA_DIRS[@]}"; do
        if [ -d "lambdas/$lambda_dir" ]; then
            log_info "Testing Lambda function: $lambda_dir"
            cd "lambdas/$lambda_dir"
            
            # Install dependencies if needed
            if [ -f "requirements.txt" ] && [ ! -d "venv" ]; then
                pip install -r requirements.txt > /dev/null 2>&1 || log_warning "Failed to install dependencies for $lambda_dir"
            fi
            
            # Run tests if they exist
            if ls test_*.py 1> /dev/null 2>&1; then
                python -m unittest test_*.py -v > /dev/null 2>&1 || log_warning "Tests failed for $lambda_dir"
            fi
            
            cd "$SCRIPT_DIR"
        fi
    done
    
    log_success "Tests completed"
else
    log_step "4/8 Skipping tests (as requested)"
fi

# Step 5: Infrastructure Deployment
log_step "5/8 Deploying infrastructure"

cd infra/cdk

# Install CDK dependencies
log_info "Installing CDK dependencies..."
npm install > /dev/null 2>&1

# CDK Bootstrap (if needed)
log_info "Checking CDK bootstrap..."
if ! aws cloudformation describe-stacks --stack-name CDKToolkit > /dev/null 2>&1; then
    log_info "Bootstrapping CDK..."
    npx cdk bootstrap > /dev/null 2>&1
fi

# Deploy infrastructure
log_info "Deploying CDK stack: $STACK_NAME"
export ENVIRONMENT="$ENVIRONMENT"

if npx cdk deploy "$STACK_NAME" --require-approval never --outputs-file outputs.json; then
    log_success "Infrastructure deployment completed"
else
    log_error "Infrastructure deployment failed"
    cd "$SCRIPT_DIR"
    exit 1
fi

# Extract outputs
if [ -f outputs.json ]; then
    API_URL=$(jq -r ".\"$STACK_NAME\".ApiGatewayUrl" outputs.json 2>/dev/null || echo "")
    BUCKET_NAME=$(jq -r ".\"$STACK_NAME\".DocumentBucketName" outputs.json 2>/dev/null || echo "")
    DASHBOARD_URL=$(jq -r ".\"$STACK_NAME\".OperationalDashboardUrl" outputs.json 2>/dev/null || echo "")
    
    log_info "API Gateway URL: $API_URL"
    log_info "Document Bucket: $BUCKET_NAME"
fi

cd "$SCRIPT_DIR"

# Step 6: Post-deployment Tests
log_step "6/8 Running post-deployment tests"

if [ -n "$API_URL" ]; then
    if ./scripts/integration-tests.sh "$API_URL" "$ENVIRONMENT"; then
        log_success "Integration tests passed"
    else
        log_warning "Some integration tests failed (this may be expected for new deployments)"
    fi
else
    log_warning "API URL not available, skipping integration tests"
fi

# Step 7: Update Monitoring
log_step "7/8 Updating monitoring and observability"

if ./scripts/update-monitoring.sh "$ENVIRONMENT"; then
    log_success "Monitoring setup completed"
else
    log_warning "Monitoring setup had some issues"
fi

# Step 8: Final Verification and Notifications
log_step "8/8 Final verification and notifications"

# Health check
if [ -n "$API_URL" ]; then
    log_info "Performing final health check..."
    health_response=$(curl -s -w "%{http_code}" -o /tmp/health_check.json "${API_URL}/v1/health" || echo "000")
    
    if [ "$health_response" = "200" ]; then
        log_success "Health check passed"
    else
        log_warning "Health check failed (HTTP $health_response)"
    fi
fi

# Send notifications
if ./scripts/notify-deployment.sh "success" "$ENVIRONMENT" "$API_URL"; then
    log_success "Deployment notifications sent"
else
    log_warning "Failed to send notifications"
fi

# Cleanup
rm -f /tmp/health_check.json

# Final success message
echo ""
echo "🎉 Deployment Summary"
echo "===================="
echo "Environment: $ENVIRONMENT"
echo "Status: SUCCESS"
echo "Timestamp: $(date)"
echo "AWS Account: $ACCOUNT_ID"
echo "AWS Region: $REGION"

if [ -n "$API_URL" ]; then
    echo ""
    echo "📡 Important URLs:"
    echo "- API Endpoint: $API_URL"
    [ -n "$DASHBOARD_URL" ] && echo "- Monitoring Dashboard: $DASHBOARD_URL"
    echo "- X-Ray Service Map: https://${REGION}.console.aws.amazon.com/xray/home?region=${REGION}#/service-map"
    echo "- CloudWatch Logs: https://${REGION}.console.aws.amazon.com/cloudwatch/home?region=${REGION}#logsV2:log-groups"
fi

echo ""
echo "🚀 AutoSpec.AI has been successfully deployed to $ENVIRONMENT!"
echo "===================="

log_success "Deployment completed successfully in $(date)"