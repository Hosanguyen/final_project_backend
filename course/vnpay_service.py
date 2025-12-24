import hashlib
import hmac
import urllib.parse
from datetime import datetime
from django.conf import settings


class VNPayService:
    """
    Service xử lý thanh toán VNPay
    Tài liệu: https://sandbox.vnpayment.vn/apis/docs/thanh-toan-pay/pay.html
    """
    
    def __init__(self):
        self.vnp_tmn_code = settings.VNPAY_TMN_CODE
        self.vnp_hash_secret = settings.VNPAY_HASH_SECRET
        self.vnp_url = settings.VNPAY_URL
        self.vnp_return_url = settings.VNPAY_RETURN_URL
        self.vnp_api_url = settings.VNPAY_API_URL
    
    def create_payment_url(self, order_code, amount, order_desc, ip_addr, locale='vn'):
        """
        Tạo URL thanh toán VNPay
        
        Args:
            order_code: Mã đơn hàng
            amount: Số tiền (VND)
            order_desc: Mô tả đơn hàng
            ip_addr: IP address của người dùng
            locale: Ngôn ngữ (vn hoặc en)
        
        Returns:
            URL thanh toán VNPay
        """
        # Tạo request data
        vnp_params = {
            'vnp_Version': '2.1.0',
            'vnp_Command': 'pay',
            'vnp_TmnCode': self.vnp_tmn_code,
            'vnp_Amount': str(int(amount * 100)),  # VNPay yêu cầu số tiền nhân 100, phải là string
            'vnp_CurrCode': 'VND',
            'vnp_TxnRef': str(order_code),
            'vnp_OrderInfo': str(order_desc),
            'vnp_OrderType': 'other',  # Loại hàng hóa
            'vnp_Locale': locale if locale in ['vn', 'en'] else 'vn',
            'vnp_ReturnUrl': self.vnp_return_url,
            'vnp_IpAddr': str(ip_addr),
            'vnp_CreateDate': datetime.now().strftime('%Y%m%d%H%M%S'),
        }
        
        # Sắp xếp params theo alphabet
        sorted_params = sorted(vnp_params.items())
        
        # Tạo hash data - VNPay yêu cầu URL encode cho hash (theo PHP example)
        hash_data = '&'.join([f'{urllib.parse.quote_plus(str(key))}={urllib.parse.quote_plus(str(val))}' for key, val in sorted_params])
        
        # Tạo secure hash
        secure_hash = self._create_secure_hash(hash_data)
        
        # Tạo query string (giống hash_data)
        query_string = hash_data
        
        # Tạo URL thanh toán
        payment_url = f"{self.vnp_url}?{query_string}&vnp_SecureHash={secure_hash}"
        
        return payment_url
    
    def validate_response(self, query_params):
        """
        Xác thực response từ VNPay
        
        Args:
            query_params: Dictionary chứa các tham số từ VNPay callback
        
        Returns:
            tuple: (is_valid, response_code, txn_ref)
        """
        # Lấy secure hash từ response
        vnp_secure_hash = query_params.get('vnp_SecureHash', '')
        
        # Loại bỏ secure hash và các params không cần thiết
        params_to_validate = {k: v for k, v in query_params.items() 
                             if k.startswith('vnp_') and k != 'vnp_SecureHash' and k != 'vnp_SecureHashType'}
        
        # Sắp xếp params
        sorted_params = sorted(params_to_validate.items())
        
        # Tạo hash data - VNPay yêu cầu URL encode (theo PHP example)
        hash_data = '&'.join([f'{urllib.parse.quote_plus(str(key))}={urllib.parse.quote_plus(str(val))}' for key, val in sorted_params])
        
        # Tạo secure hash để so sánh
        calculated_hash = self._create_secure_hash(hash_data)
        
        # Kiểm tra hash
        is_valid = hmac.compare_digest(calculated_hash, vnp_secure_hash)
        
        # Lấy thông tin giao dịch
        response_code = query_params.get('vnp_ResponseCode', '')
        txn_ref = query_params.get('vnp_TxnRef', '')
        
        return is_valid, response_code, txn_ref
    
    def _create_secure_hash(self, data):
        """
        Tạo secure hash theo chuẩn HMAC SHA512
        
        Args:
            data: Chuỗi dữ liệu cần hash
        
        Returns:
            Chuỗi hash
        """
        return hmac.new(
            self.vnp_hash_secret.encode('utf-8'),
            data.encode('utf-8'),
            hashlib.sha512
        ).hexdigest()
    
    @staticmethod
    def is_success_response(response_code):
        """
        Kiểm tra mã response có thành công không
        
        Args:
            response_code: Mã response từ VNPay
        
        Returns:
            True nếu thành công, False nếu thất bại
        """
        return response_code == '00'
