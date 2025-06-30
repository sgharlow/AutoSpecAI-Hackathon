#!/bin/bash

# AutoSpec.AI - Enhanced Document Upload Script with S3 Direct Upload
# Usage: ./enhanced-upload.sh /path/to/your/document.pdf [force-json]

set -e

API_URL="https://nlkg4e7zo4.execute-api.us-east-1.amazonaws.com/prod"
# Get API key from environment variable
API_KEY="${AUTOSPEC_API_KEY:-}"

# Check if API key is set
if [ -z "$API_KEY" ]; then
    echo "❌ Error: API key not configured!"
    echo "Please set: export AUTOSPEC_API_KEY='your-api-key'"
    exit 1
fi

# Upload method thresholds
LARGE_FILE_THRESHOLD=$((5 * 1024 * 1024))  # 5MB - use S3 direct upload for larger files
MAX_JSON_SIZE=$((8 * 1024 * 1024))         # 8MB - absolute max for JSON method

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 AutoSpec.AI Enhanced Document Upload Tool${NC}"
echo -e "${PURPLE}   Supports both JSON and S3 Direct Upload methods${NC}"
echo "================================================"

# Function to check system health
check_health() {
    echo -e "${YELLOW}🔍 Checking system health...${NC}"
    
    response=$(curl -s -X GET "${API_URL}/v1/health" \
        -H "X-API-Key: ${API_KEY}" \
        -w "\n%{http_code}")
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n -1)
    
    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✅ System is healthy!${NC}"
        echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"
        return 0
    else
        echo -e "${RED}❌ System health check failed (HTTP $http_code)${NC}"
        echo "$body"
        return 1
    fi
}

# Function to get file size in bytes
get_file_size() {
    local file_path="$1"
    if command -v stat >/dev/null 2>&1; then
        # Linux/Unix
        stat -c%s "$file_path" 2>/dev/null || stat -f%z "$file_path" 2>/dev/null
    else
        # Fallback using ls
        ls -l "$file_path" | awk '{print $5}'
    fi
}

# Function to determine upload method
determine_upload_method() {
    local file_path="$1"
    local force_json="$2"
    local file_size=$(get_file_size "$file_path")
    
    echo -e "${BLUE}📊 File size: $((file_size / 1024))KB ($file_size bytes)${NC}"
    
    if [ "$force_json" = "force-json" ]; then
        if [ "$file_size" -gt "$MAX_JSON_SIZE" ]; then
            echo -e "${RED}❌ File too large for JSON method (max ${MAX_JSON_SIZE} bytes)${NC}"
            return 1
        fi
        echo -e "${YELLOW}🔧 Forced JSON upload method${NC}"
        echo "json"
    elif [ "$file_size" -gt "$LARGE_FILE_THRESHOLD" ]; then
        echo -e "${PURPLE}🏗️  Large file detected - using S3 direct upload${NC}"
        echo "s3"
    else
        echo -e "${GREEN}📦 Small file - using JSON upload method${NC}"
        echo "json"
    fi
}

# Function to upload using JSON method (existing)
upload_json_method() {
    local file_path="$1"
    local filename=$(basename "$file_path")
    
    echo -e "${YELLOW}📤 Uploading via JSON method: $filename${NC}"
    
    # Encode file content to base64
    file_content=$(base64 -w 0 "$file_path")
    
    # Create JSON payload in temporary file to handle large files
    temp_payload=$(mktemp)
    cat > "$temp_payload" <<EOF
{
    "file_content": "$file_content",
    "filename": "$filename",
    "sender_email": "test@example.com"
}
EOF
    
    response=$(curl -s -X POST "${API_URL}/v1/upload" \
        -H "X-API-Key: ${API_KEY}" \
        -H "Content-Type: application/json" \
        -d "@$temp_payload" \
        -w "\n%{http_code}")
    
    # Clean up temporary file
    rm -f "$temp_payload"
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n -1)
    
    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ] || [ "$http_code" = "202" ]; then
        echo -e "${GREEN}✅ JSON upload successful!${NC}"
        echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"
        
        # Extract request ID for status checking
        request_id=$(echo "$body" | grep -o '"request_id":"[^"]*"' | cut -d'"' -f4)
        if [ -z "$request_id" ]; then
            request_id=$(echo "$body" | grep -o '"requestId":"[^"]*"' | cut -d'"' -f4)
        fi
        
        if [ -n "$request_id" ]; then
            echo -e "${BLUE}📋 Request ID: ${request_id}${NC}"
            echo -e "${YELLOW}⏳ Checking initial status in 3 seconds...${NC}"
            sleep 3
            check_status "$request_id"
        fi
        
        return 0
    else
        echo -e "${RED}❌ JSON upload failed (HTTP $http_code)${NC}"
        echo "$body"
        return 1
    fi
}

