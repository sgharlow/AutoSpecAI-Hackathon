#!/bin/bash

# AutoSpec.AI Demo Environment Setup Script
# Usage: ./setup_demo.sh [environment]

set -e

ENVIRONMENT=${1:-dev}

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# ASCII Art Banner
print_banner() {
    echo -e "${PURPLE}"
    cat << "EOF"
    ╔═══════════════════════════════════════════════════════════╗
    ║                  AutoSpec.AI Demo Setup                   ║
    ║                                                           ║
    ║               🎬 Preparing Demo Environment 🎬            ║
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

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

print_banner

echo "🎯 Setting up demo environment: $ENVIRONMENT"
echo "📁 Project root: $PROJECT_ROOT"
echo ""

# Step 1: Verify Environment
log_step "1/8 Verifying demo environment"

cd "$PROJECT_ROOT"

# Load configuration
if [ -f "scripts/load-config.sh" ]; then
    source ./scripts/load-config.sh "$ENVIRONMENT"
    log_success "Configuration loaded for $ENVIRONMENT"
else
    log_error "Configuration loader not found"
    exit 1
fi

# Step 2: Deploy Infrastructure (if needed)
log_step "2/8 Checking infrastructure deployment"

STACK_NAME=$(echo "$STACK_NAME" | sed 's/null//')
if [ -z "$STACK_NAME" ]; then
    STACK_NAME="AutoSpecAIStack-$ENVIRONMENT"
fi

# Check if stack exists
if aws cloudformation describe-stacks --stack-name "$STACK_NAME" > /dev/null 2>&1; then
    STACK_STATUS=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --query 'Stacks[0].StackStatus' --output text)
    log_success "Stack exists: $STACK_NAME (Status: $STACK_STATUS)"
    
    # Get API URL from stack outputs
    API_URL=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --query 'Stacks[0].Outputs[?OutputKey==`ApiGatewayUrl`].OutputValue' --output text 2>/dev/null || echo "")
    BUCKET_NAME=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --query 'Stacks[0].Outputs[?OutputKey==`DocumentBucketName`].OutputValue' --output text 2>/dev/null || echo "")
    
    if [ -n "$API_URL" ] && [ "$API_URL" != "None" ]; then
        log_success "API Gateway URL: $API_URL"
    else
        log_warning "API Gateway URL not found in stack outputs"
    fi
else
    log_warning "Infrastructure not deployed. Run './deploy.sh $ENVIRONMENT' first"
    read -p "Deploy infrastructure now? (y/n): " deploy_now
    
    if [ "$deploy_now" = "y" ] || [ "$deploy_now" = "Y" ]; then
        log_info "Deploying infrastructure..."
        if ./deploy.sh "$ENVIRONMENT" false true; then
            log_success "Infrastructure deployed successfully"
            
            # Get outputs after deployment
            API_URL=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --query 'Stacks[0].Outputs[?OutputKey==`ApiGatewayUrl`].OutputValue' --output text 2>/dev/null || echo "")
            BUCKET_NAME=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --query 'Stacks[0].Outputs[?OutputKey==`DocumentBucketName`].OutputValue' --output text 2>/dev/null || echo "")
        else
            log_error "Infrastructure deployment failed"
            exit 1
        fi
    else
        log_error "Infrastructure deployment required for demo"
        exit 1
    fi
fi

# Step 3: Prepare Demo Documents
log_step "3/8 Preparing demo documents"

DEMO_DIR="$SCRIPT_DIR"

# Convert sample documents to base64 for API calls
log_info "Converting sample documents to base64..."

if [ -f "$DEMO_DIR/sample_documents/e_commerce_requirements.txt" ]; then
    ECOMMERCE_B64=$(base64 -w 0 "$DEMO_DIR/sample_documents/e_commerce_requirements.txt")
    log_success "E-commerce document prepared"
else
    log_error "E-commerce sample document not found"
    exit 1
