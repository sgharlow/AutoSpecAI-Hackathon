#!/bin/bash

# AutoSpec.AI Deployment Script
# Supports deployment to dev, staging, and production environments

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT=""
SKIP_TESTS=false
FORCE_DEPLOY=false
CDK_STACK_NAME=""
AWS_REGION="us-east-1"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Handle SSL certificate issues in WSL/development environments
export AWS_CLI_SSL_VERIFY=false

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to display usage
usage() {
    cat << EOF
Usage: $0 <environment> [options]

Environments:
    dev         Deploy to development environment
    staging     Deploy to staging environment
    prod        Deploy to production environment

Options:
    --skip-tests        Skip running tests before deployment
    --force            Force deployment even if environment exists
    --region REGION    AWS region (default: us-east-1)
    --stack-name NAME  Custom CDK stack name
    --help             Show this help message

Examples:
    $0 dev
    $0 staging --skip-tests
    $0 prod --force --region us-west-2

EOF
}

# Parse command line arguments
parse_args() {
    if [ $# -eq 0 ]; then
        usage
        exit 1
    fi

    ENVIRONMENT=$1
    shift

    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-tests)
                SKIP_TESTS=true
                shift
                ;;
            --force)
                FORCE_DEPLOY=true
                shift
                ;;
            --region)
                AWS_REGION="$2"
                shift 2
                ;;
            --stack-name)
                CDK_STACK_NAME="$2"
                shift 2
                ;;
            --help)
                usage
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done

    # Validate environment
    case $ENVIRONMENT in
        dev|staging|prod)
            ;;
        *)
            print_error "Invalid environment: $ENVIRONMENT"
            usage
            exit 1
            ;;
    esac
}

# Function to check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."

    # Check if AWS CLI is installed
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi

    # Check if CDK is installed
    if ! command -v cdk &> /dev/null; then
        print_error "AWS CDK is not installed. Please install it first."
        exit 1
    fi

    # Check if Node.js is installed
    if ! command -v node &> /dev/null; then
        print_error "Node.js is not installed. Please install it first."
        exit 1
    fi

    # Check if Python is installed
    if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null && ! command -v py &> /dev/null; then
        print_error "Python 3 is not installed. Please install it first."
        exit 1
    fi

    # Check AWS credentials
    if ! aws sts get-caller-identity --no-verify-ssl &> /dev/null; then
        print_error "AWS credentials not configured. Please run 'aws configure' first."
        exit 1
    fi

    print_success "All prerequisites met"
}

# Function to load environment configuration
load_config() {
    print_info "Loading configuration for environment: $ENVIRONMENT"

    # Source environment-specific configuration
    CONFIG_FILE="$PROJECT_ROOT/config/environments/$ENVIRONMENT.env"
    if [ -f "$CONFIG_FILE" ]; then
        source "$CONFIG_FILE"
        print_success "Loaded configuration from $CONFIG_FILE"
    else
        print_warning "No configuration file found at $CONFIG_FILE"
    fi

    # Set default stack name if not provided
    if [ -z "$CDK_STACK_NAME" ]; then
        CDK_STACK_NAME="AutoSpecAI-${ENVIRONMENT}"
    fi

    # Export environment variables for CDK
    export ENVIRONMENT
    export AWS_REGION
    export CDK_STACK_NAME
}

