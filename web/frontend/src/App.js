// src/App.js
import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import { useAuth } from './contexts/AuthContext';
import { SyncProvider } from '../../../shared/contexts/SyncContext';
import { useRealtimeSync } from '../../../shared/hooks/useRealtimeSync';
import { authStorage } from '../../../shared/storage/authStorage';

// Composants d'authentification
import Login from './components/auth/Login';
import Register from './components/auth/Register';
import RegisterUser from './components/auth/RegisterUser';
import RegisterCompany from './components/auth/RegisterCompany';
import ForgotPassword from './components/auth/ForgotPassword';
import ResetPassword from './components/auth/ResetPassword';

// Layouts
import MainLayout from './components/layout/MainLayout';

// Contextes
import { CartProvider } from './contexts/CartContext';
import { NotificationProvider } from './contexts/NotificationContext';

// Pages
import Home from './pages/Home';
import Dashboard from './pages/Dashboard';
import Products from './pages/Products';
import Clients from './pages/Clients';
import Sales from './pages/Sales';
import Inventory from './pages/Inventory';
import Suppliers from './pages/Suppliers';
import Invoices from './pages/Invoices';
import Payments from './pages/Payments';
import AI from './pages/AI';
import Documentation from './pages/Documentation';
import Checkout from './pages/Checkout';
import OrderTracking from './pages/OrderTracking';
import SuperAdmin from './pages/SuperAdmin';
import SuperAdminProfile from './pages/SuperAdminProfile';
import Cart from './pages/Cart';
import ProductDetail from './pages/ProductDetail';
import Subscription from './pages/Subscription';
import Catalogue from './pages/Catalogue';
import Suivi from './pages/Suivi';
import Contact from './pages/Contact';
import UserOrders from './pages/UserOrders';
import Delivery from './pages/Delivery';
import HR from './pages/HR';
import Accounting from './pages/Accounting';
import Documents from './pages/Documents';
import Purchases from './pages/Purchases';
import Users from './pages/Users';
import Roles from './pages/Roles';
import Permissions from './pages/Permissions';

// Composant de protection utilisant AuthContext
const PATH_MODULE_MAP = {
  '/dashboard': 'dashboard',
  '/products': 'produits',
  '/clients': 'clients',
  '/sales': 'ventes',
  '/invoices': 'factures',
  '/payments': 'paiements',
  '/inventory': 'stocks',
  '/suppliers': null,
  '/purchases': 'achats',
  '/delivery': 'livraison',
  '/hr': 'rh',
  '/accounting': 'comptabilite',
  '/documents': 'documents',
  '/ai': 'ia',
  '/super-admin': null,
  '/users': null,
  '/roles': null,
  '/permissions': null,
};

const ADMIN_PATHS = ['/super-admin', '/users', '/roles', '/permissions'];

const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading, user, subscription, subscriptionLoading, getAllowedModules } = useAuth();
  const location = useLocation();

  const hasToken = !!authStorage.getAccessToken();
  const shouldAllow = isAuthenticated || hasToken;

  if (loading) {
    return <div>Chargement...</div>;
  }

  if (!shouldAllow) {
    return <Navigate to="/login" replace />;
  }

  const role = (user?.role || '').toLowerCase();
  if (role === 'user' && !user?.tenant_id) {
    return <Navigate to="/" replace />;
  }

  if (role === 'super_admin') {
    return children;
  }

  const isSubscriptionPage = location.pathname === '/subscription';
  const hasActiveSubscription = subscription && 
    (subscription.statut === 'actif' || subscription.statut === 'ACTIF' || subscription.statut === 'ACTIVE');

  const isAdminPath = ADMIN_PATHS.includes(location.pathname);

  if (!isAdminPath && !isSubscriptionPage && !subscriptionLoading && !hasActiveSubscription) {
    return <Navigate to="/subscription" replace />;
  }

  if (!isAdminPath) {
    const allowedModules = getAllowedModules();
    const requiredModule = PATH_MODULE_MAP[location.pathname];

    if (requiredModule && allowedModules !== null && !allowedModules.includes(requiredModule)) {
      return <Navigate to="/dashboard" replace />;
    }
  }

  return children;
};