fi

if [ -f "$DEMO_DIR/sample_documents/mobile_banking_app.txt" ]; then
    BANKING_B64=$(base64 -w 0 "$DEMO_DIR/sample_documents/mobile_banking_app.txt")
    log_success "Banking app document prepared"
else
    log_error "Banking app sample document not found"
    exit 1
fi

# Step 4: Configure Postman Collection
log_step "4/8 Configuring Postman collection"

if [ -f "$DEMO_DIR/postman_collection.json" ]; then
    # Update Postman collection with actual API URL
    if [ -n "$API_URL" ]; then
        sed -i.bak "s|https://your-api-gateway-url.amazonaws.com|$API_URL|g" "$DEMO_DIR/postman_collection.json"
        log_success "Postman collection updated with API URL"
    else
        log_warning "API URL not available for Postman collection"
    fi
else
    log_error "Postman collection not found"
fi

# Step 5: Create Demo Environment File
log_step "5/8 Creating demo environment file"

cat > "$DEMO_DIR/demo_environment.env" << EOF
# AutoSpec.AI Demo Environment Configuration
# Generated: $(date)

# Environment
DEMO_ENVIRONMENT=$ENVIRONMENT
STACK_NAME=$STACK_NAME

# API Configuration
API_URL=$API_URL
BUCKET_NAME=$BUCKET_NAME

# Demo Documents (Base64 Encoded)
ECOMMERCE_DOCUMENT_B64="$ECOMMERCE_B64"
BANKING_DOCUMENT_B64="$BANKING_B64"

# AWS Configuration
AWS_REGION=$AWS_REGION
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "unknown")

# Demo URLs
CLOUDWATCH_DASHBOARD_URL=https://$AWS_REGION.console.aws.amazon.com/cloudwatch/home?region=$AWS_REGION#dashboards:name=AutoSpecAI-Operational-Dashboard
XRAY_SERVICE_MAP_URL=https://$AWS_REGION.console.aws.amazon.com/xray/home?region=$AWS_REGION#/service-map
LOGS_URL=https://$AWS_REGION.console.aws.amazon.com/cloudwatch/home?region=$AWS_REGION#logsV2:log-groups

# Demo Script Settings
DEMO_EMAIL=demo@autospec.ai
DEMO_API_KEY=demo-key-for-presentation
EOF

log_success "Demo environment file created: $DEMO_DIR/demo_environment.env"

# Step 6: Test API Endpoints
log_step "6/8 Testing API endpoints"

if [ -n "$API_URL" ]; then
    # Test health endpoint
    log_info "Testing health endpoint..."
    health_response=$(curl -s -w "%{http_code}" -o /tmp/health_test.json "$API_URL/v1/health" || echo "000")
    
    if [ "$health_response" = "200" ]; then
        log_success "Health endpoint responding correctly"
    else
        log_warning "Health endpoint returned HTTP $health_response"
    fi
    
    # Test formats endpoint
    log_info "Testing formats endpoint..."
    formats_response=$(curl -s -w "%{http_code}" -o /tmp/formats_test.json "$API_URL/v1/formats" || echo "000")
    
    if [ "$formats_response" = "200" ]; then
        log_success "Formats endpoint responding correctly"
    else
        log_warning "Formats endpoint returned HTTP $formats_response"
    fi
    
    # Test docs endpoint
    log_info "Testing documentation endpoint..."
    docs_response=$(curl -s -w "%{http_code}" -o /tmp/docs_test.json "$API_URL/v1/docs" || echo "000")
    
    if [ "$docs_response" = "200" ]; then
        log_success "Documentation endpoint responding correctly"
    else
        log_warning "Documentation endpoint returned HTTP $docs_response"
    fi
else
    log_warning "API URL not available, skipping endpoint tests"
fi

# Step 7: Create Demo Scripts
log_step "7/8 Creating demo helper scripts"