# Function to upload using S3 direct method (new)
upload_s3_method() {
    local file_path="$1"
    local filename=$(basename "$file_path")
    local file_size=$(get_file_size "$file_path")
    
    echo -e "${PURPLE}🏗️  Uploading via S3 direct method: $filename${NC}"
    
    # Step 1: Initiate upload to get pre-signed URL
    echo -e "${YELLOW}1️⃣  Requesting pre-signed upload URL...${NC}"
    
    initiate_payload=$(cat <<EOF
{
    "filename": "$filename",
    "file_size": $file_size,
    "content_type": "application/octet-stream",
    "metadata": {
        "sender_email": "test@example.com"
    }
}
EOF
)
    
    response=$(curl -s -X POST "${API_URL}/v1/upload/initiate" \
        -H "X-API-Key: ${API_KEY}" \
        -H "Content-Type: application/json" \
        -d "$initiate_payload" \
        -w "\n%{http_code}")
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n -1)
    
    if [ "$http_code" != "200" ]; then
        echo -e "${RED}❌ Failed to get upload URL (HTTP $http_code)${NC}"
        echo "$body"
        return 1
    fi
    
    echo -e "${GREEN}✅ Pre-signed URL obtained${NC}"
    
    # Extract upload URL and request ID
    upload_url=$(echo "$body" | python3 -c "import json,sys; data=json.load(sys.stdin); print(data['upload_url'])" 2>/dev/null)
    request_id=$(echo "$body" | python3 -c "import json,sys; data=json.load(sys.stdin); print(data['request_id'])" 2>/dev/null)
    content_type=$(echo "$body" | python3 -c "import json,sys; data=json.load(sys.stdin); print(data['upload_headers']['Content-Type'])" 2>/dev/null)
    
    if [ -z "$upload_url" ] || [ -z "$request_id" ]; then
        echo -e "${RED}❌ Invalid response from upload initiate${NC}"
        echo "$body"
        return 1
    fi
    
    echo -e "${BLUE}📋 Request ID: ${request_id}${NC}"
    
    # Step 2: Upload file directly to S3
    echo -e "${YELLOW}2️⃣  Uploading file to S3...${NC}"
    
    s3_response=$(curl -s -X PUT "$upload_url" \
        -H "Content-Type: ${content_type:-application/octet-stream}" \
        -H "Content-Length: $file_size" \
        --data-binary "@$file_path" \
        -w "\n%{http_code}")
    
    s3_http_code=$(echo "$s3_response" | tail -n1)
    
    if [ "$s3_http_code" != "200" ]; then
        echo -e "${RED}❌ S3 upload failed (HTTP $s3_http_code)${NC}"
        echo "$s3_response"
        return 1
    fi
    
    echo -e "${GREEN}✅ File uploaded to S3 successfully${NC}"
    
    # Step 3: Complete upload (optional but recommended)
    echo -e "${YELLOW}3️⃣  Verifying upload completion...${NC}"
    
    complete_payload=$(cat <<EOF
{
    "request_id": "$request_id"
}
EOF
)
    
    complete_response=$(curl -s -X POST "${API_URL}/v1/upload/complete" \
        -H "X-API-Key: ${API_KEY}" \
        -H "Content-Type: application/json" \
        -d "$complete_payload" \
        -w "\n%{http_code}")
    
    complete_http_code=$(echo "$complete_response" | tail -n1)
    complete_body=$(echo "$complete_response" | head -n -1)
    
    if [ "$complete_http_code" = "200" ]; then
        echo -e "${GREEN}✅ Upload verification successful!${NC}"
        echo "$complete_body" | python3 -m json.tool 2>/dev/null || echo "$complete_body"
        
        echo -e "${YELLOW}⏳ Checking processing status in 3 seconds...${NC}"
        sleep 3
        check_status "$request_id"
        
        return 0
    else
        echo -e "${YELLOW}⚠️  Upload verification failed but file was uploaded (HTTP $complete_http_code)${NC}"
        echo "$complete_body"
        echo -e "${BLUE}📋 You can check status later with: $0 status $request_id${NC}"
        return 0
    fi
}

