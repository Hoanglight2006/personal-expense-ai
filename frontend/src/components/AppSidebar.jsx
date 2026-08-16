import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';

const AppSidebar = ({ user, onLogout }) => {
  const navigate = useNavigate();

  const scrollToPageTop = () => {
    window.scrollTo({ top: 0, left: 0, behavior: 'auto' });
  };

  const handleLogout = () => {
    onLogout();
    navigate('/login');
  };

  return (
    <aside className="app-sidebar">
      <div className="sidebar-top">
        <NavLink to="/" className="sidebar-logo" aria-label="FinAI - Trang chủ" onClick={scrollToPageTop}>
          <img src="/finai-winged-coin-favicon.png" alt="" />
          <span>FinAI</span>
        </NavLink>
        <nav className="sidebar-nav" aria-label="Điều hướng chính">
          <NavLink to="/dashboard" onClick={scrollToPageTop} className={({ isActive }) => isActive ? 'active' : ''}>
            <span className="nav-icon">📊</span>
            <span className="nav-text">Tổng quan</span>
          </NavLink>
          <NavLink to="/transactions" onClick={scrollToPageTop} className={({ isActive }) => isActive ? 'active' : ''}>
            <span className="nav-icon">💸</span>
            <span className="nav-text">Giao dịch</span>
          </NavLink>
          <NavLink to="/statistics" onClick={scrollToPageTop} className={({ isActive }) => isActive ? 'active' : ''}>
            <span className="nav-icon">📈</span>
            <span className="nav-text">Thống kê</span>
          </NavLink>
          <NavLink to="/budgets" onClick={scrollToPageTop} className={({ isActive }) => isActive ? 'active' : ''}>
            <span className="nav-icon">🎯</span>
            <span className="nav-text">Ngân sách</span>
          </NavLink>
          <NavLink to="/categories" onClick={scrollToPageTop} className={({ isActive }) => isActive ? 'active' : ''}>
            <span className="nav-icon">📁</span>
            <span className="nav-text">Danh mục</span>
          </NavLink>
          <NavLink to="/profile" onClick={scrollToPageTop} className={({ isActive }) => `sidebar-profile-link ${isActive ? 'active' : ''}`}>
            <span className="nav-icon">👤</span>
            <span className="nav-text">Hồ sơ</span>
          </NavLink>
        </nav>
      </div>
      <div className="sidebar-bottom">
        <NavLink to="/profile" onClick={scrollToPageTop} className="sidebar-account" aria-label="Mở hồ sơ người dùng">
          <div className="account-avatar">{user?.username?.[0]?.toUpperCase() || 'U'}</div>
          <div className="account-info">
            <span className="account-name" title={user?.username}>{user?.username}</span>
            <span className="account-email" title={user?.email}>{user?.email}</span>
          </div>
        </NavLink>
        <button type="button" className="btn-sidebar-logout" onClick={handleLogout}>
          <span className="nav-icon">🚪</span>
          <span className="nav-text">Đăng xuất</span>
        </button>
      </div>
    </aside>
  );
};

export default AppSidebar;
