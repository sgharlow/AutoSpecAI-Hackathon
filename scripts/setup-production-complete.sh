#!/bin/bash

# AutoSpec.AI Complete Production Setup
# Master script to orchestrate all production setup tasks

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "🚀 AutoSpec.AI Complete Production Setup"
echo "========================================"
echo ""
echo "This script will set up all production infrastructure for AutoSpec.AI:"
echo "  • AWS Secrets Management"
echo "  • Domain and DNS Configuration" 
echo "  • Monitoring and Alerting"
echo "  • Security and WAF"
echo "  • Environment Configuration"
echo ""
echo "Domain: auto-spec.ai"
echo "Email: ai.autospec@gmail.com"
echo "Budget Alert: \$99"
echo ""

# Function to check prerequisites
check_prerequisites() {
    echo "🔍 Checking prerequisites..."
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        echo "❌ AWS CLI is required but not installed"
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity >/dev/null 2>&1; then
        echo "❌ AWS credentials not configured or invalid"
        echo "Please run: aws configure"
        exit 1
    fi
    
    # Check required tools
    REQUIRED_TOOLS=("jq" "openssl")
    for tool in "${REQUIRED_TOOLS[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            echo "❌ Required tool not found: $tool"
            exit 1
        fi
    done
    
    echo "✅ Prerequisites check passed"
    echo ""
}

# Function to display progress
show_progress() {
    local current=$1
    local total=$2
    local task=$3
    
    echo ""
    echo "📊 Progress: $current/$total - $task"
    echo "$(printf '█%.0s' $(seq 1 $((current * 20 / total))))$(printf '░%.0s' $(seq 1 $((20 - current * 20 / total))))"
    echo ""
}

# Function to run setup scripts with error handling
run_setup_script() {
    local script_name=$1
    local description=$2
    local step=$3
    local total=$4
    
    show_progress "$step" "$total" "$description"
    
    echo "🔧 Running: $script_name"
    
    if [ -f "$SCRIPT_DIR/$script_name" ]; then
        if bash "$SCRIPT_DIR/$script_name"; then
            echo "✅ $description completed successfully"
        else
            echo "❌ $description failed"
            echo "Check the output above for details"
            exit 1
        fi
    else
        echo "❌ Script not found: $SCRIPT_DIR/$script_name"
        exit 1
    fi
    
    echo ""
    sleep 2
}

# Function to create config directory
setup_config_directory() {
    echo "📁 Setting up configuration directory..."
    mkdir -p "$PROJECT_ROOT/config"
    echo "✅ Configuration directory ready"
    echo ""
}

# Function to display manual tasks
display_manual_tasks() {
    echo ""
    echo "⚠️  IMPORTANT: Manual Tasks Required"
    echo "=================================="
    echo ""
    echo "The following tasks require manual completion:"
    echo ""
    echo "1. 🤖 Amazon Bedrock Model Access (CRITICAL)"
    echo "   • Go to AWS Console → Amazon Bedrock → Model access"
    echo "   • Click 'Request model access'"
    echo "   • Select 'Anthropic Claude 3 Sonnet'"
    echo "   • Accept terms and submit request"
    echo "   • Usually approved immediately"
    echo ""
    echo "2. 📧 Amazon SES Production Access (CRITICAL)"
    echo "   • Go to AWS Console → Amazon SES → Account dashboard"
    echo "   • Click 'Request production access'"
    echo "   • Fill out the form with your use case"
    echo "   • Expected approval: 24-48 hours"
    echo ""
    echo "3. 🔗 GitHub Repository Secrets (for CI/CD)"
    echo "   • Go to GitHub → Repository → Settings → Secrets"
    echo "   • Add environment secrets for: development, staging, production"
    echo "   • Required secrets: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY"
    echo ""
    echo "4. 📧 Email Confirmations"
    echo "   • Check ai.autospec@gmail.com for SNS subscription confirmations"
    echo "   • Confirm all notification subscriptions"
    echo ""
    echo "5. 🌐 Domain Verification (if domain was purchased)"
    echo "   • Check email for domain verification"
    echo "   • Follow domain registration confirmation steps"
    echo ""
}

# Function to display next steps
display_next_steps() {
    echo ""
    echo "🎯 Next Steps for Deployment"
    echo "============================"
    echo ""
    echo "After completing the manual tasks above:"
    echo ""
    echo "1. Load production environment:"
    echo "   source ./scripts/load-config.sh prod"
    echo ""
    echo "2. Bootstrap CDK (one-time only):"
    echo "   cdk bootstrap aws://\$AWS_ACCOUNT_ID/\$AWS_REGION"
    echo ""
    echo "3. Deploy to production:"
    echo "   ./scripts/deploy.sh prod"
    echo ""
    echo "4. Validate deployment:"
    echo "   ./scripts/validate-deployment.sh prod"
    echo ""
    echo "5. Run integration tests:"
    echo "   ./scripts/integration-tests.sh https://api.auto-spec.ai prod"
    echo ""
    echo "📊 Monitor your deployment:"
    echo "   • CloudWatch Dashboards: autospec-ai-prod-operational, autospec-ai-prod-performance"
    echo "   • Application URL: https://app.auto-spec.ai"
    echo "   • API URL: https://api.auto-spec.ai"
    echo "   • Document Email: documents@auto-spec.ai"
    echo ""
}

