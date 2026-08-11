import hashlib
import smtplib
from email.message import EmailMessage

from app.config import settings


def password_version(password_hash: str) -> str:
    return hashlib.sha256(password_hash.encode("utf-8")).hexdigest()


def send_password_reset_email(to_email: str, reset_url: str) -> None:
    if not settings.SMTP_HOST or not settings.SMTP_FROM_EMAIL:
        raise RuntimeError("SMTP password reset delivery is not configured")

    message = EmailMessage()
    message["Subject"] = "Đặt lại mật khẩu FinAI"
    message["From"] = settings.SMTP_FROM_EMAIL
    message["To"] = to_email
    message.set_content(
        "Bạn đã yêu cầu đặt lại mật khẩu FinAI. "
        f"Mở liên kết sau trong vòng {settings.PASSWORD_RESET_EXPIRE_MINUTES} phút:\n\n"
        f"{reset_url}\n\nNếu bạn không thực hiện yêu cầu này, hãy bỏ qua email này."
    )

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as smtp:
        smtp.starttls()
        if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
            smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        smtp.send_message(message)
