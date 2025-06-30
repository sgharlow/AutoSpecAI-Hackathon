#!/bin/bash

# AutoSpec.AI Automated Performance Testing Pipeline
# This script provides comprehensive performance testing automation for CI/CD integration

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
RESULTS_DIR="$PROJECT_ROOT/performance-results"
BASELINE_DIR="$PROJECT_ROOT/performance-baselines"

# Default values
ENVIRONMENT="dev"
RUN_LOAD_TEST=true
GENERATE_BASELINE=false
COMPARE_WITH_PREVIOUS=false
FAIL_ON_REGRESSION=true
PERFORMANCE_THRESHOLD=10  # Percentage regression threshold
COST_THRESHOLD=20         # Percentage cost increase threshold
OUTPUT_FORMAT="json"      # json, html, markdown
SLACK_WEBHOOK=""
EMAIL_REPORT=""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging functions
log_info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] [INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] [SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] [WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] [ERROR]${NC} $1"
}

# Help function
show_help() {
    cat << EOF
AutoSpec.AI Automated Performance Testing Pipeline

Usage: $0 [OPTIONS] ENVIRONMENT

ENVIRONMENTS:
    dev         Development environment
    staging     Staging environment  
    prod        Production environment

OPTIONS:
    -h, --help                    Show this help message
    --no-load-test               Skip load testing (use existing metrics)
    --baseline                   Generate new performance baseline
    --compare                    Compare with previous baseline
    --no-fail-on-regression      Continue even if performance regression detected
    --threshold PERCENT          Performance regression threshold (default: 10%)
    --cost-threshold PERCENT     Cost increase threshold (default: 20%)
    --format FORMAT              Output format: json, html, markdown (default: json)
    --slack-webhook URL          Send results to Slack webhook
    --email RECIPIENT            Email report to recipient
    --results-dir PATH           Custom results directory

EXAMPLES:
    $0 dev                                    # Basic performance test
    $0 staging --baseline --compare           # Generate baseline and compare
    $0 prod --no-load-test --compare          # Compare without new load test
    $0 dev --threshold 5 --format html       # Strict threshold with HTML output

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
            --no-load-test)
                RUN_LOAD_TEST=false
                shift
                ;;
            --baseline)
                GENERATE_BASELINE=true
                shift
                ;;
            --compare)
                COMPARE_WITH_PREVIOUS=true
                shift
                ;;
            --no-fail-on-regression)
                FAIL_ON_REGRESSION=false
                shift
                ;;
            --threshold)
                PERFORMANCE_THRESHOLD="$2"
                shift 2
                ;;
            --cost-threshold)
                COST_THRESHOLD="$2"
                shift 2
                ;;
            --format)
                OUTPUT_FORMAT="$2"
                shift 2
                ;;
            --slack-webhook)
                SLACK_WEBHOOK="$2"
                shift 2
                ;;
            --email)
                EMAIL_REPORT="$2"
                shift 2
                ;;
            --results-dir)
                RESULTS_DIR="$2"
                shift 2
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

# Setup directories
setup_directories() {
    mkdir -p "$RESULTS_DIR"
    mkdir -p "$BASELINE_DIR"
    
    log_info "Results directory: $RESULTS_DIR"
    log_info "Baseline directory: $BASELINE_DIR"
}

# Validate prerequisites
validate_prerequisites() {
    log_info "Validating prerequisites..."
    
    # Check if Python scripts exist
    local required_scripts=(
        "$SCRIPT_DIR/load-testing-suite.py"
        "$SCRIPT_DIR/performance-benchmarks.py"
    )
    
    for script in "${required_scripts[@]}"; do
        if [[ ! -f "$script" ]]; then
            log_error "Required script not found: $script"
            exit 1
        fi
    done
    
    # Check Python dependencies
    if ! python3 -c "import asyncio, aiohttp, boto3" &> /dev/null; then
        log_error "Missing Python dependencies. Install with: pip install asyncio aiohttp boto3"
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured"
        exit 1
    fi
    
    log_success "Prerequisites validated"
}

