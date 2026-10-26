import React, { useState, useEffect } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { getAvatarSrc } from '../utils/avatar';

const AppSidebar = ({ user, onLogout, isOpen = false, onClose }) => {
  const navigate = useNavigate();
  const [avatarLoadFailed, setAvatarLoadFailed] = useState(false);

  useEffect(() => {
    setAvatarLoadFailed(false);
  }, [user?.avatar_url]);

  const scrollToPageTop = () => {
    window.scrollTo({ top: 0, left: 0, behavior: 'auto' });
  };

  const handleNavClick = () => {
    scrollToPageTop();
    if (onClose) onClose();
  };

  const handleLogout = () => {
    if (onClose) onClose();
    onLogout();
    navigate('/login');
  };

  const avatarSrc = getAvatarSrc(user?.avatar_url);
  const isAdmin = user?.role === 'admin';

  return (
    <aside className={`app-sidebar ${isOpen ? 'is-open' : ''}`} aria-label="Thanh điều hướng">
      <div className="sidebar-top">
        <div className="sidebar-header-row">
          <NavLink to={isAdmin ? "/admin/dashboard" : "/dashboard"} className="sidebar-logo" aria-label="FinAI - Trang chủ" onClick={handleNavClick}>
            <img src="/finai-winged-coin-favicon.png" alt="" />
            <span>FinAI{isAdmin && <span className="logo-admin-badge" style={{ fontSize: '11px', background: '#d97706', color: '#fff', padding: '2px 6px', borderRadius: '4px', marginLeft: '6px' }}>ADMIN</span>}</span>
          </NavLink>
          {onClose && (
            <button
              type="button"
              className="btn-sidebar-close"
              onClick={onClose}
              aria-label="Đóng menu"
            >
              ✕
            </button>
          )}
        </div>
        <nav className="sidebar-nav" aria-label="Điều hướng chính">
          {isAdmin ? (
            <>
              <div
                className="sidebar-section-label"
                style={{
                  padding: '8px 16px 4px',
                  fontSize: '11px',
                  fontWeight: 700,
                  color: '#92400e',
                  textTransform: 'uppercase',
                  letterSpacing: '0.06em',
                }}
              >
                Khu vực Quản trị
              </div>
              <NavLink
                to="/admin/dashboard"
                onClick={handleNavClick}
                className={({ isActive }) => (isActive ? 'active' : '')}
              >
                <span className="nav-icon">📊</span>
                <span className="nav-text">Tổng quan hệ thống</span>
              </NavLink>
              <NavLink
                to="/admin/users"
                onClick={handleNavClick}
                className={({ isActive }) => (isActive ? 'active' : '')}
              >
                <span className="nav-icon">👥</span>
                <span className="nav-text">Quản lý người dùng</span>
              </NavLink>
              <NavLink
                to="/profile"
                onClick={handleNavClick}
                className={({ isActive }) => `sidebar-profile-link ${isActive ? 'active' : ''}`}
              >
                <span className="nav-icon">👤</span>
                <span className="nav-text">Hồ sơ Admin</span>
              </NavLink>
            </>
          ) : (
            <>
              <NavLink to="/dashboard" onClick={handleNavClick} className={({ isActive }) => isActive ? 'active' : ''}>
                <span className="nav-icon">📊</span>
                <span className="nav-text">Tổng quan</span>
              </NavLink>
              <NavLink to="/transactions" onClick={handleNavClick} className={({ isActive }) => isActive ? 'active' : ''}>
                <span className="nav-icon">💸</span>
                <span className="nav-text">Giao dịch</span>
              </NavLink>
              <NavLink to="/statistics" onClick={handleNavClick} className={({ isActive }) => isActive ? 'active' : ''}>
                <span className="nav-icon">📈</span>
                <span className="nav-text">Thống kê</span>
              </NavLink>
              <NavLink to="/budgets" onClick={handleNavClick} className={({ isActive }) => isActive ? 'active' : ''}>
                <span className="nav-icon">💳</span>
                <span className="nav-text">Ngân sách</span>
              </NavLink>
              <NavLink to="/saving-goals" onClick={handleNavClick} className={({ isActive }) => isActive ? 'active' : ''}>
                <span className="nav-icon">🎯</span>
                <span className="nav-text">Tiết kiệm</span>
              </NavLink>
              <NavLink to="/categories" onClick={handleNavClick} className={({ isActive }) => isActive ? 'active' : ''}>
                <span className="nav-icon">📁</span>
                <span className="nav-text">Danh mục</span>
              </NavLink>
              <NavLink to="/profile" onClick={handleNavClick} className={({ isActive }) => `sidebar-profile-link ${isActive ? 'active' : ''}`}>
                <span className="nav-icon">👤</span>
                <span className="nav-text">Hồ sơ</span>
              </NavLink>
            </>
          )}
        </nav>
      </div>
      <div className="sidebar-bottom">
        <NavLink to="/profile" onClick={handleNavClick} className="sidebar-account" aria-label="Mở hồ sơ người dùng">
          <div className="account-avatar">
            {avatarSrc && !avatarLoadFailed ? (
              <img
                src={avatarSrc}
                alt={user?.username || 'Avatar'}
                className="sidebar-avatar-img"
                onError={() => setAvatarLoadFailed(true)}
              />
            ) : (
              user?.username?.[0]?.toUpperCase() || 'U'
            )}
          </div>
          <div className="account-info">
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span className="account-name" title={user?.username}>{user?.username}</span>
              {isAdmin && <span className="badge-admin-tag">Admin</span>}
            </div>
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