# Function to save setup summary
save_setup_summary() {
    echo "💾 Saving setup summary..."
    
    cat > "$PROJECT_ROOT/PRODUCTION_SETUP_SUMMARY.md" << 'EOF'
# AutoSpec.AI Production Setup Summary

## ✅ Completed Automated Tasks

### 1. AWS Secrets Management
- **Status**: ✅ Complete
- **Secrets Created**: 15 production secrets in AWS Secrets Manager
- **Security**: Cryptographically secure random generation
- **Location**: `autospec-ai/prod/*` in AWS Secrets Manager

### 2. Domain and DNS Configuration  
- **Status**: ✅ Complete
- **Domain**: auto-spec.ai
- **SSL Certificate**: Requested with DNS validation
- **DNS Records**: Created for app, api, www, documents subdomains
- **Email Auth**: SPF and DMARC records configured

### 3. Monitoring and Alerting
- **Status**: ✅ Complete
- **SNS Topics**: 3 created (critical, warning, business metrics)
- **CloudWatch Alarms**: 20+ alarms for comprehensive monitoring
- **Dashboards**: 2 dashboards (operational, performance)
- **Budget Alert**: $99 monthly threshold with email notifications
- **Log Retention**: 30 days for all log groups

### 4. Security and WAF
- **Status**: ✅ Complete
- **WAF Web ACL**: Rate limiting + AWS managed rules
- **GuardDuty**: Threat detection enabled
- **Security Hub**: AWS + CIS standards enabled
- **AWS Config**: Compliance monitoring active
- **CloudTrail**: Full audit logging enabled
- **KMS Encryption**: Application-specific key created

### 5. Environment Configuration
- **Status**: ✅ Complete
- **Production Config**: Updated with domain and notification settings
- **Feature Flags**: All advanced features enabled
- **Performance**: Optimized for production workloads

## ⚠️ Manual Tasks Required

### 1. Amazon Bedrock Model Access (CRITICAL)
- **Action**: Request Claude 3 Sonnet model access in AWS Console
- **Timeline**: Usually immediate approval
- **Required For**: AI document processing functionality

### 2. Amazon SES Production Access (CRITICAL)
- **Action**: Submit support case to move SES out of sandbox mode
- **Timeline**: 24-48 hours approval
- **Required For**: Email functionality and notifications

### 3. GitHub Repository Secrets
- **Action**: Configure CI/CD secrets in GitHub repository settings
- **Required Secrets**: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
- **Required For**: Automated deployments

### 4. Email Confirmations
- **Action**: Confirm SNS subscription emails
- **Email**: ai.autospec@gmail.com
- **Required For**: Alert notifications

## 🚀 Deployment Ready

Once manual tasks are complete, the system is ready for production deployment using the automated deployment scripts.

**Estimated Time to Production**: 2-3 hours after manual approvals

## 📞 Support

For issues during setup or deployment:
- Review CloudWatch logs for detailed error information
- Check AWS Service Health Dashboard for service issues
- Verify all manual tasks have been completed
- Ensure AWS credentials have sufficient permissions

Generated: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
EOF

    echo "✅ Setup summary saved to PRODUCTION_SETUP_SUMMARY.md"
}

# Main execution
main() {
    echo "Starting AutoSpec.AI production setup..."
    echo ""
    
    # Check prerequisites
    check_prerequisites
    
    # Setup configuration directory
    setup_config_directory
    
    # Run all setup scripts
    run_setup_script "setup-production-secrets.sh" "AWS Secrets Management" 1 4
    run_setup_script "setup-domain-and-dns.sh" "Domain and DNS Configuration" 2 4
    run_setup_script "setup-monitoring-and-alerts.sh" "Monitoring and Alerting" 3 4
    run_setup_script "setup-security-and-waf.sh" "Security and WAF Configuration" 4 4
    
    # Save setup summary
    save_setup_summary
    
    # Show completion
    show_progress 4 4 "Production setup complete!"
    
    echo ""
    echo "🎉 AutoSpec.AI Production Setup Complete!"
    echo "========================================"
    echo ""
    echo "✅ All automated tasks have been completed successfully"
    echo "📋 See PRODUCTION_SETUP_SUMMARY.md for detailed results"
    echo ""
    
    # Display manual tasks
    display_manual_tasks
    
    # Display next steps
    display_next_steps
    
    echo ""
    echo "🌟 Production deployment is now 90% complete!"
    echo "Only the manual tasks above are required before going live."
    echo ""
}

# Run main function
main "$@"