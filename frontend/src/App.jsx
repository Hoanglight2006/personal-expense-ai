import React, { useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import ProtectedRoute from './components/ProtectedRoute';
import ForgotPassword from './pages/ForgotPassword';
import ResetPassword from './pages/ResetPassword';
import Categories from './pages/Categories';
import Statistics from './pages/Statistics';
import Transactions from './pages/Transactions';
import TransactionTrash from './pages/TransactionTrash';
import Budgets from './pages/Budgets';
import SavingGoals from './pages/SavingGoals';
import Profile from './pages/Profile';
import AppLayout from './components/AppLayout';

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
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password" element={<ResetPassword />} />
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      
      {/* Protected Layout Routes */}
      <Route
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/statistics" element={<Statistics />} />
        <Route path="/budgets" element={<Budgets />} />
        <Route path="/saving-goals" element={<SavingGoals />} />
        <Route path="/categories" element={<Categories />} />
        <Route path="/profile" element={<Profile />} />
        <Route path="/transactions" element={<Transactions />} />
        <Route path="/transactions/trash" element={<TransactionTrash />} />
      </Route>
    </Routes>
  );
}

export default App;
