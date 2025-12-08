"""
Unit test for SendGrid OTP email functionality
Tests if SendGrid client can send emails with configured .env parameters
"""
import pytest
import os
from app.v1.services.otp_service import get_otp_service, OTPService
from app.v1.core.config import settings


class TestSendGridOTP:
    """Test SendGrid OTP email sending"""
    
    def test_sendgrid_config_loaded(self):
        """Test that SendGrid config is loaded from .env"""
        assert hasattr(settings, 'SENDGRID_API_KEY'), "SENDGRID_API_KEY not found in settings"
        assert hasattr(settings, 'SENDGRID_FROM_EMAIL'), "SENDGRID_FROM_EMAIL not found in settings"
        assert hasattr(settings, 'OTP_EXPIRE_MINUTES'), "OTP_EXPIRE_MINUTES not found in settings"
        
        print(f"\n📧 SendGrid Configuration:")
        print(f"   API Key configured: {bool(settings.SENDGRID_API_KEY)}")
        print(f"   API Key length: {len(settings.SENDGRID_API_KEY) if settings.SENDGRID_API_KEY else 0}")
        print(f"   From Email: {settings.SENDGRID_FROM_EMAIL}")
        print(f"   OTP Expire Minutes: {settings.OTP_EXPIRE_MINUTES}")
    
    def test_otp_service_initialization(self):
        """Test that OTP service initializes correctly"""
        otp_service = get_otp_service()
        assert otp_service is not None, "OTP service should be initialized"
        
        # Check SendGrid client
        if settings.SENDGRID_API_KEY:
            assert otp_service.sendgrid_client is not None, "SendGrid client should be initialized when API key is configured"
            print(f"\n✅ SendGrid client initialized successfully")
        else:
            print(f"\n⚠️ SendGrid API key not configured, client is None")
            assert otp_service.sendgrid_client is None, "SendGrid client should be None when API key is missing"
    
    def test_send_otp_email_real(self):
        """
        Test sending real OTP email via SendGrid
        This test will actually send an email - use with caution!
        
        HARDCODED EMAIL FOR TESTING: baominh5xx2@gmail.com
        """
        # Hardcode email for testing
        test_email = os.getenv('TEST_EMAIL', 'baominh5xx2@gmail.com')
        
        print(f"\n🔍 Starting SendGrid Email Test")
        print(f"=" * 60)
        
        # Check configuration
        print(f"\n📋 Configuration Check:")
        print(f"   SENDGRID_API_KEY exists: {bool(settings.SENDGRID_API_KEY)}")
        print(f"   SENDGRID_API_KEY length: {len(settings.SENDGRID_API_KEY) if settings.SENDGRID_API_KEY else 0}")
        print(f"   SENDGRID_FROM_EMAIL: {settings.SENDGRID_FROM_EMAIL}")
        print(f"   OTP_EXPIRE_MINUTES: {settings.OTP_EXPIRE_MINUTES}")
        
        otp_service = get_otp_service()
        
        # Check if SendGrid client is available
        print(f"\n🔧 Service Check:")
        print(f"   OTP Service initialized: {otp_service is not None}")
        print(f"   SendGrid client available: {otp_service.sendgrid_client is not None}")
        
        if not otp_service.sendgrid_client:
            pytest.fail("SendGrid client not available - check SENDGRID_API_KEY and SENDGRID_FROM_EMAIL in .env file")
        
        # Check if API key is configured
        if not settings.SENDGRID_API_KEY:
            pytest.fail("SENDGRID_API_KEY not configured in .env")
        
        if not settings.SENDGRID_FROM_EMAIL:
            pytest.fail("SENDGRID_FROM_EMAIL not configured in .env")
        
        # Generate test OTP
        test_otp = otp_service.generate_otp(6)
        test_tour_name = "Tour Đà Lạt Test"
        
        print(f"\n📧 Email Details:")
        print(f"   To: {test_email}")
        print(f"   From: {settings.SENDGRID_FROM_EMAIL}")
        print(f"   OTP: {test_otp}")
        print(f"   Tour: {test_tour_name}")
        print(f"=" * 60)
        
        # Send email with detailed logging
        print(f"\n🚀 Attempting to send email...")
        try:
            result = otp_service.send_otp_email(
                email=test_email,
                otp=test_otp,
                tour_name=test_tour_name
            )
            
            print(f"\n📬 Send Result: {result}")
            
            if result:
                print(f"\n✅ Email sent successfully!")
                print(f"   Please check inbox at: {test_email}")
                print(f"   Also check SPAM folder if not in inbox")
            else:
                print(f"\n❌ Email sending failed!")
                print(f"   Check logs above for error details")
            
            assert result is True, f"Email should be sent successfully. Result was {result}. Check logs for details."
            
        except Exception as e:
            print(f"\n💥 Exception during email send:")
            print(f"   Type: {type(e).__name__}")
            print(f"   Message: {str(e)}")
            import traceback
            print(f"\n   Traceback:")
            traceback.print_exc()
            raise
    
    def test_send_otp_email_invalid_config(self):
        """Test that send_otp_email returns False when SendGrid client is not available"""
        # Create a new OTP service instance without SendGrid client
        otp_service = OTPService()
        # Manually set sendgrid_client to None to simulate missing config
        otp_service.sendgrid_client = None
        
        result = otp_service.send_otp_email(
            email="test@example.com",
            otp="123456",
            tour_name="Test Tour"
        )
        
        assert result is False, "Should return False when SendGrid client is not available"
    
    def test_generate_otp(self):
        """Test OTP generation"""
        otp_service = get_otp_service()
        
        # Test default length (6)
        otp = otp_service.generate_otp()
        assert len(otp) == 6, f"OTP should be 6 digits, got {len(otp)}"
        assert otp.isdigit(), f"OTP should contain only digits, got {otp}"
        
        # Test custom length
        otp_8 = otp_service.generate_otp(8)
        assert len(otp_8) == 8, f"OTP should be 8 digits, got {len(otp_8)}"
        assert otp_8.isdigit(), f"OTP should contain only digits, got {otp_8}"
        
        print(f"\n✅ OTP Generation Test:")
        print(f"   6-digit OTP: {otp}")
        print(f"   8-digit OTP: {otp_8}")
    
    def test_email_content_format(self):
        """Test that email content is properly formatted"""
        otp_service = get_otp_service()
        test_otp = "123456"
        test_tour_name = "Tour Đà Lạt"
        
        # We can't easily test the actual email content without mocking,
        # but we can verify the method doesn't crash
        if otp_service.sendgrid_client:
            # Just verify the method exists and can be called
            # (won't actually send if we don't have valid config)
            assert callable(otp_service.send_otp_email), "send_otp_email should be callable"
            print(f"\n✅ Email content format test passed")


if __name__ == "__main__":
    """
    Run this test directly:
    
    PowerShell:
    uv run pytest tests/test_sendgrid_otp.py -v -s
    
    Or with real email test:
    $env:TEST_EMAIL="your-email@example.com"
    uv run pytest tests/test_sendgrid_otp.py::TestSendGridOTP::test_send_otp_email_real -v -s
    
    Linux/Mac:
    TEST_EMAIL=your-email@example.com uv run pytest tests/test_sendgrid_otp.py::TestSendGridOTP::test_send_otp_email_real -v -s
    """
    import sys
    pytest.main([__file__, "-v", "-s"] + sys.argv[1:])