# Function to check processing status
check_status() {
    local request_id="$1"
    
    if [ -z "$request_id" ]; then
        echo -e "${RED}❌ Please provide a request ID${NC}"
        return 1
    fi
    
    echo -e "${YELLOW}🔍 Checking status for: $request_id${NC}"
    
    response=$(curl -s -X GET "${API_URL}/v1/status/${request_id}" \
        -H "X-API-Key: ${API_KEY}" \
        -w "\n%{http_code}")
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n -1)
    
    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✅ Status retrieved!${NC}"
        echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"
        return 0
    else
        echo -e "${RED}❌ Status check failed (HTTP $http_code)${NC}"
        echo "$body"
        return 1
    fi
}

# Function to get processing history
get_history() {
    echo -e "${YELLOW}📚 Getting processing history...${NC}"
    
    response=$(curl -s -X GET "${API_URL}/v1/history" \
        -H "X-API-Key: ${API_KEY}" \
        -w "\n%{http_code}")
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n -1)
    
    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✅ History retrieved!${NC}"
        echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"
        return 0
    else
        echo -e "${RED}❌ History retrieval failed (HTTP $http_code)${NC}"
        echo "$body"
        return 1
    fi
}

# Function to show upload method comparison
show_method_comparison() {
    echo -e "${BLUE}📊 Upload Method Comparison:${NC}"
    echo ""
    echo -e "${GREEN}JSON Upload Method:${NC}"
    echo "  ✅ Simple single API call"
    echo "  ✅ Immediate processing start"
    echo "  ❌ Limited to ~8MB files"
    echo "  ❌ Higher Lambda cost for large files"
    echo ""
    echo -e "${PURPLE}S3 Direct Upload Method:${NC}"
    echo "  ✅ Supports files up to 100MB+"
    echo "  ✅ Lower cost for large files"
    echo "  ✅ Upload progress tracking"
    echo "  ✅ Resumable uploads (with multipart)"
    echo "  ❌ Three-step process"
    echo ""
    echo -e "${YELLOW}Auto-selection: Files >5MB use S3 direct, smaller files use JSON${NC}"
}

# Main script logic
main() {
    # Always check health first
    if ! check_health; then
        echo -e "${RED}❌ System not healthy. Please check your API configuration.${NC}"
        exit 1
    fi
    
    echo ""
    
    # Check command line arguments
    if [ $# -eq 0 ]; then
        echo -e "${YELLOW}📋 No file provided. Available commands:${NC}"
        echo "  Upload document:         $0 /path/to/document.pdf"
        echo "  Force JSON upload:       $0 /path/to/document.pdf force-json"
        echo "  Check status:            $0 status REQUEST_ID"
        echo "  Get history:             $0 history"
        echo "  Health check only:       $0 health"
        echo "  Show method comparison:  $0 compare"
        echo ""
        echo -e "${BLUE}💡 Example usage:${NC}"
        echo "  $0 my-requirements.pdf"
        echo "  $0 large-document.pdf"
        echo "  $0 small-doc.txt force-json"
        echo "  $0 status 12345678-abcd-1234-efgh-123456789012"
        exit 0
    fi
    
    case "$1" in
        "health")
            # Already checked above
            ;;
        "status")
            if [ -n "$2" ]; then
                check_status "$2"
            else
                echo -e "${RED}❌ Please provide a request ID${NC}"
                echo "Usage: $0 status REQUEST_ID"
                exit 1
            fi
            ;;
        "history")
            get_history
            ;;
        "compare")
            show_method_comparison
            ;;
        *)
            # File upload
            file_path="$1"
            force_method="$2"
            
            if [ ! -f "$file_path" ]; then
                echo -e "${RED}❌ File not found: $file_path${NC}"
                exit 1
            fi
            
            # Determine upload method
            upload_method=$(determine_upload_method "$file_path" "$force_method")
            if [ $? -ne 0 ]; then
                exit 1
            fi
            
            echo ""
            
            # Execute upload based on method
            if [ "$upload_method" = "s3" ]; then
                upload_s3_method "$file_path"
            else
                upload_json_method "$file_path"
            fi
            ;;
    esac
}

# Run main function
main "$@"