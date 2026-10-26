import React, { useState, useContext } from 'react';
import { createPortal } from 'react-dom';
import { changePassword } from '../api/authApi';
import { AuthContext } from '../context/auth-context';
import { useModalLock } from '../hooks/useModalLock';

const MustChangePasswordModal = ({ isOpen }) => {
  const { setUser } = useContext(AuthContext);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPasswords, setShowPasswords] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Lock scroll when open. Note: modal cannot be closed by Esc/backdrop because password change is mandatory.
  useModalLock(isOpen, () => {});

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (!currentPassword) {
      setError('Vui lòng nhập mật khẩu hiện tại (mật khẩu tạm do hệ thống cấp).');
      return;
    }

    if (newPassword.length < 8) {
      setError('Mật khẩu mới phải có tối thiểu 8 ký tự.');
      return;
    }

    if (newPassword === currentPassword) {
      setError('Mật khẩu mới phải khác với mật khẩu hiện tại.');
      return;
    }

    if (newPassword !== confirmPassword) {
      setError('Mật khẩu xác nhận không khớp.');
      return;
    }

    setLoading(true);
    try {
      const res = await changePassword(currentPassword, newPassword);
      setSuccess(res.message || 'Đổi mật khẩu thành công! Đang chuyển vào ứng dụng...');
      setTimeout(() => {
        setUser((prev) => (prev ? { ...prev, must_change_password: false, is_verified: true } : null));
      }, 350);
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'Không thể cập nhật mật khẩu. Vui lòng kiểm tra lại mật khẩu hiện tại.');
    } finally {
      setLoading(false);
    }
  };

  return createPortal(
    <div
      className="modal-backdrop"
      style={{
        zIndex: 9999,
        background: 'rgba(28, 22, 15, 0.65)',
      }}
      role="presentation"
    >
      <div
        className="category-modal"
        style={{
          maxWidth: '460px',
          padding: '32px 28px',
          borderRadius: '24px',
          boxShadow: '0 20px 45px -10px rgba(45, 34, 18, 0.28)',
          background: '#fffdfa',
          willChange: 'transform, opacity',
        }}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="must-change-password-title"
      >
        <div style={{ textAlign: 'center', marginBottom: '20px' }}>
          <div
            style={{
              width: '64px',
              height: '64px',
              margin: '0 auto 12px',
              background: 'rgba(243, 205, 98, 0.25)',
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '32px',
            }}
          >
            🔐
          </div>
          <h2
            id="must-change-password-title"
            style={{
              fontSize: '1.45rem',
              fontWeight: 800,
              color: 'var(--text-color, #2b2319)',
              marginBottom: '6px',
            }}
          >
            Thiết lập mật khẩu mới
          </h2>
          <p
            style={{
              fontSize: '0.9rem',
              color: 'var(--text-muted, #7c7267)',
              lineHeight: 1.5,
            }}
          >
            Tài khoản của bạn vừa được cấp mới hoặc đặt lại bởi Quản trị viên. Vui lòng đổi mật khẩu để bảo vệ tài khoản và tiếp tục.
          </p>
        </div>

        {error && (
          <div
            className="error-message"
            style={{
              marginBottom: '16px',
              padding: '10px 14px',
              borderRadius: '10px',
              fontSize: '0.88rem',
            }}
            role="alert"
          >
            ⚠️ {error}
          </div>
        )}

        {success && (
          <div
            style={{
              marginBottom: '16px',
              padding: '10px 14px',
              borderRadius: '10px',
              background: '#ecfdf5',
              border: '1px solid #6ee7b7',
              color: '#065f46',
              fontWeight: 600,
              fontSize: '0.88rem',
              textAlign: 'center',
            }}
            role="status"
          >
            ✨ {success}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div className="input-group" style={{ margin: 0 }}>
            <label
              htmlFor="must-change-curr"
              style={{ fontSize: '0.88rem', fontWeight: 600, color: 'var(--text-color)' }}
            >
              Mật khẩu tạm thời
            </label>
            <input
              id="must-change-curr"
              type={showPasswords ? 'text' : 'password'}
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              placeholder="Nhập mật khẩu được gửi qua email"
              autoComplete="current-password"
              autoFocus
              required
              disabled={loading || !!success}
              style={{
                padding: '10px 14px',
                borderRadius: '12px',
                border: '1px solid var(--border-color, #e5dfd3)',
                fontSize: '0.95rem',
                outline: 'none',
              }}
            />
          </div>

          <div className="input-group" style={{ margin: 0 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <label
                htmlFor="must-change-new"
                style={{ fontSize: '0.88rem', fontWeight: 600, color: 'var(--text-color)' }}
              >
                Mật khẩu mới
              </label>
              <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Tối thiểu 8 ký tự</span>
            </div>
            <input
              id="must-change-new"
              type={showPasswords ? 'text' : 'password'}
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="Tối thiểu 8 ký tự"
              autoComplete="new-password"
              required
              disabled={loading || !!success}
              style={{
                padding: '10px 14px',
                borderRadius: '12px',
                border: '1px solid var(--border-color, #e5dfd3)',
                fontSize: '0.95rem',
                outline: 'none',
              }}
            />
          </div>

          <div className="input-group" style={{ margin: 0 }}>
            <label
              htmlFor="must-change-confirm"
              style={{ fontSize: '0.88rem', fontWeight: 600, color: 'var(--text-color)' }}
            >
              Xác nhận mật khẩu mới
            </label>
            <input
              id="must-change-confirm"
              type={showPasswords ? 'text' : 'password'}
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Nhập lại mật khẩu mới"
              autoComplete="new-password"
              required
              disabled={loading || !!success}
              style={{
                padding: '10px 14px',
                borderRadius: '12px',
                border: '1px solid var(--border-color, #e5dfd3)',
                fontSize: '0.95rem',
                outline: 'none',
              }}
            />
          </div>

          <label
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              fontSize: '0.84rem',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              userSelect: 'none',
            }}
          >
            <input
              type="checkbox"
              checked={showPasswords}
              onChange={(e) => setShowPasswords(e.target.checked)}
              style={{ cursor: 'pointer' }}
            />
            Hiển thị mật khẩu
          </label>

          <button
            type="submit"
            className="btn-primary"
            disabled={loading || !!success}
            style={{
              marginTop: '8px',
              padding: '12px',
              borderRadius: '12px',
              fontSize: '1rem',
              fontWeight: 700,
            }}
          >
            {loading ? 'Đang cập nhật…' : 'Cập nhật & Bắt đầu sử dụng'}
          </button>
        </form>
      </div>
    </div>,
    document.body
  );
};

export default React.memo(MustChangePasswordModal);