# Function to run tests
run_tests() {
    if [ "$SKIP_TESTS" = true ]; then
        print_warning "Skipping tests as requested"
        return 0
    fi

    print_info "Running tests..."

    # Run Lambda function tests
    for lambda_dir in "$PROJECT_ROOT"/lambdas/*/; do
        if [ -f "$lambda_dir/test_*.py" ]; then
            lambda_name=$(basename "$lambda_dir")
            print_info "Running tests for $lambda_name..."
            cd "$lambda_dir"
            python3 -m unittest discover -s . -p "test_*.py" -v
        fi
    done

    # Run infrastructure tests
    if [ -d "$PROJECT_ROOT/testing" ]; then
        print_info "Running integration tests..."
        cd "$PROJECT_ROOT/testing"
        npm test
    fi

    cd "$PROJECT_ROOT"
    print_success "All tests passed"
}

# Function to build Lambda packages
build_lambda_packages() {
    print_info "Building Lambda packages..."

    for lambda_dir in "$PROJECT_ROOT"/lambdas/*/; do
        lambda_name=$(basename "$lambda_dir")
        print_info "Building package for $lambda_name..."
        
        cd "$lambda_dir"
        
        # Install dependencies if requirements.txt exists
        if [ -f "requirements.txt" ]; then
            # Create minimal requirements for Lambda size limits
            MINIMAL_REQUIREMENTS="minimal_requirements.txt"
            
            # For functions with heavy dependencies, install only essential ones
            if [ "$lambda_name" = "format" ]; then
                print_info "Creating minimal requirements for format function to avoid size limits..."
                cat > "$MINIMAL_REQUIREMENTS" << EOF
boto3==1.34.0
jinja2==3.1.2
reportlab==4.0.7
EOF
            elif [ "$lambda_name" = "process" ]; then
                print_info "Creating minimal requirements for process function..."
                cat > "$MINIMAL_REQUIREMENTS" << EOF
boto3==1.34.0
EOF
            else
                # For other functions, use minimal AWS dependencies
                print_info "Creating minimal requirements for $lambda_name function..."
                cat > "$MINIMAL_REQUIREMENTS" << EOF
boto3==1.34.0
EOF
            fi
            
            # Install minimal dependencies
            print_info "Installing minimal dependencies for $lambda_name..."
            if command -v pip3 &> /dev/null; then
                pip3 install -r "$MINIMAL_REQUIREMENTS" -t . --upgrade --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org
            elif command -v pip &> /dev/null; then
                pip install -r "$MINIMAL_REQUIREMENTS" -t . --upgrade --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org
            else
                print_error "No pip command found"
                exit 1
            fi
            
            # Clean up temp file
            rm -f "$MINIMAL_REQUIREMENTS"
        fi
        
        # Determine Python command
        PYTHON_CMD=""
        if command -v python3 &> /dev/null; then
            PYTHON_CMD="python3"
        elif command -v python &> /dev/null; then
            PYTHON_CMD="python"
        elif command -v py &> /dev/null; then
            PYTHON_CMD="py"
        else
            print_error "No Python interpreter found"
            exit 1
        fi
        
        # Create deployment package using Python
        $PYTHON_CMD -c "
import zipfile
import os
import glob

def should_exclude(filepath):
    # Normalize path separators for Windows compatibility
    filepath = filepath.replace('\\\\', '/').replace('\\\\', '/')
    
    exclude_patterns = [
        'test_', '__pycache__', '.pyc', '.git', '.gitignore',
        'venv/', 'env/', '.env/', 'node_modules/', '.vscode/',
        'bin/', 'Scripts/', 'include/', 'lib/', 'lib64/',
        '.zip', 'Lib/', 'share/', 'pyvenv.cfg'
    ]
    
    # Check if any exclude pattern matches
    for pattern in exclude_patterns:
        if pattern in filepath or filepath.endswith(pattern.rstrip('/')):
            return True
    
    # Check basename
    basename = os.path.basename(filepath)
    if basename.startswith('test_') or basename.startswith('.'):
        return True
        
    return False

def safe_write_to_zip(zipf, filepath, arcname):
    try:
        if os.path.exists(filepath) and os.access(filepath, os.R_OK):
            zipf.write(filepath, arcname)
            return True
    except (OSError, PermissionError) as e:
        print(f'Skipping {filepath}: {e}')
        return False
    return False

with zipfile.ZipFile('../${lambda_name}.zip', 'w', zipfile.ZIP_DEFLATED) as zipf:
    for root, dirs, files in os.walk('.'):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if not should_exclude(os.path.join(root, d))]
        
        for file in files:
            filepath = os.path.join(root, file)
            if not should_exclude(filepath):
                arcname = os.path.relpath(filepath, '.')
                safe_write_to_zip(zipf, filepath, arcname)
"
    done

    cd "$PROJECT_ROOT"
    print_success "Lambda packages built successfully"
}

