import React, { useState, useEffect, useContext } from 'react';
import { sendVerificationEmail, verifyEmail } from '../api/authApi';
import { AuthContext } from '../context/auth-context';

const RESEND_COOLDOWN_SECONDS = 60;

const EmailVerificationSection = () => {
  const { user, setUser } = useContext(AuthContext);
  const [code, setCode] = useState('');
  const [sending, setSending] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [codeSent, setCodeSent] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Countdown timer for OTP resend
  useEffect(() => {
    if (countdown <= 0) return;
    const timer = setInterval(() => {
      setCountdown((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(timer);
  }, [countdown]);

  if (!user) return null;

  const handleSendCode = async () => {
    setError('');
    setSuccess('');
    setSending(true);
    try {
      const res = await sendVerificationEmail();
      setCodeSent(true);
      setCountdown(RESEND_COOLDOWN_SECONDS);
      setSuccess(res.message || `Đã gửi mã xác minh 6 số tới ${user.email}.`);
    } catch (err) {
      setError(err.response?.data?.detail || 'Không thể gửi email xác thực. Vui lòng thử lại sau.');
    } finally {
      setSending(false);
    }
  };

  const handleVerify = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    const cleanCode = code.trim();
    if (!cleanCode || cleanCode.length < 6) {
      setError('Vui lòng nhập đầy đủ mã OTP 6 chữ số.');
      return;
    }

    setVerifying(true);
    try {
      const updatedUser = await verifyEmail(cleanCode);
      setUser(updatedUser);
      setCodeSent(false);
      setCode('');
      setSuccess('🎉 Xác minh email thành công! Bạn đã sẵn sàng nhận cảnh báo tài chính.');
    } catch (err) {
      setError(err.response?.data?.detail || 'Mã xác thực không chính xác hoặc đã hết hạn.');
    } finally {
      setVerifying(false);
    }
  };

  return (
    <section id="verify-email-section" className="profile-panel profile-verify-panel">
      <div className="profile-panel-heading">
        <span
          className="profile-panel-icon"
          style={{
            background: user.is_verified ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)',
            color: user.is_verified ? '#059669' : '#d97706',
          }}
        >
          {user.is_verified ? '🛡️' : '✉️'}
        </span>
        <div className="profile-panel-heading-text">
          <h2>Xác thực địa chỉ Email</h2>
          <p>Nhận báo cáo tổng quan & cảnh báo chi tiêu vượt ngưỡng trực tiếp qua email của bạn.</p>
        </div>
      </div>

      {user.is_verified ? (
        <div className="email-verify-box email-verify-box-success">
          <div className="email-verify-icon-wrap" aria-hidden="true">
            ✓
          </div>
          <div className="email-verify-content">
            <strong className="email-verify-title">Email đã được xác thực an toàn</strong>
            <div className="email-verify-badge-row">
              <span className="email-verify-address-tag">
                {user.email}
              </span>
            </div>
            <p className="email-verify-desc">
              Tài khoản đã kích hoạt nhận thông báo tài chính và cảnh báo thông minh qua email khi có khoản chi tiêu vượt mức kế hoạch.
            </p>
          </div>
        </div>
      ) : (
        <div className="email-verify-unverified-wrap">
          <div className="email-verify-box email-verify-box-warning">
            <span className="email-verify-warning-icon" aria-hidden="true">⚠️</span>
            <div className="email-verify-content">
              <strong className="email-verify-title email-verify-title-warning">Chưa xác minh địa chỉ email</strong>
              <div className="email-verify-badge-row">
                <span className="email-verify-address-tag email-verify-address-tag-warning">
                  {user.email}
                </span>
              </div>
              <p className="email-verify-desc email-verify-desc-warning">
                Để nhận được cảnh báo tự động khi sắp hết ngân sách hoặc tài khoản có biến động bất thường, vui lòng xác minh email của bạn ngay hôm nay.
              </p>
            </div>
          </div>

          {error && (
            <div className="error-message" style={{ margin: 0 }} role="alert">
              ⚠️ {error}
            </div>
          )}

          {success && (
            <div className="email-verify-feedback-success" role="status">
              ✨ {success}
            </div>
          )}

          {!codeSent ? (
            <div>
              <button
                type="button"
                className="btn-primary email-verify-send-btn"
                onClick={handleSendCode}
                disabled={sending}
              >
                {sending ? 'Đang gửi mã…' : '✉️ Gửi mã OTP xác nhận'}
              </button>
            </div>
          ) : (
            <form onSubmit={handleVerify} className="email-verify-form">
              <div className="input-group" style={{ margin: 0 }}>
                <label htmlFor="verify-email-otp" style={{ fontSize: '0.88rem', fontWeight: 600 }}>
                  Nhập mã OTP 6 số đã gửi tới {user.email}
                </label>
                <div className="email-verify-otp-row">
                  <input
                    id="verify-email-otp"
                    type="text"
                    inputMode="numeric"
                    maxLength={6}
                    value={code}
                    onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                    placeholder="VD: 123456"
                    className="email-verify-otp-input"
                    required
                  />
                  <button
                    type="submit"
                    className="btn-primary email-verify-btn"
                    disabled={verifying || code.length < 6}
                  >
                    {verifying ? 'Đang xác thực…' : 'Xác minh'}
                  </button>
                </div>
              </div>

              <div>
                {countdown > 0 ? (
                  <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                    Gửi lại mã xác minh sau <strong>{countdown}s</strong>
                  </span>
                ) : (
                  <button
                    type="button"
                    onClick={handleSendCode}
                    disabled={sending}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: 'var(--primary-color)',
                      fontSize: '0.88rem',
                      fontWeight: 600,
                      cursor: 'pointer',
                      textDecoration: 'underline',
                      padding: 0,
                    }}
                  >
                    Chưa nhận được mã? Gửi lại mã mới
                  </button>
                )}
              </div>
            </form>
          )}
        </div>
      )}
    </section>
  );
};

export default EmailVerificationSection;

