"""
Test VNPay với course title có ký tự đặc biệt
"""
import re

# Test cases
test_titles = [
    "Lập trình Python cơ bản",
    "Khóa học Django & REST API",
    "Web Development (Full-stack)",
    "Machine Learning 101!",
    "Data Science @2024",
]

print("="*80)
print("Test sanitize course title for VNPay")
print("="*80)

for title in test_titles:
    # Original
    print(f"\nOriginal: {title}")
    
    # Sanitized - Loại bỏ ký tự đặc biệt
    safe_title = re.sub(r'[^a-zA-Z0-9 ]', '', title)
    print(f"After remove special chars: {safe_title}")
    
    # Replace spaces
    safe_title = safe_title.replace(' ', '_')
    print(f"After replace spaces: {safe_title}")
    
    # Final order_desc
    order_desc = f"Thanh_toan_khoa_hoc_{safe_title}"[:255]
    print(f"Final OrderInfo: {order_desc}")
    print(f"Length: {len(order_desc)} chars")

print("\n" + "="*80)
print("✓ Tất cả ký tự đặc biệt đã được loại bỏ")
print("✓ Spaces đã được thay thế bằng underscore")
print("✓ Độ dài đã được giới hạn ≤ 255 chars")
print("="*80)
