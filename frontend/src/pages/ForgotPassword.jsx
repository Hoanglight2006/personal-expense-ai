import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { requestPasswordReset } from '../api/authApi';
import AuthLayout from '../components/AuthLayout';

const ForgotPassword = () => {
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setSuccess('');
    setIsSubmitting(true);
    try {
      const data = await requestPasswordReset(email);
      setSuccess(data.message);
    } catch (err) {
      setError(err.response?.data?.detail || 'Không thể gửi yêu cầu. Vui lòng thử lại.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AuthLayout
      mode="forgot-password"
      title="Đặt lại mật khẩu"
      subtitle="Nhập email đã đăng ký để nhận hướng dẫn đặt lại mật khẩu."
      error={error}
      success={success}
    >
      <form onSubmit={handleSubmit} className="auth-form">
        <div className="input-group">
          <label htmlFor="forgot-email">Email</label>
          <input id="forgot-email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" required />
        </div>
        <button type="submit" className="btn-primary" disabled={isSubmitting}>
          {isSubmitting ? 'Đang gửi…' : 'Gửi yêu cầu'}
        </button>
      </form>
      <p className="auth-link"><Link to="/login">Quay lại đăng nhập</Link></p>
    </AuthLayout>
  );
};

export default ForgotPassword;
