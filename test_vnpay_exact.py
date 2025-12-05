"""
Test với VNPay params đầy đủ theo docs chính thức
https://sandbox.vnpayment.vn/apis/docs/thanh-toan-pay/pay.html
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.conf import settings
import hashlib
import hmac
import urllib.parse
from datetime import datetime

TMN_CODE = settings.VNPAY_TMN_CODE
HASH_SECRET = settings.VNPAY_HASH_SECRET
VNPAY_URL = settings.VNPAY_URL
RETURN_URL = settings.VNPAY_RETURN_URL

print("="*100)
print("VNPay Payment URL Test - Full Params")
print("="*100)

# Test với đầy đủ params theo docs VNPay
vnp_params = {
    'vnp_Version': '2.1.0',
    'vnp_Command': 'pay',
    'vnp_TmnCode': TMN_CODE,
    'vnp_Amount': '10000000',  # 100k VND
    'vnp_CurrCode': 'VND',
    'vnp_TxnRef': 'TEST' + datetime.now().strftime('%Y%m%d%H%M%S'),
    'vnp_OrderInfo': 'Test_thanh_toan',
    'vnp_OrderType': 'other',
    'vnp_Locale': 'vn',
    'vnp_ReturnUrl': RETURN_URL,
    'vnp_IpAddr': '127.0.0.1',
    'vnp_CreateDate': datetime.now().strftime('%Y%m%d%H%M%S'),
}

print("\nParams BEFORE sorting:")
for k, v in vnp_params.items():
    print(f"  {k}={v}")

# Sort theo alphabet
sorted_params = sorted(vnp_params.items())

print("\nParams AFTER sorting:")
for k, v in sorted_params:
    print(f"  {k}={v}")

# Tạo hash data - KHÔNG encode
hash_data = '&'.join([f'{k}={v}' for k, v in sorted_params])
print(f"\nHash data (raw, no encoding):")
print(f"  {hash_data}")

# Tạo hash
secure_hash = hmac.new(
    HASH_SECRET.encode('utf-8'),
    hash_data.encode('utf-8'),
    hashlib.sha512
).hexdigest()

print(f"\nSecure Hash:")
print(f"  {secure_hash}")

# Tạo query string - CÓ encode
query_string = '&'.join([f'{k}={urllib.parse.quote_plus(str(v))}' for k, v in sorted_params])

# Final URL
payment_url = f"{VNPAY_URL}?{query_string}&vnp_SecureHash={secure_hash}"

print(f"\nFinal Payment URL:")
print(f"  {payment_url}")

print("\n" + "="*100)
print("Copy URL trên và test trong browser!")
print("="*100)

# Also test signature theo cách VNPay docs
print("\n\nAlternative: Test theo exact VNPay sample")
print("="*100)

# Theo sample VNPay
sample_data = (
    f"vnp_Amount={vnp_params['vnp_Amount']}"
    f"&vnp_Command={vnp_params['vnp_Command']}"
    f"&vnp_CreateDate={vnp_params['vnp_CreateDate']}"
    f"&vnp_CurrCode={vnp_params['vnp_CurrCode']}"
    f"&vnp_IpAddr={vnp_params['vnp_IpAddr']}"
    f"&vnp_Locale={vnp_params['vnp_Locale']}"
    f"&vnp_OrderInfo={vnp_params['vnp_OrderInfo']}"
    f"&vnp_OrderType={vnp_params['vnp_OrderType']}"
    f"&vnp_ReturnUrl={vnp_params['vnp_ReturnUrl']}"
    f"&vnp_TmnCode={vnp_params['vnp_TmnCode']}"
    f"&vnp_TxnRef={vnp_params['vnp_TxnRef']}"
    f"&vnp_Version={vnp_params['vnp_Version']}"
)

print(f"Sample data (manual sort):")
print(f"  {sample_data}")

sample_hash = hmac.new(
    HASH_SECRET.encode('utf-8'),
    sample_data.encode('utf-8'),
    hashlib.sha512
).hexdigest()

print(f"\nSample hash:")
print(f"  {sample_hash}")

print(f"\nHashes match? {secure_hash == sample_hash}")

if secure_hash != sample_hash:
    print("\n⚠️ WARNING: Sorting might be wrong!")
    print("Check if Python sorted() gives same order as manual sort")