# Run load testing
run_load_testing() {
    if [[ "$RUN_LOAD_TEST" != "true" ]]; then
        log_info "Skipping load testing as requested"
        return 0
    fi
    
    log_info "Running comprehensive load testing suite..."
    
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local load_test_output="$RESULTS_DIR/load_test_${ENVIRONMENT}_${timestamp}.json"
    
    # Run load testing suite
    if python3 "$SCRIPT_DIR/load-testing-suite.py" \
        --environment "$ENVIRONMENT" \
        --test-type full \
        --report \
        --output-file "$load_test_output"; then
        
        log_success "Load testing completed successfully"
        echo "$load_test_output"
    else
        log_error "Load testing failed"
        return 1
    fi
}

# Generate performance baseline
generate_baseline() {
    if [[ "$GENERATE_BASELINE" != "true" ]]; then
        return 0
    fi
    
    log_info "Generating performance baseline..."
    
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local baseline_file="$BASELINE_DIR/baseline_${ENVIRONMENT}_${timestamp}.json"
    local report_file="$RESULTS_DIR/baseline_report_${ENVIRONMENT}_${timestamp}.md"
    
    # Generate baseline with load test if requested
    local baseline_args="--environment $ENVIRONMENT --baseline --output $report_file"
    if [[ "$RUN_LOAD_TEST" == "true" ]]; then
        baseline_args="$baseline_args --load-test"
    fi
    
    if python3 "$SCRIPT_DIR/performance-benchmarks.py" $baseline_args; then
        log_success "Baseline generated successfully"
        echo "$baseline_file"
    else
        log_error "Baseline generation failed"
        return 1
    fi
}

# Compare with previous baseline
compare_baselines() {
    if [[ "$COMPARE_WITH_PREVIOUS" != "true" ]]; then
        return 0
    fi
    
    log_info "Comparing with previous baseline..."
    
    # Find the most recent baseline file
    local previous_baseline=$(find "$BASELINE_DIR" -name "baseline_${ENVIRONMENT}_*.json" -type f | sort -r | head -n 2 | tail -n 1)
    local current_baseline=$(find "$BASELINE_DIR" -name "baseline_${ENVIRONMENT}_*.json" -type f | sort -r | head -n 1)
    
    if [[ -z "$previous_baseline" || -z "$current_baseline" ]]; then
        log_warning "Cannot find baselines for comparison"
        return 1
    fi
    
    log_info "Comparing baselines:"
    log_info "  Previous: $(basename "$previous_baseline")"
    log_info "  Current:  $(basename "$current_baseline")"
    
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local comparison_report="$RESULTS_DIR/comparison_${ENVIRONMENT}_${timestamp}.md"
    
    if python3 "$SCRIPT_DIR/performance-benchmarks.py" \
        --environment "$ENVIRONMENT" \
        --compare \
        --before-file "$previous_baseline" \
        --after-file "$current_baseline" \
        --output "$comparison_report"; then
        
        log_success "Baseline comparison completed"
        echo "$comparison_report"
    else
        log_error "Baseline comparison failed"
        return 1
    fi
}

