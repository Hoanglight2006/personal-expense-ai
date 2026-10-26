import React, { useContext, useState } from 'react';
import { Outlet, NavLink } from 'react-router-dom';
import AppSidebar from './AppSidebar';
import CoinAssistant from './CoinAssistant';
import EmailVerificationBanner from './EmailVerificationBanner';
import MustChangePasswordModal from './MustChangePasswordModal';
import InitialBalanceGuideModal from './InitialBalanceGuideModal';
import { AuthContext } from '../context/auth-context';
import { getAvatarSrc } from '../utils/avatar';

const AppLayout = () => {
  const { user, logout } = useContext(AuthContext);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const toggleMobileMenu = () => setMobileMenuOpen((prev) => !prev);
  const closeMobileMenu = () => setMobileMenuOpen(false);

  const avatarSrc = getAvatarSrc(user?.avatar_url);

  return (
    <div className={`app-layout ${mobileMenuOpen ? 'drawer-open' : ''}`}>
      {/* Mobile Top Header with Left Hamburger Button */}
      <header className="app-mobile-header" aria-label="Thanh công cụ di động">
        <button
          type="button"
          className="btn-hamburger"
          onClick={toggleMobileMenu}
          aria-label={mobileMenuOpen ? 'Đóng menu' : 'Mở menu'}
          aria-expanded={mobileMenuOpen}
        >
          <span className="hamburger-icon">{mobileMenuOpen ? '✕' : '☰'}</span>
        </button>
        <NavLink to={user?.role === 'admin' ? "/admin/dashboard" : "/dashboard"} className="mobile-header-logo" onClick={closeMobileMenu}>
          <img src="/finai-winged-coin-favicon.png" alt="" />
          <span>FinAI</span>
        </NavLink>
        <NavLink to="/profile" className="mobile-header-avatar" onClick={closeMobileMenu} aria-label="Hồ sơ người dùng">
          {avatarSrc ? (
            <img src={avatarSrc} alt={user?.username || 'Avatar'} />
          ) : (
            <span>{user?.username?.[0]?.toUpperCase() || 'U'}</span>
          )}
        </NavLink>
      </header>

      {/* Backdrop overlay for mobile drawer */}
      {mobileMenuOpen && (
        <div
          className="sidebar-backdrop"
          onClick={closeMobileMenu}
          aria-hidden="true"
        />
      )}

      <AppSidebar
        user={user}
        onLogout={logout}
        isOpen={mobileMenuOpen}
        onClose={closeMobileMenu}
      />

      <main className="app-main-content">
        {/* Banner reminding user to verify email (only for regular users, if not verified) */}
        {user?.role !== 'admin' && <EmailVerificationBanner user={user} />}
        <Outlet />
      </main>

      {user?.role !== 'admin' && <CoinAssistant />}

      {/* Enforce password change when flagged by system or admin */}
      <MustChangePasswordModal isOpen={Boolean(user?.must_change_password)} />

      {/* Show initial balance guide once upon first access for non-admin users */}
      <InitialBalanceGuideModal
        isOpen={Boolean(user && !user.has_seen_initial_balance_guide && user.role !== 'admin' && !user.must_change_password)}
      />
    </div>
  );
};

export default AppLayout;
