"""
Test cases for Payment Service and VNPay Integration
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from uuid import uuid4
from datetime import datetime, timezone
import hmac
import hashlib
import urllib.parse

from app.v1.services.payment_service import PaymentService
from app.v1.services.vnpay_service import VNPayService


# ==================== FIXTURES ====================

@pytest.fixture
def mock_supabase():
    """Mock Supabase client"""
    return MagicMock()


@pytest.fixture
def payment_service(mock_supabase):
    """Create PaymentService instance with mock client"""
    return PaymentService(mock_supabase)


@pytest.fixture
def vnpay_service():
    """Create VNPayService instance"""
    with patch('app.v1.services.vnpay_service.settings') as mock_settings:
        mock_settings.VNPAY_TMN_CODE = "TEST_TMN_CODE"
        mock_settings.VNPAY_HASH_SECRET = "TEST_HASH_SECRET"
        mock_settings.VNPAY_URL = "https://sandbox.vnpayment.vn/paymentv2/vpcpay.html"
        mock_settings.VNPAY_RETURN_URL = "http://localhost:8000/api/v1/payments/vnpay/return"
        service = VNPayService()
        return service


@pytest.fixture
def sample_booking_data():
    """Sample booking data for testing"""
    return {
        "booking_id": str(uuid4()),
        "total_amount": 7680000.0,
        "status": "pending",
        "user_id": str(uuid4()),
        "tour_packages": {
            "package_name": "Tour Đà Lạt 3N2Đ"
        }
    }


@pytest.fixture
def sample_payment_data():
    """Sample payment data"""
    payment_id = str(uuid4())
    booking_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    return {
        "payment_id": payment_id,
        "booking_id": booking_id,
        "amount": 7680000.0,
        "payment_method": "vnpay",
        "payment_status": "pending",
        "transaction_id": None,
        "paid_at": None,
        "created_at": now,
        "updated_at": now
    }


@pytest.fixture
def sample_vnpay_callback_success():
    """Sample VNPay callback data for successful payment"""
    payment_id = str(uuid4())
    # Generate valid hash for testing
    callback_data = {
        "vnp_Amount": "768000000",
        "vnp_BankCode": "NCB",
        "vnp_BankTranNo": "VNP12345678",
        "vnp_CardType": "ATM",
        "vnp_OrderInfo": "Thanh toan tour",
        "vnp_PayDate": "20231207170112",
        "vnp_ResponseCode": "00",
        "vnp_TmnCode": "TEST_TMN_CODE",
        "vnp_TransactionNo": "12345678",
        "vnp_TransactionStatus": "00",
        "vnp_TxnRef": payment_id
    }
    
    # Generate hash
    sorted_data = sorted(callback_data.items())
    hash_data = ''
    seq = 0
    for key, val in sorted_data:
        if str(key).startswith('vnp_'):
            if seq == 1:
                hash_data = hash_data + "&" + str(key) + '=' + urllib.parse.quote_plus(str(val))
            else:
                seq = 1
                hash_data = str(key) + '=' + urllib.parse.quote_plus(str(val))
    
    hash_secret = "TEST_HASH_SECRET"
    secure_hash = hmac.new(
        hash_secret.encode('utf-8'),
        hash_data.encode('utf-8'),
        hashlib.sha512
    ).hexdigest()
    
    callback_data['vnp_SecureHash'] = secure_hash
    
    return callback_data, payment_id


# ==================== VNPAY SERVICE TESTS ====================

class TestVNPayService:
    """Test cases for VNPayService"""
    
    def test_create_payment_url_success(self, vnpay_service):
        """Test creating payment URL successfully"""
        payment_id = str(uuid4())
        amount = 7680000.0
        order_info = "Thanh toan tour"
        ip_addr = "127.0.0.1"
        
        url = vnpay_service.create_payment_url(
            payment_id=payment_id,
            amount=amount,
            order_info=order_info,
            ip_addr=ip_addr
        )
        
        assert url.startswith("https://sandbox.vnpayment.vn/paymentv2/vpcpay.html")
        assert "vnp_Version=2.1.0" in url
        assert "vnp_Command=pay" in url
        assert "vnp_TmnCode=TEST_TMN_CODE" in url
        assert "vnp_Amount=768000000" in url  # amount * 100
        assert f"vnp_TxnRef={payment_id}" in url
        assert "vnp_SecureHash=" in url
    
    def test_create_payment_url_with_bank_code(self, vnpay_service):
        """Test creating payment URL with bank code"""
        payment_id = str(uuid4())
        url = vnpay_service.create_payment_url(
            payment_id=payment_id,
            amount=1000000.0,
            order_info="Test",
            bank_code="NCB"
        )
        
        assert "vnp_BankCode=NCB" in url
    
    def test_remove_diacritics(self, vnpay_service):
        """Test removing Vietnamese diacritics"""
        text = "Thanh toán tour Đà Lạt"
        result = vnpay_service._remove_diacritics(text)
        
        assert "á" not in result
        assert "à" not in result
        assert "Đ" not in result
        assert "Thanh toan tour Da Lat" in result
    
    def test_verify_payment_response_success(self, vnpay_service, sample_vnpay_callback_success):
        """Test verifying payment response with valid signature"""
        callback_data, payment_id = sample_vnpay_callback_success
        
        result = vnpay_service.verify_payment_response(callback_data)
        
        assert result['is_valid'] is True
        assert result['payment_id'] == payment_id
        assert result['response_code'] == "00"
        assert result['transaction_status'] == "00"
        assert result['amount'] == 7680000.0
    
    def test_verify_payment_response_invalid_signature(self, vnpay_service):
        """Test verifying payment response with invalid signature"""
        callback_data = {
            "vnp_Amount": "768000000",
            "vnp_ResponseCode": "00",
            "vnp_TransactionStatus": "00",
            "vnp_TxnRef": str(uuid4()),
            "vnp_SecureHash": "invalid_hash"
        }
        
        result = vnpay_service.verify_payment_response(callback_data)
        
        assert result['is_valid'] is False
    
    def test_is_payment_success(self, vnpay_service):
        """Test checking payment success status"""
        assert vnpay_service.is_payment_success("00", "00") is True
        assert vnpay_service.is_payment_success("00", "01") is False
        assert vnpay_service.is_payment_success("01", "00") is False
        assert vnpay_service.is_payment_success("24", "00") is False
    
    def test_get_response_message(self, vnpay_service):
        """Test getting response messages"""
        assert "thành công" in vnpay_service.get_response_message("00").lower()
        assert "không đủ số dư" in vnpay_service.get_response_message("51").lower()
        assert "hủy giao dịch" in vnpay_service.get_response_message("24").lower()
        assert "Lỗi không xác định" in vnpay_service.get_response_message("99")
        # Test unknown code
        assert "Mã lỗi: 88" in vnpay_service.get_response_message("88")


# ==================== PAYMENT SERVICE TESTS ====================

class TestPaymentService:
    """Test cases for PaymentService"""
    
    @pytest.mark.asyncio
    async def test_create_payment_success(
        self, payment_service, mock_supabase, sample_booking_data, sample_payment_data
    ):
        """Test creating payment successfully"""
        booking_id = sample_booking_data["booking_id"]
        
        # Mock booking query
        mock_booking_result = MagicMock()
        mock_booking_result.data = [sample_booking_data]
        
        # Mock existing payment check (no existing payment)
        mock_existing_result = MagicMock()
        mock_existing_result.data = []
        
        # Mock payment insert
        mock_payment_result = MagicMock()
        mock_payment_result.data = [sample_payment_data]
        
        # Track calls to table('payments')
        payment_table_calls = []
        
        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "bookings":
                mock_query = MagicMock()
                mock_query.select.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_query.execute.return_value = mock_booking_result
                mock_table.select.return_value = mock_query
            elif table_name == "payments":
                payment_table_calls.append(len(payment_table_calls))
                call_idx = len(payment_table_calls) - 1
                
                if call_idx == 0:
                    # First call: check existing payment
                    mock_query = MagicMock()
                    mock_query.select.return_value = mock_query
                    mock_query.eq.return_value = mock_query
                    mock_query.in_.return_value = mock_query
                    mock_query.execute.return_value = mock_existing_result
                    mock_table.select.return_value = mock_query
                else:
                    # Second call: insert payment
                    mock_insert = MagicMock()
                    mock_insert.execute.return_value = mock_payment_result
                    mock_table.insert.return_value = mock_insert
            return mock_table
        
        mock_supabase.table.side_effect = table_side_effect
        
        result = await payment_service.create_payment(
            booking_id=booking_id,
            payment_method="vnpay",
            ip_addr="127.0.0.1"
        )
        
        assert result["EC"] == 0
        assert result["EM"] == "Payment created successfully"
        assert result["data"]["payment_id"] == sample_payment_data["payment_id"]
        assert "payment_url" in result["data"]
    
    @pytest.mark.asyncio
    async def test_create_payment_booking_not_found(
        self, payment_service, mock_supabase
    ):
        """Test creating payment for non-existent booking"""
        mock_result = MagicMock()
        mock_result.data = []
        
        mock_query = MagicMock()
        mock_query.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.execute.return_value = mock_result
        
        mock_supabase.table.return_value = mock_query
        
        result = await payment_service.create_payment(
            booking_id=str(uuid4()),
            payment_method="vnpay"
        )
        
        assert result["EC"] == 1
        assert result["EM"] == "Booking not found"
    
    @pytest.mark.asyncio
    async def test_create_payment_already_paid(
        self, payment_service, mock_supabase, sample_booking_data
    ):
        """Test creating payment for already paid booking"""
        booking_id = sample_booking_data["booking_id"]
        
        # Mock booking query
        mock_booking_result = MagicMock()
        mock_booking_result.data = [sample_booking_data]
        
        # Mock existing completed payment
        mock_existing_result = MagicMock()
        mock_existing_result.data = [{"payment_id": str(uuid4()), "payment_status": "completed"}]
        
        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "bookings":
                mock_query = MagicMock()
                mock_query.select.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_query.execute.return_value = mock_booking_result
                mock_table.select.return_value = mock_query
            elif table_name == "payments":
                mock_query = MagicMock()
                mock_query.select.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_query.in_.return_value = mock_query
                mock_query.execute.return_value = mock_existing_result
                mock_table.select.return_value = mock_query
            return mock_table
        
        mock_supabase.table.side_effect = table_side_effect
        
        result = await payment_service.create_payment(booking_id=booking_id)
        
        assert result["EC"] == 3
        assert result["EM"] == "Booking already paid"
    
    @pytest.mark.asyncio
    async def test_get_payment_by_id_success(
        self, payment_service, mock_supabase, sample_payment_data
    ):
        """Test getting payment by ID successfully"""
        payment_id = sample_payment_data["payment_id"]
        
        mock_result = MagicMock()
        mock_result.data = [sample_payment_data]
        
        mock_query = MagicMock()
        mock_query.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.execute.return_value = mock_result
        
        mock_supabase.table.return_value = mock_query
        
        result = await payment_service.get_payment_by_id(payment_id)
        
        assert result["EC"] == 0
        assert result["EM"] == "Success"
        assert result["data"]["payment_id"] == payment_id
    
    @pytest.mark.asyncio
    async def test_get_payment_by_id_not_found(
        self, payment_service, mock_supabase
    ):
        """Test getting non-existent payment"""
        mock_result = MagicMock()
        mock_result.data = []
        
        mock_query = MagicMock()
        mock_query.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.execute.return_value = mock_result
        
        mock_supabase.table.return_value = mock_query
        
        result = await payment_service.get_payment_by_id(str(uuid4()))
        
        assert result["EC"] == 1
        assert result["EM"] == "Payment not found"
    
    @pytest.mark.asyncio
    async def test_update_payment_status_success(
        self, payment_service, mock_supabase, sample_payment_data
    ):
        """Test updating payment status successfully"""
        payment_id = sample_payment_data["payment_id"]
        
        updated_payment = sample_payment_data.copy()
        updated_payment["payment_status"] = "completed"
        updated_payment["transaction_id"] = "12345678"
        updated_payment["paid_at"] = datetime.now(timezone.utc).isoformat()
        
        mock_result = MagicMock()
        mock_result.data = [updated_payment]
        
        mock_query = MagicMock()
        mock_query.update.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.execute.return_value = mock_result
        
        mock_supabase.table.return_value = mock_query
        
        result = await payment_service.update_payment_status(
            payment_id=payment_id,
            status="completed",
            transaction_id="12345678"
        )
        
        assert result["EC"] == 0
        assert result["EM"] == "Payment status updated"
        assert result["data"]["payment_status"] == "completed"
    
    @pytest.mark.asyncio
    async def test_verify_and_complete_payment_success(
        self, payment_service, mock_supabase, sample_vnpay_callback_success, sample_payment_data, vnpay_service
    ):
        """Test verifying and completing payment successfully"""
        callback_data, payment_id = sample_vnpay_callback_success
        sample_payment_data["payment_id"] = payment_id
        sample_payment_data["amount"] = 7680000.0
        
        # Override vnpay_service to use test fixture with matching hash secret
        payment_service.vnpay_service = vnpay_service
        
        # Mock get_payment_by_id
        mock_payment_result = MagicMock()
        mock_payment_result.data = [sample_payment_data]
        
        # Mock update payment
        updated_payment = sample_payment_data.copy()
        updated_payment["payment_status"] = "completed"
        updated_payment["transaction_id"] = "12345678"
        mock_update_result = MagicMock()
        mock_update_result.data = [updated_payment]
        
        # Track calls
        payment_table_calls = []
        
        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "payments":
                payment_table_calls.append(len(payment_table_calls))
                call_idx = len(payment_table_calls) - 1
                
                if call_idx == 0:
                    # First call: get payment
                    mock_query = MagicMock()
                    mock_query.select.return_value = mock_query
                    mock_query.eq.return_value = mock_query
                    mock_query.execute.return_value = mock_payment_result
                    mock_table.select.return_value = mock_query
                else:
                    # Second call: update payment
                    mock_query = MagicMock()
                    mock_query.update.return_value = mock_query
                    mock_query.eq.return_value = mock_query
                    mock_query.execute.return_value = mock_update_result
                    mock_table.update.return_value = mock_query
            elif table_name == "bookings":
                mock_query = MagicMock()
                mock_query.update.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_table.update.return_value = mock_query
            return mock_table
        
        mock_supabase.table.side_effect = table_side_effect
        
        result = await payment_service.verify_and_complete_payment(callback_data)
        
        assert result["EC"] == 0
        assert result["is_success"] is True
        assert "thành công" in result["EM"].lower()
    
    @pytest.mark.asyncio
    async def test_verify_and_complete_payment_invalid_signature(
        self, payment_service, mock_supabase
    ):
        """Test verifying payment with invalid signature"""
        callback_data = {
            "vnp_TxnRef": str(uuid4()),
            "vnp_SecureHash": "invalid_hash"
        }
        
        result = await payment_service.verify_and_complete_payment(callback_data)
        
        assert result["EC"] == 97
        assert result["is_success"] is False
        assert "Invalid signature" in result["EM"]
    
    @pytest.mark.asyncio
    async def test_get_user_payments_success(
        self, payment_service, mock_supabase
    ):
        """Test getting user payments successfully"""
        user_id = str(uuid4())
        booking_id = str(uuid4())
        
        # Mock bookings query
        mock_bookings_result = MagicMock()
        mock_bookings_result.data = [{"booking_id": booking_id}]
        
        # Mock payments query
        payment_data = {
            "payment_id": str(uuid4()),
            "booking_id": booking_id,
            "amount": 7680000.0,
            "payment_method": "vnpay",
            "payment_status": "completed",
            "transaction_id": "12345678",
            "paid_at": datetime.now(timezone.utc).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "bookings": {
                "tour_packages": {
                    "package_name": "Tour Đà Lạt",
                    "destination": "Đà Lạt"
                }
            }
        }
        
        mock_payments_result = MagicMock()
        mock_payments_result.data = [payment_data]
        mock_payments_result.count = 1
        
        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "bookings":
                mock_query = MagicMock()
                mock_query.select.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_query.execute.return_value = mock_bookings_result
                mock_table.select.return_value = mock_query
            elif table_name == "payments":
                mock_query = MagicMock()
                mock_query.select.return_value = mock_query
                mock_query.in_.return_value = mock_query
                mock_query.order.return_value = mock_query
                mock_query.execute.return_value = mock_payments_result
                mock_table.select.return_value = mock_query
            return mock_table
        
        mock_supabase.table.side_effect = table_side_effect
        
        result = await payment_service.get_user_payments(user_id=user_id)
        
        assert result["EC"] == 0
        assert result["EM"] == "Success"
        assert len(result["data"]) == 1
        assert result["total"] == 1


# ==================== INTEGRATION TESTS ====================

class TestPaymentIntegration:
    """Integration tests for payment flow"""
    
    @pytest.mark.asyncio
    async def test_full_payment_flow(
        self, payment_service, mock_supabase, sample_booking_data, sample_payment_data,
        sample_vnpay_callback_success, vnpay_service
    ):
        """Test complete payment flow: create -> verify -> complete"""
        booking_id = sample_booking_data["booking_id"]
        callback_data, payment_id = sample_vnpay_callback_success
        sample_payment_data["payment_id"] = payment_id
        sample_payment_data["amount"] = 7680000.0
        
        # Override vnpay_service to use test fixture
        payment_service.vnpay_service = vnpay_service
        
        # This is a simplified integration test
        # In real scenario, you'd test the full flow with proper mocks
        
        # Step 1: Create payment
        mock_booking_result = MagicMock()
        mock_booking_result.data = [sample_booking_data]
        
        mock_existing_result = MagicMock()
        mock_existing_result.data = []
        
        mock_payment_result = MagicMock()
        mock_payment_result.data = [sample_payment_data]
        
        payment_table_calls = []
        
        def table_side_effect_create(table_name):
            mock_table = MagicMock()
            if table_name == "bookings":
                mock_query = MagicMock()
                mock_query.select.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_query.execute.return_value = mock_booking_result
                mock_table.select.return_value = mock_query
            elif table_name == "payments":
                payment_table_calls.append(len(payment_table_calls))
                call_idx = len(payment_table_calls) - 1
                
                if call_idx == 0:
                    mock_query = MagicMock()
                    mock_query.select.return_value = mock_query
                    mock_query.eq.return_value = mock_query
                    mock_query.in_.return_value = mock_query
                    mock_query.execute.return_value = mock_existing_result
                    mock_table.select.return_value = mock_query
                else:
                    mock_insert = MagicMock()
                    mock_insert.execute.return_value = mock_payment_result
                    mock_table.insert.return_value = mock_insert
            return mock_table
        
        mock_supabase.table.side_effect = table_side_effect_create
        
        create_result = await payment_service.create_payment(booking_id=booking_id)
        assert create_result["EC"] == 0
        
        # Step 2: Verify and complete payment
        updated_payment = sample_payment_data.copy()
        updated_payment["payment_status"] = "completed"
        updated_payment["transaction_id"] = "12345678"
        mock_update_result = MagicMock()
        mock_update_result.data = [updated_payment]
        
        mock_payment_get = MagicMock()
        mock_payment_get.data = [sample_payment_data]
        
        payment_table_calls_verify = []
        
        def table_side_effect_verify(table_name):
            mock_table = MagicMock()
            if table_name == "payments":
                payment_table_calls_verify.append(len(payment_table_calls_verify))
                call_idx = len(payment_table_calls_verify) - 1
                
                if call_idx == 0:
                    mock_query = MagicMock()
                    mock_query.select.return_value = mock_query
                    mock_query.eq.return_value = mock_query
                    mock_query.execute.return_value = mock_payment_get
                    mock_table.select.return_value = mock_query
                else:
                    mock_query = MagicMock()
                    mock_query.update.return_value = mock_query
                    mock_query.eq.return_value = mock_query
                    mock_query.execute.return_value = mock_update_result
                    mock_table.update.return_value = mock_query
            elif table_name == "bookings":
                mock_query = MagicMock()
                mock_query.update.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_table.update.return_value = mock_query
            return mock_table
        
        mock_supabase.table.side_effect = table_side_effect_verify
        
        verify_result = await payment_service.verify_and_complete_payment(callback_data)
        assert verify_result["EC"] == 0
        assert verify_result["is_success"] is True


# ==================== API ENDPOINT TESTS ====================

class TestPaymentEndpoints:
    """Test cases for Payment API endpoints"""
    
    @pytest.fixture
    def mock_current_user(self):
        """Mock current authenticated user"""
        return {
            "user_id": str(uuid4()),
            "email": "test@example.com",
            "full_name": "Test User"
        }
    
    @pytest.fixture
    def mock_request(self):
        """Mock FastAPI Request"""
        mock = MagicMock()
        mock.query_params = MagicMock()
        mock.query_params.__iter__ = lambda x: iter([])
        mock.query_params.get = lambda x, y=None: y
        mock.client.host = "127.0.0.1"
        return mock
    
    @pytest.mark.asyncio
    async def test_create_payment_endpoint_success(
        self, mock_supabase, sample_booking_data, sample_payment_data, mock_current_user, mock_request
    ):
        """Test POST /create endpoint successfully"""
        from app.v1.api.endpoints.payments import create_payment
        from app.v1.schema.payment_schema import PaymentCreate
        
        booking_id = sample_booking_data["booking_id"]
        sample_booking_data["user_id"] = mock_current_user["user_id"]
        
        # Mock booking query
        mock_booking_result = MagicMock()
        mock_booking_result.data = [sample_booking_data]
        
        # Mock existing payment check
        mock_existing_result = MagicMock()
        mock_existing_result.data = []
        
        # Mock payment insert
        mock_payment_result = MagicMock()
        mock_payment_result.data = [sample_payment_data]
        
        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "bookings":
                mock_query = MagicMock()
                mock_query.select.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_query.execute.return_value = mock_booking_result
                mock_table.select.return_value = mock_query
            elif table_name == "payments":
                # Track calls to payments table
                if not hasattr(table_side_effect, '_payment_calls'):
                    table_side_effect._payment_calls = 0
                
                table_side_effect._payment_calls += 1
                call_idx = table_side_effect._payment_calls
                
                if call_idx == 1:
                    # First call: check existing payment
                    mock_query = MagicMock()
                    mock_query.select.return_value = mock_query
                    mock_query.eq.return_value = mock_query
                    mock_query.in_.return_value = mock_query
                    mock_query.execute.return_value = mock_existing_result
                    mock_table.select.return_value = mock_query
                else:
                    # Second call: insert payment
                    mock_insert = MagicMock()
                    mock_insert.execute.return_value = mock_payment_result
                    mock_table.insert.return_value = mock_insert
            return mock_table
        
        mock_supabase.table.side_effect = table_side_effect
        
        # Fix sample_payment_data to match what Supabase returns
        # Supabase returns: UUIDs as strings, datetimes as ISO strings
        # PaymentResponse expects: UUID objects, datetime objects (Pydantic auto-converts)
        sample_payment_data_with_url = sample_payment_data.copy()
        sample_payment_data_with_url["payment_url"] = "https://sandbox.vnpayment.vn/paymentv2/vpcpay.html?test=url"
        # Remove updated_at as it's not in PaymentResponse schema
        if "updated_at" in sample_payment_data_with_url:
            del sample_payment_data_with_url["updated_at"]
        
        # Ensure created_at is proper ISO format string (Pydantic will convert to datetime)
        from datetime import datetime, timezone
        if isinstance(sample_payment_data_with_url.get("created_at"), str):
            # Validate it's a valid ISO format
            try:
                datetime.fromisoformat(sample_payment_data_with_url["created_at"].replace('Z', '+00:00'))
            except:
                sample_payment_data_with_url["created_at"] = datetime.now(timezone.utc).isoformat()
        
        mock_payment_result.data = [sample_payment_data_with_url]
        
        with patch('app.v1.api.endpoints.payments.get_supabase_client', return_value=mock_supabase):
            payment_service = PaymentService(mock_supabase)
            
            from uuid import UUID
            payment_create = PaymentCreate(booking_id=UUID(booking_id), payment_method="vnpay")
            
            try:
                response = await create_payment(
                    payment=payment_create,
                    request=mock_request,
                    current_user=mock_current_user,
                    service=payment_service
                )
                
                assert response.EC == 0
                assert response.EM == "Payment created successfully"
                assert response.data is not None
                assert str(response.data.payment_id) == str(sample_payment_data["payment_id"])
                assert response.data.payment_url is not None
            except Exception as e:
                # Print error details for debugging
                import traceback
                print(f"Error: {e}")
                print(traceback.format_exc())
                raise
    
    @pytest.mark.asyncio
    async def test_create_payment_endpoint_booking_not_found(
        self, mock_supabase, mock_current_user, mock_request
    ):
        """Test POST /create endpoint with non-existent booking"""
        from app.v1.api.endpoints.payments import create_payment
        from app.v1.schema.payment_schema import PaymentCreate
        
        mock_result = MagicMock()
        mock_result.data = []
        
        mock_query = MagicMock()
        mock_query.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.execute.return_value = mock_result
        
        mock_supabase.table.return_value = mock_query
        
        with patch('app.v1.api.endpoints.payments.get_supabase_client', return_value=mock_supabase):
            with patch('app.v1.api.endpoints.payments.get_payment_service') as mock_get_service:
                payment_service = PaymentService(mock_supabase)
                mock_get_service.return_value = payment_service
                
                payment_create = PaymentCreate(booking_id=str(uuid4()), payment_method="vnpay")
                
                with pytest.raises(Exception):  # Should raise HTTPException
                    await create_payment(
                        payment=payment_create,
                        request=mock_request,
                        current_user=mock_current_user
                    )
    
    @pytest.mark.asyncio
    async def test_vnpay_ipn_endpoint_success(
        self, mock_supabase, sample_vnpay_callback_success, sample_payment_data
    ):
        """Test GET/POST /vnpay/ipn endpoint successfully"""
        from app.v1.api.endpoints.payments import vnpay_ipn
        
        callback_data, payment_id = sample_vnpay_callback_success
        sample_payment_data["payment_id"] = payment_id
        sample_payment_data["amount"] = 7680000.0
        
        # Mock get payment
        mock_payment_result = MagicMock()
        mock_payment_result.data = [sample_payment_data]
        
        # Mock update payment
        updated_payment = sample_payment_data.copy()
        updated_payment["payment_status"] = "completed"
        updated_payment["transaction_id"] = "12345678"
        mock_update_result = MagicMock()
        mock_update_result.data = [updated_payment]
        
        # Mock update booking
        mock_booking_update = MagicMock()
        mock_booking_update.execute.return_value = MagicMock()
        
        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "payments":
                if not hasattr(mock_table, '_call_count'):
                    mock_table._call_count = 0
                if mock_table._call_count == 0:
                    mock_query = MagicMock()
                    mock_query.select.return_value = mock_query
                    mock_query.eq.return_value = mock_query
                    mock_query.execute.return_value = mock_payment_result
                    mock_table.select.return_value = mock_query
                    mock_table._call_count += 1
                else:
                    mock_query = MagicMock()
                    mock_query.update.return_value = mock_query
                    mock_query.eq.return_value = mock_query
                    mock_query.execute.return_value = mock_update_result
                    mock_table.update.return_value = mock_query
            elif table_name == "bookings":
                mock_query = MagicMock()
                mock_query.update.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_table.update.return_value = mock_query
            return mock_table
        
        mock_supabase.table.side_effect = table_side_effect
        
        # Mock request with query_params
        mock_request = MagicMock()
        mock_query_params = MagicMock()
        mock_query_params.__iter__ = lambda x: iter(callback_data.items())
        mock_query_params.__getitem__ = lambda x, key: callback_data.get(key)
        mock_query_params.get = lambda x, y=None: callback_data.get(x, y)
        mock_request.query_params = mock_query_params
        mock_request.form = AsyncMock(return_value={})
        
        with patch('app.v1.api.endpoints.payments.get_supabase_client', return_value=mock_supabase):
            payment_service = PaymentService(mock_supabase)
            payment_service.vnpay_service = vnpay_service
            
            response = await vnpay_ipn(request=mock_request, service=payment_service)
            
            assert isinstance(response, dict)
            assert response["RspCode"] == "00"
            assert "success" in response["Message"].lower()
    
    @pytest.mark.asyncio
    async def test_vnpay_return_endpoint_success(
        self, mock_supabase, sample_vnpay_callback_success, sample_payment_data
    ):
        """Test GET /vnpay/return endpoint successfully"""
        from app.v1.api.endpoints.payments import vnpay_return
        from fastapi.responses import RedirectResponse
        
        callback_data, payment_id = sample_vnpay_callback_success
        sample_payment_data["payment_id"] = payment_id
        sample_payment_data["amount"] = 7680000.0
        
        # Mock get payment
        mock_payment_result = MagicMock()
        mock_payment_result.data = [sample_payment_data]
        
        # Mock update payment
        updated_payment = sample_payment_data.copy()
        updated_payment["payment_status"] = "completed"
        updated_payment["transaction_id"] = "12345678"
        mock_update_result = MagicMock()
        mock_update_result.data = [updated_payment]
        
        # Mock update booking
        mock_booking_update = MagicMock()
        mock_booking_update.execute.return_value = MagicMock()
        
        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "payments":
                if not hasattr(mock_table, '_call_count'):
                    mock_table._call_count = 0
                if mock_table._call_count == 0:
                    mock_query = MagicMock()
                    mock_query.select.return_value = mock_query
                    mock_query.eq.return_value = mock_query
                    mock_query.execute.return_value = mock_payment_result
                    mock_table.select.return_value = mock_query
                    mock_table._call_count += 1
                else:
                    mock_query = MagicMock()
                    mock_query.update.return_value = mock_query
                    mock_query.eq.return_value = mock_query
                    mock_query.execute.return_value = mock_update_result
                    mock_table.update.return_value = mock_query
            elif table_name == "bookings":
                mock_query = MagicMock()
                mock_query.update.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_table.update.return_value = mock_query
            return mock_table
        
        mock_supabase.table.side_effect = table_side_effect
        
        # Mock request with query_params
        mock_request = MagicMock()
        mock_query_params = MagicMock()
        mock_query_params.__iter__ = lambda x: iter(callback_data.items())
        mock_query_params.__getitem__ = lambda x, key: callback_data.get(key)
        mock_query_params.get = lambda x, y=None: callback_data.get(x, y)
        mock_request.query_params = mock_query_params
        
        with patch('app.v1.api.endpoints.payments.get_supabase_client', return_value=mock_supabase):
            payment_service = PaymentService(mock_supabase)
            payment_service.vnpay_service = vnpay_service
            
            response = await vnpay_return(request=mock_request, service=payment_service, vnpay_service=vnpay_service)
            
            assert isinstance(response, RedirectResponse)
            assert "payment/success" in response.headers["location"] or "payment/failed" in response.headers["location"]
    
    @pytest.mark.asyncio
    async def test_get_my_payments_endpoint_success(
        self, mock_supabase, mock_current_user
    ):
        """Test GET /my-payments endpoint successfully"""
        from app.v1.api.endpoints.payments import get_my_payments
        
        user_id = mock_current_user["user_id"]
        booking_id = str(uuid4())
        
        # Mock bookings query
        mock_bookings_result = MagicMock()
        mock_bookings_result.data = [{"booking_id": booking_id}]
        
        # Mock payments query
        payment_data = {
            "payment_id": str(uuid4()),
            "booking_id": booking_id,
            "amount": 7680000.0,
            "payment_method": "vnpay",
            "payment_status": "completed",
            "transaction_id": "12345678",
            "paid_at": datetime.now(timezone.utc).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "bookings": {
                "tour_packages": {
                    "package_name": "Tour Đà Lạt",
                    "destination": "Đà Lạt"
                }
            }
        }
        
        mock_payments_result = MagicMock()
        mock_payments_result.data = [payment_data]
        mock_payments_result.count = 1
        
        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "bookings":
                mock_query = MagicMock()
                mock_query.select.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_query.execute.return_value = mock_bookings_result
                mock_table.select.return_value = mock_query
            elif table_name == "payments":
                mock_query = MagicMock()
                mock_query.select.return_value = mock_query
                mock_query.in_.return_value = mock_query
                mock_query.order.return_value = mock_query
                mock_query.execute.return_value = mock_payments_result
                mock_table.select.return_value = mock_query
            return mock_table
        
        mock_supabase.table.side_effect = table_side_effect
        
        with patch('app.v1.api.endpoints.payments.get_supabase_client', return_value=mock_supabase):
            payment_service = PaymentService(mock_supabase)
            
            response = await get_my_payments(
                current_user=mock_current_user,
                status=None,
                limit=None,
                offset=None,
                service=payment_service
            )
            
            assert response.EC == 0
            assert response.EM == "Success"
            assert len(response.data) == 1
            assert response.total == 1
    
    @pytest.mark.asyncio
    async def test_get_payment_by_booking_endpoint_success(
        self, mock_supabase, sample_payment_data, mock_current_user
    ):
        """Test GET /booking/{booking_id} endpoint successfully"""
        from app.v1.api.endpoints.payments import get_payment_by_booking
        
        booking_id = sample_payment_data["booking_id"]
        
        mock_result = MagicMock()
        mock_result.data = [sample_payment_data]
        
        mock_query = MagicMock()
        mock_query.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.order.return_value = mock_query
        mock_query.execute.return_value = mock_result
        
        mock_supabase.table.return_value = mock_query
        
        # Mock booking check
        mock_booking_result = MagicMock()
        mock_booking_result.data = [{"user_id": mock_current_user["user_id"]}]
        
        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "bookings":
                mock_query = MagicMock()
                mock_query.select.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_query.execute.return_value = mock_booking_result
                mock_table.select.return_value = mock_query
            elif table_name == "payments":
                mock_query = MagicMock()
                mock_query.select.return_value = mock_query
                mock_query.eq.return_value = mock_query
                mock_query.order.return_value = mock_query
                mock_query.execute.return_value = mock_result
                mock_table.select.return_value = mock_query
            return mock_table
        
        mock_supabase.table.side_effect = table_side_effect
        
        with patch('app.v1.api.endpoints.payments.get_supabase_client', return_value=mock_supabase):
            payment_service = PaymentService(mock_supabase)
            
            response = await get_payment_by_booking(
                booking_id=booking_id,
                current_user=mock_current_user,
                service=payment_service
            )
            
            assert response.EC == 0
            assert response.EM == "Success"
            # Convert both to string for comparison (UUID vs string)
            assert str(response.data.payment_id) == str(sample_payment_data["payment_id"])

