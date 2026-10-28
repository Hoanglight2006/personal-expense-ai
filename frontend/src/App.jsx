import React, { useEffect, useContext } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import ProtectedRoute from './components/ProtectedRoute';
import AdminRoute from './components/AdminRoute';
import UserRoute from './components/UserRoute';
import AppLayout from './components/AppLayout';
import { AuthContext } from './context/auth-context';
import ErrorBoundary from './components/ErrorBoundary';

import Login from './pages/Login';
import Register from './pages/Register';
import ForgotPassword from './pages/ForgotPassword';
import ResetPassword from './pages/ResetPassword';
import Dashboard from './pages/Dashboard';
import Statistics from './pages/Statistics';
import Categories from './pages/Categories';
import Budgets from './pages/Budgets';
import SavingGoals from './pages/SavingGoals';
import Profile from './pages/Profile';
import Transactions from './pages/Transactions';
import TransactionTrash from './pages/TransactionTrash';
import AdminDashboard from './pages/admin/AdminDashboard';
import AdminUsers from './pages/admin/AdminUsers';

const RootRedirect = () => {
  const { user, loading } = useContext(AuthContext);
  if (loading) {
    return <div className="loading" style={{ padding: '2rem', textAlign: 'center' }}>Đang tải...</div>;
  }
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  return <Navigate to={user.role === 'admin' ? '/admin/dashboard' : '/dashboard'} replace />;
};

function App() {
  // Prevent number inputs from changing values when scrolling the mouse wheel
  useEffect(() => {
    const handleWheel = () => {
      if (document.activeElement && document.activeElement.type === 'number') {
        document.activeElement.blur();
      }
    };
    window.addEventListener('wheel', handleWheel, { passive: true });
    return () => window.removeEventListener('wheel', handleWheel);
  }, []);

  return (
    <ErrorBoundary>
      <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password" element={<ResetPassword />} />
      <Route path="/" element={<RootRedirect />} />
      
      {/* Protected Layout Routes */}
      <Route
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        {/* User-only Financial Routes (Zero-Knowledge Privacy: Admin cannot access) */}
        <Route
          path="/dashboard"
          element={
            <UserRoute>
              <Dashboard />
            </UserRoute>
          }
        />
        <Route
          path="/statistics"
          element={
            <UserRoute>
              <Statistics />
            </UserRoute>
          }
        />
        <Route
          path="/budgets"
          element={
            <UserRoute>
              <Budgets />
            </UserRoute>
          }
        />
        <Route
          path="/saving-goals"
          element={
            <UserRoute>
              <SavingGoals />
            </UserRoute>
          }
        />
        <Route
          path="/categories"
          element={
            <UserRoute>
              <Categories />
            </UserRoute>
          }
        />
        <Route
          path="/transactions"
          element={
            <UserRoute>
              <Transactions />
            </UserRoute>
          }
        />
        <Route
          path="/transactions/trash"
          element={
            <UserRoute>
              <TransactionTrash />
            </UserRoute>
          }
        />

        {/* Profile is accessible to both User and Admin */}
        <Route path="/profile" element={<Profile />} />

        {/* Admin-only Routes */}
        <Route
          path="/admin/dashboard"
          element={
            <AdminRoute>
              <AdminDashboard />
            </AdminRoute>
          }
        />
        <Route
          path="/admin/users"
          element={
            <AdminRoute>
              <AdminUsers />
            </AdminRoute>
          }
        />
      </Route>

      {/* Fallback */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
    </ErrorBoundary>
  );
}

export default App;
