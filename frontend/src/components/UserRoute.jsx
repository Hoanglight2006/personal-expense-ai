import React, { useContext } from 'react';
import { Navigate } from 'react-router-dom';
import { AuthContext } from '../context/auth-context';

const UserRoute = ({ children }) => {
  const { user, loading } = useContext(AuthContext);

  if (loading) {
    return <div className="loading" style={{ padding: '2rem', textAlign: 'center' }}>Đang tải...</div>;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (user.role === 'admin') {
    return <Navigate to="/admin/dashboard" replace />;
  }

  return children;
};

export default UserRoute;

