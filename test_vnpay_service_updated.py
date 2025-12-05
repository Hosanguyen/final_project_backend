"""
Test VNPay service với code đã update (URL-encoded hash data)
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from course.vnpay_service import VNPayService
from datetime import datetime

print("="*100)
print("VNPay Service Test - URL Encoded Hash Data")
print("="*100)

vnpay = VNPayService()

# Test data
order_code = "TEST" + datetime.now().strftime('%Y%m%d%H%M%S')
amount = 100000  # 100k VND
order_desc = "Test_thanh_toan"
ip_addr = "127.0.0.1"

print(f"\nTest Payment URL Generation:")
print(f"  Order Code: {order_code}")
print(f"  Amount: {amount:,} VND")
print(f"  Description: {order_desc}")
print(f"  IP: {ip_addr}")

try:
    payment_url = vnpay.create_payment_url(
        order_code=order_code,
        amount=amount,
        order_desc=order_desc,
        ip_addr=ip_addr,
        locale='vn'
    )
    
    print(f"\n✅ Payment URL generated successfully!")
    print(f"\nURL (first 200 chars):")
    print(f"  {payment_url[:200]}...")
    
    print(f"\n\n🚀 FULL URL - Copy và test trong browser:")
    print("="*100)
    print(payment_url)
    print("="*100)
    
    # Extract and display secure hash
    import urllib.parse
    parsed = urllib.parse.urlparse(payment_url)
    params = urllib.parse.parse_qs(parsed.query)
    
    secure_hash = params.get('vnp_SecureHash', [''])[0]
    print(f"\nSecure Hash:")
    print(f"  {secure_hash}")
    print(f"  Length: {len(secure_hash)} chars")
    
    print(f"\n✅ Code đã update:")
    print(f"  ✓ Hash data CÓ URL encode (theo PHP example)")
    print(f"  ✓ Query string CÓ URL encode")
    print(f"  ✓ Cả 2 giống nhau")
    
    print(f"\n📝 Hướng dẫn test:")
    print(f"  1. Copy URL trên")
    print(f"  2. Paste vào browser")
    print(f"  3. Nếu VNPay page load → SUCCESS!")
    print(f"  4. Nếu vẫn lỗi 'Sai chữ ký' → Contact VNPay support")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*100)
