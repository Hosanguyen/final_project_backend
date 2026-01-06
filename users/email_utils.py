"""
Utility functions for sending emails
"""
import random
import string
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from .models import EmailOTP


def generate_otp(length=6):
    return ''.join(random.choices(string.digits, k=length))


def create_otp(email, otp_type):
    EmailOTP.objects.filter(
        email=email,
        otp_type=otp_type,
        is_used=False
    ).update(is_used=True)
    
    otp_code = generate_otp(settings.OTP_LENGTH)
    expires_at = timezone.now() + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)
    
    otp = EmailOTP.objects.create(
        email=email,
        otp_code=otp_code,
        otp_type=otp_type,
        expires_at=expires_at
    )
    
    return otp


def send_verification_email(email, otp_code):
    subject = 'Xác thực tài khoản - Hệ thống luyện tập lập trình'
    message = f"""
Xin chào,

Cảm ơn bạn đã đăng ký tài khoản tại hệ thống luyện tập lập trình của chúng tôi.

Mã OTP xác thực tài khoản của bạn là: {otp_code}

Mã này sẽ hết hạn sau {settings.OTP_EXPIRY_MINUTES} phút.

Vui lòng không chia sẻ mã này với bất kỳ ai.

Trân trọng,
Đội ngũ phát triển
"""
    
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [email]
    
    send_mail(subject, message, from_email, recipient_list, fail_silently=False)


def send_password_reset_email(email, otp_code):
    subject = 'Đặt lại mật khẩu - Hệ thống luyện tập lập trình'
    message = f"""
Xin chào,

Bạn đã yêu cầu đặt lại mật khẩu cho tài khoản của mình.

Mã OTP để đặt lại mật khẩu là: {otp_code}

Mã này sẽ hết hạn sau {settings.OTP_EXPIRY_MINUTES} phút.

Nếu bạn không thực hiện yêu cầu này, vui lòng bỏ qua email này.

Trân trọng,
Đội ngũ phát triển
"""
    
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [email]
    
    send_mail(subject, message, from_email, recipient_list, fail_silently=False)


def verify_otp(email, otp_code, otp_type):
    try:
        otp = EmailOTP.objects.get(
            email=email,
            otp_code=otp_code,
            otp_type=otp_type,
            is_used=False
        )
        
        if otp.is_expired():
            return False, "Mã OTP đã hết hạn"
        
        otp.is_used = True
        otp.used_at = timezone.now()
        otp.save()
        
        return True, "Xác thực thành công"
        
    except EmailOTP.DoesNotExist:
        return False, "Mã OTP không hợp lệ"
