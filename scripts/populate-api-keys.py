#!/usr/bin/env python3

"""
Script to populate DynamoDB API keys table with the API keys from API Gateway usage plan.
This fixes the authentication issue where Lambda function can't find API keys in DynamoDB.
"""

import boto3
import hashlib
import json
from datetime import datetime, timezone, timedelta

def main():
    # Initialize AWS clients
    apigateway = boto3.client('apigateway', region_name='us-east-1')
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    
    # Get usage plan ID
    usage_plans = apigateway.get_usage_plans()
    autospec_plan = None
    for plan in usage_plans['items']:
        if 'AutoSpec' in plan['name']:
            autospec_plan = plan
            break
    
    if not autospec_plan:
        print("❌ AutoSpec usage plan not found")
        return False
    
    print(f"📋 Found usage plan: {autospec_plan['name']} (ID: {autospec_plan['id']})")
    
    # Get API keys from usage plan
    api_keys = apigateway.get_usage_plan_keys(usagePlanId=autospec_plan['id'])
    
    if not api_keys['items']:
        print("❌ No API keys found in usage plan")
        return False
    
    print(f"🔑 Found {len(api_keys['items'])} API keys in usage plan")
    
    # Get DynamoDB table
    table_name = 'autospec-ai-api-keys-prod'
    table = dynamodb.Table(table_name)
    
    print(f"📊 Using DynamoDB table: {table_name}")
    
    # Process each API key
    for api_key_info in api_keys['items']:
        api_key = api_key_info['value']
        key_name = api_key_info['name']
        key_id = api_key_info['id']
        
        # Generate SHA256 hash of the API key
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        # Create DynamoDB item
        current_time = datetime.now(timezone.utc)
        expiry_date = current_time + timedelta(days=365)  # 1 year expiry
        
        item = {
            'keyHash': key_hash,
            'keyId': key_id,
            'clientId': f"client-{key_name.lower().replace(' ', '-')}",
            'clientName': key_name,
            'isActive': True,
            'createdAt': current_time.isoformat(),
            'expiryDate': expiry_date.isoformat(),
            'lastUsed': current_time.isoformat(),
            'usageCount': 0,
            'rateLimitTier': 'standard',
            'permissions': ['read', 'write', 'upload', 'status', 'history'],
            'description': f'Production API key for {key_name}',
            'environment': 'production'
        }
        
        # Insert into DynamoDB
        try:
            table.put_item(Item=item)
            print(f"✅ Added API key: {key_name} (hash: {key_hash[:12]}...)")
        except Exception as e:
            print(f"❌ Failed to add API key {key_name}: {str(e)}")
            return False
    
    print(f"\n🎉 Successfully populated DynamoDB table with {len(api_keys['items'])} API keys!")
    
    # Verify by scanning the table
    print("\n🔍 Verifying table contents...")
    response = table.scan()
    print(f"📊 Table now contains {response['Count']} items")
    
    for item in response['Items']:
        print(f"   • {item['clientName']} - Active: {item['isActive']} - Permissions: {item['permissions']}")
    
    return True

if __name__ == '__main__':
    if main():
        print("\n✅ API key population completed successfully!")
        print("🚀 You can now test API authentication with the existing API keys.")
    else:
        print("\n❌ API key population failed!")
        exit(1)