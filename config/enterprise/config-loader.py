"""
Configuration loader for enterprise integrations.
Reads JSON configuration files and replaces ${VAR_NAME} placeholders with environment variables.
"""

import json
import os
import re
from typing import Any, Dict


def load_config_with_env_vars(config_path: str) -> Dict[str, Any]:
    """
    Load a JSON configuration file and replace ${VAR_NAME} placeholders with environment variables.
    
    Args:
        config_path: Path to the JSON configuration file
        
    Returns:
        Dictionary with environment variables substituted
    """
    # Read the configuration file
    with open(config_path, 'r') as f:
        config_str = f.read()
    
    # Find all ${VAR_NAME} placeholders
    pattern = r'\$\{([^}]+)\}'
    
    def replace_env_var(match):
        var_name = match.group(1)
        value = os.environ.get(var_name)
        if value is None:
            raise ValueError(f"Environment variable {var_name} is not set")
        return value
    
    # Replace all placeholders with environment variables
    config_str = re.sub(pattern, replace_env_var, config_str)
    
    # Parse the JSON
    return json.loads(config_str)


def load_third_party_config():
    """Load third-party integrations configuration."""
    config_file = os.path.join(os.path.dirname(__file__), 'third-party-integrations.json')
    
    # Check if actual config exists, otherwise use example
    if not os.path.exists(config_file):
        config_file = config_file + '.example'
    
    return load_config_with_env_vars(config_file)


def load_ldap_config():
    """Load LDAP configuration."""
    config_file = os.path.join(os.path.dirname(__file__), 'ldap-config.json')
    
    # Check if actual config exists, otherwise use example
    if not os.path.exists(config_file):
        config_file = config_file + '.example'
    
    return load_config_with_env_vars(config_file)


def load_oauth_config():
    """Load OAuth configuration."""
    config_file = os.path.join(os.path.dirname(__file__), 'sso-oauth-config.json')
    
    # Check if actual config exists, otherwise use example
    if not os.path.exists(config_file):
        config_file = config_file + '.example'
    
    return load_config_with_env_vars(config_file)


if __name__ == "__main__":
    # Example usage
    try:
        # Load third-party integrations config
        third_party_config = load_third_party_config()
        print("Third-party integrations loaded successfully")
        
        # Access specific configurations
        if 'slack' in third_party_config:
            slack_webhook = third_party_config['slack']['webhook_url']
            print(f"Slack webhook configured: {slack_webhook[:20]}...")
            
    except ValueError as e:
        print(f"Configuration error: {e}")
        print("Please ensure all required environment variables are set")
    except Exception as e:
        print(f"Error loading configuration: {e}")