# Create quick upload script
cat > "$DEMO_DIR/quick_upload.sh" << 'EOF'
#!/bin/bash

# Quick document upload for demo
# Usage: ./quick_upload.sh [document_type]

DOCUMENT_TYPE=${1:-ecommerce}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load demo environment
if [ -f "$SCRIPT_DIR/demo_environment.env" ]; then
    source "$SCRIPT_DIR/demo_environment.env"
else
    echo "Demo environment not found. Run setup_demo.sh first."
    exit 1
fi

case $DOCUMENT_TYPE in
    ecommerce)
        DOCUMENT_B64="$ECOMMERCE_DOCUMENT_B64"
        FILENAME="e_commerce_requirements.txt"
        ;;
    banking)
        DOCUMENT_B64="$BANKING_DOCUMENT_B64"
        FILENAME="mobile_banking_app.txt"
        ;;
    *)
        echo "Invalid document type. Use 'ecommerce' or 'banking'"
        exit 1
        ;;
esac

echo "Uploading $FILENAME to AutoSpec.AI..."

response=$(curl -s -X POST "$API_URL/v1/upload" \
    -H "Content-Type: application/json" \
    -d "{
        \"file_content\": \"$DOCUMENT_B64\",
        \"filename\": \"$FILENAME\",
        \"sender_email\": \"$DEMO_EMAIL\",
        \"preferences\": {
            \"quality\": \"premium\",
            \"formats\": [\"html\", \"pdf\", \"json\", \"markdown\"],
            \"charts\": true,
            \"interactive\": true
        }
    }")

echo "Response:"
echo "$response" | jq '.' 2>/dev/null || echo "$response"

# Extract request ID
REQUEST_ID=$(echo "$response" | jq -r '.request_id' 2>/dev/null || echo "")
if [ -n "$REQUEST_ID" ] && [ "$REQUEST_ID" != "null" ]; then
    echo ""
    echo "Request ID: $REQUEST_ID"
    echo "Check status with: curl -s \"$API_URL/v1/status/$REQUEST_ID\" | jq '.'"
fi
EOF

chmod +x "$DEMO_DIR/quick_upload.sh"
log_success "Quick upload script created"

# Create monitoring dashboard opener
cat > "$DEMO_DIR/open_dashboards.sh" << EOF
#!/bin/bash

# Open monitoring dashboards for demo
echo "Opening AutoSpec.AI monitoring dashboards..."

if command -v open >/dev/null 2>&1; then
    # macOS
    open "$CLOUDWATCH_DASHBOARD_URL"
    open "$XRAY_SERVICE_MAP_URL"
    open "$LOGS_URL"
elif command -v xdg-open >/dev/null 2>&1; then
    # Linux
    xdg-open "$CLOUDWATCH_DASHBOARD_URL"
    xdg-open "$XRAY_SERVICE_MAP_URL"
    xdg-open "$LOGS_URL"
else
    echo "Monitoring URLs:"
    echo "CloudWatch Dashboard: $CLOUDWATCH_DASHBOARD_URL"
    echo "X-Ray Service Map: $XRAY_SERVICE_MAP_URL"
    echo "CloudWatch Logs: $LOGS_URL"
fi
EOF

chmod +x "$DEMO_DIR/open_dashboards.sh"
log_success "Dashboard opener script created"

# Step 8: Create Demo Instructions
log_step "8/8 Creating demo instructions"

cat > "$DEMO_DIR/DEMO_INSTRUCTIONS.md" << EOF
# AutoSpec.AI Demo Instructions

## Quick Start Guide

### 1. Environment Setup
- Demo environment: **$ENVIRONMENT**
- API Gateway URL: $API_URL
- Stack name: $STACK_NAME

### 2. Demo Flow

