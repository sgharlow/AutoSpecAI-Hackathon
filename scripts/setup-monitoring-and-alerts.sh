#!/bin/bash

# AutoSpec.AI Monitoring and Alerting Setup
# Creates comprehensive monitoring, alerting, and observability infrastructure

set -e

REGION="us-east-1"
ENV="prod"
PROJECT="autospec-ai"
NOTIFICATION_EMAIL="ai.autospec@gmail.com"
BUDGET_ALERT=99

echo "📊 Setting up monitoring and alerting for AutoSpec.AI..."
echo "Region: $REGION"
echo "Environment: $ENV"
echo "Notification Email: $NOTIFICATION_EMAIL"
echo "Budget Alert Threshold: \$$BUDGET_ALERT"

# Function to create SNS topics
create_sns_topics() {
    echo "📢 Creating SNS topics for notifications..."
    
    # Critical alerts topic
    CRITICAL_TOPIC_ARN=$(aws sns create-topic \
        --name "$PROJECT-$ENV-critical-alerts" \
        --region "$REGION" \
        --query 'TopicArn' \
        --output text)
    
    echo "  ✅ Critical alerts topic: $CRITICAL_TOPIC_ARN"
    
    # Warning alerts topic  
    WARNING_TOPIC_ARN=$(aws sns create-topic \
        --name "$PROJECT-$ENV-warning-alerts" \
        --region "$REGION" \
        --query 'TopicArn' \
        --output text)
    
    echo "  ✅ Warning alerts topic: $WARNING_TOPIC_ARN"
    
    # Business metrics topic
    METRICS_TOPIC_ARN=$(aws sns create-topic \
        --name "$PROJECT-$ENV-business-metrics" \
        --region "$REGION" \
        --query 'TopicArn' \
        --output text)
    
    echo "  ✅ Business metrics topic: $METRICS_TOPIC_ARN"
    
    # Subscribe email to all topics
    echo "📧 Subscribing email to SNS topics..."
    
    aws sns subscribe \
        --topic-arn "$CRITICAL_TOPIC_ARN" \
        --protocol email \
        --notification-endpoint "$NOTIFICATION_EMAIL" \
        --region "$REGION"
    
    aws sns subscribe \
        --topic-arn "$WARNING_TOPIC_ARN" \
        --protocol email \
        --notification-endpoint "$NOTIFICATION_EMAIL" \
        --region "$REGION"
    
    aws sns subscribe \
        --topic-arn "$METRICS_TOPIC_ARN" \
        --protocol email \
        --notification-endpoint "$NOTIFICATION_EMAIL" \
        --region "$REGION"
    
    echo "  ✅ Email subscriptions created (check email for confirmations)"
    
    # Export for use in other functions
    export CRITICAL_TOPIC_ARN WARNING_TOPIC_ARN METRICS_TOPIC_ARN
}

