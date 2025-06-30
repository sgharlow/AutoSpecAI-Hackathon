import json
import logging

logger = logging.getLogger()

class FormatPreferences:
    """Handle user format preferences and selection options."""
    
    DEFAULT_FORMATS = ['markdown', 'json', 'html', 'pdf']
    
    @staticmethod
    def parse_email_preferences(email_body):
        """Parse format preferences from email body."""
        try:
            preferences = {
                'formats': FormatPreferences.DEFAULT_FORMATS.copy(),
                'quality': 'standard',  # standard, high, premium
                'charts': True,
                'interactive': True
            }
            
            email_lower = email_body.lower()
            
            # Check for format requests
            if 'pdf only' in email_lower or 'just pdf' in email_lower:
                preferences['formats'] = ['pdf']
            elif 'no pdf' in email_lower or 'skip pdf' in email_lower:
                preferences['formats'] = [f for f in preferences['formats'] if f != 'pdf']
            elif 'markdown only' in email_lower:
                preferences['formats'] = ['markdown']
            elif 'json only' in email_lower:
                preferences['formats'] = ['json']
            
            # Check for quality preferences
            if 'high quality' in email_lower or 'detailed' in email_lower:
                preferences['quality'] = 'high'
            elif 'premium' in email_lower or 'professional' in email_lower:
                preferences['quality'] = 'premium'
            elif 'simple' in email_lower or 'basic' in email_lower:
                preferences['quality'] = 'standard'
                preferences['charts'] = False
                preferences['interactive'] = False
            
            # Check for chart preferences
            if 'no charts' in email_lower or 'no graphs' in email_lower:
                preferences['charts'] = False
            elif 'with charts' in email_lower or 'include charts' in email_lower:
                preferences['charts'] = True
            
            # Check for interactive preferences
            if 'static' in email_lower or 'no interactive' in email_lower:
                preferences['interactive'] = False
            
            return preferences
            
        except Exception as e:
            logger.error(f"Error parsing email preferences: {str(e)}")
            return FormatPreferences.get_default_preferences()
    
    @staticmethod
    def parse_api_preferences(request_body):
        """Parse format preferences from API request."""
        try:
            preferences = FormatPreferences.get_default_preferences()
            
            if isinstance(request_body, dict):
                # Direct preferences in request
                user_prefs = request_body.get('preferences', {})
                
                if 'formats' in user_prefs:
                    requested_formats = user_prefs['formats']
                    if isinstance(requested_formats, list):
                        valid_formats = [f for f in requested_formats if f in FormatPreferences.DEFAULT_FORMATS]
                        if valid_formats:
                            preferences['formats'] = valid_formats
                
                if 'quality' in user_prefs:
                    quality = user_prefs['quality']
                    if quality in ['standard', 'high', 'premium']:
                        preferences['quality'] = quality
                
                if 'charts' in user_prefs:
                    preferences['charts'] = bool(user_prefs['charts'])
                
                if 'interactive' in user_prefs:
                    preferences['interactive'] = bool(user_prefs['interactive'])
            
            return preferences
            
        except Exception as e:
            logger.error(f"Error parsing API preferences: {str(e)}")
            return FormatPreferences.get_default_preferences()
    
    @staticmethod
    def get_default_preferences():
        """Get default format preferences."""
        return {
            'formats': FormatPreferences.DEFAULT_FORMATS.copy(),
            'quality': 'standard',
            'charts': True,
            'interactive': True
        }
    
    @staticmethod
    def apply_preferences_to_generation(preferences, request_data):
        """Apply user preferences to format generation process."""
        try:
            # Update request data with preferences
            enhanced_request = request_data.copy()
            enhanced_request['formatPreferences'] = preferences
            
            # Adjust processing based on quality level
            if preferences['quality'] == 'premium':
                enhanced_request['enableAdvancedCharts'] = True
                enhanced_request['enableDetailedAnalysis'] = True
                enhanced_request['enableInteractiveFeatures'] = True
            elif preferences['quality'] == 'high':
                enhanced_request['enableAdvancedCharts'] = preferences['charts']
                enhanced_request['enableDetailedAnalysis'] = True
                enhanced_request['enableInteractiveFeatures'] = preferences['interactive']
            else:  # standard
                enhanced_request['enableAdvancedCharts'] = preferences['charts']
                enhanced_request['enableDetailedAnalysis'] = False
                enhanced_request['enableInteractiveFeatures'] = preferences['interactive']
            
            return enhanced_request
            
        except Exception as e:
            logger.error(f"Error applying preferences: {str(e)}")
            return request_data
    
    @staticmethod
    def filter_outputs_by_preferences(formatted_outputs, preferences):
        """Filter generated outputs based on user preferences."""
        try:
            filtered_outputs = {}
            
            for format_type in preferences['formats']:
                if format_type in formatted_outputs:
                    filtered_outputs[format_type] = formatted_outputs[format_type]
            
            # Always include markdown and json for system use
            if 'markdown' not in filtered_outputs and 'markdown' in formatted_outputs:
                filtered_outputs['markdown'] = formatted_outputs['markdown']
            if 'json' not in filtered_outputs and 'json' in formatted_outputs:
                filtered_outputs['json'] = formatted_outputs['json']
            
            return filtered_outputs
            
        except Exception as e:
            logger.error(f"Error filtering outputs: {str(e)}")
            return formatted_outputs
    
    @staticmethod
    def create_preference_summary(preferences):
        """Create a human-readable summary of preferences."""
        try:
            summary_parts = []
            
            # Formats
            if len(preferences['formats']) == 1:
                summary_parts.append(f"Format: {preferences['formats'][0].upper()}")
            else:
                formats_str = ', '.join(f.upper() for f in preferences['formats'])
                summary_parts.append(f"Formats: {formats_str}")
            
            # Quality
            quality_desc = {
                'standard': 'Standard Quality',
                'high': 'High Quality with Charts',
                'premium': 'Premium Quality with Advanced Features'
            }
            summary_parts.append(quality_desc.get(preferences['quality'], 'Standard Quality'))
            
            # Special features
            features = []
            if preferences['charts']:
                features.append('Charts')
            if preferences['interactive']:
                features.append('Interactive Elements')
            
            if features:
                summary_parts.append(f"Features: {', '.join(features)}")
            
            return ' | '.join(summary_parts)
            
        except Exception as e:
            logger.error(f"Error creating preference summary: {str(e)}")
            return "Standard formatting preferences"

def extract_preferences_from_request(event_source, request_data):
    """Extract format preferences from different request sources."""
    try:
        if event_source == 'email':
            # Look for email body or subject preferences
            email_content = request_data.get('emailBody', '')
            return FormatPreferences.parse_email_preferences(email_content)
        
        elif event_source == 'api':
            # Look for preferences in API request
            return FormatPreferences.parse_api_preferences(request_data)
        
        elif event_source == 'slack':
            # Default for Slack (could be enhanced to parse slash command options)
            return {
                'formats': ['html', 'pdf'],  # Slack-friendly formats
                'quality': 'high',
                'charts': True,
                'interactive': False  # Slack doesn't support interactive HTML
            }
        
        else:
            return FormatPreferences.get_default_preferences()
            
    except Exception as e:
        logger.error(f"Error extracting preferences: {str(e)}")
        return FormatPreferences.get_default_preferences()