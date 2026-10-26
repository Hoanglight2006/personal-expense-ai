import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { createAdminUser } from '../../api/adminApi';
import useModalLock from '../../hooks/useModalLock';
import useBackdropDismiss from '../../hooks/useBackdropDismiss';

const generateRandomPassword = () => {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz';
  const nums = '23456789';
  const specials = '@#$%';
  let pass = '';
  for (let i = 0; i < 4; i++) pass += chars.charAt(Math.floor(Math.random() * chars.length));
  for (let i = 0; i < 3; i++) pass += nums.charAt(Math.floor(Math.random() * nums.length));
  pass += specials.charAt(Math.floor(Math.random() * specials.length));
  return `Pass@${pass}`;
};

const AdminCreateUserModal = ({ isOpen, onClose, onSuccess }) => {
  useModalLock(isOpen, onClose);

  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('user');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Auto reset form on open
  useEffect(() => {
    if (isOpen) {
      setUsername('');
      setEmail('');
      setPassword('');
      setRole('user');
      setShowPassword(false);
      setError(null);
    }
  }, [isOpen]);

  const backdropDismissHandlers = useBackdropDismiss(onClose, loading);

  if (!isOpen) return null;

  const handleGeneratePassword = () => {
    const randomPass = generateRandomPassword();
    setPassword(randomPass);
    setShowPassword(true);
    if (error) setError(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    const cleanUsername = username.trim();
    const cleanEmail = email.trim().toLowerCase();

    if (!cleanUsername || cleanUsername.length < 2) {
      setError('Tên đăng nhập phải có ít nhất 2 ký tự.');
      return;
    }
    if (!cleanEmail || !cleanEmail.includes('@')) {
      setError('Địa chỉ email không hợp lệ.');
      return;
    }
    if (!password || password.length < 6) {
      setError('Mật khẩu khởi tạo phải có ít nhất 6 ký tự.');
      return;
    }

    try {
      setLoading(true);
      const payload = {
        username: cleanUsername,
        email: cleanEmail,
        password: password,
        role: role,
      };
      const created = await createAdminUser(payload);
      onSuccess(created, password);
    } catch (err) {
      const msg = err.response?.data?.detail || 'Không thể cấp tài khoản. Vui lòng thử lại.';
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg));
    } finally {
      setLoading(false);
    }
  };

  return createPortal(
    <div
      className="admin-modal-backdrop"
      {...backdropDismissHandlers}
      role="presentation"
    >
      <div
        className="admin-modal-content"
        style={{ maxWidth: '480px' }}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="create-user-modal-title"
      >
        <div className="admin-modal-header">
          <h3 id="create-user-modal-title">
            ➕ Cấp tài khoản mới
          </h3>
          <p>
            Khởi tạo tài khoản trực tiếp bởi Quản trị viên
          </p>
        </div>

        {error && (
          <div
            style={{
              margin: '16px 0',
              padding: '12px 14px',
              background: '#fee2e2',
              color: '#991b1b',
              borderRadius: '12px',
              fontSize: '0.9rem',
              fontWeight: 600,
            }}
          >
            ⚠️ {error}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ marginTop: '16px' }}>
          <div style={{ marginBottom: '14px' }}>
            <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 700, marginBottom: '6px', color: '#574c43' }}>
              Tên đăng nhập (Username) <span style={{ color: '#dc2626' }}>*</span>
            </label>
            <input
              type="text"
              className="admin-search-input"
              style={{ width: '100%', boxSizing: 'border-box' }}
              placeholder="Ví dụ: nguyenvana"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              disabled={loading}
              required
              autoFocus
            />
          </div>

          <div style={{ marginBottom: '14px' }}>
            <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 700, marginBottom: '6px', color: '#574c43' }}>
              Địa chỉ Email <span style={{ color: '#dc2626' }}>*</span>
            </label>
            <input
              type="email"
              className="admin-search-input"
              style={{ width: '100%', boxSizing: 'border-box' }}
              placeholder="Ví dụ: user@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={loading}
              required
            />
          </div>

          <div style={{ marginBottom: '14px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
              <label style={{ fontSize: '0.85rem', fontWeight: 700, color: '#574c43' }}>
                Mật khẩu khởi tạo <span style={{ color: '#dc2626' }}>*</span>
              </label>
              <button
                type="button"
                onClick={handleGeneratePassword}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#d97706',
                  fontSize: '0.8rem',
                  fontWeight: 700,
                  cursor: 'pointer',
                  padding: 0,
                }}
              >
                🎲 Tạo ngẫu nhiên
              </button>
            </div>
            <div style={{ position: 'relative' }}>
              <input
                type={showPassword ? 'text' : 'password'}
                className="admin-search-input"
                style={{ width: '100%', paddingRight: '40px', boxSizing: 'border-box' }}
                placeholder="Nhập ít nhất 6 ký tự..."
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={loading}
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                style={{
                  position: 'absolute',
                  right: '12px',
                  top: '50%',
                  transform: 'translateY(-50%)',
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  fontSize: '1rem',
                  opacity: 0.6,
                }}
                title={showPassword ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'}
              >
                {showPassword ? '🙈' : '👁️'}
              </button>
            </div>
          </div>

          <div style={{ marginBottom: '20px' }}>
            <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 700, marginBottom: '8px', color: '#574c43' }}>
              Vai trò (Role)
            </label>
            <div style={{ display: 'flex', gap: '12px' }}>
              <label
                style={{
                  flex: 1,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '10px 14px',
                  borderRadius: '12px',
                  border: role === 'user' ? '2px solid #d97706' : '1px solid #e7ded4',
                  background: role === 'user' ? '#fffbeb' : '#fff',
                  cursor: 'pointer',
                  fontWeight: 600,
                  fontSize: '0.9rem',
                }}
              >
                <input
                  type="radio"
                  name="role"
                  value="user"
                  checked={role === 'user'}
                  onChange={() => setRole('user')}
                />
                <span>👤 Người dùng</span>
              </label>

              <label
                style={{
                  flex: 1,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '10px 14px',
                  borderRadius: '12px',
                  border: role === 'admin' ? '2px solid #d97706' : '1px solid #e7ded4',
                  background: role === 'admin' ? '#fffbeb' : '#fff',
                  cursor: 'pointer',
                  fontWeight: 600,
                  fontSize: '0.9rem',
                }}
              >
                <input
                  type="radio"
                  name="role"
                  value="admin"
                  checked={role === 'admin'}
                  onChange={() => setRole('admin')}
                />
                <span>🛡️ Quản trị viên</span>
              </label>
            </div>
            <p style={{ margin: '6px 0 0 0', fontSize: '0.75rem', color: '#817367' }}>
              {role === 'user'
                ? '💡 Người dùng thường sẽ được tự động tạo sẵn 12 danh mục thu/chi mặc định.'
                : '⚠️ Quản trị viên sẽ có toàn quyền truy cập phân hệ Quản lý tài khoản & Giám sát.'}
            </p>
          </div>

          <div className="admin-modal-actions" style={{ marginTop: '24px' }}>
            <button
              type="button"
              className="btn-modal-cancel"
              onClick={onClose}
              disabled={loading}
            >
              Hủy
            </button>
            <button
              type="submit"
              className="btn-modal-submit"
              disabled={loading}
            >
              {loading ? '⏳ Đang khởi tạo...' : 'Xác nhận cấp tài khoản'}
            </button>
          </div>
        </form>
      </div>
    </div>,
    document.body
  );
};

export default React.memo(AdminCreateUserModal);
