#!/bin/bash

# AutoSpec.AI Security and WAF Configuration
# Sets up comprehensive security controls, WAF rules, and compliance measures

set -e

REGION="us-east-1"
ENV="prod"
PROJECT="autospec-ai"
DOMAIN="auto-spec.ai"
NOTIFICATION_EMAIL="ai.autospec@gmail.com"

echo "🔒 Setting up security and WAF for AutoSpec.AI..."
echo "Region: $REGION"
echo "Environment: $ENV"
echo "Domain: $DOMAIN"

# Function to create WAF Web ACL
create_waf_web_acl() {
    echo "🛡️  Creating WAF Web ACL..."
    
    # Create WAF Web ACL with comprehensive rules
    WAF_ACL_CONFIG=$(cat << 'EOF'
{
    "Name": "autospec-ai-prod-web-acl",
    "Scope": "CLOUDFRONT",
    "DefaultAction": {
        "Allow": {}
    },
    "Description": "WAF rules for AutoSpec.AI production security",
    "Rules": [
        {
            "Name": "RateLimitRule",
            "Priority": 1,
            "Statement": {
                "RateBasedStatement": {
                    "Limit": 2000,
                    "AggregateKeyType": "IP"
                }
            },
            "Action": {
                "Block": {}
            },
            "VisibilityConfig": {
                "SampledRequestsEnabled": true,
                "CloudWatchMetricsEnabled": true,
                "MetricName": "RateLimitRule"
            }
        },
        {
            "Name": "AWSManagedRulesCommonRuleSet",
            "Priority": 2,
            "OverrideAction": {
                "None": {}
            },
            "Statement": {
                "ManagedRuleGroupStatement": {
                    "VendorName": "AWS",
                    "Name": "AWSManagedRulesCommonRuleSet"
                }
            },
            "VisibilityConfig": {
                "SampledRequestsEnabled": true,
                "CloudWatchMetricsEnabled": true,
                "MetricName": "CommonRuleSet"
            }
        },
        {
            "Name": "AWSManagedRulesKnownBadInputsRuleSet",
            "Priority": 3,
            "OverrideAction": {
                "None": {}
            },
            "Statement": {
                "ManagedRuleGroupStatement": {
                    "VendorName": "AWS",
                    "Name": "AWSManagedRulesKnownBadInputsRuleSet"
                }
            },
            "VisibilityConfig": {
                "SampledRequestsEnabled": true,
                "CloudWatchMetricsEnabled": true,
                "MetricName": "KnownBadInputs"
            }
        },
        {
            "Name": "AWSManagedRulesSQLiRuleSet",
            "Priority": 4,
            "OverrideAction": {
                "None": {}
            },
            "Statement": {
                "ManagedRuleGroupStatement": {
                    "VendorName": "AWS",
                    "Name": "AWSManagedRulesSQLiRuleSet"
                }
            },
            "VisibilityConfig": {
                "SampledRequestsEnabled": true,
                "CloudWatchMetricsEnabled": true,
                "MetricName": "SQLiRuleSet"
            }
        },
        {
            "Name": "IPReputationList",
            "Priority": 5,
            "OverrideAction": {
                "None": {}
            },
            "Statement": {
                "ManagedRuleGroupStatement": {
                    "VendorName": "AWS",
                    "Name": "AWSManagedRulesAmazonIpReputationList"
                }
            },
            "VisibilityConfig": {
                "SampledRequestsEnabled": true,
                "CloudWatchMetricsEnabled": true,
                "MetricName": "IPReputationList"
            }
        }
    ],
    "VisibilityConfig": {
        "SampledRequestsEnabled": true,
        "CloudWatchMetricsEnabled": true,
        "MetricName": "autospecAIWebACL"
    }
}
EOF
)

    # Create the Web ACL
    WAF_ACL_ARN=$(aws wafv2 create-web-acl \
        --scope CLOUDFRONT \
        --region us-east-1 \
        --cli-input-json "$WAF_ACL_CONFIG" \
        --query 'Summary.ARN' \
        --output text)
    
    echo "  ✅ WAF Web ACL created: $WAF_ACL_ARN"
    export WAF_ACL_ARN
}