function App() {
  useRealtimeSync();
  const [planLimitModal, setPlanLimitModal] = useState({ open: false, message: '' });

  useEffect(() => {
    const handler = (e) => {
      setPlanLimitModal({ open: true, message: e.detail?.message || 'Limite du plan atteinte' });
    };
    window.addEventListener('plan-limit-reached', handler);
    return () => window.removeEventListener('plan-limit-reached', handler);
  }, []);

  return (
    <SyncProvider>
      <NotificationProvider>
          <CartProvider>
            <BrowserRouter>
              <div className="app">
              <Routes>
                <Route path="/" element={<Home />} />
                <Route path="/login" element={<Login />} />
                <Route path="/register" element={<Register />} />
                <Route path="/register/simple" element={<RegisterUser />} />
                <Route path="/register/company" element={<RegisterCompany />} />
                <Route path="/forgot-password" element={<ForgotPassword />} />
                <Route path="/reset-password/:token" element={<ResetPassword />} />

                <Route
                  element={
                    <ProtectedRoute>
                      <MainLayout />
                    </ProtectedRoute>
                  }
                >
                  <Route path="dashboard" element={<Dashboard />} />
                  <Route path="products" element={<Products />} />
                  <Route path="clients" element={<Clients />} />
                  <Route path="sales" element={<Sales />} />
                  <Route path="inventory" element={<Inventory />} />
                  <Route path="suppliers" element={<Suppliers />} />
                  <Route path="invoices" element={<Invoices />} />
                  <Route path="payments" element={<Payments />} />
                  <Route path="ai" element={<AI />} />
                  <Route path="documentation" element={<Documentation />} />
                  <Route path="subscription" element={<Subscription />} />
                  <Route path="delivery" element={<Delivery />} />
                  <Route path="hr" element={<HR />} />
                  <Route path="accounting" element={<Accounting />} />
                  <Route path="documents" element={<Documents />} />
                  <Route path="purchases" element={<Purchases />} />
                  <Route path="super-admin" element={<SuperAdmin />} />
                  <Route path="super-admin/profile" element={<SuperAdminProfile />} />
                  <Route path="users" element={<Users />} />
                  <Route path="roles" element={<Roles />} />
                  <Route path="permissions" element={<Permissions />} />
                </Route>

                <Route path="/checkout" element={<Checkout />} />
                <Route path="/order-tracking/:ref" element={<OrderTracking />} />

                <Route path="/cart" element={<Cart />} />
                <Route path="/produits/:id" element={<ProductDetail />} />

                <Route path="/catalogue" element={<Catalogue />} />
                <Route path="/suivi" element={<Suivi />} />
                <Route path="/contact" element={<Contact />} />
                <Route path="/mes-commandes" element={<UserOrders />} />

                <Route path="*" element={<Navigate to="/" replace />} />
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

              {planLimitModal.open && (
                <div className="modal-overlay" onClick={() => setPlanLimitModal({ open: false, message: '' })}>
                  <div className="modal" onClick={(e) => e.stopPropagation()}>
                    <div className="modal-header">
                      <h2>Limite du plan atteinte</h2>
                      <button onClick={() => setPlanLimitModal({ open: false, message: '' })} className="btn-close">×</button>
                    </div>
                    <div className="modal-body">
                      <p>{planLimitModal.message}</p>
                    </div>
                    <div className="modal-footer">
                      <button
                        type="button"
                        onClick={() => { setPlanLimitModal({ open: false, message: '' }); window.location.href = '/subscription'; }}
                        className="btn-primary"
                      >
                        Modifier mon abonnement
                      </button>
                      <button
                        type="button"
                        onClick={() => { setPlanLimitModal({ open: false, message: '' }); }}
                        className="btn-secondary"
                      >
                        Fermer
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </BrowserRouter>
        </CartProvider>
      </NotificationProvider>
    </SyncProvider>
);
}

export default App;
