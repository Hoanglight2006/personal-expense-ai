import React, { useState, useContext, useEffect } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { loginUser, getMe } from '../api/authApi';
import { AuthContext } from '../context/auth-context';
import AuthLayout, { PasswordField } from '../components/AuthLayout';

const Login = () => {
  const location = useLocation();
  const [identifier, setIdentifier] = useState(location.state?.identifier || '');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(location.state?.successMessage || '');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { login, setUser } = useContext(AuthContext);
  const navigate = useNavigate();

  useEffect(() => {
    if (location.state?.identifier) {
      setIdentifier(location.state.identifier);
    }
    if (location.state?.successMessage) {
      setSuccess(location.state.successMessage);
    }
  }, [location.state]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    const cleanIdentifier = identifier.trim();
    if (!cleanIdentifier) {
      setError('Vui lòng nhập Tên đăng nhập hoặc Email.');
      return;
    }

    setIsSubmitting(true);
    try {
      const data = await loginUser(cleanIdentifier, password);
      login(data.access_token);
      const userData = await getMe();
      setUser(userData);
      navigate('/');
    } catch (err) {
      if (err.response && err.response.data && err.response.data.detail) {
        setError(err.response.data.detail);
      } else {
        setError('Đăng nhập thất bại. Vui lòng thử lại.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AuthLayout
      mode="login"
      title="Chào mừng trở lại"
      subtitle="Đăng nhập để tiếp tục cùng FinAI."
      error={error}
      success={success}
    >
      <form onSubmit={handleSubmit} className="auth-form">
        <div className="input-group">
          <label htmlFor="login-username">Tên đăng nhập hoặc Email</label>
          <input
            id="login-username"
            type="text"
            value={identifier}
            onChange={(e) => {
              setIdentifier(e.target.value);
              if (success) setSuccess('');
            }}
            placeholder="VD: letaman101@gmail.com hoặc username"
            autoComplete="username"
            required
          />
        </div>
        <PasswordField
          id="login-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="current-password"
        />
        <div className="login-options">
          <Link className="forgot-link" to="/forgot-password">
            Quên mật khẩu?
          </Link>
        </div>
        <button type="submit" className="btn-primary" disabled={isSubmitting}>
          {isSubmitting ? 'Đang đăng nhập…' : 'Đăng nhập'}
        </button>
      </form>
    </AuthLayout>
  );
};

export default Login;
