"""
Admin Settings Service
Handles admin configuration settings stored in database
"""
import logging
from typing import Any, Optional
from datetime import datetime, timezone
from supabase import Client

logger = logging.getLogger(__name__)


class AdminSettingsService:
    """Service for managing admin settings"""
    
    def __init__(self, supabase_client: Client):
        """
        Initialize AdminSettingsService
        
        Args:
            supabase_client: Supabase client instance
        """
        self.supabase = supabase_client
    
    def get_admin_setting(self, setting_key: str, default_value: Any = None) -> Any:
        """
        Get admin setting from database
        
        Args:
            setting_key: Setting key (e.g., 'ADMIN_RECOMMENDATION_ENABLED')
            default_value: Default value if setting not found
            
        Returns:
            Setting value (parsed from JSONB) or default_value
        """
        try:
            result = self.supabase.table('admin_settings') \
                .select('setting_value') \
                .eq('setting_key', setting_key) \
                .execute()
            
            if result.data and len(result.data) > 0:
                value = result.data[0].get('setting_value')
                # Parse JSONB value
                if isinstance(value, bool):
                    return value
                elif isinstance(value, str):
                    # Handle string booleans
                    if value.lower() in ('true', 'false'):
                        return value.lower() == 'true'
                    return value
                elif isinstance(value, (int, float)):
                    return value
                else:
                    return value
            else:
                logger.info(f"Setting {setting_key} not found, using default: {default_value}")
                return default_value
                
        except Exception as e:
            logger.error(f"Error getting admin setting {setting_key}: {str(e)}")
            return default_value
    
    def set_admin_setting(self, setting_key: str, setting_value: Any, updated_by: Optional[str] = None) -> bool:
        """
        Set admin setting in database
        
        Args:
            setting_key: Setting key (e.g., 'ADMIN_RECOMMENDATION_ENABLED')
            setting_value: Setting value (will be stored as JSONB)
            updated_by: Optional user ID who made the update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Prepare data
            data = {
                'setting_key': setting_key,
                'setting_value': setting_value,  # Supabase will handle JSONB conversion
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
            
            if updated_by:
                data['updated_by'] = updated_by
                # Also store admin_id for traceability
                data['admin_id'] = updated_by
            
            # Upsert (insert or update)
            result = self.supabase.table('admin_settings') \
                .upsert(data) \
                .execute()
            
            if result.data:
                logger.info(f"✅ Updated admin setting {setting_key} = {setting_value}")
                return True
            else:
                logger.warning(f"⚠️ Upsert returned no data for {setting_key}")
                return False
                
        except Exception as e:
            logger.error(f"Error setting admin setting {setting_key}: {str(e)}")
            return False