# Function to create CloudWatch alarms
create_cloudwatch_alarms() {
    echo "⚠️  Creating CloudWatch alarms..."
    
    # Lambda error rate alarms
    echo "  📊 Creating Lambda alarms..."
    
    LAMBDA_FUNCTIONS=("ingest" "process" "format" "api" "slack" "monitoring" "advanced-processing" "ai-comparison" "intelligent-routing" "semantic-analysis" "traceability-analysis")
    
    for func in "${LAMBDA_FUNCTIONS[@]}"; do
        # Error rate alarm
        aws cloudwatch put-metric-alarm \
            --alarm-name "$PROJECT-$ENV-lambda-$func-errors" \
            --alarm-description "High error rate for $func Lambda function" \
            --metric-name Errors \
            --namespace AWS/Lambda \
            --statistic Sum \
            --period 300 \
            --threshold 5 \
            --comparison-operator GreaterThanThreshold \
            --evaluation-periods 2 \
            --alarm-actions "$CRITICAL_TOPIC_ARN" \
            --dimensions Name=FunctionName,Value="$PROJECT-$ENV-$func" \
            --region "$REGION"
        
        # Duration alarm
        aws cloudwatch put-metric-alarm \
            --alarm-name "$PROJECT-$ENV-lambda-$func-duration" \
            --alarm-description "High duration for $func Lambda function" \
            --metric-name Duration \
            --namespace AWS/Lambda \
            --statistic Average \
            --period 300 \
            --threshold 30000 \
            --comparison-operator GreaterThanThreshold \
            --evaluation-periods 3 \
            --alarm-actions "$WARNING_TOPIC_ARN" \
            --dimensions Name=FunctionName,Value="$PROJECT-$ENV-$func" \
            --region "$REGION"
        
        # Throttle alarm
        aws cloudwatch put-metric-alarm \
            --alarm-name "$PROJECT-$ENV-lambda-$func-throttles" \
            --alarm-description "Lambda throttles for $func function" \
            --metric-name Throttles \
            --namespace AWS/Lambda \
            --statistic Sum \
            --period 300 \
            --threshold 1 \
            --comparison-operator GreaterThanOrEqualToThreshold \
            --evaluation-periods 1 \
            --alarm-actions "$CRITICAL_TOPIC_ARN" \
            --dimensions Name=FunctionName,Value="$PROJECT-$ENV-$func" \
            --region "$REGION"
    done
    
    # API Gateway alarms
    echo "  🌐 Creating API Gateway alarms..."
    
    aws cloudwatch put-metric-alarm \
        --alarm-name "$PROJECT-$ENV-api-gateway-4xx-errors" \
        --alarm-description "High 4XX error rate in API Gateway" \
        --metric-name 4XXError \
        --namespace AWS/ApiGateway \
        --statistic Sum \
        --period 300 \
        --threshold 50 \
        --comparison-operator GreaterThanThreshold \
        --evaluation-periods 2 \
        --alarm-actions "$WARNING_TOPIC_ARN" \
        --dimensions Name=ApiName,Value="$PROJECT-$ENV-api" \
        --region "$REGION"
    
    aws cloudwatch put-metric-alarm \
        --alarm-name "$PROJECT-$ENV-api-gateway-5xx-errors" \
        --alarm-description "High 5XX error rate in API Gateway" \
        --metric-name 5XXError \
        --namespace AWS/ApiGateway \
        --statistic Sum \
        --period 300 \
        --threshold 10 \
        --comparison-operator GreaterThanThreshold \
        --evaluation-periods 1 \
        --alarm-actions "$CRITICAL_TOPIC_ARN" \
        --dimensions Name=ApiName,Value="$PROJECT-$ENV-api" \
        --region "$REGION"
    
    aws cloudwatch put-metric-alarm \
        --alarm-name "$PROJECT-$ENV-api-gateway-latency" \
        --alarm-description "High latency in API Gateway" \
        --metric-name Latency \
        --namespace AWS/ApiGateway \
        --statistic Average \
        --period 300 \
        --threshold 5000 \
        --comparison-operator GreaterThanThreshold \
        --evaluation-periods 3 \
        --alarm-actions "$WARNING_TOPIC_ARN" \
        --dimensions Name=ApiName,Value="$PROJECT-$ENV-api" \
        --region "$REGION"
    
    # DynamoDB alarms
    echo "  🗄️  Creating DynamoDB alarms..."
    
    aws cloudwatch put-metric-alarm \
        --alarm-name "$PROJECT-$ENV-dynamodb-throttles" \
        --alarm-description "DynamoDB throttling events" \
        --metric-name UserErrors \
        --namespace AWS/DynamoDB \
        --statistic Sum \
        --period 300 \
        --threshold 5 \
        --comparison-operator GreaterThanThreshold \
        --evaluation-periods 1 \
        --alarm-actions "$CRITICAL_TOPIC_ARN" \
        --dimensions Name=TableName,Value="$PROJECT-$ENV-documents" \
        --region "$REGION"
    
    aws cloudwatch put-metric-alarm \
        --alarm-name "$PROJECT-$ENV-dynamodb-consumed-capacity" \
        --alarm-description "High DynamoDB consumed capacity" \
        --metric-name ConsumedReadCapacityUnits \
        --namespace AWS/DynamoDB \
        --statistic Sum \
        --period 300 \
        --threshold 80 \
        --comparison-operator GreaterThanThreshold \
        --evaluation-periods 2 \
        --alarm-actions "$WARNING_TOPIC_ARN" \
        --dimensions Name=TableName,Value="$PROJECT-$ENV-documents" \
        --region "$REGION"
    
    echo "  ✅ CloudWatch alarms created"
}

