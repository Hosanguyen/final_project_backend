"""
Test VNPay signature với credentials thật
"""
import hashlib
import hmac
import urllib.parse
from datetime import datetime

# Credentials thật từ .env
TMN_CODE = "I3AK43TG"
HASH_SECRET = "20QX2956M3DV7NF342NWIFJJGH9QJ1TY"

# Test data
vnp_params = {
    'vnp_Version': '2.1.0',
    'vnp_Command': 'pay',
    'vnp_TmnCode': TMN_CODE,
    'vnp_Amount': '10000000',  # 100,000 VND * 100
    'vnp_CurrCode': 'VND',
    'vnp_TxnRef': 'TEST123456',
    'vnp_OrderInfo': 'Test khoa hoc',
    'vnp_OrderType': 'other',
    'vnp_Locale': 'vn',
    'vnp_ReturnUrl': 'https://josephine-unsurmising-importantly.ngrok-free.dev/api/payment/vnpay/return/',
    'vnp_IpAddr': '127.0.0.1',
    'vnp_CreateDate': datetime.now().strftime('%Y%m%d%H%M%S'),
}

print("="*80)
print("VNPay Signature Test")
print("="*80)

print("\n1. Original params:")
for k, v in vnp_params.items():
    print(f"   {k}: {v}")

# Sắp xếp theo alphabet
sorted_params = sorted(vnp_params.items())

print("\n2. Sorted params:")
for k, v in sorted_params:
    print(f"   {k}: {v}")

# Tạo hash data (KHÔNG encode URL)
hash_data = '&'.join([f'{key}={val}' for key, val in sorted_params])

print("\n3. Hash data (KHÔNG encode):")
print(f"   {hash_data}")

# Tạo secure hash
secure_hash = hmac.new(
    HASH_SECRET.encode('utf-8'),
    hash_data.encode('utf-8'),
    hashlib.sha512
).hexdigest()

print("\n4. Secure Hash (SHA512):")
print(f"   {secure_hash}")

# Tạo query string (CÓ encode URL)
query_string = '&'.join([f'{key}={urllib.parse.quote_plus(str(val))}' for key, val in sorted_params])

print("\n5. Query string (CÓ encode):")
print(f"   {query_string[:100]}...")

# URL cuối cùng
payment_url = f"https://sandbox.vnpayment.vn/paymentv2/vpcpay.html?{query_string}&vnp_SecureHash={secure_hash}"

print("\n6. Full URL:")
print(f"   {payment_url[:150]}...")

print("\n7. Verification:")
print(f"   ✓ All params are strings: {all(isinstance(v, str) for v in vnp_params.values())}")
print(f"   ✓ Amount is integer string: {vnp_params['vnp_Amount'].isdigit()}")
print(f"   ✓ Hash length: {len(secure_hash)} chars")
print(f"   ✓ Expected hash length: 128 chars (SHA512)")

print("\n" + "="*80)
print("Copy URL này và test trên browser:")
print(payment_url)
print("="*80)
