#!/bin/bash

# AutoSpec.AI - Simple Document Upload Script
# Usage: ./test-upload.sh /path/to/your/document.pdf

set -e

# Configuration - Set these environment variables or update the values below
API_URL="${AUTOSPEC_API_URL:-YOUR_API_GATEWAY_URL}"
API_KEY="${AUTOSPEC_API_KEY:-YOUR_API_KEY_HERE}"

# Check if API configuration is set
if [ "$API_URL" = "YOUR_API_GATEWAY_URL" ] || [ "$API_KEY" = "YOUR_API_KEY_HERE" ]; then
    echo "❌ Error: API configuration not set!"
    echo "Please set the following environment variables:"
    echo "  export AUTOSPEC_API_URL='https://your-api.execute-api.us-east-1.amazonaws.com/prod'"
    echo "  export AUTOSPEC_API_KEY='your-api-key'"
    exit 1
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 AutoSpec.AI Document Upload Tool${NC}"
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

# Function to upload document
upload_document() {
    local file_path="$1"
    
    if [ ! -f "$file_path" ]; then
        echo -e "${RED}❌ File not found: $file_path${NC}"
        return 1
    fi
    
    echo -e "${YELLOW}📤 Uploading document: $(basename "$file_path")${NC}"
    
    # Check file size (max 10MB)
    file_size=$(stat -c%s "$file_path")
    max_size=$((10 * 1024 * 1024))  # 10MB
    
    if [ "$file_size" -gt "$max_size" ]; then
        echo -e "${RED}❌ File too large: $(($file_size / 1024 / 1024))MB (max 10MB)${NC}"
        return 1
    fi
    
    echo -e "${BLUE}📊 File size: $(($file_size / 1024))KB${NC}"
    
    # Encode file content to base64
    file_content=$(base64 -w 0 "$file_path")
    filename=$(basename "$file_path")
    
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
        echo -e "${GREEN}✅ Upload successful!${NC}"
        echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"
        
        # Extract request ID
        request_id=$(echo "$body" | grep -o '"request_id":"[^"]*"' | cut -d'"' -f4)
        if [ -z "$request_id" ]; then
            request_id=$(echo "$body" | grep -o '"requestId":"[^"]*"' | cut -d'"' -f4)
        fi
        
        if [ -n "$request_id" ]; then
            echo -e "${BLUE}📋 Your Request ID: ${request_id}${NC}"
            echo -e "${YELLOW}💡 Save this ID to check processing status later!${NC}"
            
            # Auto-check status after a short delay
            echo -e "${YELLOW}⏳ Checking initial status in 3 seconds...${NC}"
            sleep 3
            check_status "$request_id"
        fi
        
        return 0
    else
        echo -e "${RED}❌ Upload failed (HTTP $http_code)${NC}"
        echo "$body"
        return 1
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
        echo "  Upload document:     $0 /path/to/document.pdf"
        echo "  Check status:        $0 status REQUEST_ID"
        echo "  Get history:         $0 history"
        echo "  Health check only:   $0 health"
        echo ""
        echo -e "${BLUE}💡 Example usage:${NC}"
        echo "  $0 my-requirements.pdf"
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
        *)
            upload_document "$1"
            ;;
    esac
}

# Run main function
main "$@"