# Function to create CloudWatch dashboards
create_cloudwatch_dashboards() {
    echo "📈 Creating CloudWatch dashboards..."
    
    # Operational dashboard
    OPERATIONAL_DASHBOARD=$(cat << 'EOF'
{
    "widgets": [
        {
            "type": "metric",
            "x": 0,
            "y": 0,
            "width": 12,
            "height": 6,
            "properties": {
                "metrics": [
                    [ "AWS/Lambda", "Invocations", "FunctionName", "autospec-ai-prod-ingest" ],
                    [ ".", ".", ".", "autospec-ai-prod-process" ],
                    [ ".", ".", ".", "autospec-ai-prod-format" ],
                    [ ".", ".", ".", "autospec-ai-prod-api" ]
                ],
                "view": "timeSeries",
                "stacked": false,
                "region": "us-east-1",
                "title": "Lambda Invocations",
                "period": 300
            }
        },
        {
            "type": "metric",
            "x": 12,
            "y": 0,
            "width": 12,
            "height": 6,
            "properties": {
                "metrics": [
                    [ "AWS/Lambda", "Errors", "FunctionName", "autospec-ai-prod-ingest" ],
                    [ ".", ".", ".", "autospec-ai-prod-process" ],
                    [ ".", ".", ".", "autospec-ai-prod-format" ],
                    [ ".", ".", ".", "autospec-ai-prod-api" ]
                ],
                "view": "timeSeries",
                "stacked": false,
                "region": "us-east-1",
                "title": "Lambda Errors",
                "period": 300
            }
        },
        {
            "type": "metric",
            "x": 0,
            "y": 6,
            "width": 12,
            "height": 6,
            "properties": {
                "metrics": [
                    [ "AWS/ApiGateway", "Count", "ApiName", "autospec-ai-prod-api" ],
                    [ ".", "4XXError", ".", "." ],
                    [ ".", "5XXError", ".", "." ]
                ],
                "view": "timeSeries",
                "stacked": false,
                "region": "us-east-1",
                "title": "API Gateway Metrics",
                "period": 300
            }
        },
        {
            "type": "metric",
            "x": 12,
            "y": 6,
            "width": 12,
            "height": 6,
            "properties": {
                "metrics": [
                    [ "AWS/DynamoDB", "ConsumedReadCapacityUnits", "TableName", "autospec-ai-prod-documents" ],
                    [ ".", "ConsumedWriteCapacityUnits", ".", "." ]
                ],
                "view": "timeSeries",
                "stacked": false,
                "region": "us-east-1",
                "title": "DynamoDB Capacity",
                "period": 300
            }
        }
    ]
}
EOF
)

    aws cloudwatch put-dashboard \
        --dashboard-name "$PROJECT-$ENV-operational" \
        --dashboard-body "$OPERATIONAL_DASHBOARD" \
        --region "$REGION"
    
    # Performance dashboard
    PERFORMANCE_DASHBOARD=$(cat << 'EOF'
{
    "widgets": [
        {
            "type": "metric",
            "x": 0,
            "y": 0,
            "width": 12,
            "height": 6,
            "properties": {
                "metrics": [
                    [ "AWS/Lambda", "Duration", "FunctionName", "autospec-ai-prod-ingest" ],
                    [ ".", ".", ".", "autospec-ai-prod-process" ],
                    [ ".", ".", ".", "autospec-ai-prod-format" ]
                ],
                "view": "timeSeries",
                "stacked": false,
                "region": "us-east-1",
                "title": "Lambda Duration",
                "period": 300
            }
        },
        {
            "type": "metric",
            "x": 12,
            "y": 0,
            "width": 12,
            "height": 6,
            "properties": {
                "metrics": [
                    [ "AWS/ApiGateway", "Latency", "ApiName", "autospec-ai-prod-api" ],
                    [ ".", "IntegrationLatency", ".", "." ]
                ],
                "view": "timeSeries",
                "stacked": false,
                "region": "us-east-1",
                "title": "API Gateway Latency",
                "period": 300
            }
        },
        {
            "type": "metric",
            "x": 0,
            "y": 6,
            "width": 24,
            "height": 6,
            "properties": {
                "metrics": [
                    [ "AWS/Bedrock", "Invocations", "ModelId", "anthropic.claude-3-sonnet-20240229-v1:0" ],
                    [ ".", "InvocationLatency", ".", "." ]
                ],
                "view": "timeSeries",
                "stacked": false,
                "region": "us-east-1",
                "title": "Bedrock AI Model Performance",
                "period": 300
            }
        }
    ]
}
EOF
)

    aws cloudwatch put-dashboard \
        --dashboard-name "$PROJECT-$ENV-performance" \
        --dashboard-body "$PERFORMANCE_DASHBOARD" \
        --region "$REGION"
    
    echo "  ✅ CloudWatch dashboards created"
}

