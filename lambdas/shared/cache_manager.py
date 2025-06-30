"""
AutoSpec.AI Caching Manager

Provides multi-layer caching strategies for frequently accessed data:
- In-memory caching for function-level data
- Redis/ElastiCache for distributed caching
- DynamoDB TTL for persistent but expiring data
- S3 caching for large objects with intelligent tiering

Usage:
    from shared.cache_manager import CacheManager
    
    cache = CacheManager()
    
    # Simple caching
    result = cache.get_or_set('key', expensive_function, ttl=300)
    
    # Multi-layer caching
    data = cache.get_cached_analysis('document_id', analysis_function)
    
    # Configuration caching
    config = cache.get_cached_config('environment')
"""

import json
import time
import hashlib
import os
import boto3
import logging
from typing import Any, Optional, Dict, List, Callable, Union
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
from functools import wraps
import threading

logger = logging.getLogger(__name__)

@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    key: str
    value: Any
    created_at: float
    ttl: int
    access_count: int = 0
    last_accessed: float = 0
    size_bytes: int = 0

@dataclass
class CacheStats:
    """Cache performance statistics."""
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    evictions: int = 0
    total_size_bytes: int = 0
    
    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0

class InMemoryCache:
    """High-performance in-memory cache with LRU eviction."""
    
    def __init__(self, max_size_mb: int = 50, max_entries: int = 1000):
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.max_entries = max_entries
        self.cache: Dict[str, CacheEntry] = {}
        self.stats = CacheStats()
        self._lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        with self._lock:
            entry = self.cache.get(key)
            if not entry:
                self.stats.misses += 1
                return None
            
            # Check TTL
            if time.time() - entry.created_at > entry.ttl:
                self.delete(key)
                self.stats.misses += 1
                return None
            
            # Update access stats
            entry.access_count += 1
            entry.last_accessed = time.time()
            self.stats.hits += 1
            
            return entry.value
    
    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Set value in cache with TTL."""
        with self._lock:
            # Calculate size
            size_bytes = self._calculate_size(value)
            
            # Check if we need to evict
            if len(self.cache) >= self.max_entries or \
               self.stats.total_size_bytes + size_bytes > self.max_size_bytes:
                self._evict_if_needed(size_bytes)
            
            # Create cache entry
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=time.time(),
                ttl=ttl,
                size_bytes=size_bytes
            )
            
            # Remove old entry if exists
            if key in self.cache:
                self.stats.total_size_bytes -= self.cache[key].size_bytes
            
            self.cache[key] = entry
            self.stats.total_size_bytes += size_bytes
            self.stats.sets += 1
            
            return True
    
    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        with self._lock:
            if key in self.cache:
                self.stats.total_size_bytes -= self.cache[key].size_bytes
                del self.cache[key]
                self.stats.deletes += 1
                return True
            return False
    
    def clear(self):
        """Clear all cache entries."""
        with self._lock:
            self.cache.clear()
            self.stats.total_size_bytes = 0
    
    def _calculate_size(self, value: Any) -> int:
        """Estimate memory size of value."""
        try:
            if isinstance(value, str):
                return len(value.encode('utf-8'))
            elif isinstance(value, (dict, list)):
                return len(json.dumps(value).encode('utf-8'))
            else:
                return len(str(value).encode('utf-8'))
        except Exception:
            return 1024  # Default estimate
    
    def _evict_if_needed(self, incoming_size: int):
        """Evict least recently used items if needed."""
        # Sort by last accessed time (LRU)
        sorted_entries = sorted(
            self.cache.values(),
            key=lambda x: x.last_accessed or x.created_at
        )
        
        # Evict until we have space
        while (len(self.cache) >= self.max_entries or 
               self.stats.total_size_bytes + incoming_size > self.max_size_bytes) and \
               sorted_entries:
            
            entry_to_evict = sorted_entries.pop(0)
            self.delete(entry_to_evict.key)
            self.stats.evictions += 1

class DynamoDBCache:
    """Persistent cache using DynamoDB with TTL."""
    
    def __init__(self, table_name: str, environment: str = 'dev'):
        self.table_name = f"{table_name}-{environment}"
        self.dynamodb = boto3.resource('dynamodb')
        self.table = None
        self._ensure_table()
    
    def _ensure_table(self):
        """Ensure cache table exists."""
        try:
            self.table = self.dynamodb.Table(self.table_name)
            # Test table access
            self.table.describe()
        except Exception as e:
            logger.warning(f"DynamoDB cache table not available: {e}")
            self.table = None
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from DynamoDB cache."""
        if not self.table:
            return None
        
        try:
            response = self.table.get_item(
                Key={'cache_key': key}
            )
            
            if 'Item' not in response:
                return None
            
            item = response['Item']
            
            # Check TTL (DynamoDB TTL is handled automatically, but we double-check)
            if 'ttl' in item and item['ttl'] < int(time.time()):
                return None
            
            # Deserialize value
            if item['value_type'] == 'json':
                return json.loads(item['value'])
            else:
                return item['value']
                
        except Exception as e:
            logger.error(f"Error getting from DynamoDB cache: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set value in DynamoDB cache with TTL."""
        if not self.table:
            return False
        
        try:
            # Serialize value
            if isinstance(value, (dict, list)):
                serialized_value = json.dumps(value)
                value_type = 'json'
            else:
                serialized_value = str(value)
                value_type = 'string'
            
            expiry_time = int(time.time()) + ttl
            
            self.table.put_item(
                Item={
                    'cache_key': key,
                    'value': serialized_value,
                    'value_type': value_type,
                    'created_at': int(time.time()),
                    'ttl': expiry_time
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error setting DynamoDB cache: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete value from DynamoDB cache."""
        if not self.table:
            return False
        
        try:
            self.table.delete_item(
                Key={'cache_key': key}
            )
            return True
        except Exception as e:
            logger.error(f"Error deleting from DynamoDB cache: {e}")
            return False

class S3Cache:
    """S3-based cache for large objects with intelligent tiering."""
    
    def __init__(self, bucket_name: str, prefix: str = 'cache/'):
        self.bucket_name = bucket_name
        self.prefix = prefix
        self.s3_client = boto3.client('s3')
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from S3 cache."""
        try:
            s3_key = f"{self.prefix}{key}"
            
            # Get object
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            # Check metadata for TTL
            metadata = response.get('Metadata', {})
            if 'ttl' in metadata:
                ttl = int(metadata['ttl'])
                if ttl < int(time.time()):
                    # Object expired, delete it
                    self.delete(key)
                    return None
            
            # Read and deserialize content
            content = response['Body'].read()
            
            content_type = metadata.get('content_type', 'string')
            if content_type == 'json':
                return json.loads(content.decode('utf-8'))
            else:
                return content.decode('utf-8')
                
        except self.s3_client.exceptions.NoSuchKey:
            return None
        except Exception as e:
            logger.error(f"Error getting from S3 cache: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set value in S3 cache with TTL."""
        try:
            s3_key = f"{self.prefix}{key}"
            
            # Serialize value
            if isinstance(value, (dict, list)):
                content = json.dumps(value).encode('utf-8')
                content_type = 'json'
            else:
                content = str(value).encode('utf-8')
                content_type = 'string'
            
            # Calculate expiry
            expiry_time = int(time.time()) + ttl
            
            # Store with metadata
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=content,
                Metadata={
                    'content_type': content_type,
                    'created_at': str(int(time.time())),
                    'ttl': str(expiry_time)
                },
                StorageClass='STANDARD_IA'  # Use Infrequent Access for cost efficiency
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error setting S3 cache: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete value from S3 cache."""
        try:
            s3_key = f"{self.prefix}{key}"
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            return True
        except Exception as e:
            logger.error(f"Error deleting from S3 cache: {e}")
            return False

class CacheManager:
    """Multi-layer cache manager with intelligent caching strategies."""
    
    def __init__(self, environment: str = 'dev'):
        self.environment = environment
        
        # Initialize cache layers
        self.memory_cache = InMemoryCache()
        
        # DynamoDB cache (optional)
        cache_table = os.environ.get('CACHE_TABLE', 'autospec-ai-cache')
        self.dynamodb_cache = DynamoDBCache(cache_table, environment)
        
        # S3 cache (optional)
        cache_bucket = os.environ.get('PROCESSING_BUCKET') or os.environ.get('DOCUMENT_BUCKET')
        self.s3_cache = S3Cache(cache_bucket, 'cache/') if cache_bucket else None
        
        # Cache strategies configuration
        self.strategies = {
            'config': {'memory': True, 'dynamodb': True, 's3': False, 'ttl': 1800},
            'analysis': {'memory': True, 'dynamodb': True, 's3': True, 'ttl': 3600},
            'template': {'memory': True, 'dynamodb': True, 's3': False, 'ttl': 7200},
            'document_meta': {'memory': True, 'dynamodb': True, 's3': False, 'ttl': 900},
            'api_response': {'memory': True, 'dynamodb': False, 's3': False, 'ttl': 300},
            'bedrock_result': {'memory': False, 'dynamodb': True, 's3': True, 'ttl': 86400}
        }
    
    def get(self, key: str, cache_type: str = 'default') -> Optional[Any]:
        """Get value using multi-layer cache strategy."""
        strategy = self.strategies.get(cache_type, {'memory': True, 'dynamodb': False, 's3': False})
        
        # Try memory cache first
        if strategy.get('memory', True):
            value = self.memory_cache.get(key)
            if value is not None:
                logger.debug(f"Cache hit (memory): {key}")
                return value
        
        # Try DynamoDB cache
        if strategy.get('dynamodb', False):
            value = self.dynamodb_cache.get(key)
            if value is not None:
                logger.debug(f"Cache hit (DynamoDB): {key}")
                # Populate memory cache for faster access
                if strategy.get('memory', True):
                    self.memory_cache.set(key, value, strategy.get('ttl', 300))
                return value
        
        # Try S3 cache
        if strategy.get('s3', False) and self.s3_cache:
            value = self.s3_cache.get(key)
            if value is not None:
                logger.debug(f"Cache hit (S3): {key}")
                # Populate lower-level caches
                if strategy.get('memory', True):
                    self.memory_cache.set(key, value, strategy.get('ttl', 300))
                if strategy.get('dynamodb', False):
                    self.dynamodb_cache.set(key, value, strategy.get('ttl', 300))
                return value
        
        logger.debug(f"Cache miss: {key}")
        return None
    
    def set(self, key: str, value: Any, cache_type: str = 'default', ttl: Optional[int] = None) -> bool:
        """Set value using multi-layer cache strategy."""
        strategy = self.strategies.get(cache_type, {'memory': True, 'dynamodb': False, 's3': False})
        effective_ttl = ttl or strategy.get('ttl', 300)
        
        success = True
        
        # Set in memory cache
        if strategy.get('memory', True):
            success &= self.memory_cache.set(key, value, effective_ttl)
        
        # Set in DynamoDB cache
        if strategy.get('dynamodb', False):
            success &= self.dynamodb_cache.set(key, value, effective_ttl)
        
        # Set in S3 cache
        if strategy.get('s3', False) and self.s3_cache:
            success &= self.s3_cache.set(key, value, effective_ttl)
        
        if success:
            logger.debug(f"Cache set: {key} (type: {cache_type})")
        
        return success
    
    def get_or_set(self, key: str, factory_func: Callable[[], Any], 
                   cache_type: str = 'default', ttl: Optional[int] = None) -> Any:
        """Get value from cache or compute and cache it."""
        # Try to get from cache first
        value = self.get(key, cache_type)
        
        if value is not None:
            return value
        
        # Compute value using factory function
        try:
            value = factory_func()
            
            # Cache the computed value
            self.set(key, value, cache_type, ttl)
            
            return value
            
        except Exception as e:
            logger.error(f"Error computing value for cache key {key}: {e}")
            raise
    
    def invalidate(self, key: str, cache_type: str = 'default') -> bool:
        """Invalidate cache entry across all layers."""
        strategy = self.strategies.get(cache_type, {'memory': True, 'dynamodb': False, 's3': False})
        
        success = True
        
        if strategy.get('memory', True):
            success &= self.memory_cache.delete(key)
        
        if strategy.get('dynamodb', False):
            success &= self.dynamodb_cache.delete(key)
        
        if strategy.get('s3', False) and self.s3_cache:
            success &= self.s3_cache.delete(key)
        
        return success
    
    def invalidate_pattern(self, pattern: str, cache_type: str = 'default'):
        """Invalidate all cache entries matching a pattern."""
        # For memory cache, we can check all keys
        keys_to_delete = []
        for key in self.memory_cache.cache.keys():
            if pattern in key:
                keys_to_delete.append(key)
        
        for key in keys_to_delete:
            self.invalidate(key, cache_type)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        return {
            'memory_cache': asdict(self.memory_cache.stats),
            'memory_cache_entries': len(self.memory_cache.cache),
            'memory_cache_size_mb': self.memory_cache.stats.total_size_bytes / 1024 / 1024,
            'cache_strategies': self.strategies
        }
    
    # Specialized caching methods for common use cases
    
    def get_cached_config(self, config_key: str) -> Optional[Dict[str, Any]]:
        """Get cached configuration with automatic key generation."""
        cache_key = f"config:{self.environment}:{config_key}"
        return self.get(cache_key, 'config')
    
    def set_cached_config(self, config_key: str, config_data: Dict[str, Any]):
        """Set cached configuration."""
        cache_key = f"config:{self.environment}:{config_key}"
        self.set(cache_key, config_data, 'config')
    
    def get_cached_analysis(self, document_id: str, document_hash: str) -> Optional[Dict[str, Any]]:
        """Get cached AI analysis result."""
        cache_key = f"analysis:{document_hash}:{document_id}"
        return self.get(cache_key, 'analysis')
    
    def set_cached_analysis(self, document_id: str, document_hash: str, analysis_result: Dict[str, Any]):
        """Set cached AI analysis result."""
        cache_key = f"analysis:{document_hash}:{document_id}"
        self.set(cache_key, analysis_result, 'analysis')
    
    def get_cached_template(self, template_name: str, template_vars: Dict[str, Any]) -> Optional[str]:
        """Get cached template result."""
        vars_hash = hashlib.md5(json.dumps(template_vars, sort_keys=True).encode()).hexdigest()[:8]
        cache_key = f"template:{template_name}:{vars_hash}"
        return self.get(cache_key, 'template')
    
    def set_cached_template(self, template_name: str, template_vars: Dict[str, Any], rendered_template: str):
        """Set cached template result."""
        vars_hash = hashlib.md5(json.dumps(template_vars, sort_keys=True).encode()).hexdigest()[:8]
        cache_key = f"template:{template_name}:{vars_hash}"
        self.set(cache_key, rendered_template, 'template')

# Decorator for automatic caching
def cached(cache_type: str = 'default', ttl: Optional[int] = None, key_func: Optional[Callable] = None):
    """Decorator for automatic function result caching."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get cache manager (assumes it's available in context)
            cache_manager = kwargs.pop('_cache_manager', None) or getattr(wrapper, '_cache_manager', None)
            
            if not cache_manager:
                # No cache manager available, execute function normally
                return func(*args, **kwargs)
            
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Generate key from function name and arguments
                args_str = json.dumps([str(arg) for arg in args], sort_keys=True)
                kwargs_str = json.dumps(kwargs, sort_keys=True)
                combined = f"{func.__name__}:{args_str}:{kwargs_str}"
                cache_key = hashlib.md5(combined.encode()).hexdigest()
            
            # Try to get from cache
            result = cache_manager.get(cache_key, cache_type)
            if result is not None:
                return result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache_manager.set(cache_key, result, cache_type, ttl)
            
            return result
        
        return wrapper
    return decorator

# Initialize global cache manager
_cache_manager_instance = None

def get_cache_manager(environment: str = None) -> CacheManager:
    """Get global cache manager instance."""
    global _cache_manager_instance
    
    if _cache_manager_instance is None:
        env = environment or os.environ.get('ENVIRONMENT', 'dev')
        _cache_manager_instance = CacheManager(env)
    
    return _cache_manager_instance