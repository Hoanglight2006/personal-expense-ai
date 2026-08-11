import React, { useState } from 'react';
import { Link } from 'react-router-dom';

export const PasswordField = ({ id, label = 'Mật khẩu', value, onChange, helper, autoComplete = 'current-password' }) => {
  const [visible, setVisible] = useState(false);

  return (
    <div className="input-group">
      <div className="label-row">
        <label htmlFor={id}>{label}</label>
        {helper && <span className="input-helper">{helper}</span>}
      </div>
      <div className="password-input">
        <input
          id={id}
          type={visible ? 'text' : 'password'}
          value={value}
          onChange={onChange}
          autoComplete={autoComplete}
          required
        />
        <button
          type="button"
          className="password-toggle"
          onClick={() => setVisible((current) => !current)}
          aria-label={visible ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'}
          aria-pressed={visible}
        >
          {visible ? (
            <svg className="password-toggle-icon" viewBox="0 0 24 24" aria-hidden="true">
              <path d="M3 3l18 18" />
              <path d="M10.7 5.1A10.8 10.8 0 0 1 12 5c5 0 8.5 4 9.7 5.6a2.4 2.4 0 0 1 0 2.8 17 17 0 0 1-2.5 2.8" />
              <path d="M14.1 14.1A3 3 0 0 1 9.9 9.9" />
              <path d="M6.6 6.6a16.7 16.7 0 0 0-4.3 4 2.4 2.4 0 0 0 0 2.8C3.5 15 7 19 12 19a10.6 10.6 0 0 0 4.1-.8" />
            </svg>
          ) : (
            <svg className="password-toggle-icon" viewBox="0 0 24 24" aria-hidden="true">
              <path d="M2.3 10.6C3.5 9 7 5 12 5s8.5 4 9.7 5.6a2.4 2.4 0 0 1 0 2.8C20.5 15 17 19 12 19s-8.5-4-9.7-5.6a2.4 2.4 0 0 1 0-2.8Z" />
              <circle cx="12" cy="12" r="3" />
            </svg>
          )}
        </button>
      </div>
    </div>
  );
};


const AuthLayout = ({ mode, title, subtitle, error, success, children }) => {
  const isLogin = mode === 'login';
  const isAccountPage = mode === 'login' || mode === 'register';
  const errorMessage = formatMessage(error);

  return (
    <main className="auth-container">
      <div className="auth-bg-orb orb-1" aria-hidden="true" />
      <div className="auth-bg-orb orb-2" aria-hidden="true" />
      <section className={`auth-layout auth-layout-${mode}`}>
        <aside className="brand-panel" aria-label="Giới thiệu FinAI">
          <p className="brand-name">FinAI</p>
          <h2>Tài chính cá nhân,<br /><span>thông minh hơn</span> cùng AI.</h2>
          <p className="brand-description">Theo dõi chi tiêu, tự động tối ưu hóa ngân sách và hiểu sâu hơn về thói quen tài chính của bạn nhờ AI.</p>
          <div className="brand-orbit" aria-hidden="true">
            <span className="orbit-dot orbit-dot-one" />
            <span className="orbit-dot orbit-dot-two" />
            <span className="orbit-core" />
          </div>
          <div className="brand-note">
            <span>Trợ lý FinAI</span>
            <strong>Mỗi khoản chi đều có một câu chuyện.</strong>
          </div>
        </aside>

        <div className="auth-card">
          <div className="form-mascot" aria-label="Mascot FinAI">
            <span className="form-mascot-greeting" aria-hidden="true">Xin chào !</span>
            <img className="form-mascot-image" src="/finai-winged-coin-favicon.png" alt="Đồng coin FinAI có cánh" />
          </div>
          <div className="auth-heading">
            <h1>{title}</h1>
            <p>{subtitle}</p>
          </div>

          {errorMessage && <div className="message message-error" role="alert">{errorMessage}</div>}
          {success && <div className="message message-success" role="status">{success}</div>}

          {children}

          {isAccountPage && (
            <p className="auth-link">
              {isLogin ? 'Chưa có tài khoản?' : 'Đã có tài khoản?'}{' '}
              <Link to={isLogin ? '/register' : '/login'}>
                {isLogin ? 'Đăng ký' : 'Đăng nhập'}
              </Link>
            </p>
          )}
        </div>
      </section>
    </main>
  );
};

function formatMessage(value) {
  if (!value) return '';
  if (typeof value === 'string') return value;
  if (Array.isArray(value)) {
    return value.map((item) => formatMessage(item)).filter(Boolean).join(' ');
  }
  if (typeof value === 'object') {
    if (value.msg) return formatMessage(value.msg);
    if (value.message) return formatMessage(value.message);
    return Object.values(value).map((item) => formatMessage(item)).filter(Boolean).join(' ');
  }
  return String(value);
}

export default AuthLayout;