# Analyze performance results
analyze_performance_results() {
    local comparison_report="$1"
    
    if [[ -z "$comparison_report" || ! -f "$comparison_report" ]]; then
        log_info "No comparison report available for analysis"
        return 0
    fi
    
    log_info "Analyzing performance results..."
    
    # Extract key metrics from the report
    local performance_score=$(grep "Overall Performance Score:" "$comparison_report" | head -n 1 | grep -oE '[-+]?[0-9]+\.?[0-9]*' || echo "0")
    local cost_impact=$(grep "Cost Change:" "$comparison_report" | head -n 1 | grep -oE '[-+]?[0-9]+\.?[0-9]*' || echo "0")
    
    log_info "Performance Score: ${performance_score}%"
    log_info "Cost Impact: ${cost_impact}%"
    
    # Check thresholds
    local has_regression=false
    
    if (( $(echo "$performance_score < -$PERFORMANCE_THRESHOLD" | bc -l) )); then
        log_error "Performance regression detected: ${performance_score}% (threshold: -${PERFORMANCE_THRESHOLD}%)"
        has_regression=true
    fi
    
    if (( $(echo "$cost_impact > $COST_THRESHOLD" | bc -l) )); then
        log_error "Cost increase detected: ${cost_impact}% (threshold: ${COST_THRESHOLD}%)"
        has_regression=true
    fi
    
    if [[ "$has_regression" == "true" ]]; then
        if [[ "$FAIL_ON_REGRESSION" == "true" ]]; then
            log_error "Performance regression threshold exceeded - failing pipeline"
            return 1
        else
            log_warning "Performance regression detected but continuing as requested"
        fi
    else
        log_success "Performance within acceptable thresholds"
    fi
    
    return 0
}

# Generate comprehensive report
generate_comprehensive_report() {
    local load_test_output="$1"
    local comparison_report="$2"
    
    log_info "Generating comprehensive performance report..."
    
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local comprehensive_report="$RESULTS_DIR/performance_report_${ENVIRONMENT}_${timestamp}"
    
    case "$OUTPUT_FORMAT" in
        json)
            comprehensive_report="${comprehensive_report}.json"
            generate_json_report "$load_test_output" "$comparison_report" "$comprehensive_report"
            ;;
        html)
            comprehensive_report="${comprehensive_report}.html"
            generate_html_report "$load_test_output" "$comparison_report" "$comprehensive_report"
            ;;
        markdown)
            comprehensive_report="${comprehensive_report}.md"
            generate_markdown_report "$load_test_output" "$comparison_report" "$comprehensive_report"
            ;;
        *)
            log_error "Unsupported output format: $OUTPUT_FORMAT"
            return 1
            ;;
    esac
    
    log_success "Comprehensive report generated: $comprehensive_report"
    echo "$comprehensive_report"
}

# Generate JSON report
generate_json_report() {
    local load_test_output="$1"
    local comparison_report="$2"
    local output_file="$3"
    
    local json_report="{
        \"environment\": \"$ENVIRONMENT\",
        \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)\",
        \"pipeline_config\": {
            \"load_test_enabled\": $RUN_LOAD_TEST,
            \"baseline_generated\": $GENERATE_BASELINE,
            \"comparison_enabled\": $COMPARE_WITH_PREVIOUS,
            \"performance_threshold\": $PERFORMANCE_THRESHOLD,
            \"cost_threshold\": $COST_THRESHOLD
        },
        \"files\": {
            \"load_test_output\": \"$(basename "$load_test_output" 2>/dev/null || echo "null")\",
            \"comparison_report\": \"$(basename "$comparison_report" 2>/dev/null || echo "null")\"
        }
    }"
    
    echo "$json_report" > "$output_file"
}

