#!/bin/bash

# AutoSpec.AI Domain and DNS Setup
# Automates domain purchase, DNS configuration, and SSL certificate setup

set -e

DOMAIN="auto-spec.ai"
REGION="us-east-1"
ENV="prod"
NOTIFICATION_EMAIL="ai.autospec@gmail.com"

echo "🌐 Setting up domain and DNS for AutoSpec.AI..."
echo "Domain: $DOMAIN"
echo "Region: $REGION"
echo "Environment: $ENV"
echo "Notification Email: $NOTIFICATION_EMAIL"

# Function to check if domain is available
check_domain_availability() {
    echo "🔍 Checking domain availability..."
    
    AVAILABILITY=$(aws route53domains check-domain-availability \
        --domain-name "$DOMAIN" \
        --region us-east-1 \
        --query 'Availability' \
        --output text)
    
    echo "Domain availability: $AVAILABILITY"
    return 0
}

# Function to register domain
register_domain() {
    echo "💳 Registering domain: $DOMAIN"
    
    # Create domain registration request
    aws route53domains register-domain \
        --domain-name "$DOMAIN" \
        --duration-in-years 1 \
        --auto-renew \
        --admin-contact '{
            "FirstName": "AutoSpec",
            "LastName": "Administrator", 
            "ContactType": "COMPANY",
            "OrganizationName": "AutoSpec AI",
            "AddressLine1": "123 Tech Street",
            "City": "San Francisco",
            "State": "CA",
            "CountryCode": "US",
            "ZipCode": "94105",
            "PhoneNumber": "+1.5551234567",
            "Email": "'$NOTIFICATION_EMAIL'"
        }' \
        --registrant-contact '{
            "FirstName": "AutoSpec",
            "LastName": "Administrator",
            "ContactType": "COMPANY", 
            "OrganizationName": "AutoSpec AI",
            "AddressLine1": "123 Tech Street",
            "City": "San Francisco",
            "State": "CA",
            "CountryCode": "US",
            "ZipCode": "94105",
            "PhoneNumber": "+1.5551234567",
            "Email": "'$NOTIFICATION_EMAIL'"
        }' \
        --tech-contact '{
            "FirstName": "AutoSpec",
            "LastName": "Administrator",
            "ContactType": "COMPANY",
            "OrganizationName": "AutoSpec AI", 
            "AddressLine1": "123 Tech Street",
            "City": "San Francisco",
            "State": "CA",
            "CountryCode": "US",
            "ZipCode": "94105",
            "PhoneNumber": "+1.5551234567",
            "Email": "'$NOTIFICATION_EMAIL'"
        }' \
        --privacy-protect-admin-contact \
        --privacy-protect-registrant-contact \
        --privacy-protect-tech-contact \
        --region us-east-1
    
    echo "✅ Domain registration initiated. Check email for confirmation."
}

# Function to create hosted zone
create_hosted_zone() {
    echo "🏗️  Creating Route 53 hosted zone..."
    
    # Check if hosted zone already exists
    EXISTING_ZONE=$(aws route53 list-hosted-zones-by-name \
        --dns-name "$DOMAIN" \
        --query "HostedZones[?Name=='$DOMAIN.'].Id" \
        --output text 2>/dev/null || echo "")
    
    if [ -n "$EXISTING_ZONE" ]; then
        echo "  ⚠️  Hosted zone already exists: $EXISTING_ZONE"
        HOSTED_ZONE_ID="$EXISTING_ZONE"
    else
        echo "  ✅ Creating new hosted zone for $DOMAIN"
        
        HOSTED_ZONE_ID=$(aws route53 create-hosted-zone \
            --name "$DOMAIN" \
            --caller-reference "autospec-$(date +%s)" \
            --hosted-zone-config Comment="AutoSpec.AI production hosted zone" \
            --query 'HostedZone.Id' \
            --output text)
        
        echo "Created hosted zone: $HOSTED_ZONE_ID"
    fi
    
    # Get name servers
    NAME_SERVERS=$(aws route53 get-hosted-zone \
        --id "$HOSTED_ZONE_ID" \
        --query 'DelegationSet.NameServers' \
        --output text)
    
    echo "📝 Name servers for $DOMAIN:"
    echo "$NAME_SERVERS" | tr '\t' '\n' | sed 's/^/  • /'
    
    # Export for use in other functions
    export HOSTED_ZONE_ID
}

