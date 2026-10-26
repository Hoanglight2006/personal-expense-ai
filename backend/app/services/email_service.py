"""Email delivery service supporting SMTP and development fallback logging."""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Encapsulates all outgoing transactional email logic for FinAI."""

    @staticmethod
    def _send_email(to_email: str, subject: str, text_content: str, html_content: str | None = None) -> bool:
        """Send email via SMTP if configured, otherwise print and log to console for development."""
        has_smtp = bool(
            settings.SMTP_HOST
            and settings.SMTP_FROM_EMAIL
            and settings.SMTP_USERNAME
            and settings.SMTP_PASSWORD
        )

        if not has_smtp:
            print(
                f"\n======================================================================\n"
                f"📧 [FINAI EMAIL SIMULATOR - CHƯA CẤU HÌNH SMTP HOẶC THIẾU TÀI KHOẢN]\n"
                f"Gửi tới (To): {to_email}\n"
                f"Tiêu đề (Subject): {subject}\n"
                f"Nội dung (Body):\n{text_content}\n"
                f"💡 LƯU Ý: Để gửi email thật tới hòm thư, bạn chỉ cần điền SMTP_USERNAME,\n"
                f"SMTP_PASSWORD (Mật khẩu ứng dụng 16 số của Google), SMTP_FROM_EMAIL vào file .env\n"
                f"======================================================================\n",
                flush=True,
            )
            logger.info("📧 [EMAIL SIMULATOR] To: %s | Subject: %s", to_email, subject)
            return True

        try:
            msg = EmailMessage()
            msg["Subject"] = subject
            msg["From"] = settings.SMTP_FROM_EMAIL
            msg["To"] = to_email
            msg.set_content(text_content)
            if html_content:
                msg.add_alternative(html_content, subtype="html")

            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=12) as server:
                server.starttls()
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.send_message(msg)
            print(f"✅ [SMTP SUCCESS] Đã gửi email thành công tới {to_email} qua {settings.SMTP_HOST}!", flush=True)
            logger.info("✅ Đã gửi email thành công tới %s: %s", to_email, subject)
            return True
        except Exception as e:
            print(
                f"\n❌ [SMTP ERROR - KHÔNG THỂ GỬI QUA MÁY CHỦ EMAIL]\n"
                f"Chi tiết lỗi: {e}\n"
                f"📧 [FALLBACK MÃ XÁC THỰC HIỂN THỊ DƯỚI ĐÂY ĐỂ BẠN TIẾP TỤC TEST]:\n"
                f"Gửi tới: {to_email}\n"
                f"Tiêu đề: {subject}\n"
                f"Nội dung:\n{text_content}\n"
                f"======================================================================\n",
                flush=True,
            )
            logger.exception("❌ Gửi email thất bại tới %s: %s", to_email, e)
            return False

    @classmethod
    def send_password_reset_otp(cls, to_email: str, otp_code: str) -> bool:
        subject = "[FinAI] Mã xác nhận đặt lại mật khẩu"
        text = (
            f"Xin chào,\n\n"
            f"Bạn vừa yêu cầu đặt lại mật khẩu trên FinAI.\n"
            f"Mã OTP xác nhận của bạn là: {otp_code}\n"
            f"Mã có hiệu lực trong vòng 15 phút. Tuyệt đối không chia sẻ mã này cho bất kỳ ai.\n\n"
            f"Nếu bạn không yêu cầu, vui lòng bỏ qua email này.\n"
            f"FinAI Team."
        )
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 520px; margin: 0 auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 16px;">
            <h2 style="color: #d97706; margin-top: 0;">FinAI - Đặt lại mật khẩu</h2>
            <p>Bạn vừa gửi yêu cầu đặt lại mật khẩu cho tài khoản tại FinAI.</p>
            <div style="background: #fef3c7; border: 2px dashed #d97706; padding: 18px; text-align: center; border-radius: 12px; margin: 20px 0;">
                <span style="font-size: 28px; font-weight: 800; letter-spacing: 6px; color: #92400e;">{otp_code}</span>
            </div>
            <p style="color: #64748b; font-size: 13px;">Mã xác thực có hiệu lực trong 15 phút. Nếu bạn không thực hiện yêu cầu này, vui lòng bỏ qua email.</p>
        </div>
        """
        return cls._send_email(to_email, subject, text, html)

    @classmethod
    def send_account_activation(
        cls, to_email: str, username: str, temp_password: str, role: str = "user"
    ) -> bool:
        role_label = "Quản trị viên" if role == "admin" else "Người dùng"
        subject = "[FinAI] Tài khoản của bạn đã được khởi tạo"
        text = (
            f"Xin chào {username},\n\n"
            f"Quản trị viên FinAI đã khởi tạo tài khoản {role_label} cho bạn.\n"
            f"Thông tin đăng nhập:\n"
            f"- Email: {to_email}\n"
            f"- Tên người dùng: {username}\n"
            f"- Mật khẩu khởi tạo: {temp_password}\n\n"
            f"⚠️ LƯU Ý BẢO MẬT: Đây là tài khoản được cấp mới. Hệ thống sẽ bắt buộc bạn đổi mật khẩu ngay trong lần đăng nhập đầu tiên.\n\n"
            f"Đăng nhập tại: {settings.FRONTEND_BASE_URL}\n"
            f"FinAI Team."
        )
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 520px; margin: 0 auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 16px;">
            <h2 style="color: #d97706; margin-top: 0;">🎉 Chào mừng bạn đến với FinAI!</h2>
            <p>Quản trị viên đã cấp tài khoản <strong>{role_label}</strong> cho bạn với thông tin:</p>
            <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
                <tr><td style="padding: 8px 0; color: #64748b;">Email:</td><td style="font-weight: bold;">{to_email}</td></tr>
                <tr><td style="padding: 8px 0; color: #64748b;">Tên người dùng:</td><td style="font-weight: bold;">{username}</td></tr>
                <tr><td style="padding: 8px 0; color: #64748b;">Mật khẩu ban đầu:</td><td style="font-weight: bold; color: #b45309; font-family: monospace; font-size: 16px;">{temp_password}</td></tr>
            </table>
            <div style="background: #fffbeb; border-left: 4px solid #d97706; padding: 12px; margin: 16px 0; font-size: 13px; color: #92400e;">
                ⚠️ <strong>Bắt buộc đổi mật khẩu:</strong> Bạn sẽ cần đặt mật khẩu mới của riêng mình ngay khi đăng nhập lần đầu tiên.
            </div>
            <p><a href="{settings.FRONTEND_BASE_URL}" style="display: inline-block; background: #d97706; color: white; padding: 10px 20px; border-radius: 8px; text-decoration: none; font-weight: bold;">Đăng nhập ngay</a></p>
        </div>
        """
        return cls._send_email(to_email, subject, text, html)

    @classmethod
    def send_email_verification_otp(cls, to_email: str, otp_code: str) -> bool:
        subject = "[FinAI] Mã xác minh địa chỉ Email"
        text = (
            f"Xin chào,\n\n"
            f"Mã OTP xác minh email của bạn trên FinAI là: {otp_code}\n"
            f"Mã có hiệu lực trong vòng 15 phút.\n"
            f"Sau khi xác minh, tài khoản của bạn sẽ nhận được các thông báo và cảnh báo tài chính tự động.\n\n"
            f"FinAI Team."
        )
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 520px; margin: 0 auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 16px;">
            <h2 style="color: #2563eb; margin-top: 0;">FinAI - Xác minh Email</h2>
            <p>Vui lòng nhập mã OTP sau để hoàn tất xác minh địa chỉ email của bạn:</p>
            <div style="background: #eff6ff; border: 2px dashed #3b82f6; padding: 18px; text-align: center; border-radius: 12px; margin: 20px 0;">
                <span style="font-size: 28px; font-weight: 800; letter-spacing: 6px; color: #1e40af;">{otp_code}</span>
            </div>
            <p style="color: #64748b; font-size: 13px;">Mã có hiệu lực trong 15 phút. Xác minh email giúp bạn nhận được cảnh báo tức thời khi chi tiêu vượt ngân sách.</p>
        </div>
        """
        return cls._send_email(to_email, subject, text, html)

    @classmethod
    def send_financial_alert(
        cls,
        to_email: str,
        category_name: str,
        budget_amount: float,
        spent_amount: float,
        percentage_used: float,
        status: str,
    ) -> bool:
        is_exceeded = status == "exceeded" or percentage_used >= 100
        alert_title = "VƯỢT HẠN MỨC" if is_exceeded else "CHẠM NGƯỠNG CẢNH BÁO"
        subject = f"[FinAI Cảnh báo tài chính] {alert_title}: Danh mục {category_name}"

        formatted_budget = f"{budget_amount:,.0f} đ"
        formatted_spent = f"{spent_amount:,.0f} đ"

        text = (
            f"CẢNH BÁO TÀI CHÍNH TỪ FINAI\n\n"
            f"Danh mục: {category_name}\n"
            f"Trạng thái: {alert_title} ({percentage_used:.1f}% hạn mức)\n"
            f"- Đã chi tiêu: {formatted_spent}\n"
            f"- Ngân sách đã đặt: {formatted_budget}\n\n"
            f"Khuyến nghị từ FinAI: Bạn nên cân nhắc hạn chế các khoản chi không cấp thiết thuộc danh mục này trong phần còn lại của tháng để đảm bảo an toàn tài chính cá nhân.\n\n"
            f"Truy cập FinAI để quản lý chi tiêu: {settings.FRONTEND_BASE_URL}\n"
        )
        badge_color = "#ef4444" if is_exceeded else "#f59e0b"
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 520px; margin: 0 auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 16px;">
            <div style="display: inline-block; background: {badge_color}; color: white; padding: 4px 12px; border-radius: 100px; font-weight: bold; font-size: 12px; margin-bottom: 12px;">
                {alert_title} ({percentage_used:.1f}%)
            </div>
            <h2 style="color: #1e293b; margin-top: 0;">Cảnh báo ngân sách: {category_name}</h2>
            <p>Hệ thống FinAI phát hiện chi tiêu của bạn trong tháng này đã chạm ngưỡng chú ý:</p>
            <div style="background: #f8fafc; border-radius: 12px; padding: 16px; margin: 16px 0;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <span style="color: #64748b;">Hạn mức đã đặt:</span>
                    <strong>{formatted_budget}</strong>
                </div>
                <div style="display: flex; justify-content: space-between;">
                    <span style="color: #64748b;">Thực tế đã chi:</span>
                    <strong style="color: {badge_color};">{formatted_spent}</strong>
                </div>
            </div>
            <p style="color: #475569; font-size: 14px; line-height: 1.5;">
                💡 <strong>Gợi ý từ trợ lý FinAI:</strong> Bạn nên chủ động kiểm tra lại các khoản chi trong danh mục này để tránh thâm hụt số dư khả dụng của tháng.
            </p>
            <p><a href="{settings.FRONTEND_BASE_URL}/budgets" style="display: inline-block; background: #2563eb; color: white; padding: 10px 20px; border-radius: 8px; text-decoration: none; font-weight: bold;">Xem ngân sách chi tiết</a></p>
        </div>
        """
        return cls._send_email(to_email, subject, text, html)