# Function to create IP Sets for additional security
create_ip_sets() {
    echo "🌍 Creating IP sets for geographic and threat protection..."
    
    # Create IP set for blocked countries (example: high-risk countries)
    BLOCKED_COUNTRIES_IPV4=$(cat << 'EOF'
{
    "Name": "BlockedCountriesIPv4",
    "Scope": "CLOUDFRONT",
    "IPAddressVersion": "IPV4",
    "Addresses": [],
    "Description": "IPv4 addresses from blocked countries"
}
EOF
)

    aws wafv2 create-ip-set \
        --scope CLOUDFRONT \
        --region us-east-1 \
        --cli-input-json "$BLOCKED_COUNTRIES_IPV4" >/dev/null
    
    # Create IP set for allowed admin IPs (to be populated)
    ADMIN_ALLOW_IPV4=$(cat << 'EOF'
{
    "Name": "AdminAllowIPv4",
    "Scope": "CLOUDFRONT", 
    "IPAddressVersion": "IPV4",
    "Addresses": ["0.0.0.0/32"],
    "Description": "Allowed admin IP addresses"
}
EOF
)

    aws wafv2 create-ip-set \
        --scope CLOUDFRONT \
        --region us-east-1 \
        --cli-input-json "$ADMIN_ALLOW_IPV4" >/dev/null
    
    echo "  ✅ IP sets created for geographic and admin access control"
}

# Function to enable GuardDuty
enable_guardduty() {
    echo "🔍 Enabling GuardDuty threat detection..."
    
    # Check if GuardDuty is already enabled
    DETECTOR_ID=$(aws guardduty list-detectors \
        --region "$REGION" \
        --query 'DetectorIds[0]' \
        --output text 2>/dev/null || echo "None")
    
    if [ "$DETECTOR_ID" = "None" ] || [ -z "$DETECTOR_ID" ]; then
        echo "  🛡️  Creating GuardDuty detector..."
        DETECTOR_ID=$(aws guardduty create-detector \
            --enable \
            --finding-publishing-frequency FIFTEEN_MINUTES \
            --region "$REGION" \
            --query 'DetectorId' \
            --output text)
        
        echo "  ✅ GuardDuty detector created: $DETECTOR_ID"
    else
        echo "  ℹ️  GuardDuty already enabled: $DETECTOR_ID"
    fi
    
    # Enable S3 protection
    aws guardduty update-detector \
        --detector-id "$DETECTOR_ID" \
        --data-sources '{
            "S3Logs": {"Enable": true},
            "MalwareProtection": {"ScanEc2InstanceWithFindings": {"EbsVolumes": true}},
            "Kubernetes": {"AuditLogs": {"Enable": true}}
        }' \
        --region "$REGION"
    
    echo "  ✅ GuardDuty S3 and malware protection enabled"
    export DETECTOR_ID
}

# Function to enable AWS Config
enable_aws_config() {
    echo "📋 Enabling AWS Config for compliance monitoring..."
    
    # Create S3 bucket for Config
    CONFIG_BUCKET="$PROJECT-$ENV-config-$(date +%s)"
    aws s3 mb "s3://$CONFIG_BUCKET" --region "$REGION"
    
    # Create IAM role for Config
    CONFIG_ROLE_POLICY=$(cat << 'EOF'
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "config.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
EOF
)

    aws iam create-role \
        --role-name "$PROJECT-$ENV-config-role" \
        --assume-role-policy-document "$CONFIG_ROLE_POLICY" \
        --region "$REGION" 2>/dev/null || echo "  ℹ️  Config role may already exist"
    
    # Attach managed policy
    aws iam attach-role-policy \
        --role-name "$PROJECT-$ENV-config-role" \
        --policy-arn "arn:aws:iam::aws:policy/service-role/ConfigRole" \
        --region "$REGION"
    
    # Create Config delivery channel
    aws configservice put-delivery-channel \
        --delivery-channel '{
            "name": "'$PROJECT-$ENV'-config-delivery-channel",
            "s3BucketName": "'$CONFIG_BUCKET'",
            "configSnapshotDeliveryProperties": {
                "deliveryFrequency": "TwentyFour_Hours"
            }
        }' \
        --region "$REGION" 2>/dev/null || echo "  ℹ️  Config delivery channel may already exist"
    
    # Create Config configuration recorder
    aws configservice put-configuration-recorder \
        --configuration-recorder '{
            "name": "'$PROJECT-$ENV'-config-recorder",
            "roleARN": "arn:aws:iam::'$(aws sts get-caller-identity --query Account --output text)':role/'$PROJECT-$ENV'-config-role",
            "recordingGroup": {
                "allSupported": true,
                "includeGlobalResourceTypes": true
            }
        }' \
        --region "$REGION" 2>/dev/null || echo "  ℹ️  Config recorder may already exist"
    
    # Start Config recorder
    aws configservice start-configuration-recorder \
        --configuration-recorder-name "$PROJECT-$ENV-config-recorder" \
        --region "$REGION"
    
    echo "  ✅ AWS Config enabled for compliance monitoring"
}

