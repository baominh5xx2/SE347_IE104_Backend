"""
OTP Service
Handles OTP generation, storage, email sending, and verification
"""
import logging
import random
import json
from typing import Optional, Dict, Any
import redis
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
from app.v1.core.config import settings

logger = logging.getLogger(__name__)


class OTPService:
    """Service for managing OTP operations"""
    
    def __init__(self):
        """Initialize OTP Service with Redis and SendGrid clients"""
        try:
            self.redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                decode_responses=True
            )
            # Test connection
            self.redis_client.ping()
            logger.info("Redis connection established for OTP service")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            self.redis_client = None
        
        try:
            if settings.SENDGRID_API_KEY:
                self.sendgrid_client = SendGridAPIClient(api_key=settings.SENDGRID_API_KEY)
                logger.info("SendGrid client initialized")
            else:
                logger.warning("SENDGRID_API_KEY not configured")
                self.sendgrid_client = None
        except Exception as e:
            logger.error(f"Failed to initialize SendGrid client: {str(e)}")
            self.sendgrid_client = None
    
    def generate_otp(self, length: int = 6) -> str:
        """
        Generate a random OTP code
        
        Args:
            length: Length of OTP (default: 6)
            
        Returns:
            OTP code as string
        """
        return ''.join([str(random.randint(0, 9)) for _ in range(length)])
    
    def store_otp(self, email: str, otp: str) -> bool:
        """
        Store OTP in Redis with expiration
        
        Args:
            email: User email address
            otp: OTP code to store
            
        Returns:
            True if successful, False otherwise
        """
        if not self.redis_client:
            logger.error("Redis client not available")
            return False
        
        try:
            key = f"otp:{email.lower().strip()}"
            expire_seconds = settings.OTP_EXPIRE_MINUTES * 60
            self.redis_client.setex(key, expire_seconds, otp)
            logger.info(f"OTP stored for {email} (expires in {expire_seconds}s)")
            return True
        except Exception as e:
            logger.error(f"Failed to store OTP: {str(e)}")
            return False
    
    def verify_otp(self, email: str, otp: str) -> bool:
        """
        Verify OTP code
        
        Args:
            email: User email address
            otp: OTP code to verify
            
        Returns:
            True if OTP is valid, False otherwise
        """
        if not self.redis_client:
            logger.error("Redis client not available")
            return False
        
        try:
            key = f"otp:{email.lower().strip()}"
            stored_otp = self.redis_client.get(key)
            
            if stored_otp is None:
                logger.warning(f"No OTP found for {email}")
                return False
            
            if stored_otp != otp:
                logger.warning(f"OTP mismatch for {email}")
                return False
            
            # Delete OTP after successful verification
            self.redis_client.delete(key)
            logger.info(f"OTP verified and deleted for {email}")
            return True
        except Exception as e:
            logger.error(f"Failed to verify OTP: {str(e)}")
            return False
    
    def send_otp_email(self, email: str, otp: str, tour_name: str) -> bool:
        """
        Send OTP via SendGrid email
        
        Args:
            email: Recipient email address
            otp: OTP code to send
            tour_name: Name of the tour for context
            
        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.sendgrid_client:
            logger.error("SendGrid client not available")
            return False
        
        try:
            from_email = Email(settings.SENDGRID_FROM_EMAIL)
            to_email = To(email)
            subject = "Mã xác thực đặt tour"
            
            # Email content in Vietnamese
            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #2c3e50;">Mã xác thực đặt tour</h2>
                    <p>Xin chào,</p>
                    <p>Bạn đang thực hiện đặt tour: <strong>{tour_name}</strong></p>
                    <p>Mã xác thực của bạn là:</p>
                    <div style="background-color: #f4f4f4; padding: 20px; text-align: center; margin: 20px 0; border-radius: 5px;">
                        <h1 style="color: #27ae60; font-size: 32px; margin: 0; letter-spacing: 5px;">{otp}</h1>
                    </div>
                    <p>Mã này có hiệu lực trong <strong>{settings.OTP_EXPIRE_MINUTES} phút</strong>.</p>
                    <p>Nếu bạn không yêu cầu mã này, vui lòng bỏ qua email này.</p>
                    <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                    <p style="color: #7f8c8d; font-size: 12px;">Đây là email tự động, vui lòng không trả lời.</p>
                </div>
            </body>
            </html>
            """
            
            plain_content = f"""
Mã xác thực đặt tour

Xin chào,
Bạn đang thực hiện đặt tour: {tour_name}

Mã xác thực của bạn là: {otp}

Mã này có hiệu lực trong {settings.OTP_EXPIRE_MINUTES} phút.

Nếu bạn không yêu cầu mã này, vui lòng bỏ qua email này.
            """
            
            content = Content("text/html", html_content)
            mail = Mail(from_email, to_email, subject, content)
            
            response = self.sendgrid_client.send(mail)
            
            if response.status_code in [200, 202]:
                logger.info(f"OTP email sent successfully to {email}")
                return True
            else:
                logger.error(f"Failed to send OTP email. Status: {response.status_code}, Body: {response.body}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending OTP email: {str(e)}")
            return False
    
    def store_pending_booking(self, email: str, booking_data: Dict[str, Any]) -> bool:
        """
        Store pending booking data in Redis
        
        Args:
            email: User email address
            booking_data: Dictionary containing booking information
            
        Returns:
            True if successful, False otherwise
        """
        if not self.redis_client:
            logger.error("Redis client not available")
            return False
        
        try:
            key = f"pending_booking:{email.lower().strip()}"
            expire_seconds = settings.OTP_EXPIRE_MINUTES * 60
            booking_json = json.dumps(booking_data)
            self.redis_client.setex(key, expire_seconds, booking_json)
            logger.info(f"Pending booking stored for {email}")
            return True
        except Exception as e:
            logger.error(f"Failed to store pending booking: {str(e)}")
            return False
    
    def get_pending_booking(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Get pending booking data from Redis
        
        Args:
            email: User email address
            
        Returns:
            Booking data dictionary or None if not found
        """
        if not self.redis_client:
            logger.error("Redis client not available")
            return None
        
        try:
            key = f"pending_booking:{email.lower().strip()}"
            booking_json = self.redis_client.get(key)
            
            if booking_json is None:
                return None
            
            booking_data = json.loads(booking_json)
            return booking_data
        except Exception as e:
            logger.error(f"Failed to get pending booking: {str(e)}")
            return None
    
    def delete_pending_booking(self, email: str) -> bool:
        """
        Delete pending booking data from Redis
        
        Args:
            email: User email address
            
        Returns:
            True if successful, False otherwise
        """
        if not self.redis_client:
            return False
        
        try:
            key = f"pending_booking:{email.lower().strip()}"
            self.redis_client.delete(key)
            logger.info(f"Pending booking deleted for {email}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete pending booking: {str(e)}")
            return False


# Singleton instance
_otp_service = None

def get_otp_service() -> OTPService:
    """Get singleton OTP service instance"""
    global _otp_service
    if _otp_service is None:
        _otp_service = OTPService()
    return _otp_service
