"""
Debug VNPay Hash Secret - Kiểm tra chi tiết
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.conf import settings
import hashlib
import hmac

print("="*80)
print("VNPay Hash Secret Debug")
print("="*80)

hash_secret = settings.VNPAY_HASH_SECRET
tmn_code = settings.VNPAY_TMN_CODE

print(f"\n1. Basic Info:")
print(f"   TMN_CODE: '{tmn_code}'")
print(f"   TMN_CODE length: {len(tmn_code)}")
print(f"   TMN_CODE has spaces: {' ' in tmn_code}")

print(f"\n2. Hash Secret Info:")
print(f"   HASH_SECRET: '{hash_secret}'")
print(f"   HASH_SECRET length: {len(hash_secret)}")
print(f"   HASH_SECRET has spaces: {' ' in hash_secret}")
print(f"   HASH_SECRET has newline: {hash_secret != hash_secret.strip()}")

# Test encoding
print(f"\n3. Encoding Test:")
test_string = "vnp_Amount=10000000&vnp_Command=pay"
print(f"   Test string: {test_string}")

# Test with current hash_secret
hash1 = hmac.new(
    hash_secret.encode('utf-8'),
    test_string.encode('utf-8'),
    hashlib.sha512
).hexdigest()
print(f"   Hash (current): {hash1[:40]}...")

# Test with stripped hash_secret
hash2 = hmac.new(
    hash_secret.strip().encode('utf-8'),
    test_string.encode('utf-8'),
    hashlib.sha512
).hexdigest()
print(f"   Hash (stripped): {hash2[:40]}...")

print(f"\n4. Are they equal? {hash1 == hash2}")

if hash1 != hash2:
    print("\n⚠️ WARNING: Hash secret has whitespace/newline!")
    print("   Fix: Update settings.py to use .strip()")

print("\n5. Recommended Hash Secret (stripped):")
print(f"   '{hash_secret.strip()}'")

print("\n" + "="*80)
