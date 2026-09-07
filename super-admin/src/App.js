import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useSuperAdminAuth } from './contexts/SuperAdminAuthContext';
import SuperAdminLayout from './components/layout/SuperAdminLayout';
import ErrorBoundary from './components/common/ErrorBoundary';
import LoginPage from './pages/LoginPage';
import Dashboard from './pages/Dashboard';
import Tenants from './pages/Tenants';
import TenantDetail from './pages/TenantDetail';
import Users from './pages/Users';
import Subscriptions from './pages/Subscriptions';
import Plans from './pages/Plans';
import Audit from './pages/Audit';
import Profile from './pages/Profile';
import { useAdminRealtime } from './hooks/useAdminRealtime';

const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading } = useSuperAdminAuth();

  if (loading) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#0f172a',
        color: '#e2e8f0',
        fontSize: '18px',
      }}>
        Chargement...
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return children;
};

function App() {
  useAdminRealtime();
  const { user } = useSuperAdminAuth();

  return (
    <ErrorBoundary fallbackTitle="La console d'administration a rencontré une erreur">
    <Routes>
      <Route path="/login" element={
        user ? <Navigate to="/" replace /> : <LoginPage />
      } />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <SuperAdminLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="tenants" element={<Tenants />} />
        <Route path="tenants/:id" element={<TenantDetail />} />
        <Route path="users" element={<Users />} />
        <Route path="subscriptions" element={<Subscriptions />} />
        <Route path="plans" element={<Plans />} />
        <Route path="audit" element={<Audit />} />
        <Route path="profile" element={<Profile />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
    </ErrorBoundary>
  );
}

export default App;
