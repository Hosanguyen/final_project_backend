"""
Script để debug VNPay parameters
Chạy: python manage.py shell < course/vnpay_debug.py
"""
from course.vnpay_service import VNPayService
from django.conf import settings
import json

print("\n" + "="*60)
print("VNPay Configuration Debug")
print("="*60)

print("\n1. Settings:")
print(f"   TMN_CODE: {settings.VNPAY_TMN_CODE}")
print(f"   HASH_SECRET: {'*' * len(settings.VNPAY_HASH_SECRET) if settings.VNPAY_HASH_SECRET else 'NOT SET'}")
print(f"   URL: {settings.VNPAY_URL}")
print(f"   RETURN_URL: {settings.VNPAY_RETURN_URL}")

print("\n2. Test Payment URL Generation:")
vnpay = VNPayService()

# Test data
test_order_code = "TEST123456"
test_amount = 100000  # 100,000 VND
test_desc = "Test khóa học Python"
test_ip = "127.0.0.1"

print(f"   Order Code: {test_order_code}")
print(f"   Amount: {test_amount:,} VND")
print(f"   Description: {test_desc}")
print(f"   IP: {test_ip}")

try:
    payment_url = vnpay.create_payment_url(
        order_code=test_order_code,
        amount=test_amount,
        order_desc=test_desc,
        ip_addr=test_ip
    )
    
    print("\n3. Generated URL:")
    print(f"   {payment_url[:100]}...")
    
    print("\n4. URL Parameters:")
    from urllib.parse import urlparse, parse_qs
    parsed = urlparse(payment_url)
    params = parse_qs(parsed.query)
    
    for key in sorted(params.keys()):
        value = params[key][0]
        if key == 'vnp_SecureHash':
            print(f"   {key}: {value[:20]}...{value[-20:]}")
        else:
            print(f"   {key}: {value}")
    
    print("\n5. Amount Check:")
    vnp_amount = params.get('vnp_Amount', [''])[0]
    print(f"   vnp_Amount: {vnp_amount}")
    print(f"   Expected: {int(test_amount * 100)}")
    print(f"   Match: {vnp_amount == str(int(test_amount * 100))}")
    
    print("\n✅ Test passed! URL generated successfully.")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("Lưu ý:")
print("- vnp_Amount phải là số nguyên (VND * 100)")
print("- Tất cả params phải là string")
print("- Hash data KHÔNG được URL encode")
print("- Query string cuối cùng CÓ URL encode")
print("="*60 + "\n")
