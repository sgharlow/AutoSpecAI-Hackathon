# AutoSpecAI Production System Validation Test Script
# This script validates all components of the production deployment
# Run this after adding API stage to usage plan in AWS Console

param(
    [string]$ApiKey = $env:AUTOSPEC_API_KEY,
    [string]$ApiUrl = "https://nlkg4e7zo4.execute-api.us-east-1.amazonaws.com/prod",
    [string]$Region = "us-east-1"
)

# Check if API key is provided
if ([string]::IsNullOrEmpty($ApiKey)) {
    Write-Host "❌ Error: API key not provided!" -ForegroundColor Red
    Write-Host "Please set the AUTOSPEC_API_KEY environment variable or pass it as a parameter:" -ForegroundColor Yellow
    Write-Host "  $env:AUTOSPEC_API_KEY = 'your-api-key'" -ForegroundColor Cyan
    Write-Host "  OR" -ForegroundColor Yellow
    Write-Host "  .\test-production-system.ps1 -ApiKey 'your-api-key'" -ForegroundColor Cyan
    exit 1
}

Write-Host "🚀 AutoSpecAI Production System Validation" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green
Write-Host ""

$TestResults = @{}
$TotalTests = 0
$PassedTests = 0

function Test-Component {
    param($Name, $TestFunction)
    $global:TotalTests++
    Write-Host "Testing: $Name" -ForegroundColor Yellow
    try {
        $result = & $TestFunction
        if ($result) {
            Write-Host "✅ PASS: $Name" -ForegroundColor Green
            $global:PassedTests++
            $global:TestResults[$Name] = "PASS"
        } else {
            Write-Host "❌ FAIL: $Name" -ForegroundColor Red
            $global:TestResults[$Name] = "FAIL"
        }
    } catch {
        Write-Host "❌ ERROR: $Name - $($_.Exception.Message)" -ForegroundColor Red
        $global:TestResults[$Name] = "ERROR: $($_.Exception.Message)"
    }
    Write-Host ""
}

# Test 1: AWS CLI Connectivity
Test-Component "AWS CLI Connectivity" {
    $identity = aws sts get-caller-identity 2>$null | ConvertFrom-Json
    return $identity.Account -eq "461293170793"
}

# Test 2: CloudFormation Stack Status
Test-Component "CloudFormation Stack Exists" {
    $stacks = aws cloudformation list-stacks --region $Region --query 'StackSummaries[?StackName==`AutoSpecAI-prod` && StackStatus!=`DELETE_COMPLETE`]' --output json | ConvertFrom-Json
    return $stacks.Count -gt 0
}

# Test 3: Lambda Functions Exist and Optimized
Test-Component "Lambda Functions Deployed and Optimized" {
    $functions = aws lambda list-functions --region $Region --query 'Functions[?contains(FunctionName, `AutoSpecAI`) && contains(FunctionName, `prod`)]' --output json | ConvertFrom-Json
    
    $requiredFunctions = @("ProcessFunction", "FormatFunction", "IngestFunction", "ApiFunction")
    $foundFunctions = @()
    
    foreach ($func in $functions) {
        foreach ($required in $requiredFunctions) {
            if ($func.FunctionName -like "*$required*") {
                $foundFunctions += $required
                Write-Host "  Found: $($func.FunctionName) - Memory: $($func.MemorySize)MB" -ForegroundColor Cyan
            }
        }
    }
    
    return $foundFunctions.Count -eq $requiredFunctions.Count
}

# Test 4: API Gateway Exists
Test-Component "API Gateway Deployed" {
    $apis = aws apigateway get-rest-apis --region $Region --query 'items[?id==`nlkg4e7zo4`]' --output json | ConvertFrom-Json
    return $apis.Count -gt 0
}

# Test 5: Usage Plan and API Keys
Test-Component "Usage Plan and API Keys Configured" {
    $usagePlans = aws apigateway get-usage-plans --region $Region --query 'items[?contains(name, `AutoSpec`)]' --output json | ConvertFrom-Json
    
    if ($usagePlans.Count -eq 0) { return $false }
    
    foreach ($plan in $usagePlans) {
        $keys = aws apigateway get-usage-plan-keys --usage-plan-id $plan.id --region $Region --output json | ConvertFrom-Json
        if ($keys.items.Count -gt 0) {
            Write-Host "  Usage Plan: $($plan.name) - API Keys: $($keys.items.Count)" -ForegroundColor Cyan
            if ($plan.apiStages.Count -gt 0) {
                Write-Host "  API Stages: $($plan.apiStages.Count)" -ForegroundColor Cyan
                return $true
            } else {
                Write-Host "  ⚠️  No API stages linked to usage plan!" -ForegroundColor Yellow
                return $false
            }
        }
    }
    return $false
}

