import React, { useContext } from 'react';
import { Outlet } from 'react-router-dom';
import AppSidebar from './AppSidebar';
import CoinAssistant from './CoinAssistant';
import { AuthContext } from '../context/auth-context';

const AppLayout = () => {
  const { user, logout } = useContext(AuthContext);

  return (
    <div className="app-layout">
      <AppSidebar user={user} onLogout={logout} />
      <main className="app-main-content">
        <Outlet />
      </main>
      <CoinAssistant />
    </div>
  );
};

export default AppLayout;
