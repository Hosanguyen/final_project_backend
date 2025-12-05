"""
Test cả SHA256 và SHA512 để xem VNPay dùng algo nào
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

# Test data
vnp_params = {
    'vnp_Version': '2.1.0',
    'vnp_Command': 'pay',
    'vnp_TmnCode': TMN_CODE,
    'vnp_Amount': '10000000',
    'vnp_CurrCode': 'VND',
    'vnp_TxnRef': 'TEST' + datetime.now().strftime('%Y%m%d%H%M%S'),
    'vnp_OrderInfo': 'Test',
    'vnp_OrderType': 'other',
    'vnp_Locale': 'vn',
    'vnp_ReturnUrl': settings.VNPAY_RETURN_URL,
    'vnp_IpAddr': '127.0.0.1',
    'vnp_CreateDate': datetime.now().strftime('%Y%m%d%H%M%S'),
}

# Sort
sorted_params = sorted(vnp_params.items())
hash_data = '&'.join([f'{k}={v}' for k, v in sorted_params])

print("="*100)
print("VNPay Hash Algorithm Test")
print("="*100)

print(f"\nHash data:")
print(f"  {hash_data}")

print(f"\nCredentials:")
print(f"  TMN_CODE: {TMN_CODE}")
print(f"  HASH_SECRET: {HASH_SECRET}")

# Test SHA512
hash_sha512 = hmac.new(
    HASH_SECRET.encode('utf-8'),
    hash_data.encode('utf-8'),
    hashlib.sha512
).hexdigest()

# Test SHA256
hash_sha256 = hmac.new(
    HASH_SECRET.encode('utf-8'),
    hash_data.encode('utf-8'),
    hashlib.sha256
).hexdigest()

# Test MD5
hash_md5 = hashlib.md5((HASH_SECRET + hash_data).encode('utf-8')).hexdigest()

print(f"\n1. SHA512 (current):")
print(f"  {hash_sha512}")
print(f"  Length: {len(hash_sha512)}")

print(f"\n2. SHA256:")
print(f"  {hash_sha256}")
print(f"  Length: {len(hash_sha256)}")

print(f"\n3. MD5 (legacy):")
print(f"  {hash_md5}")
print(f"  Length: {len(hash_md5)}")

# Generate URLs
query_string = '&'.join([f'{k}={urllib.parse.quote_plus(str(v))}' for k, v in sorted_params])

url_sha512 = f"{settings.VNPAY_URL}?{query_string}&vnp_SecureHash={hash_sha512}"
url_sha256 = f"{settings.VNPAY_URL}?{query_string}&vnp_SecureHash={hash_sha256}"

print(f"\n" + "="*100)
print("Test URLs:")
print("="*100)

print(f"\nURL with SHA512:")
print(f"{url_sha512}\n")

print(f"\nURL with SHA256:")
print(f"{url_sha256}\n")

print("="*100)
print("Hướng dẫn test:")
print("1. Copy URL SHA512 → Test trong browser")
print("2. Nếu lỗi 'Sai chữ ký' → Copy URL SHA256 → Test lại")
print("3. URL nào work → Update code sử dụng algorithm đó")
print("="*100)