# Test 6: S3 Buckets
Test-Component "S3 Buckets Created" {
    $buckets = aws s3api list-buckets --query 'Buckets[?contains(Name, `autospec-ai`) && contains(Name, `prod`)]' --output json | ConvertFrom-Json
    
    $requiredBuckets = @("documents", "emails")
    $foundBuckets = @()
    
    foreach ($bucket in $buckets) {
        foreach ($required in $requiredBuckets) {
            if ($bucket.Name -like "*$required*") {
                $foundBuckets += $required
                Write-Host "  Found: $($bucket.Name)" -ForegroundColor Cyan
            }
        }
    }
    
    return $foundBuckets.Count -eq $requiredBuckets.Count
}

# Test 7: DynamoDB Tables
Test-Component "DynamoDB Tables Created" {
    $tables = aws dynamodb list-tables --region $Region --query 'TableNames[?contains(@, `autospec-ai`) && contains(@, `prod`)]' --output json | ConvertFrom-Json
    
    $requiredTables = @("history", "api-keys", "rate-limits")
    $foundTables = @()
    
    foreach ($table in $tables) {
        foreach ($required in $requiredTables) {
            if ($table -like "*$required*") {
                $foundTables += $required
                Write-Host "  Found: $table" -ForegroundColor Cyan
            }
        }
    }
    
    return $foundTables.Count -eq $requiredTables.Count
}

# Test 8: SNS Topics and Subscriptions
Test-Component "SNS Alerts Configured and Confirmed" {
    $topics = aws sns list-topics --region $Region --query 'Topics[?contains(TopicArn, `autospec-ai-prod`)]' --output json | ConvertFrom-Json
    
    if ($topics.Count -eq 0) { return $false }
    
    $confirmedCount = 0
    foreach ($topic in $topics) {
        $subscriptions = aws sns list-subscriptions-by-topic --topic-arn $topic.TopicArn --region $Region --output json | ConvertFrom-Json
        foreach ($sub in $subscriptions.Subscriptions) {
            if ($sub.SubscriptionArn -notlike "*pending*") {
                $confirmedCount++
                Write-Host "  Confirmed: $($topic.TopicArn | Split-Path -Leaf)" -ForegroundColor Cyan
            }
        }
    }
    
    return $confirmedCount -ge 3
}

# Test 9: CloudWatch Dashboard
Test-Component "CloudWatch Dashboard Created" {
    $dashboards = aws cloudwatch list-dashboards --region $Region --query 'DashboardEntries[?contains(DashboardName, `AutoSpecAI`)]' --output json | ConvertFrom-Json
    return $dashboards.Count -gt 0
}

# Test 10: Budget Monitoring
Test-Component "Budget Monitoring Configured" {
    $budgets = aws budgets describe-budgets --account-id 461293170793 --region $Region --query 'Budgets[?contains(BudgetName, `AutoSpecAI`)]' --output json | ConvertFrom-Json
    
    if ($budgets.Count -gt 0) {
        foreach ($budget in $budgets) {
            Write-Host "  Budget: $($budget.BudgetName) - Limit: $($budget.BudgetLimit.Amount) $($budget.BudgetLimit.Unit)" -ForegroundColor Cyan
            Write-Host "  Current: $($budget.CalculatedSpend.ActualSpend.Amount) $($budget.CalculatedSpend.ActualSpend.Unit)" -ForegroundColor Cyan
        }
        return $true
    }
    return $false
}

# Test 11: API Connectivity (without authentication)
Test-Component "API Gateway Connectivity" {
    try {
        $response = Invoke-RestMethod -Uri "$ApiUrl/v1/health" -Method OPTIONS -TimeoutSec 10
        return $true
    } catch {
        return $false
    }
}

# Test 12: API Key Authentication (if usage plan is properly configured)
Test-Component "API Key Authentication" {
    try {
        $headers = @{"X-API-Key" = $ApiKey}
        $response = Invoke-RestMethod -Uri "$ApiUrl/v1/health" -Method GET -Headers $headers -TimeoutSec 10
        return $response.status -eq "healthy"
    } catch {
        $errorMessage = $_.Exception.Message
        if ($errorMessage -like "*Invalid API key*") {
            Write-Host "  ⚠️  API key invalid - Usage plan may need API stage added" -ForegroundColor Yellow
            return $false
        } elseif ($errorMessage -like "*Unauthorized*") {
            Write-Host "  ⚠️  API authentication not properly configured" -ForegroundColor Yellow
            return $false
        } else {
            Write-Host "  Error: $errorMessage" -ForegroundColor Red
            return $false
        }
    }
}

# Test 13: Test SNS Alert
Test-Component "SNS Alert Test" {
    try {
        $testMessage = aws sns publish --topic-arn "arn:aws:sns:$Region:461293170793:autospec-ai-prod-critical-alerts" --message "AutoSpecAI Production System Test - All systems operational $(Get-Date)" --region $Region | ConvertFrom-Json
        return ![string]::IsNullOrEmpty($testMessage.MessageId)
    } catch {
        return $false
    }
}

