#!/bin/bash
# Fix AWS CLI Configuration for Production Deployment

echo "🔧 AutoSpec.AI AWS CLI Configuration Fix"
echo "========================================"

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found. Please install AWS CLI v2:"
    echo "   https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
    exit 1
fi

echo "✅ AWS CLI found: $(aws --version)"

# Create .aws directory if it doesn't exist
mkdir -p ~/.aws

# Backup existing files
if [ -f ~/.aws/credentials ]; then
    cp ~/.aws/credentials ~/.aws/credentials.backup
    echo "📁 Backed up existing credentials to ~/.aws/credentials.backup"
fi

if [ -f ~/.aws/config ]; then
    cp ~/.aws/config ~/.aws/config.backup
    echo "📁 Backed up existing config to ~/.aws/config.backup"
fi

# Create properly formatted credentials file
echo "🔑 Please enter your AWS credentials:"
read -p "AWS Access Key ID: " aws_access_key_id
read -s -p "AWS Secret Access Key: " aws_secret_access_key
echo

# Write credentials file
cat > ~/.aws/credentials << EOF
[default]
aws_access_key_id = $aws_access_key_id
aws_secret_access_key = $aws_secret_access_key
EOF

# Write config file
cat > ~/.aws/config << EOF
[default]
region = us-east-1
output = json
cli_timestamp_format = iso8601
cli_pager = 
cli_follow_urlparam = false
EOF

echo "✅ AWS CLI configuration updated"

# Test the configuration
echo "🧪 Testing AWS CLI configuration..."
if aws sts get-caller-identity &> /dev/null; then
    echo "✅ AWS CLI working! Account: $(aws sts get-caller-identity --query 'Account' --output text)"
    echo "✅ Region: $(aws configure get region)"
    
    echo ""
    echo "🚀 Ready to deploy! Run:"
    echo "   ./deploy-s3-upload.sh"
else
    echo "❌ AWS CLI test failed. Please check your credentials."
    echo "   You can also configure manually with: aws configure"
fi