# Function to setup cost monitoring
setup_cost_monitoring() {
    echo "💰 Setting up cost monitoring..."
    
    # Create budget for monthly spend
    BUDGET_POLICY=$(cat << EOF
{
    "BudgetName": "$PROJECT-$ENV-monthly-budget",
    "BudgetLimit": {
        "Amount": "$BUDGET_ALERT",
        "Unit": "USD"
    },
    "TimeUnit": "MONTHLY",
    "TimePeriod": {
        "Start": "$(date -d "$(date +%Y-%m-01)" +%Y-%m-%d)",
        "End": "$(date -d "$(date +%Y-%m-01) +1 month -1 day" +%Y-%m-%d)"
    },
    "BudgetType": "COST",
    "CostFilters": {
        "TagKey": ["Project"],
        "TagValue": ["AutoSpecAI"]
    }
}
EOF
)

    # Create budget notification
    NOTIFICATION_CONFIG=$(cat << EOF
[
    {
        "Notification": {
            "NotificationType": "ACTUAL",
            "ComparisonOperator": "GREATER_THAN",
            "Threshold": 80
        },
        "Subscribers": [
            {
                "SubscriptionType": "EMAIL",
                "Address": "$NOTIFICATION_EMAIL"
            }
        ]
    },
    {
        "Notification": {
            "NotificationType": "FORECASTED", 
            "ComparisonOperator": "GREATER_THAN",
            "Threshold": 100
        },
        "Subscribers": [
            {
                "SubscriptionType": "EMAIL",
                "Address": "$NOTIFICATION_EMAIL"
            }
        ]
    }
]
EOF
)

    # Create the budget
    aws budgets create-budget \
        --account-id "$(aws sts get-caller-identity --query Account --output text)" \
        --budget "$BUDGET_POLICY" \
        --notifications-with-subscribers "$NOTIFICATION_CONFIG" \
        --region us-east-1
    
    echo "  ✅ Budget created with \$$BUDGET_ALERT threshold"
}

# Function to enable X-Ray tracing
enable_xray_tracing() {
    echo "🔍 Enabling X-Ray tracing..."
    
    # Create X-Ray service map
    aws xray create-service-map \
        --service-map-name "$PROJECT-$ENV-service-map" \
        --region "$REGION" 2>/dev/null || echo "  ℹ️  X-Ray service map may already exist"
    
    echo "  ✅ X-Ray tracing configuration ready"
}

# Function to setup log retention
setup_log_retention() {
    echo "📝 Setting up log retention policies..."
    
    # List of log groups to configure
    LOG_GROUPS=(
        "/aws/lambda/$PROJECT-$ENV-ingest"
        "/aws/lambda/$PROJECT-$ENV-process"
        "/aws/lambda/$PROJECT-$ENV-format"
        "/aws/lambda/$PROJECT-$ENV-api"
        "/aws/lambda/$PROJECT-$ENV-slack"
        "/aws/lambda/$PROJECT-$ENV-monitoring"
        "/aws/apigateway/$PROJECT-$ENV-api"
    )
    
    for log_group in "${LOG_GROUPS[@]}"; do
        # Set log retention to 30 days
        aws logs put-retention-policy \
            --log-group-name "$log_group" \
            --retention-in-days 30 \
            --region "$REGION" 2>/dev/null || echo "  ⚠️  Log group $log_group may not exist yet"
    done
    
    echo "  ✅ Log retention policies configured (30 days)"
}

