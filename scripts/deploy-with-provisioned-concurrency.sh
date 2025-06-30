#!/bin/bash

# AutoSpec.AI Enhanced Deployment Script with Provisioned Concurrency
# This script handles deployment of the optimized stack with provisioned concurrency management

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CDK_DIR="$PROJECT_ROOT/infra/cdk"

# Default values
ENVIRONMENT="dev"
SKIP_TESTS=false
FORCE_DEPLOY=false
ENABLE_PROVISIONED_CONCURRENCY=true
MONITOR_DEPLOYMENT=true
DRY_RUN=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# Help function
show_help() {
    cat << EOF
AutoSpec.AI Enhanced Deployment Script with Provisioned Concurrency

Usage: $0 [OPTIONS] ENVIRONMENT

ENVIRONMENTS:
    dev         Development environment
    staging     Staging environment  
    prod        Production environment

OPTIONS:
    -h, --help                    Show this help message
    --skip-tests                  Skip running tests before deployment
    --force                       Force deployment even if tests fail
    --disable-provisioned-concurrency  Disable provisioned concurrency optimization
    --no-monitoring               Skip deployment monitoring
    --dry-run                     Show what would be deployed without actually deploying

EXAMPLES:
    $0 dev
    $0 staging --skip-tests
    $0 prod --force --no-monitoring
    $0 dev --dry-run

EOF
}

# Parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            --skip-tests)
                SKIP_TESTS=true
                shift
                ;;
            --force)
                FORCE_DEPLOY=true
                shift
                ;;
            --disable-provisioned-concurrency)
                ENABLE_PROVISIONED_CONCURRENCY=false
                shift
                ;;
            --no-monitoring)
                MONITOR_DEPLOYMENT=false
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            dev|staging|prod)
                ENVIRONMENT=$1
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# Validate prerequisites
validate_prerequisites() {
    log_info "Validating prerequisites..."
    
    # Check if AWS CLI is configured
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS CLI not configured or credentials invalid"
        exit 1
    fi
    
    # Check if CDK is installed
    if ! command -v cdk &> /dev/null; then
        log_error "AWS CDK not installed. Please install with: npm install -g aws-cdk"
        exit 1
    fi
    
    # Check if Python dependencies are available
    if ! python3 -c "import boto3" &> /dev/null; then
        log_error "boto3 not available. Please install with: pip install boto3"
        exit 1
    fi
    
    # Check CDK version
    CDK_VERSION=$(cdk --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
    log_info "Using AWS CDK version: $CDK_VERSION"
    
    # Verify environment configuration exists
    CONFIG_FILE="$PROJECT_ROOT/config/environments/$ENVIRONMENT.json"
    if [[ ! -f "$CONFIG_FILE" ]]; then
        log_error "Configuration file not found: $CONFIG_FILE"
        exit 1
    fi
    
    log_success "Prerequisites validated"
}

# Run tests
run_tests() {
    if [[ "$SKIP_TESTS" == "true" ]]; then
        log_warning "Skipping tests as requested"
        return 0
    fi
    
    log_info "Running tests..."
    
    # Run Lambda function tests
    local test_failed=false
    
    for lambda_dir in "$PROJECT_ROOT/lambdas"/*; do
        if [[ -d "$lambda_dir" && -f "$lambda_dir/test_*.py" ]]; then
            lambda_name=$(basename "$lambda_dir")
            log_info "Testing $lambda_name..."
            
            if ! (cd "$lambda_dir" && python3 -m unittest test_*.py -v); then
                log_error "Tests failed for $lambda_name"
                test_failed=true
            fi
        fi
    done
    
    if [[ "$test_failed" == "true" ]]; then
        if [[ "$FORCE_DEPLOY" == "true" ]]; then
            log_warning "Tests failed but continuing due to --force flag"
        else
            log_error "Tests failed. Use --force to deploy anyway"
            exit 1
        fi
    else
        log_success "All tests passed"
    fi
}

# Analyze current provisioned concurrency configuration
analyze_provisioned_concurrency() {
    log_info "Analyzing current provisioned concurrency configuration..."
    
    if python3 "$SCRIPT_DIR/manage-provisioned-concurrency.py" \
        --environment "$ENVIRONMENT" \
        --action analyze > /tmp/pc_analysis.json 2>/dev/null; then
        
        # Extract key metrics
        local current_cost=$(cat /tmp/pc_analysis.json | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f\"{data['cost_estimate']:.2f}\")
        ")
        
        local function_count=$(cat /tmp/pc_analysis.json | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(len(data['functions']))
        ")
        
        log_info "Current provisioned concurrency cost: \$$current_cost/month"
        log_info "Functions with provisioned concurrency: $function_count"
        
        # Show recommendations if any
        local recommendations=$(cat /tmp/pc_analysis.json | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(len(data['recommendations']))
        ")
        
        if [[ "$recommendations" -gt 0 ]]; then
            log_info "Found $recommendations optimization recommendations"
        fi
    else
        log_warning "Could not analyze current provisioned concurrency (functions may not exist yet)"
    fi
}

# Deploy the CDK stack
deploy_stack() {
    log_info "Deploying AutoSpec.AI stack to $ENVIRONMENT environment..."
    
    cd "$CDK_DIR"
    
    # Install CDK dependencies
    if [[ ! -d "node_modules" ]]; then
        log_info "Installing CDK dependencies..."
        npm install
    fi
    
    # Set environment variables
    export ENVIRONMENT="$ENVIRONMENT"
    export CDK_DEFAULT_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
    export CDK_DEFAULT_REGION=$(aws configure get region || echo "us-east-1")
    
    log_info "Deploying to account: $CDK_DEFAULT_ACCOUNT"
    log_info "Deploying to region: $CDK_DEFAULT_REGION"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Showing what would be deployed..."
        cdk diff AutoSpecAIStackOptimized
        return 0
    fi
    
    # Deploy the optimized stack
    local deploy_cmd="cdk deploy AutoSpecAIStackOptimized --require-approval never"
    
    if [[ "$ENABLE_PROVISIONED_CONCURRENCY" == "true" ]]; then
        log_info "Deploying with provisioned concurrency optimizations"
    else
        log_warning "Provisioned concurrency disabled"
        export DISABLE_PROVISIONED_CONCURRENCY=true
    fi
    
    if eval "$deploy_cmd"; then
        log_success "Stack deployed successfully"
    else
        log_error "Stack deployment failed"
        exit 1
    fi
}

# Configure provisioned concurrency post-deployment
configure_provisioned_concurrency() {
    if [[ "$ENABLE_PROVISIONED_CONCURRENCY" != "true" || "$DRY_RUN" == "true" ]]; then
        return 0
    fi
    
    log_info "Configuring provisioned concurrency optimizations..."
    
    # Wait for Lambda functions to be ready
    log_info "Waiting for Lambda functions to be fully deployed..."
    sleep 30
    
    # Run optimization analysis
    if python3 "$SCRIPT_DIR/manage-provisioned-concurrency.py" \
        --environment "$ENVIRONMENT" \
        --action optimize \
        --apply > /tmp/pc_optimization.json 2>/dev/null; then
        
        # Show optimization results
        local changes_count=$(cat /tmp/pc_optimization.json | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(len(data['changes_applied']))
        ")
        
        local cost_impact=$(cat /tmp/pc_optimization.json | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f\"{data['total_cost_impact']:.2f}\")
        ")
        
        if [[ "$changes_count" -gt 0 ]]; then
            log_success "Applied $changes_count provisioned concurrency optimizations"
            if [[ $(echo "$cost_impact > 0" | bc -l) -eq 1 ]]; then
                log_success "Estimated monthly savings: \$$cost_impact"
            else
                log_info "Estimated monthly cost increase: \$$(echo "$cost_impact * -1" | bc -l)"
            fi
        else
            log_info "No provisioned concurrency optimizations needed"
        fi
    else
        log_warning "Could not optimize provisioned concurrency automatically"
    fi
}

# Monitor deployment health
monitor_deployment() {
    if [[ "$MONITOR_DEPLOYMENT" != "true" || "$DRY_RUN" == "true" ]]; then
        return 0
    fi
    
    log_info "Monitoring deployment health..."
    
    # Run validation script if it exists
    local validation_script="$SCRIPT_DIR/validate-deployment.sh"
    if [[ -f "$validation_script" ]]; then
        if bash "$validation_script" "$ENVIRONMENT"; then
            log_success "Deployment validation passed"
        else
            log_warning "Deployment validation had issues"
        fi
    fi
    
    # Generate provisioned concurrency report
    log_info "Generating post-deployment provisioned concurrency report..."
    python3 "$SCRIPT_DIR/manage-provisioned-concurrency.py" \
        --environment "$ENVIRONMENT" \
        --action report > "/tmp/pc_report_$ENVIRONMENT.txt"
    
    log_info "Provisioned concurrency report saved to: /tmp/pc_report_$ENVIRONMENT.txt"
    
    # Show key metrics
    log_info "=== Post-Deployment Summary ==="
    echo
    cat "/tmp/pc_report_$ENVIRONMENT.txt" | head -20
    echo
    log_info "Full report available at: /tmp/pc_report_$ENVIRONMENT.txt"
}

# Cleanup function
cleanup() {
    rm -f /tmp/pc_analysis.json /tmp/pc_optimization.json
}

# Set trap for cleanup
trap cleanup EXIT

# Main execution
main() {
    log_info "Starting AutoSpec.AI enhanced deployment with provisioned concurrency"
    log_info "Environment: $ENVIRONMENT"
    log_info "Enable Provisioned Concurrency: $ENABLE_PROVISIONED_CONCURRENCY"
    log_info "Dry Run: $DRY_RUN"
    
    validate_prerequisites
    
    if [[ "$DRY_RUN" != "true" ]]; then
        run_tests
    fi
    
    analyze_provisioned_concurrency
    deploy_stack
    configure_provisioned_concurrency
    monitor_deployment
    
    log_success "Deployment completed successfully!"
    
    if [[ "$ENABLE_PROVISIONED_CONCURRENCY" == "true" && "$DRY_RUN" != "true" ]]; then
        log_info ""
        log_info "=== Next Steps ==="
        log_info "1. Monitor function performance in CloudWatch"
        log_info "2. Review provisioned concurrency utilization after 24-48 hours"
        log_info "3. Run optimization analysis weekly: ./scripts/manage-provisioned-concurrency.py --environment $ENVIRONMENT --action report"
        log_info "4. Consider auto-scaling for production workloads"
    fi
}

# Parse arguments and run
parse_arguments "$@"
main