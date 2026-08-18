// src/App.js
import React, { useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

import { useAuth } from './contexts/AuthContext';
import { DesktopProvider } from './contexts/DesktopContext';

// Authentification
import Login from './components/auth/Login';
import Register from './components/auth/Register';
import RegisterUser from './components/auth/RegisterUser';
import RegisterCompany from './components/auth/RegisterCompany';
import ForgotPassword from './components/auth/ForgotPassword';
import ResetPassword from './components/auth/ResetPassword';

// Layout desktop
import DesktopLayout from './components/layout/DesktopLayout';

// Pages protégées
import Dashboard from './pages/Dashboard';
import Products from './pages/Products';
import Clients from './pages/Clients';
import Sales from './pages/Sales';
import Invoices from './pages/Invoices';
import Payments from './pages/Payments';
import Inventory from './pages/Inventory';
import Suppliers from './pages/Suppliers';
import Purchases from './pages/Purchases';
import Delivery from './pages/Delivery';
import HR from './pages/HR';
import Accounting from './pages/Accounting';
import Documents from './pages/Documents';
import AI from './pages/AI';
import Subscription from './pages/Subscription';
import SuperAdmin from './pages/SuperAdmin';
import SuperAdminProfile from './pages/SuperAdminProfile';
import Roles from './pages/Roles';
import Permissions from './pages/Permissions';
import Users from './pages/Users';

// Protection des routes (cohérent avec le comportement web/AuthContext).
const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading, user, subscription } = useAuth();
  const location = useLocation();

  const hasToken = !!localStorage.getItem('access_token');
  const shouldAllow = isAuthenticated || hasToken;

  if (loading) {
    return <div className="loading-screen">Chargement…</div>;
  }

  if (!shouldAllow) {
    return <Navigate to="/login" replace />;
  }

  const role = (user?.role || '').toLowerCase();
  if (role === 'user') {
    return <Navigate to="/" replace />;
  }

  if (role === 'super_admin') {
    return children;
  }

  const isSubscriptionPage = location.pathname === '/subscription';
  const hasActiveSubscription = subscription &&
    (subscription.statut === 'actif' || subscription.statut === 'ACTIF' || subscription.statut === 'ACTIVE');

  if (!isSubscriptionPage && !hasActiveSubscription) {
    return <Navigate to="/subscription" replace />;
  }

  return children;
};

const App = () => {
  const [darkMode, setDarkMode] = useState(() => {
    try {
      return localStorage.getItem('dark_mode') === 'true';
    } catch {
      return false;
    }
  });

  const toggleDarkMode = (next) => {
    setDarkMode(next);
    try {
      localStorage.setItem('dark_mode', String(next));
    } catch {
      // ignore
    }
  };

  const handleLogout = () => {
    try {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('user');
      localStorage.removeItem('tenant');
      localStorage.removeItem('subscription');
    } catch {
      // ignore
    }
    window.location.href = '/';
  };

  return (
    <DesktopProvider>
      <Routes>
        {/* Routes publiques */}
        <Route path="/" element={<Navigate to="/login" replace />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/register/simple" element={<RegisterUser />} />
        <Route path="/register/company" element={<RegisterCompany />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password/:token" element={<ResetPassword />} />

        {/* Espace protégé (layout desktop) */}
        <Route
          element={(
            <ProtectedRoute>
              <DesktopLayout
                darkMode={darkMode}
                onToggleDarkMode={toggleDarkMode}
                onLogout={handleLogout}
              />
            </ProtectedRoute>
          )}
        >
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="products" element={<Products />} />
          <Route path="clients" element={<Clients />} />
          <Route path="sales" element={<Sales />} />
          <Route path="invoices" element={<Invoices />} />
          <Route path="payments" element={<Payments />} />
          <Route path="inventory" element={<Inventory />} />
          <Route path="suppliers" element={<Suppliers />} />
          <Route path="purchases" element={<Purchases />} />
          <Route path="delivery" element={<Delivery />} />
          <Route path="hr" element={<HR />} />
          <Route path="accounting" element={<Accounting />} />
          <Route path="documents" element={<Documents />} />
          <Route path="ai" element={<AI />} />
          <Route path="subscription" element={<Subscription />} />
          <Route path="super-admin" element={<SuperAdmin />} />
          <Route path="super-admin/profile" element={<SuperAdminProfile />} />
        </Route>

        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>

      <ToastContainer
        position="top-right"
        autoClose={5000}
        hideProgressBar={false}
        newestOnTop
        closeOnClick
        rtl={false}
        pauseOnFocusLoss
        draggable
        pauseOnHover
        theme="light"
      />
    </DesktopProvider>
  );
};

export default App;