# Function to deploy infrastructure
deploy_infrastructure() {
    print_info "Deploying infrastructure to $ENVIRONMENT..."

    cd "$PROJECT_ROOT/infra/cdk"

    # Install CDK dependencies only if not already installed
    if [ ! -d "node_modules" ] || [ ! -f "node_modules/.package-lock.json" ]; then
        print_info "Installing CDK dependencies..."
        npm install --production --no-optional
    else
        print_info "CDK dependencies already installed, skipping npm install"
    fi

    # Bootstrap CDK if needed
    print_info "Bootstrapping CDK..."
    cdk bootstrap --profile default

    # Synthesize CloudFormation template
    print_info "Synthesizing CloudFormation template..."
    cdk synth

    # Deploy the stack
    print_info "Deploying CDK stack: $CDK_STACK_NAME"
    if [ "$FORCE_DEPLOY" = true ]; then
        cdk deploy --require-approval never --force
    else
        cdk deploy --require-approval never
    fi

    cd "$PROJECT_ROOT"
    print_success "Infrastructure deployed successfully"
}

# Function to deploy Lambda functions
deploy_lambda_functions() {
    print_info "Deploying Lambda functions..."

    # Get the stack outputs to find function names
    STACK_OUTPUTS=$(aws cloudformation describe-stacks \
        --stack-name "$CDK_STACK_NAME" \
        --region "$AWS_REGION" \
        --query 'Stacks[0].Outputs' \
        --output json)

    for lambda_dir in "$PROJECT_ROOT"/lambdas/*/; do
        lambda_name=$(basename "$lambda_dir")
        function_name="${CDK_STACK_NAME}-${lambda_name}"
        
        print_info "Deploying $lambda_name to $function_name..."
        
        # Update function code
        aws lambda update-function-code \
            --function-name "$function_name" \
            --zip-file "fileb://$PROJECT_ROOT/lambdas/${lambda_name}.zip" \
            --region "$AWS_REGION"
    done

    print_success "Lambda functions deployed successfully"
}

# Function to run post-deployment validation
validate_deployment() {
    print_info "Validating deployment..."

    # Run validation script if it exists
    VALIDATION_SCRIPT="$PROJECT_ROOT/scripts/validate-deployment.sh"
    if [ -f "$VALIDATION_SCRIPT" ]; then
        bash "$VALIDATION_SCRIPT" "$ENVIRONMENT"
    else
        print_warning "No validation script found"
    fi

    # Test API endpoints
    API_URL=$(aws cloudformation describe-stacks \
        --stack-name "$CDK_STACK_NAME" \
        --region "$AWS_REGION" \
        --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' \
        --output text)

    if [ -n "$API_URL" ]; then
        print_info "Testing API endpoint: $API_URL"
        if curl -f "$API_URL/health" > /dev/null 2>&1; then
            print_success "API endpoint is responding"
        else
            print_warning "API endpoint is not responding"
        fi
    fi

    print_success "Deployment validation completed"
}

# Function to update monitoring
update_monitoring() {
    print_info "Updating monitoring and observability..."

    MONITORING_SCRIPT="$PROJECT_ROOT/scripts/update-monitoring.sh"
    if [ -f "$MONITORING_SCRIPT" ]; then
        bash "$MONITORING_SCRIPT" "$ENVIRONMENT"
    else
        print_warning "No monitoring update script found"
    fi
}

# Function to display deployment summary
display_summary() {
    print_success "Deployment completed successfully!"
    echo
    echo "Environment: $ENVIRONMENT"
    echo "Region: $AWS_REGION"
    echo "Stack: $CDK_STACK_NAME"
    echo
    
    # Display important outputs
    print_info "Stack Outputs:"
    aws cloudformation describe-stacks \
        --stack-name "$CDK_STACK_NAME" \
        --region "$AWS_REGION" \
        --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
        --output table
}

# Main deployment function
main() {
    print_info "Starting AutoSpec.AI deployment..."
    echo "Environment: $ENVIRONMENT"
    echo "Region: $AWS_REGION"
    echo "Skip Tests: $SKIP_TESTS"
    echo "Force Deploy: $FORCE_DEPLOY"
    echo

    check_prerequisites
    load_config
    run_tests
    build_lambda_packages
    deploy_infrastructure
    deploy_lambda_functions
    validate_deployment
    update_monitoring
    display_summary
}

# Parse arguments and run main function
parse_args "$@"
main