#### A. Document Upload Demo
\`\`\`bash
# Upload e-commerce requirements
./quick_upload.sh ecommerce

# Upload banking app requirements  
./quick_upload.sh banking
\`\`\`

#### B. Monitor Processing
\`\`\`bash
# Open monitoring dashboards
./open_dashboards.sh

# Check specific request status
curl -s "$API_URL/v1/status/REQUEST_ID" | jq '.'
\`\`\`

#### C. View Results
- Check email for delivered results
- View generated PDF, HTML, and JSON outputs
- Demonstrate different quality levels and formats

### 3. Key Demo Points

1. **Serverless Architecture**: Show AWS Lambda functions in action
2. **AI Processing**: Demonstrate Bedrock integration with real documents
3. **Multi-format Output**: Show PDF, HTML, JSON, and Markdown results
4. **Monitoring**: Display real-time CloudWatch dashboards and X-Ray traces
5. **API Integration**: Demonstrate REST API with authentication
6. **Enterprise Features**: Show monitoring, security, and scalability

### 4. Demo Timing (3 minutes)

- **0:00-0:20**: Introduction and problem statement
- **0:20-0:55**: Architecture overview and document upload
- **0:55-1:30**: AI processing and monitoring
- **1:30-2:00**: Results demonstration
- **2:00-2:35**: Advanced features showcase
- **2:35-3:00**: Conclusion and next steps

### 5. Troubleshooting

#### API Not Responding
\`\`\`bash
# Check stack status
aws cloudformation describe-stacks --stack-name $STACK_NAME

# Check Lambda function logs
aws logs tail "/aws/lambda/AutoSpecAI-ApiFunction" --follow
\`\`\`

#### Processing Stuck
\`\`\`bash
# Check processing Lambda logs
aws logs tail "/aws/lambda/AutoSpecAI-ProcessFunction" --follow

# Verify Bedrock access
aws bedrock list-foundation-models --region $AWS_REGION
\`\`\`

### 6. Demo Assets

- **Sample Documents**: 
  - E-commerce platform requirements
  - Mobile banking application requirements
- **Postman Collection**: Pre-configured API requests
- **Monitoring Dashboards**: Real-time operational metrics
- **X-Ray Traces**: Distributed tracing visualization

### 7. Key URLs

- **API Documentation**: $API_URL/v1/docs
- **Health Check**: $API_URL/v1/health
- **CloudWatch Dashboard**: $CLOUDWATCH_DASHBOARD_URL
- **X-Ray Service Map**: $XRAY_SERVICE_MAP_URL
- **CloudWatch Logs**: $LOGS_URL

### 8. Demo Script

See \`demo_video_script.md\` for detailed narration and timing.

### 9. Recording Tips

- Use 1920x1080 resolution
- Enable clear audio recording
- Show multiple browser windows for monitoring
- Use Postman for API demonstrations
- Highlight key features and benefits
- Keep within 3-minute time limit

### 10. Post-Demo Actions

- Share GitHub repository
- Provide deployment instructions
- Offer to answer questions
- Collect feedback and contact information
EOF

log_success "Demo instructions created: $DEMO_DIR/DEMO_INSTRUCTIONS.md"

# Cleanup
rm -f /tmp/health_test.json /tmp/formats_test.json /tmp/docs_test.json

echo ""
echo "🎉 Demo Environment Setup Complete!"
echo "===================================="
echo "Environment: $ENVIRONMENT"
echo "API URL: $API_URL"
echo "Demo Directory: $DEMO_DIR"
echo ""
echo "📋 Next Steps:"
echo "1. Review demo instructions: $DEMO_DIR/DEMO_INSTRUCTIONS.md"
echo "2. Test upload script: $DEMO_DIR/quick_upload.sh ecommerce"
echo "3. Open monitoring dashboards: $DEMO_DIR/open_dashboards.sh"
echo "4. Import Postman collection for API testing"
echo "5. Follow demo video script for recording"
echo ""
echo "🚀 Ready for demo recording!"
echo "===================================="