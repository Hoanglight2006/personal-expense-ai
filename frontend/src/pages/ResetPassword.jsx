import React, { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { resetPassword } from '../api/authApi';
import AuthLayout, { PasswordField } from '../components/AuthLayout';

const ResetPassword = () => {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') || '';
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState(token ? '' : 'Liên kết đặt lại mật khẩu không hợp lệ.');
  const [success, setSuccess] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    if (password !== confirmPassword) {
      setError('Mật khẩu xác nhận không khớp.');
      return;
    }
    setIsSubmitting(true);
    try {
      const data = await resetPassword(token, password);
      setSuccess(data.message);
    } catch (err) {
      setError(err.response?.data?.detail || 'Không thể cập nhật mật khẩu.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AuthLayout
      mode="reset-password"
      title="Tạo mật khẩu mới"
      subtitle="Chọn một mật khẩu mới để tiếp tục sử dụng FinAI."
      error={error}
      success={success}
    >
      <form onSubmit={handleSubmit} className="auth-form">
        <PasswordField id="reset-password" label="Mật khẩu mới" value={password} onChange={(event) => setPassword(event.target.value)} helper="Tối thiểu 8 ký tự" autoComplete="new-password" />
        <PasswordField id="reset-confirm-password" label="Xác nhận mật khẩu" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} autoComplete="new-password" />
        <button type="submit" className="btn-primary" disabled={isSubmitting || !token}>
          {isSubmitting ? 'Đang cập nhật…' : 'Cập nhật mật khẩu'}
        </button>
      </form>
      <p className="auth-link"><Link to="/login">Quay lại đăng nhập</Link></p>
    </AuthLayout>
  );
};

export default ResetPassword;