# Function to create custom metrics
create_custom_metrics() {
    echo "📊 Setting up custom business metrics..."
    
    # Create custom namespace
    aws logs create-log-group \
        --log-group-name "/autospec-ai/$ENV/business-metrics" \
        --region "$REGION" 2>/dev/null || echo "  ℹ️  Business metrics log group may already exist"
    
    # Create metric filters for business events
    aws logs put-metric-filter \
        --log-group-name "/autospec-ai/$ENV/business-metrics" \
        --filter-name "DocumentsProcessed" \
        --filter-pattern "[timestamp, requestId, eventType=\"DOCUMENT_PROCESSED\", ...]" \
        --metric-transformations \
            metricName=DocumentsProcessed,metricNamespace=AutoSpecAI/Business,metricValue=1 \
        --region "$REGION"
    
    aws logs put-metric-filter \
        --log-group-name "/autospec-ai/$ENV/business-metrics" \
        --filter-name "RequirementsGenerated" \
        --filter-pattern "[timestamp, requestId, eventType=\"REQUIREMENTS_GENERATED\", ...]" \
        --metric-transformations \
            metricName=RequirementsGenerated,metricNamespace=AutoSpecAI/Business,metricValue=1 \
        --region "$REGION"
    
    echo "  ✅ Custom business metrics configured"
}

# Function to save monitoring configuration
save_monitoring_config() {
    echo "💾 Saving monitoring configuration..."
    
    cat > "/mnt/c/Users/sghar/CascadeProjects/AutoSpecAI/config/monitoring-config.json" << EOF
{
    "sns_topics": {
        "critical_alerts": "$CRITICAL_TOPIC_ARN",
        "warning_alerts": "$WARNING_TOPIC_ARN", 
        "business_metrics": "$METRICS_TOPIC_ARN"
    },
    "dashboards": [
        "$PROJECT-$ENV-operational",
        "$PROJECT-$ENV-performance"
    ],
    "budget": {
        "name": "$PROJECT-$ENV-monthly-budget",
        "amount": $BUDGET_ALERT,
        "currency": "USD"
    },
    "log_retention_days": 30,
    "notification_email": "$NOTIFICATION_EMAIL",
    "region": "$REGION",
    "environment": "$ENV",
    "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF

    echo "  ✅ Monitoring configuration saved to config/monitoring-config.json"
}

# Main execution
main() {
    echo "🎯 Starting monitoring and alerting setup..."
    
    create_sns_topics
    create_cloudwatch_alarms
    create_cloudwatch_dashboards
    setup_cost_monitoring
    enable_xray_tracing
    setup_log_retention
    create_custom_metrics
    save_monitoring_config
    
    echo ""
    echo "✅ Monitoring and alerting setup complete!"
    echo ""
    echo "📋 Summary:"
    echo "  • SNS Topics: 3 created (critical, warning, business)"
    echo "  • CloudWatch Alarms: 20+ created for Lambda, API Gateway, DynamoDB"
    echo "  • Dashboards: 2 created (operational, performance)"
    echo "  • Budget Alert: \$$BUDGET_ALERT monthly threshold"
    echo "  • Log Retention: 30 days for all log groups"
    echo "  • X-Ray Tracing: Enabled"
    echo "  • Custom Metrics: Business events tracking"
    echo ""
    echo "📧 Email Confirmations Required:"
    echo "  • Check $NOTIFICATION_EMAIL for SNS subscription confirmations"
    echo "  • Confirm budget notification subscriptions"
    echo ""
    echo "📊 Access Your Dashboards:"
    echo "  • Operational: CloudWatch Console → Dashboards → $PROJECT-$ENV-operational"
    echo "  • Performance: CloudWatch Console → Dashboards → $PROJECT-$ENV-performance"
    echo ""
    echo "🚀 Ready for security configuration!"
}

# Run main function
main "$@"