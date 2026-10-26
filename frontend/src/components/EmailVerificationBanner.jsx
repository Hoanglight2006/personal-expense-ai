import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

const EmailVerificationBanner = ({ user }) => {
  const navigate = useNavigate();
  const [dismissed, setDismissed] = useState(false);

  // If user is verified or no user logged in, or user dismissed for this view session
  if (!user || user.is_verified || dismissed) {
    return null;
  }

  const handleGoToVerification = () => {
    navigate('/profile', { state: { scrollToVerify: true } });
  };

  return (
    <div
      className="email-verification-banner"
      style={{
        background: 'linear-gradient(90deg, #fffbeb 0%, #fef3c7 100%)',
        borderBottom: '1px solid #fde68a',
        padding: '10px 20px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '12px',
        color: '#92400e',
        fontSize: '0.9rem',
        fontWeight: 500,
        boxShadow: '0 2px 6px rgba(180, 83, 9, 0.05)',
        position: 'relative',
        zIndex: 30,
      }}
      role="alert"
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flex: '1 1 auto' }}>
        <span style={{ fontSize: '1.2rem', lineHeight: 1 }}>✉️</span>
        <span>
          <strong>Tài khoản chưa xác minh email:</strong> Vui lòng xác minh địa chỉ <u>{user.email}</u> để kích hoạt cảnh báo tài chính & bảo vệ tài khoản của bạn.
        </span>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexShrink: 0 }}>
        <button
          type="button"
          onClick={handleGoToVerification}
          style={{
            background: '#f59e0b',
            color: '#ffffff',
            border: 'none',
            borderRadius: '8px',
            padding: '6px 14px',
            fontSize: '0.85rem',
            fontWeight: 700,
            cursor: 'pointer',
            transition: 'background 0.2s',
          }}
          onMouseEnter={(e) => (e.currentTarget.style.background = '#d97706')}
          onMouseLeave={(e) => (e.currentTarget.style.background = '#f59e0b')}
        >
          Xác minh ngay →
        </button>
        <button
          type="button"
          onClick={() => setDismissed(true)}
          style={{
            background: 'none',
            border: 'none',
            color: '#b45309',
            fontSize: '1rem',
            cursor: 'pointer',
            padding: '4px',
            display: 'flex',
            alignItems: 'center',
          }}
          title="Để sau"
          aria-label="Đóng thông báo"
        >
          ✕
        </button>
      </div>
    </div>
  );
};

export default EmailVerificationBanner;