# Function to setup Security Hub
enable_security_hub() {
    echo "🛡️  Enabling Security Hub..."
    
    # Enable Security Hub
    aws securityhub enable-security-hub \
        --enable-default-standards \
        --region "$REGION" 2>/dev/null || echo "  ℹ️  Security Hub may already be enabled"
    
    # Enable important standards
    STANDARDS=(
        "arn:aws:securityhub:$REGION::standard/aws-foundational-security/v/1.0.0"
        "arn:aws:securityhub:$REGION::standard/cis-aws-foundations-benchmark/v/1.2.0"
    )
    
    for standard in "${STANDARDS[@]}"; do
        aws securityhub batch-enable-standards \
            --standards-subscription-requests StandardsArn="$standard" \
            --region "$REGION" 2>/dev/null || echo "  ℹ️  Standard may already be enabled: $standard"
    done
    
    echo "  ✅ Security Hub enabled with AWS and CIS standards"
}

# Function to create security groups
create_security_groups() {
    echo "🔐 Creating security groups..."
    
    # Get default VPC ID
    VPC_ID=$(aws ec2 describe-vpcs \
        --filters "Name=isDefault,Values=true" \
        --query 'Vpcs[0].VpcId' \
        --output text \
        --region "$REGION")
    
    # Create ALB security group
    ALB_SG_ID=$(aws ec2 create-security-group \
        --group-name "$PROJECT-$ENV-alb-sg" \
        --description "Security group for AutoSpec.AI ALB" \
        --vpc-id "$VPC_ID" \
        --region "$REGION" \
        --query 'GroupId' \
        --output text)
    
    # Add ALB security group rules
    aws ec2 authorize-security-group-ingress \
        --group-id "$ALB_SG_ID" \
        --protocol tcp \
        --port 80 \
        --cidr 0.0.0.0/0 \
        --region "$REGION"
    
    aws ec2 authorize-security-group-ingress \
        --group-id "$ALB_SG_ID" \
        --protocol tcp \
        --port 443 \
        --cidr 0.0.0.0/0 \
        --region "$REGION"
    
    # Create Lambda security group
    LAMBDA_SG_ID=$(aws ec2 create-security-group \
        --group-name "$PROJECT-$ENV-lambda-sg" \
        --description "Security group for AutoSpec.AI Lambda functions" \
        --vpc-id "$VPC_ID" \
        --region "$REGION" \
        --query 'GroupId' \
        --output text)
    
    # Add Lambda security group rules (outbound HTTPS)
    aws ec2 authorize-security-group-egress \
        --group-id "$LAMBDA_SG_ID" \
        --protocol tcp \
        --port 443 \
        --cidr 0.0.0.0/0 \
        --region "$REGION"
    
    echo "  ✅ Security groups created: ALB ($ALB_SG_ID), Lambda ($LAMBDA_SG_ID)"
    export ALB_SG_ID LAMBDA_SG_ID
}

# Function to setup encryption keys
setup_encryption_keys() {
    echo "🔑 Setting up encryption keys..."
    
    # Create KMS key for application encryption
    KMS_KEY_POLICY=$(cat << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "Enable IAM User Permissions",
            "Effect": "Allow",
            "Principal": {
                "AWS": "arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):root"
            },
            "Action": "kms:*",
            "Resource": "*"
        },
        {
            "Sid": "Allow AutoSpec.AI services",
            "Effect": "Allow",
            "Principal": {
                "Service": [
                    "lambda.amazonaws.com",
                    "s3.amazonaws.com",
                    "dynamodb.amazonaws.com",
                    "secretsmanager.amazonaws.com"
                ]
            },
            "Action": [
                "kms:Encrypt",
                "kms:Decrypt",
                "kms:ReEncrypt*",
                "kms:GenerateDataKey*",
                "kms:DescribeKey"
            ],
            "Resource": "*"
        }
    ]
}
EOF
)

    KMS_KEY_ID=$(aws kms create-key \
        --policy "$KMS_KEY_POLICY" \
        --description "AutoSpec.AI production encryption key" \
        --region "$REGION" \
        --query 'KeyMetadata.KeyId' \
        --output text)
    
    # Create key alias
    aws kms create-alias \
        --alias-name "alias/$PROJECT-$ENV-encryption-key" \
        --target-key-id "$KMS_KEY_ID" \
        --region "$REGION"
    
    echo "  ✅ KMS encryption key created: $KMS_KEY_ID"
    export KMS_KEY_ID
}

