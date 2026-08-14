import React, { useState, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { registerUser, loginUser, getMe } from '../api/authApi';
import { AuthContext } from '../context/auth-context';
import AuthLayout, { PasswordField } from '../components/AuthLayout';

const Register = () => {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { login, setUser } = useContext(AuthContext);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    if (password !== confirmPassword) {
      setError('Mật khẩu xác nhận không khớp.');
      return;
    }
    setIsSubmitting(true);
    try {
      await registerUser(username, email, password);
      // Auto login after registration
      const loginData = await loginUser(username, password);
      login(loginData.access_token);
      const userData = await getMe();
      setUser(userData);
      setSuccess("Đăng ký thành công! Đang chuyển đến bảng điều khiển...");
      setTimeout(() => {
        navigate('/', { state: { openInitialBalance: true } });
      }, 800);
    } catch (err) {
      if (err.response && err.response.data && err.response.data.detail) {
        setError(err.response.data.detail);
      } else {
        setError("Đăng ký thất bại. Vui lòng thử lại.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AuthLayout
      mode="register"
      title="Đăng ký tài khoản"
      subtitle="Bắt đầu xây dựng thói quen tài chính tốt hơn."
      error={error}
      success={success}
    >
      <form onSubmit={handleSubmit} className="auth-form">
        <div className="input-group">
          <label htmlFor="register-username">Tên đăng nhập</label>
          <input id="register-username" type="text" value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required />
        </div>
        <div className="input-group">
          <label htmlFor="register-email">Email</label>
          <input id="register-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" required />
        </div>
        <PasswordField
          id="register-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          helper="Tối thiểu 8 ký tự"
          autoComplete="new-password"
        />
        <PasswordField
          id="register-confirm-password"
          label="Xác nhận mật khẩu"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          autoComplete="new-password"
        />
        <button type="submit" className="btn-primary" disabled={isSubmitting}>
          {isSubmitting ? 'Đang tạo tài khoản…' : 'Đăng ký'}
        </button>
      </form>
    </AuthLayout>
  );
};

export default Register;