# Function to request SSL certificate
request_ssl_certificate() {
    echo "🔒 Requesting SSL certificate..."
    
    # Request certificate for domain and wildcard subdomain
    CERT_ARN=$(aws acm request-certificate \
        --domain-name "$DOMAIN" \
        --subject-alternative-names "*.$DOMAIN" \
        --validation-method DNS \
        --region "$REGION" \
        --query 'CertificateArn' \
        --output text)
    
    echo "Certificate requested: $CERT_ARN"
    
    # Wait for certificate to be issued
    echo "⏳ Waiting for certificate validation records..."
    sleep 10
    
    # Get DNS validation records
    VALIDATION_RECORDS=$(aws acm describe-certificate \
        --certificate-arn "$CERT_ARN" \
        --region "$REGION" \
        --query 'Certificate.DomainValidationOptions[*].ResourceRecord' \
        --output json)
    
    echo "📋 DNS validation records:"
    echo "$VALIDATION_RECORDS" | jq -r '.[] | "  • Name: \(.Name) | Value: \(.Value) | Type: \(.Type)"'
    
    # Create DNS validation records in Route 53
    echo "🔧 Creating DNS validation records in Route 53..."
    
    echo "$VALIDATION_RECORDS" | jq -c '.[]' | while read -r record; do
        RECORD_NAME=$(echo "$record" | jq -r '.Name')
        RECORD_VALUE=$(echo "$record" | jq -r '.Value')
        RECORD_TYPE=$(echo "$record" | jq -r '.Type')
        
        echo "Adding record: $RECORD_NAME ($RECORD_TYPE)"
        
        aws route53 change-resource-record-sets \
            --hosted-zone-id "$HOSTED_ZONE_ID" \
            --change-batch '{
                "Changes": [{
                    "Action": "CREATE",
                    "ResourceRecordSet": {
                        "Name": "'$RECORD_NAME'",
                        "Type": "'$RECORD_TYPE'",
                        "TTL": 300,
                        "ResourceRecords": [{"Value": "\"'$RECORD_VALUE'\""}]
                    }
                }]
            }' >/dev/null
    done
    
    echo "✅ SSL certificate validation records created"
    echo "Certificate ARN: $CERT_ARN"
    
    # Export for use in deployment
    export CERT_ARN
}

# Function to create application DNS records
create_app_dns_records() {
    echo "🚀 Creating application DNS records..."
    
    # Placeholder values - will be updated during deployment
    CLOUDFRONT_DOMAIN="placeholder.cloudfront.net"
    API_GATEWAY_DOMAIN="placeholder.execute-api.us-east-1.amazonaws.com"
    
    # Create DNS records for application
    cat > /tmp/dns-records.json << EOF
{
    "Changes": [
        {
            "Action": "CREATE",
            "ResourceRecordSet": {
                "Name": "app.$DOMAIN",
                "Type": "CNAME",
                "TTL": 300,
                "ResourceRecords": [{"Value": "$CLOUDFRONT_DOMAIN"}]
            }
        },
        {
            "Action": "CREATE", 
            "ResourceRecordSet": {
                "Name": "www.$DOMAIN",
                "Type": "CNAME",
                "TTL": 300,
                "ResourceRecords": [{"Value": "$CLOUDFRONT_DOMAIN"}]
            }
        },
        {
            "Action": "CREATE",
            "ResourceRecordSet": {
                "Name": "api.$DOMAIN", 
                "Type": "CNAME",
                "TTL": 300,
                "ResourceRecords": [{"Value": "$API_GATEWAY_DOMAIN"}]
            }
        },
        {
            "Action": "CREATE",
            "ResourceRecordSet": {
                "Name": "documents.$DOMAIN",
                "Type": "MX",
                "TTL": 300,
                "ResourceRecords": [{"Value": "10 inbound-smtp.$REGION.amazonaws.com"}]
            }
        }
    ]
}
EOF

    echo "📝 Creating application DNS records..."
    aws route53 change-resource-record-sets \
        --hosted-zone-id "$HOSTED_ZONE_ID" \
        --change-batch file:///tmp/dns-records.json

    rm /tmp/dns-records.json
    echo "✅ Application DNS records created (with placeholder values)"
}

