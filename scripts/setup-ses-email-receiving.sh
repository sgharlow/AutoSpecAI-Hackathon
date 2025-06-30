#!/bin/bash

# AutoSpec.AI - SES Email Receiving Setup Script
# This script configures SES receipt rules for documents@autospec-ai.com

set -e

# Configuration
ENVIRONMENT="${1:-prod}"
DOMAIN="autospec-ai.com"
EMAIL_ADDRESS="documents@autospec-ai.com"
RULE_SET_NAME="autospec-email-rules-${ENVIRONMENT}"
EMAIL_BUCKET="autospec-ai-emails-${ENVIRONMENT}-$(aws sts get-caller-identity --query Account --output text)"
LAMBDA_FUNCTION_NAME="AutoSpecAI-IngestFunction-v2-${ENVIRONMENT}"

echo "🔧 Setting up SES email receiving for AutoSpec.AI"
echo "Environment: ${ENVIRONMENT}"
echo "Email Address: ${EMAIL_ADDRESS}"
echo "Rule Set: ${RULE_SET_NAME}"

# Function to check if domain is verified
check_domain_verification() {
    echo "📧 Checking domain verification status..."
    local verification_status=$(aws ses get-identity-verification-attributes \
        --identities ${DOMAIN} \
        --query "VerificationAttributes.\"${DOMAIN}\".VerificationStatus" \
        --output text 2>/dev/null || echo "NotFound")
    
    if [ "$verification_status" = "Success" ]; then
        echo "✅ Domain ${DOMAIN} is verified"
        return 0
    else
        echo "❌ Domain ${DOMAIN} is not verified (Status: ${verification_status})"
        echo "Please verify the domain in SES console first:"
        echo "https://console.aws.amazon.com/ses/home?region=us-east-1#verified-senders-domain:"
        return 1
    fi
}

# Function to get Lambda function ARN
get_lambda_arn() {
    aws lambda get-function \
        --function-name ${LAMBDA_FUNCTION_NAME} \
        --query 'Configuration.FunctionArn' \
        --output text
}

# Function to check if receipt rule set exists
check_receipt_rule_set() {
    aws ses describe-receipt-rule-set \
        --rule-set-name ${RULE_SET_NAME} \
        >/dev/null 2>&1
}

# Function to set active receipt rule set
set_active_receipt_rule_set() {
    echo "🔄 Setting ${RULE_SET_NAME} as active receipt rule set..."
    aws ses set-active-receipt-rule-set \
        --rule-set-name ${RULE_SET_NAME}
    echo "✅ Receipt rule set ${RULE_SET_NAME} is now active"
}

# Function to create receipt rule
create_receipt_rule() {
    local lambda_arn=$(get_lambda_arn)
    echo "📝 Creating receipt rule for ${EMAIL_ADDRESS}..."
    echo "Lambda ARN: ${lambda_arn}"
    echo "S3 Bucket: ${EMAIL_BUCKET}"
    
    # Create the receipt rule with S3 and Lambda actions
    aws ses create-receipt-rule \
        --rule-set-name ${RULE_SET_NAME} \
        --rule '{
            "Name": "documents-email-rule-'${ENVIRONMENT}'",
            "Enabled": true,
            "Recipients": ["'${EMAIL_ADDRESS}'"],
            "Actions": [
                {
                    "S3Action": {
                        "BucketName": "'${EMAIL_BUCKET}'",
                        "ObjectKeyPrefix": "incoming-emails/"
                    }
                },
                {
                    "LambdaAction": {
                        "FunctionArn": "'${lambda_arn}'",
                        "InvocationType": "Event"
                    }
                }
            ]
        }'
    
    echo "✅ Receipt rule created successfully"
}

# Function to display MX record information
display_mx_records() {
    echo ""
    echo "📋 DNS Configuration Required:"
    echo "=============================================="
    echo "To complete email receiving setup, add these MX records to your DNS:"
    echo ""
    echo "Record Type: MX"
    echo "Name: ${DOMAIN}"
    echo "Value: 10 inbound-smtp.us-east-1.amazonaws.com"
    echo "TTL: 300"
    echo ""
    echo "For subdomain email receiving:"
    echo "Record Type: MX" 
    echo "Name: documents.${DOMAIN}"
    echo "Value: 10 inbound-smtp.us-east-1.amazonaws.com"
    echo "TTL: 300"
    echo ""
    echo "You can verify MX records with:"
    echo "nslookup -type=MX ${DOMAIN}"
    echo "nslookup -type=MX documents.${DOMAIN}"
}

# Function to test email receiving
test_email_receiving() {
    echo ""
    echo "🧪 Testing Email Receiving Setup:"
    echo "=================================="
    echo "1. Send a test email to: ${EMAIL_ADDRESS}"
    echo "2. Check CloudWatch logs for the Lambda function:"
    echo "   https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#logsV2:log-groups/log-group/%252Faws%252Flambda%252F${LAMBDA_FUNCTION_NAME}"
    echo "3. Check S3 bucket for stored emails:"
    echo "   aws s3 ls s3://${EMAIL_BUCKET}/incoming-emails/"
    echo "4. Check DynamoDB for processing records:"
    echo "   aws dynamodb scan --table-name autospec-ai-history-${ENVIRONMENT}"
}

# Main execution
main() {
    echo "Starting SES email receiving setup..."
    
    # Check if domain is verified
    if ! check_domain_verification; then
        echo "❌ Setup cannot continue without domain verification"
        exit 1
    fi
    
    # Check if receipt rule set exists
    if check_receipt_rule_set; then
        echo "✅ Receipt rule set ${RULE_SET_NAME} already exists"
    else
        echo "❌ Receipt rule set ${RULE_SET_NAME} does not exist"
        echo "This should have been created by CDK deployment. Please check stack outputs."
        exit 1
    fi
    
    # Set as active receipt rule set
    set_active_receipt_rule_set
    
    # Create receipt rule
    create_receipt_rule
    
    # Display DNS configuration
    display_mx_records
    
    # Display testing instructions
    test_email_receiving
    
    echo ""
    echo "🎉 SES email receiving setup completed!"
    echo "💡 Don't forget to configure MX records in your DNS provider"
    echo "📧 Test by sending an email with a document attachment to: ${EMAIL_ADDRESS}"
}

# Execute main function
main "$@"