# Function to enable CloudTrail
enable_cloudtrail() {
    echo "📊 Enabling CloudTrail for audit logging..."
    
    # Create S3 bucket for CloudTrail
    CLOUDTRAIL_BUCKET="$PROJECT-$ENV-cloudtrail-$(date +%s)"
    aws s3 mb "s3://$CLOUDTRAIL_BUCKET" --region "$REGION"
    
    # Create CloudTrail bucket policy
    BUCKET_POLICY=$(cat << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AWSCloudTrailAclCheck",
            "Effect": "Allow",
            "Principal": {
                "Service": "cloudtrail.amazonaws.com"
            },
            "Action": "s3:GetBucketAcl",
            "Resource": "arn:aws:s3:::$CLOUDTRAIL_BUCKET"
        },
        {
            "Sid": "AWSCloudTrailWrite",
            "Effect": "Allow",
            "Principal": {
                "Service": "cloudtrail.amazonaws.com"
            },
            "Action": "s3:PutObject",
            "Resource": "arn:aws:s3:::$CLOUDTRAIL_BUCKET/*",
            "Condition": {
                "StringEquals": {
                    "s3:x-amz-acl": "bucket-owner-full-control"
                }
            }
        }
    ]
}
EOF
)

    # Apply bucket policy
    aws s3api put-bucket-policy \
        --bucket "$CLOUDTRAIL_BUCKET" \
        --policy "$BUCKET_POLICY"
    
    # Create CloudTrail
    aws cloudtrail create-trail \
        --name "$PROJECT-$ENV-audit-trail" \
        --s3-bucket-name "$CLOUDTRAIL_BUCKET" \
        --include-global-service-events \
        --is-multi-region-trail \
        --enable-log-file-validation \
        --region "$REGION"
    
    # Start logging
    aws cloudtrail start-logging \
        --name "$PROJECT-$ENV-audit-trail" \
        --region "$REGION"
    
    echo "  ✅ CloudTrail enabled for comprehensive audit logging"
}

# Function to save security configuration
save_security_config() {
    echo "💾 Saving security configuration..."
    
    cat > "/mnt/c/Users/sghar/CascadeProjects/AutoSpecAI/config/security-config.json" << EOF
{
    "waf": {
        "web_acl_arn": "$WAF_ACL_ARN",
        "rate_limit": 2000,
        "managed_rules": [
            "AWSManagedRulesCommonRuleSet",
            "AWSManagedRulesKnownBadInputsRuleSet", 
            "AWSManagedRulesSQLiRuleSet",
            "AWSManagedRulesAmazonIpReputationList"
        ]
    },
    "guardduty": {
        "detector_id": "$DETECTOR_ID",
        "s3_protection": true,
        "malware_protection": true
    },
    "security_groups": {
        "alb": "$ALB_SG_ID",
        "lambda": "$LAMBDA_SG_ID"
    },
    "encryption": {
        "kms_key_id": "$KMS_KEY_ID",
        "kms_alias": "alias/$PROJECT-$ENV-encryption-key"
    },
    "compliance": {
        "config_enabled": true,
        "security_hub_enabled": true,
        "cloudtrail_enabled": true
    },
    "region": "$REGION",
    "environment": "$ENV",
    "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF

    echo "  ✅ Security configuration saved to config/security-config.json"
}

# Main execution
main() {
    echo "🎯 Starting security and WAF setup..."
    
    create_waf_web_acl
    create_ip_sets
    enable_guardduty
    enable_aws_config
    enable_security_hub
    create_security_groups
    setup_encryption_keys
    enable_cloudtrail
    save_security_config
    
    echo ""
    echo "✅ Security and WAF setup complete!"
    echo ""
    echo "📋 Security Summary:"
    echo "  • WAF Web ACL: Rate limiting + AWS managed rules"
    echo "  • GuardDuty: Threat detection enabled"
    echo "  • Security Hub: AWS + CIS standards enabled"
    echo "  • AWS Config: Compliance monitoring active"
    echo "  • CloudTrail: Full audit logging enabled"
    echo "  • KMS Encryption: Application-specific key created"
    echo "  • Security Groups: ALB and Lambda configured"
    echo ""
    echo "🛡️  Security Features:"
    echo "  • Rate limiting: 2000 requests/5min per IP"
    echo "  • SQL injection protection"
    echo "  • XSS protection"
    echo "  • Known bad inputs blocking"
    echo "  • IP reputation filtering"
    echo "  • Real-time threat detection"
    echo ""
    echo "📊 Compliance Standards:"
    echo "  • AWS Foundational Security Standard"
    echo "  • CIS AWS Foundations Benchmark"
    echo "  • Continuous compliance monitoring"
    echo ""
    echo "🚀 Ready for final environment configuration!"
}

# Run main function
main "$@"