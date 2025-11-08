#!/usr/bin/env python3
"""
Test environment configuration loading
"""
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

def test_config():
    """Test that all required configuration is loaded"""
    print("🔍 Testing environment configuration...\n")
    
    try:
        from app.v1.core.config import settings
        
        # Test required fields
        required_fields = {
            'SUPABASE_URL': settings.SUPABASE_URL,
            'SUPABASE_KEY': settings.SUPABASE_KEY,
            'JWT_SECRET': settings.JWT_SECRET,
            'JWT_EXPIRE': settings.JWT_EXPIRE,
            'OPENAI_API_KEY': settings.OPENAI_API_KEY,
        }
        
        print("✅ Required Configuration:")
        for key, value in required_fields.items():
            if value and value != "":
                # Mask sensitive values
                if 'KEY' in key or 'SECRET' in key:
                    masked = value[:8] + "..." + value[-4:] if len(value) > 12 else "***"
                    print(f"   ✓ {key}: {masked}")
                else:
                    print(f"   ✓ {key}: {value}")
            else:
                print(f"   ✗ {key}: NOT SET ⚠️")
                return False
        
        print("\n✅ Optional Configuration:")
        optional_fields = {
            'FALKORDB_HOST': settings.FALKORDB_HOST,
            'LANGCHAIN_API_KEY': settings.LANGCHAIN_API_KEY,
            'DATABASE_URL': settings.DATABASE_URL,
        }
        
        for key, value in optional_fields.items():
            if value and value != "":
                if 'KEY' in key or 'PASSWORD' in key or 'URL' in key:
                    masked = value[:8] + "..." + value[-4:] if len(value) > 12 else "***"
                    print(f"   ✓ {key}: {masked}")
                else:
                    print(f"   ✓ {key}: {value}")
            else:
                print(f"   - {key}: Not configured (optional)")
        
        print("\n✅ All required configuration is loaded successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error loading configuration: {str(e)}")
        print("\n💡 Make sure:")
        print("   1. You have copied .env.example to .env")
        print("   2. You have set all required values in .env")
        print("   3. You have generated a JWT_SECRET using generate_jwt_secret.py")
        return False

if __name__ == "__main__":
    success = test_config()
    sys.exit(0 if success else 1)
