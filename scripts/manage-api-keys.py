#!/usr/bin/env python3
"""
API Key Management Script for AutoSpec.AI

This script provides utilities to create, list, and manage API keys
for the AutoSpec.AI system.

Usage:
    python3 manage-api-keys.py create --client-name "Client Name" --environment dev
    python3 manage-api-keys.py list --environment dev
    python3 manage-api-keys.py revoke --key-id <key_id> --environment dev
    python3 manage-api-keys.py rotate --key-id <key_id> --environment dev
"""

import argparse
import boto3
import hashlib
import secrets
import json
import sys
from datetime import datetime, timezone, timedelta
from botocore.exceptions import ClientError

class APIKeyManager:
    def __init__(self, environment='dev'):
        self.environment = environment
        self.dynamodb = boto3.resource('dynamodb')
        self.table_name = f'autospec-ai-api-keys-{environment}'
        
        try:
            self.table = self.dynamodb.Table(self.table_name)
            # Test table access
            self.table.meta.reload()
        except Exception as e:
            print(f"Error accessing DynamoDB table '{self.table_name}': {e}")
            sys.exit(1)
    
    def generate_api_key(self):
        """Generate a secure API key."""
        # Generate 32 random bytes and encode as hex (64 character string)
        return secrets.token_hex(32)
    
    def create_api_key(self, client_name, rate_limit_tier='standard', 
                      permissions=None, expiry_days=365):
        """Create a new API key."""
        if permissions is None:
            permissions = ['read', 'write']
        
        # Generate API key and hash
        api_key = self.generate_api_key()
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        # Generate client ID
        client_id = f"client-{secrets.token_hex(8)}"
        
        # Calculate expiry date
        expiry_date = datetime.now(timezone.utc) + timedelta(days=expiry_days)
        
        # Create DynamoDB item
        item = {
            'keyHash': key_hash,
            'clientId': client_id,
            'clientName': client_name,
            'isActive': True,
            'rateLimitTier': rate_limit_tier,
            'permissions': permissions,
            'createdAt': datetime.now(timezone.utc).isoformat(),
            'expiryDate': expiry_date.isoformat(),
            'usageCount': 0,
            'environment': self.environment
        }
        
        try:
            # Store in DynamoDB
            self.table.put_item(Item=item)
            
            # Return the API key and metadata (key is only shown once)
            return {
                'api_key': api_key,
                'client_id': client_id,
                'client_name': client_name,
                'rate_limit_tier': rate_limit_tier,
                'permissions': permissions,
                'created_at': item['createdAt'],
                'expiry_date': item['expiryDate']
            }
            
        except ClientError as e:
            print(f"Error creating API key: {e}")
            return None
    
    def list_api_keys(self):
        """List all API keys (without revealing the actual keys)."""
        try:
            response = self.table.scan()
            items = response['Items']
            
            # Handle pagination if needed
            while 'LastEvaluatedKey' in response:
                response = self.table.scan(
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                items.extend(response['Items'])
            
            # Format for display
            keys = []
            for item in items:
                keys.append({
                    'key_id': item['keyHash'][:16] + '...',  # Show partial hash
                    'client_id': item.get('clientId'),
                    'client_name': item.get('clientName'),
                    'is_active': item.get('isActive'),
                    'rate_limit_tier': item.get('rateLimitTier'),
                    'permissions': item.get('permissions'),
                    'created_at': item.get('createdAt'),
                    'last_used': item.get('lastUsed', 'Never'),
                    'usage_count': item.get('usageCount', 0),
                    'expiry_date': item.get('expiryDate')
                })
            
            return sorted(keys, key=lambda x: x['created_at'], reverse=True)
            
        except ClientError as e:
            print(f"Error listing API keys: {e}")
            return []
    
    def revoke_api_key(self, key_hash_prefix):
        """Revoke (deactivate) an API key by hash prefix."""
        try:
            # Find the key by hash prefix
            response = self.table.scan(
                FilterExpression='begins_with(keyHash, :prefix)',
                ExpressionAttributeValues={':prefix': key_hash_prefix}
            )
            
            if not response['Items']:
                print(f"No API key found with hash prefix: {key_hash_prefix}")
                return False
            
            if len(response['Items']) > 1:
                print(f"Multiple keys found with prefix {key_hash_prefix}. Please provide a more specific prefix.")
                return False
            
            item = response['Items'][0]
            key_hash = item['keyHash']
            
            # Update the key to deactivate it
            self.table.update_item(
                Key={'keyHash': key_hash},
                UpdateExpression='SET isActive = :active, revokedAt = :timestamp',
                ExpressionAttributeValues={
                    ':active': False,
                    ':timestamp': datetime.now(timezone.utc).isoformat()
                }
            )
            
            print(f"API key revoked successfully for client: {item.get('clientName')}")
            return True
            
        except ClientError as e:
            print(f"Error revoking API key: {e}")
            return False
    
    def rotate_api_key(self, key_hash_prefix):
        """Create a new API key for an existing client and revoke the old one."""
        try:
            # Find the existing key
            response = self.table.scan(
                FilterExpression='begins_with(keyHash, :prefix)',
                ExpressionAttributeValues={':prefix': key_hash_prefix}
            )
            
            if not response['Items']:
                print(f"No API key found with hash prefix: {key_hash_prefix}")
                return None
            
            if len(response['Items']) > 1:
                print(f"Multiple keys found with prefix {key_hash_prefix}. Please provide a more specific prefix.")
                return None
            
            old_item = response['Items'][0]
            
            # Create a new key with the same client details
            new_key_data = self.create_api_key(
                client_name=old_item.get('clientName'),
                rate_limit_tier=old_item.get('rateLimitTier', 'standard'),
                permissions=old_item.get('permissions', ['read', 'write'])
            )
            
            if new_key_data:
                # Revoke the old key
                self.revoke_api_key(key_hash_prefix)
                print(f"API key rotated successfully for client: {old_item.get('clientName')}")
                return new_key_data
            
            return None
            
        except ClientError as e:
            print(f"Error rotating API key: {e}")
            return None

def main():
    parser = argparse.ArgumentParser(description='Manage AutoSpec.AI API Keys')
    parser.add_argument('--environment', '-e', default='dev', 
                       choices=['dev', 'staging', 'prod'],
                       help='Environment (dev, staging, prod)')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Create command
    create_parser = subparsers.add_parser('create', help='Create a new API key')
    create_parser.add_argument('--client-name', required=True,
                              help='Name of the client')
    create_parser.add_argument('--rate-limit-tier', default='standard',
                              choices=['basic', 'standard', 'premium'],
                              help='Rate limit tier')
    create_parser.add_argument('--permissions', nargs='+', default=['read', 'write'],
                              help='Permissions for the API key')
    create_parser.add_argument('--expiry-days', type=int, default=365,
                              help='Number of days until key expires')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List all API keys')
    
    # Revoke command
    revoke_parser = subparsers.add_parser('revoke', help='Revoke an API key')
    revoke_parser.add_argument('--key-id', required=True,
                              help='Key hash prefix to revoke')
    
    # Rotate command
    rotate_parser = subparsers.add_parser('rotate', help='Rotate an API key')
    rotate_parser.add_argument('--key-id', required=True,
                              help='Key hash prefix to rotate')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Initialize API key manager
    manager = APIKeyManager(args.environment)
    
    if args.command == 'create':
        print(f"Creating API key for '{args.client_name}' in {args.environment} environment...")
        result = manager.create_api_key(
            client_name=args.client_name,
            rate_limit_tier=args.rate_limit_tier,
            permissions=args.permissions,
            expiry_days=args.expiry_days
        )
        
        if result:
            print("\\n" + "="*60)
            print("API KEY CREATED SUCCESSFULLY")
            print("="*60)
            print(f"Client Name: {result['client_name']}")
            print(f"Client ID: {result['client_id']}")
            print(f"API Key: {result['api_key']}")
            print(f"Rate Limit Tier: {result['rate_limit_tier']}")
            print(f"Permissions: {', '.join(result['permissions'])}")
            print(f"Created: {result['created_at']}")
            print(f"Expires: {result['expiry_date']}")
            print("="*60)
            print("⚠️  IMPORTANT: Save this API key now. It cannot be retrieved again!")
            print("="*60)
        else:
            print("Failed to create API key.")
            sys.exit(1)
    
    elif args.command == 'list':
        print(f"Listing API keys for {args.environment} environment...\\n")
        keys = manager.list_api_keys()
        
        if not keys:
            print("No API keys found.")
        else:
            print(f"{'Key ID':<20} {'Client Name':<20} {'Active':<8} {'Tier':<10} {'Usage':<8} {'Created':<20}")
            print("-" * 100)
            for key in keys:
                status = "✅" if key['is_active'] else "❌"
                created = key['created_at'][:10] if key['created_at'] else 'Unknown'
                print(f"{key['key_id']:<20} {key['client_name']:<20} {status:<8} {key['rate_limit_tier']:<10} {key['usage_count']:<8} {created:<20}")
    
    elif args.command == 'revoke':
        print(f"Revoking API key {args.key_id} in {args.environment} environment...")
        success = manager.revoke_api_key(args.key_id)
        if not success:
            sys.exit(1)
    
    elif args.command == 'rotate':
        print(f"Rotating API key {args.key_id} in {args.environment} environment...")
        result = manager.rotate_api_key(args.key_id)
        
        if result:
            print("\\n" + "="*60)
            print("API KEY ROTATED SUCCESSFULLY")
            print("="*60)
            print(f"New API Key: {result['api_key']}")
            print(f"Client ID: {result['client_id']}")
            print("="*60)
            print("⚠️  IMPORTANT: Update your applications with the new API key!")
            print("="*60)
        else:
            sys.exit(1)

if __name__ == '__main__':
    main()