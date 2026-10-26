import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { requestPasswordReset, resetPasswordWithOtp } from '../api/authApi';
import AuthLayout, { PasswordField } from '../components/AuthLayout';

const RESEND_COOLDOWN_SECONDS = 60;

const ForgotPassword = () => {
  const navigate = useNavigate();
  const [step, setStep] = useState(1); // 1: Email input, 2: OTP + New Password input
  const [email, setEmail] = useState('');
  const [otpCode, setOtpCode] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [countdown, setCountdown] = useState(0);

  // Countdown timer for resend OTP
  useEffect(() => {
    if (countdown <= 0) return;
    const timer = setInterval(() => {
      setCountdown((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(timer);
  }, [countdown]);

  // Step 1: Send OTP to email
  const handleRequestOtp = async (e) => {
    e?.preventDefault?.();
    const cleanEmail = email.trim().toLowerCase();
    if (!cleanEmail) {
      setError('Vui lòng nhập địa chỉ email.');
      return;
    }

    setError('');
    setSuccess('');
    setIsSubmitting(true);

    try {
      const data = await requestPasswordReset(cleanEmail);
      setSuccess(data.message || 'Nếu email tồn tại trong hệ thống, mã xác thực và hướng dẫn đặt lại mật khẩu đã được gửi đến bạn.');
      setStep(2);
      setCountdown(RESEND_COOLDOWN_SECONDS);
    } catch (err) {
      setError(err.response?.data?.detail || 'Không thể gửi yêu cầu đặt lại mật khẩu. Vui lòng thử lại sau.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const goToLogin = (targetEmail) => {
    navigate('/login', {
      state: {
        identifier: targetEmail || email.trim().toLowerCase(),
        successMessage: 'Đặt lại mật khẩu thành công! Vui lòng đăng nhập bằng mật khẩu mới.',
      },
    });
  };

  // Step 2: Confirm OTP & set new password
  const handleResetPassword = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    const cleanEmail = email.trim().toLowerCase();
    const cleanCode = otpCode.trim();
    if (!cleanCode || cleanCode.length < 6) {
      setError('Vui lòng nhập đầy đủ mã xác thực OTP 6 số.');
      return;
    }

    if (newPassword.length < 8) {
      setError('Mật khẩu mới phải có ít nhất 8 ký tự.');
      return;
    }

    if (newPassword !== confirmPassword) {
      setError('Mật khẩu xác nhận không khớp.');
      return;
    }

    setIsSubmitting(true);
    try {
      const data = await resetPasswordWithOtp(cleanEmail, cleanCode, newPassword);
      setSuccess(data.message || 'Đặt lại mật khẩu thành công! Đang chuyển sang màn hình đăng nhập...');
      // Chuyển sang login sau 1.2s hoặc người dùng có thể bấm nút ngay
      setTimeout(() => {
        goToLogin(cleanEmail);
      }, 1200);
    } catch (err) {
      setError(err.response?.data?.detail || 'Mã xác thực không hợp lệ hoặc đã hết hạn.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleBackToStep1 = () => {
    setStep(1);
    setError('');
    setSuccess('');
    setOtpCode('');
  };

  return (
    <AuthLayout
      mode="forgot-password"
      title={step === 1 ? 'Quên mật khẩu?' : 'Xác thực & Tạo mật khẩu mới'}
      subtitle={
        step === 1
          ? 'Nhập email đã đăng ký để nhận mã xác thực OTP 6 chữ số.'
          : `Nhập mã 6 chữ số vừa được gửi đến email ${email} và mật khẩu mới của bạn.`
      }
      error={error}
      success={success}
    >
      {step === 1 ? (
        <form onSubmit={handleRequestOtp} className="auth-form">
          <div className="input-group">
            <label htmlFor="forgot-email">Địa chỉ Email</label>
            <input
              id="forgot-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="name@example.com"
              autoComplete="email"
              required
            />
          </div>
          <button type="submit" className="btn-primary" disabled={isSubmitting}>
            {isSubmitting ? 'Đang gửi mã…' : 'Gửi mã xác thực'}
          </button>
        </form>
      ) : (
        <form onSubmit={handleResetPassword} className="auth-form">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{ fontSize: '0.88rem', color: 'var(--text-muted)' }}>
              Gửi tới: <strong>{email}</strong>
            </span>
            <button
              type="button"
              onClick={handleBackToStep1}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--primary-color)',
                fontSize: '0.85rem',
                cursor: 'pointer',
                textDecoration: 'underline',
              }}
            >
              Đổi email
            </button>
          </div>

          <div
            style={{
              background: '#f8fafc',
              border: '1px solid #e2e8f0',
              borderRadius: '10px',
              padding: '9px 12px',
              fontSize: '0.82rem',
              color: 'var(--text-muted)',
              lineHeight: '1.4',
            }}
          >
            💡 <strong>Lưu ý bảo mật:</strong> Nếu không nhận được mã sau vài phút, vui lòng kiểm tra kỹ chính tả địa chỉ email hoặc hòm thư Rác (Spam).
          </div>

          <div className="input-group">
            <label htmlFor="otp-code">Mã xác thực OTP (6 chữ số)</label>
            <input
              id="otp-code"
              type="text"
              inputMode="numeric"
              maxLength={10}
              value={otpCode}
              onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
              placeholder="VD: 123456"
              style={{ letterSpacing: '4px', fontSize: '1.2rem', textAlign: 'center', fontWeight: 'bold' }}
              required
              disabled={isSubmitting || !!success}
            />
          </div>

          <PasswordField
            id="new-password"
            label="Mật khẩu mới"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            helper="Tối thiểu 8 ký tự"
            autoComplete="new-password"
            disabled={isSubmitting || !!success}
          />

          <PasswordField
            id="confirm-password"
            label="Xác nhận mật khẩu mới"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            autoComplete="new-password"
            disabled={isSubmitting || !!success}
          />

          {success ? (
            <button
              type="button"
              className="btn-primary"
              onClick={() => goToLogin(email.trim().toLowerCase())}
              style={{ marginTop: '8px', padding: '12px' }}
            >
              Đăng nhập ngay với mật khẩu mới →
            </button>
          ) : (
            <button type="submit" className="btn-primary" disabled={isSubmitting}>
              {isSubmitting ? 'Đang cập nhật…' : 'Đặt lại mật khẩu'}
            </button>
          )}

          {!success && (
            <div style={{ textAlign: 'center', marginTop: '12px' }}>
              {countdown > 0 ? (
                <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                  Gửi lại mã sau <strong>{countdown}s</strong>
                </span>
              ) : (
                <button
                  type="button"
                  onClick={handleRequestOtp}
                  disabled={isSubmitting}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'var(--primary-color)',
                    fontSize: '0.88rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                    textDecoration: 'underline',
                  }}
                >
                  Chưa nhận được mã? Gửi lại
                </button>
              )}
            </div>
          )}
        </form>
      )}

      <p className="auth-link">
        <Link to="/login">← Quay lại đăng nhập</Link>
      </p>
    </AuthLayout>
  );
};

export default ForgotPassword;