# Generate HTML report
generate_html_report() {
    local load_test_output="$1"
    local comparison_report="$2"
    local output_file="$3"
    
    cat > "$output_file" << EOF
<!DOCTYPE html>
<html>
<head>
    <title>AutoSpec.AI Performance Report - $ENVIRONMENT</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background-color: #f0f0f0; padding: 20px; border-radius: 5px; }
        .section { margin: 20px 0; padding: 15px; border-left: 4px solid #007cba; }
        .success { border-left-color: #28a745; }
        .warning { border-left-color: #ffc107; }
        .error { border-left-color: #dc3545; }
        pre { background-color: #f8f9fa; padding: 10px; border-radius: 3px; overflow-x: auto; }
    </style>
</head>
<body>
    <div class="header">
        <h1>AutoSpec.AI Performance Report</h1>
        <p><strong>Environment:</strong> $ENVIRONMENT</p>
        <p><strong>Generated:</strong> $(date)</p>
    </div>
    
    <div class="section success">
        <h2>Test Execution Summary</h2>
        <ul>
            <li>Load Testing: $([ "$RUN_LOAD_TEST" == "true" ] && echo "✅ Executed" || echo "❌ Skipped")</li>
            <li>Baseline Generation: $([ "$GENERATE_BASELINE" == "true" ] && echo "✅ Generated" || echo "❌ Skipped")</li>
            <li>Comparison: $([ "$COMPARE_WITH_PREVIOUS" == "true" ] && echo "✅ Performed" || echo "❌ Skipped")</li>
        </ul>
    </div>
    
    <div class="section">
        <h2>Files Generated</h2>
        <ul>
            <li>Load Test Output: $(basename "$load_test_output" 2>/dev/null || echo "None")</li>
            <li>Comparison Report: $(basename "$comparison_report" 2>/dev/null || echo "None")</li>
        </ul>
    </div>
    
    <div class="section">
        <h2>Next Steps</h2>
        <ol>
            <li>Review detailed reports in the results directory</li>
            <li>Check CloudWatch dashboards for real-time metrics</li>
            <li>Monitor provisioned concurrency utilization</li>
            <li>Schedule regular performance testing</li>
        </ol>
    </div>
</body>
</html>
EOF
}

# Generate Markdown report
generate_markdown_report() {
    local load_test_output="$1"
    local comparison_report="$2"
    local output_file="$3"
    
    cat > "$output_file" << EOF
# AutoSpec.AI Performance Testing Pipeline Report

## Environment: $ENVIRONMENT
**Generated:** $(date)

## Pipeline Configuration
- **Load Testing:** $([ "$RUN_LOAD_TEST" == "true" ] && echo "✅ Enabled" || echo "❌ Disabled")
- **Baseline Generation:** $([ "$GENERATE_BASELINE" == "true" ] && echo "✅ Enabled" || echo "❌ Disabled")
- **Baseline Comparison:** $([ "$COMPARE_WITH_PREVIOUS" == "true" ] && echo "✅ Enabled" || echo "❌ Disabled")
- **Performance Threshold:** ${PERFORMANCE_THRESHOLD}%
- **Cost Threshold:** ${COST_THRESHOLD}%

## Generated Files
- **Load Test Output:** $(basename "$load_test_output" 2>/dev/null || echo "None")
- **Comparison Report:** $(basename "$comparison_report" 2>/dev/null || echo "None")

## Next Steps
1. Review detailed reports in the results directory
2. Check CloudWatch dashboards for real-time metrics
3. Monitor provisioned concurrency utilization
4. Schedule regular performance testing

## Automation Commands
\`\`\`bash
# Run full performance pipeline
$0 $ENVIRONMENT --baseline --compare

# Run with strict thresholds
$0 $ENVIRONMENT --threshold 5 --cost-threshold 10

# Generate HTML report
$0 $ENVIRONMENT --format html
\`\`\`
EOF
}

# Send notifications
send_notifications() {
    local report_file="$1"
    local has_regression="$2"
    
    if [[ -n "$SLACK_WEBHOOK" ]]; then
        send_slack_notification "$report_file" "$has_regression"
    fi
    
    if [[ -n "$EMAIL_REPORT" ]]; then
        send_email_notification "$report_file" "$has_regression"
    fi
}

# Send Slack notification
send_slack_notification() {
    local report_file="$1"
    local has_regression="$2"
    
    log_info "Sending Slack notification..."
    
    local color="good"
    local title="✅ Performance Test Passed"
    
    if [[ "$has_regression" == "true" ]]; then
        color="danger"
        title="⚠️ Performance Regression Detected"
    fi
    
    local payload=$(cat <<EOF
{
    "attachments": [
        {
            "color": "$color",
            "title": "$title",
            "fields": [
                {
                    "title": "Environment",
                    "value": "$ENVIRONMENT",
                    "short": true
                },
                {
                    "title": "Timestamp",
                    "value": "$(date)",
                    "short": true
                },
                {
                    "title": "Report",
                    "value": "$(basename "$report_file")",
                    "short": false
                }
            ]
        }
    ]
}
EOF
    )
    
    if curl -X POST -H 'Content-type: application/json' \
        --data "$payload" \
        "$SLACK_WEBHOOK" &> /dev/null; then
        log_success "Slack notification sent"
    else
        log_warning "Failed to send Slack notification"
    fi
}

# Send email notification
send_email_notification() {
    local report_file="$1"
    local has_regression="$2"
    
    log_info "Sending email notification to $EMAIL_REPORT..."
    
    local subject="AutoSpec.AI Performance Test - $ENVIRONMENT"
    if [[ "$has_regression" == "true" ]]; then
        subject="$subject - REGRESSION DETECTED"
    fi
    
    # Use AWS SES if available, otherwise mail command
    if command -v aws &> /dev/null && aws ses describe-identity --identity "$EMAIL_REPORT" &> /dev/null; then
        aws ses send-email \
            --source "noreply@autospec.ai" \
            --destination "ToAddresses=$EMAIL_REPORT" \
            --message "Subject={Data='$subject'},Body={Text={Data='Performance test completed. See attached report: $(basename "$report_file")'}}" \
            &> /dev/null && log_success "Email sent via SES" || log_warning "Failed to send email via SES"
    elif command -v mail &> /dev/null; then
        echo "Performance test completed. Report: $(basename "$report_file")" | \
            mail -s "$subject" "$EMAIL_REPORT" && \
            log_success "Email sent via mail command" || \
            log_warning "Failed to send email via mail command"
    else
        log_warning "No email service available"
    fi
}

# Main execution
main() {
    log_info "Starting AutoSpec.AI Performance Testing Pipeline"
    log_info "Environment: $ENVIRONMENT"
    log_info "Configuration: Load Test=$RUN_LOAD_TEST, Baseline=$GENERATE_BASELINE, Compare=$COMPARE_WITH_PREVIOUS"
    
    setup_directories
    validate_prerequisites
    
    local load_test_output=""
    local comparison_report=""
    local has_regression=false
    
    # Run load testing
    if load_test_output=$(run_load_testing); then
        log_success "Load testing phase completed"
    else
        log_error "Load testing phase failed"
        exit 1
    fi
    
    # Generate baseline
    if generate_baseline; then
        log_success "Baseline generation completed"
    else
        log_warning "Baseline generation had issues"
    fi
    
    # Compare baselines
    if comparison_report=$(compare_baselines); then
        log_success "Baseline comparison completed"
        
        # Analyze results for regressions
        if ! analyze_performance_results "$comparison_report"; then
            has_regression=true
        fi
    else
        log_warning "Baseline comparison had issues"
    fi
    
    # Generate comprehensive report
    local final_report
    if final_report=$(generate_comprehensive_report "$load_test_output" "$comparison_report"); then
        log_success "Comprehensive report generated: $final_report"
    else
        log_warning "Report generation had issues"
    fi
    
    # Send notifications
    send_notifications "$final_report" "$has_regression"
    
    # Final status
    if [[ "$has_regression" == "true" && "$FAIL_ON_REGRESSION" == "true" ]]; then
        log_error "Performance pipeline failed due to regression"
        exit 1
    else
        log_success "Performance pipeline completed successfully"
        
        log_info ""
        log_info "=== Pipeline Summary ==="
        log_info "Results Directory: $RESULTS_DIR"
        log_info "Baseline Directory: $BASELINE_DIR"
        log_info "Final Report: $final_report"
        log_info ""
        log_info "Next steps:"
        log_info "1. Review the comprehensive report"
        log_info "2. Check CloudWatch dashboards"
        log_info "3. Monitor ongoing performance"
        log_info "4. Schedule regular testing"
    fi
}

# Parse arguments and run
parse_arguments "$@"
main