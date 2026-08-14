import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';

const AppSidebar = ({ user, onLogout }) => {
  const navigate = useNavigate();

  const handleLogout = () => {
    onLogout();
    navigate('/login');
  };

  return (
    <aside className="app-sidebar">
      <div className="sidebar-top">
        <NavLink to="/" className="sidebar-logo" aria-label="FinAI - Trang chủ">
          <img src="/finai-winged-coin-favicon.png" alt="" />
          <span>FinAI</span>
        </NavLink>
        <nav className="sidebar-nav" aria-label="Điều hướng chính">
          <NavLink to="/dashboard" className={({ isActive }) => isActive ? 'active' : ''}>
            <span className="nav-icon">📊</span>
            <span className="nav-text">Tổng quan</span>
          </NavLink>
          <NavLink to="/transactions" className={({ isActive }) => isActive ? 'active' : ''}>
            <span className="nav-icon">💸</span>
            <span className="nav-text">Giao dịch</span>
          </NavLink>
          <NavLink to="/statistics" className={({ isActive }) => isActive ? 'active' : ''}>
            <span className="nav-icon">📈</span>
            <span className="nav-text">Thống kê</span>
          </NavLink>
          <NavLink to="/categories" className={({ isActive }) => isActive ? 'active' : ''}>
            <span className="nav-icon">📁</span>
            <span className="nav-text">Danh mục</span>
          </NavLink>
        </nav>
      </div>
      <div className="sidebar-bottom">
        <div className="sidebar-account">
          <div className="account-avatar">{user?.username?.[0]?.toUpperCase() || 'U'}</div>
          <div className="account-info">
            <span className="account-name" title={user?.username}>{user?.username}</span>
            <span className="account-email" title={user?.email}>{user?.email}</span>
          </div>
        </div>
        <button type="button" className="btn-sidebar-logout" onClick={handleLogout}>
          <span className="nav-icon">🚪</span>
          <span className="nav-text">Đăng xuất</span>
        </button>
      </div>
    </aside>
  );
};

export default AppSidebar;