# Test 14: Performance Metrics Check
Test-Component "Lambda Performance Optimization" {
    $processFunc = aws lambda get-function-configuration --function-name "AutoSpecAI-ProcessFunction-prod" --region $Region 2>$null | ConvertFrom-Json
    $formatFunc = aws lambda get-function-configuration --function-name "AutoSpecAI-FormatFunction-prod" --region $Region 2>$null | ConvertFrom-Json
    $ingestFunc = aws lambda get-function-configuration --function-name "AutoSpecAI-IngestFunction-v2-prod" --region $Region 2>$null | ConvertFrom-Json
    $apiFunc = aws lambda get-function-configuration --function-name "AutoSpecAI-ApiFunction-prod" --region $Region 2>$null | ConvertFrom-Json
    
    if ($processFunc -and $formatFunc -and $ingestFunc -and $apiFunc) {
        Write-Host "  ProcessFunction: $($processFunc.MemorySize)MB (Target: 2048MB)" -ForegroundColor Cyan
        Write-Host "  FormatFunction: $($formatFunc.MemorySize)MB (Target: 1536MB)" -ForegroundColor Cyan  
        Write-Host "  IngestFunction: $($ingestFunc.MemorySize)MB (Target: 1024MB)" -ForegroundColor Cyan
        Write-Host "  ApiFunction: $($apiFunc.MemorySize)MB (Target: 512MB)" -ForegroundColor Cyan
        
        return ($processFunc.MemorySize -ge 2048 -and 
                $formatFunc.MemorySize -ge 1536 -and 
                $ingestFunc.MemorySize -ge 1024 -and 
                $apiFunc.MemorySize -ge 512)
    }
    return $false
}

# Run all tests
Write-Host "Running comprehensive production system validation..." -ForegroundColor Cyan
Write-Host ""

# Execute all tests
$testNames = @(
    "AWS CLI Connectivity",
    "CloudFormation Stack Exists", 
    "Lambda Functions Deployed and Optimized",
    "API Gateway Deployed",
    "Usage Plan and API Keys Configured",
    "S3 Buckets Created",
    "DynamoDB Tables Created", 
    "SNS Alerts Configured and Confirmed",
    "CloudWatch Dashboard Created",
    "Budget Monitoring Configured",
    "API Gateway Connectivity",
    "API Key Authentication",
    "SNS Alert Test",
    "Lambda Performance Optimization"
)

# Summary
Write-Host "=============================================" -ForegroundColor Green
Write-Host "🎯 PRODUCTION SYSTEM TEST SUMMARY" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Tests Passed: $PassedTests / $TotalTests" -ForegroundColor $(if ($PassedTests -eq $TotalTests) { "Green" } else { "Yellow" })
Write-Host ""

# Detailed results
foreach ($testName in $testNames) {
    if ($TestResults.ContainsKey($testName)) {
        $status = $TestResults[$testName]
        $color = if ($status -eq "PASS") { "Green" } elseif ($status -eq "FAIL") { "Red" } else { "Yellow" }
        Write-Host "$testName : $status" -ForegroundColor $color
    }
}

Write-Host ""
Write-Host "=============================================" -ForegroundColor Green

# Final recommendations
$passRate = [math]::Round(($PassedTests / $TotalTests) * 100, 1)

if ($passRate -ge 90) {
    Write-Host "🎉 EXCELLENT! Your production system is $passRate% functional!" -ForegroundColor Green
    Write-Host "✅ AutoSpecAI is ready for production use!" -ForegroundColor Green
} elseif ($passRate -ge 80) {
    Write-Host "👍 GOOD! Your production system is $passRate% functional!" -ForegroundColor Yellow
    Write-Host "⚠️  Address the failed tests to achieve full functionality." -ForegroundColor Yellow
} else {
    Write-Host "⚠️  Your production system is $passRate% functional." -ForegroundColor Red
    Write-Host "❌ Several critical components need attention." -ForegroundColor Red
}

Write-Host ""
Write-Host "💡 Next Steps:" -ForegroundColor Cyan
if ($TestResults["Usage Plan and API Keys Configured"] -ne "PASS") {
    Write-Host "1. Add API stage to usage plan in AWS Console (API Gateway → Usage Plans)" -ForegroundColor White
}
if ($TestResults["API Key Authentication"] -ne "PASS") {
    Write-Host "2. Test API authentication after fixing usage plan" -ForegroundColor White
}
Write-Host "3. Wait for SES production access approval" -ForegroundColor White
Write-Host "4. Run: ./scripts/setup-ses-email-receiving.sh prod" -ForegroundColor White
Write-Host ""
Write-Host "📧 Check your email for SNS test message!" -ForegroundColor Cyan
Write-Host ""