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
    <section id="verify-email-section" className="profile-panel" style={{ marginTop: '24px' }}>
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
        <div>
          <h2>Xác thực địa chỉ Email</h2>
          <p>Nhận báo cáo tổng quan & cảnh báo chi tiêu vượt ngưỡng trực tiếp qua email của bạn.</p>
        </div>
      </div>

      {user.is_verified ? (
        <div
          style={{
            background: 'rgba(16, 185, 129, 0.08)',
            border: '1px solid rgba(16, 185, 129, 0.25)',
            borderRadius: '16px',
            padding: '20px 24px',
            display: 'flex',
            alignItems: 'center',
            gap: '16px',
          }}
        >
          <div
            style={{
              width: '44px',
              height: '44px',
              borderRadius: '50%',
              background: '#10b981',
              color: '#ffffff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '22px',
              flexShrink: 0,
            }}
          >
            ✓
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <strong style={{ fontSize: '1rem', color: '#065f46' }}>Email đã được xác thực an toàn</strong>
              <span
                style={{
                  background: '#d1fae5',
                  color: '#047857',
                  padding: '2px 8px',
                  borderRadius: '12px',
                  fontSize: '0.75rem',
                  fontWeight: 700,
                }}
              >
                {user.email}
              </span>
            </div>
            <p style={{ margin: 0, fontSize: '0.88rem', color: '#047857', lineHeight: 1.5 }}>
              Tài khoản đã kích hoạt nhận thông báo tài chính và cảnh báo thông minh qua email khi có khoản chi tiêu vượt mức kế hoạch.
            </p>
          </div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div
            style={{
              background: 'rgba(245, 158, 11, 0.08)',
              border: '1px solid rgba(245, 158, 11, 0.25)',
              borderRadius: '16px',
              padding: '18px 22px',
              display: 'flex',
              alignItems: 'flex-start',
              gap: '14px',
            }}
          >
            <span style={{ fontSize: '24px', lineHeight: 1 }}>⚠️</span>
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                <strong style={{ fontSize: '0.96rem', color: '#92400e' }}>Chưa xác minh địa chỉ:</strong>
                <span
                  style={{
                    background: '#fef3c7',
                    color: '#92400e',
                    padding: '2px 8px',
                    borderRadius: '12px',
                    fontSize: '0.8rem',
                    fontWeight: 700,
                  }}
                >
                  {user.email}
                </span>
              </div>
              <p style={{ margin: 0, fontSize: '0.86rem', color: '#b45309', lineHeight: 1.5 }}>
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
            <div
              style={{
                padding: '10px 14px',
                borderRadius: '10px',
                background: '#ecfdf5',
                border: '1px solid #6ee7b7',
                color: '#065f46',
                fontWeight: 600,
                fontSize: '0.88rem',
              }}
              role="status"
            >
              ✨ {success}
            </div>
          )}

          {!codeSent ? (
            <div>
              <button
                type="button"
                className="btn-primary"
                onClick={handleSendCode}
                disabled={sending}
                style={{ padding: '10px 20px', borderRadius: '12px' }}
              >
                {sending ? 'Đang gửi mã…' : '✉️ Gửi mã OTP xác nhận'}
              </button>
            </div>
          ) : (
            <form onSubmit={handleVerify} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div className="input-group" style={{ margin: 0 }}>
                <label htmlFor="verify-email-otp" style={{ fontSize: '0.88rem', fontWeight: 600 }}>
                  Nhập mã OTP 6 số đã gửi tới {user.email}
                </label>
                <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                  <input
                    id="verify-email-otp"
                    type="text"
                    inputMode="numeric"
                    maxLength={6}
                    value={code}
                    onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                    placeholder="VD: 123456"
                    style={{
                      maxWidth: '180px',
                      padding: '10px 14px',
                      fontSize: '1.2rem',
                      fontWeight: 700,
                      letterSpacing: '4px',
                      textAlign: 'center',
                      borderRadius: '12px',
                      border: '1px solid var(--border-color)',
                    }}
                    required
                  />
                  <button
                    type="submit"
                    className="btn-primary"
                    disabled={verifying || code.length < 6}
                    style={{ padding: '10px 20px', borderRadius: '12px' }}
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

