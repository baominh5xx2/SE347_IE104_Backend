"""
VNPay Service
Service xử lý tích hợp VNPay payment gateway
"""
import logging
import hashlib
import hmac
import urllib.parse
import unicodedata
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional

from ..core.config import settings

logger = logging.getLogger(__name__)


class VNPayService:
    """Service for VNPay payment gateway integration"""
    
    def __init__(self):
        """Initialize VNPayService"""
        # Strip whitespace to avoid issues
        self.tmn_code = settings.VNPAY_TMN_CODE.strip() if settings.VNPAY_TMN_CODE else ""
        self.hash_secret = settings.VNPAY_HASH_SECRET.strip() if settings.VNPAY_HASH_SECRET else ""
        self.vnpay_url = settings.VNPAY_URL
        self.return_url = settings.VNPAY_RETURN_URL
    
    def create_payment_url(
        self,
        payment_id: str,
        amount: float,
        order_info: str,
        ip_addr: str = "127.0.0.1",
        locale: str = "vn",
        bank_code: Optional[str] = None,
        client_return_url: Optional[str] = None
    ) -> str:
        """Tạo URL thanh toán VNPay"""
        
        # FIX: Dùng str(int()) thay vì f-string
        vnp_amount = int(amount * 100)
        vnp_amount_str = str(vnp_amount)  # ✅ ĐÚNG - str(int) không bao giờ tạo scientific notation
        
        # Datetime - GMT+7 như Python demo
        vietnam_tz = timezone(timedelta(hours=7))
        now = datetime.now(vietnam_tz)
        create_date = now.strftime('%Y%m%d%H%M%S')
        
        # vnp_OrderInfo: Remove diacritics theo tài liệu
        clean_order_info = self._remove_diacritics(order_info)
        
        # Build requestData - KHỚP VỚI URL MẪU VNPAY (KHÔNG CÓ vnp_ExpireDate)
        requestData = {}
        requestData['vnp_Version'] = '2.1.0'
        requestData['vnp_Command'] = 'pay'
        requestData['vnp_TmnCode'] = self.tmn_code
        requestData['vnp_Amount'] = vnp_amount_str  # String từ str(int)
        requestData['vnp_CurrCode'] = 'VND'
        requestData['vnp_TxnRef'] = payment_id
        requestData['vnp_OrderInfo'] = clean_order_info
        requestData['vnp_OrderType'] = 'other'
        requestData['vnp_Locale'] = locale
        
        # Cho phép FE truyền return_url để quay lại trang trước khi thanh toán
        final_return_url = self.return_url
        if client_return_url:
            # append redirect param
            connector = "&" if "?" in final_return_url else "?"
            final_return_url = f"{final_return_url}{connector}redirect={urllib.parse.quote_plus(client_return_url)}"
        requestData['vnp_ReturnUrl'] = final_return_url
        requestData['vnp_IpAddr'] = ip_addr
        requestData['vnp_CreateDate'] = create_date
        # KHÔNG CÓ vnp_ExpireDate - khớp với URL mẫu và Python demo
        
        if bank_code:
            requestData['vnp_BankCode'] = bank_code
        
        # Sort và build query string
        inputData = sorted(requestData.items())
        queryString = ''
        seq = 0
        for key, val in inputData:
            if seq == 1:
                queryString = queryString + "&" + key + '=' + urllib.parse.quote_plus(str(val))
            else:
                seq = 1
                queryString = key + '=' + urllib.parse.quote_plus(str(val))
        
        # Generate hash
        hashValue = self._generate_hash(queryString)
        payment_url = f"{self.vnpay_url}?{queryString}&vnp_SecureHash={hashValue}"
        
        logger.info(f"Query String: {queryString}")
        logger.info(f"Secure Hash: {hashValue}")
        
        return payment_url


    def verify_payment_response(self, callback_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify VNPay callback response - COPY Y CHANG TỪ PYTHON DEMO
        """
        # Y CHANG như Python demo - validate_response method
        responseData = dict(callback_data)
        vnp_SecureHash = responseData.get('vnp_SecureHash', '')
        
        # Remove hash params
        if 'vnp_SecureHash' in responseData.keys():
            responseData.pop('vnp_SecureHash')
        if 'vnp_SecureHashType' in responseData.keys():
            responseData.pop('vnp_SecureHashType')
        
        # Y CHANG như Python demo
        inputData = sorted(responseData.items())
        hasData = ''
        seq = 0
        for key, val in inputData:
            if str(key).startswith('vnp_'):
                if seq == 1:
                    hasData = hasData + "&" + str(key) + '=' + urllib.parse.quote_plus(str(val))
                else:
                    seq = 1
                    hasData = str(key) + '=' + urllib.parse.quote_plus(str(val))
        
        # Generate hash
        hashValue = self._generate_hash(hasData)
        
        # Verify - Y CHANG như Python demo
        is_valid = (hashValue == vnp_SecureHash)
        
        logger.info(f"VNPay Verify HashData: {hasData}")
        logger.info(f"VNPay HashValue: {hashValue}")
        logger.info(f"VNPay InputHash: {vnp_SecureHash}")
        
        result = {
            "is_valid": is_valid,
            "payment_id": callback_data.get("vnp_TxnRef"),
            "response_code": callback_data.get("vnp_ResponseCode"),
            "transaction_status": callback_data.get("vnp_TransactionStatus"),
            "transaction_id": callback_data.get("vnp_TransactionNo"),
            "bank_code": callback_data.get("vnp_BankCode"),
            "amount": int(callback_data.get("vnp_Amount", 0)) / 100,
            "pay_date": callback_data.get("vnp_PayDate"),
            "order_info": callback_data.get("vnp_OrderInfo")
        }
        
        if not is_valid:
            logger.warning(f"Invalid VNPay signature for payment_id: {result['payment_id']}")
        else:
            logger.info(f"Valid VNPay response for payment_id: {result['payment_id']}, code: {result['response_code']}")
        
        return result

    def _generate_hash(self, data: str) -> str:
        """Generate HMAC SHA512 hash"""
        return hmac.new(
            self.hash_secret.encode('utf-8'),
            data.encode('utf-8'),
            hashlib.sha512
        ).hexdigest()
    
    def is_payment_success(self, response_code: str, transaction_status: str) -> bool:
        """Check if payment is successful"""
        return response_code == "00" and transaction_status == "00"
    
    def get_response_message(self, response_code: str) -> str:
        """Get human-readable message from VNPay response code"""
        messages = {
            "00": "Giao dịch thành công",
            "07": "Trừ tiền thành công. Giao dịch bị nghi ngờ (liên quan tới lừa đảo, giao dịch bất thường)",
            "09": "Giao dịch không thành công do: Thẻ/Tài khoản của khách hàng chưa đăng ký dịch vụ InternetBanking tại ngân hàng",
            "10": "Giao dịch không thành công do: Khách hàng xác thực thông tin thẻ/tài khoản không đúng quá 3 lần",
            "11": "Giao dịch không thành công do: Đã hết hạn chờ thanh toán. Xin quý khách vui lòng thực hiện lại giao dịch",
            "12": "Giao dịch không thành công do: Thẻ/Tài khoản của khách hàng bị khóa",
            "13": "Giao dịch không thành công do Quý khách nhập sai mật khẩu xác thực giao dịch (OTP)",
            "24": "Giao dịch không thành công do: Khách hàng hủy giao dịch",
            "51": "Giao dịch không thành công do: Tài khoản của quý khách không đủ số dư để thực hiện giao dịch",
            "65": "Giao dịch không thành công do: Tài khoản của Quý khách đã vượt quá hạn mức giao dịch trong ngày",
            "75": "Ngân hàng thanh toán đang bảo trì",
            "79": "Giao dịch không thành công do: KH nhập sai mật khẩu thanh toán quá số lần quy định",
            "99": "Lỗi không xác định"
        }
        return messages.get(response_code, f"Mã lỗi: {response_code}")

    def _remove_diacritics(self, text: str) -> str:
        """Remove Vietnamese diacritics"""
        if not text:
            return ""
        
        text = unicodedata.normalize("NFD", text)
        text = re.sub(r"[\u0300-\u036f]", "", text)
        text = text.replace("Đ", "D").replace("đ", "d")
        text = re.sub(r"[^a-zA-Z0-9\s]", "", text)
        text = ' '.join(text.split())
        
        return text