# Function to setup email authentication records
setup_email_authentication() {
    echo "📧 Setting up email authentication records..."
    
    # Create SPF record
    aws route53 change-resource-record-sets \
        --hosted-zone-id "$HOSTED_ZONE_ID" \
        --change-batch '{
            "Changes": [{
                "Action": "CREATE",
                "ResourceRecordSet": {
                    "Name": "'$DOMAIN'",
                    "Type": "TXT",
                    "TTL": 300,
                    "ResourceRecords": [{"Value": "\"v=spf1 include:amazonses.com ~all\""}]
                }
            }]
        }'
    
    # Create DMARC record
    aws route53 change-resource-record-sets \
        --hosted-zone-id "$HOSTED_ZONE_ID" \
        --change-batch '{
            "Changes": [{
                "Action": "CREATE", 
                "ResourceRecordSet": {
                    "Name": "_dmarc.'$DOMAIN'",
                    "Type": "TXT",
                    "TTL": 300,
                    "ResourceRecords": [{"Value": "\"v=DMARC1; p=quarantine; rua=mailto:'$NOTIFICATION_EMAIL'\""}]
                }
            }]
        }'
    
    echo "✅ Email authentication records created"
}

# Function to save domain configuration
save_domain_config() {
    echo "💾 Saving domain configuration..."
    
    # Create domain configuration file
    cat > "/mnt/c/Users/sghar/CascadeProjects/AutoSpecAI/config/domain-config.json" << EOF
{
    "domain": "$DOMAIN",
    "hosted_zone_id": "$HOSTED_ZONE_ID",
    "certificate_arn": "$CERT_ARN",
    "region": "$REGION",
    "email": "$NOTIFICATION_EMAIL",
    "subdomains": {
        "app": "app.$DOMAIN",
        "api": "api.$DOMAIN", 
        "www": "www.$DOMAIN",
        "documents": "documents.$DOMAIN"
    },
    "dns_records": {
        "spf": "v=spf1 include:amazonses.com ~all",
        "dmarc": "v=DMARC1; p=quarantine; rua=mailto:$NOTIFICATION_EMAIL"
    },
    "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF

    echo "✅ Domain configuration saved to config/domain-config.json"
}

# Main execution
main() {
    echo "🎯 Starting domain setup process..."
    
    # Check if domain is available and register if needed
    if check_domain_availability; then
        if [ "$AVAILABILITY" = "AVAILABLE" ]; then
            echo "✅ Domain is available for registration"
            read -p "🤔 Do you want to register $DOMAIN now? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                register_domain
                echo "⏳ Domain registration in progress. Continuing with DNS setup..."
            else
                echo "⚠️  Skipping domain registration. You'll need to register manually."
            fi
        else
            echo "ℹ️  Domain not available for registration (may already be owned)"
        fi
    fi
    
    # Create hosted zone and DNS records
    create_hosted_zone
    request_ssl_certificate
    create_app_dns_records
    setup_email_authentication
    save_domain_config
    
    echo ""
    echo "✅ Domain and DNS setup complete!"
    echo ""
    echo "📋 Summary:"
    echo "  • Domain: $DOMAIN"
    echo "  • Hosted Zone ID: $HOSTED_ZONE_ID" 
    echo "  • SSL Certificate ARN: $CERT_ARN"
    echo "  • Application URL: https://app.$DOMAIN"
    echo "  • API URL: https://api.$DOMAIN"
    echo "  • Document Email: documents@$DOMAIN"
    echo ""
    echo "⚠️  Important Next Steps:"
    echo "  1. If domain was registered, check email for verification"
    echo "  2. Update name servers if domain was registered elsewhere"
    echo "  3. SSL certificate will auto-validate via DNS (takes 5-10 minutes)"
    echo "  4. DNS records will be updated with real values during deployment"
    echo ""
    echo "🚀 Ready for monitoring and security setup!"
}

# Run main function
main "$@"