// src/App.js
import React, { lazy, Suspense, useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import { useAuth, AuthProvider } from './contexts/AuthContext';
import { SyncProvider } from '../../../shared/contexts/SyncContext';
import { useRealtimeSync } from '../../../shared/hooks/useRealtimeSync';
import { authStorage } from '../../../shared/storage/authStorage';
import { canAccessRoute } from '@shared/utils/navPermissions';
import { PATH_PERMISSION_MAP, PATH_MODULE_MAP, ADMIN_PATHS, NAV_ITEMS } from '@shared/navConfig';

// Composants d'authentification
const Login = lazy(() => import('./components/auth/Login'));
const Register = lazy(() => import('./components/auth/Register'));
const RegisterUser = lazy(() => import('./components/auth/RegisterUser'));
const RegisterCompany = lazy(() => import('./components/auth/RegisterCompany'));
const ForgotPassword = lazy(() => import('./components/auth/ForgotPassword'));
const ResetPassword = lazy(() => import('./components/auth/ResetPassword'));
const FirstChangePassword = lazy(() => import('./components/auth/FirstChangePassword'));

// Layouts
import MainLayout from './components/layout/MainLayout';

// Contextes
import { CartProvider } from './contexts/CartContext';
import { NotificationProvider } from './contexts/NotificationContext';
import { LanguageProvider, useTranslation } from './i18n';

// Pages
const Home = lazy(() => import('./pages/Home'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Products = lazy(() => import('./pages/Products'));
const Clients = lazy(() => import('./pages/Clients'));
const Sales = lazy(() => import('./pages/Sales'));
const Inventory = lazy(() => import('./pages/Inventory'));
const Suppliers = lazy(() => import('./pages/Suppliers'));
const Invoices = lazy(() => import('./pages/Invoices'));
const Payments = lazy(() => import('./pages/Payments'));
const AI = lazy(() => import('./pages/AI'));
const Documentation = lazy(() => import('./pages/Documentation'));
const Checkout = lazy(() => import('./pages/Checkout'));
const OrderTracking = lazy(() => import('./pages/OrderTracking'));
const SuperAdmin = lazy(() => import('./pages/SuperAdmin'));
const SuperAdminProfile = lazy(() => import('./pages/SuperAdminProfile'));
const Profile = lazy(() => import('./pages/Profile'));
const Cart = lazy(() => import('./pages/Cart'));
const ProductDetail = lazy(() => import('./pages/ProductDetail'));
const Subscription = lazy(() => import('./pages/Subscription'));
const PaymentSettings = lazy(() => import('./pages/PaymentSettings'));
const Catalogue = lazy(() => import('./pages/Catalogue'));
const Suivi = lazy(() => import('./pages/Suivi'));
const Contact = lazy(() => import('./pages/Contact'));
const UserOrders = lazy(() => import('./pages/UserOrders'));
const Delivery = lazy(() => import('./pages/Delivery'));
const HR = lazy(() => import('./pages/HR'));
const Accounting = lazy(() => import('./pages/Accounting'));
const Documents = lazy(() => import('./pages/Documents'));
const Purchases = lazy(() => import('./pages/Purchases'));
const Users = lazy(() => import('./pages/Users'));
const Roles = lazy(() => import('./pages/Roles'));
const Permissions = lazy(() => import('./pages/Permissions'));

// Composant de protection utilisant AuthContext.
// PATH_MODULE_MAP, PATH_PERMISSION_MAP, ADMIN_PATHS et la logique
// de fallback par rôle sont importés depuis shared/navConfig + navPermissions
// pour garantir une source unique de vérité.

const roleFallbackForPath = (pathname) => {
  const item = NAV_ITEMS.find((i) => i.path === pathname);
  return Array.isArray(item?.roleFallback) ? item.roleFallback : null;
};

// Écran d'accès refusé explicite (audit P1 ordre 3) : remplace toute
// redirection silencieuse vers /dashboard par un message 403 exploitable
// (permission manquante + module du plan). Aucune donnée n'est exposée.
const AccessDenied = ({ pathname }) => {
  const { t } = useTranslation();
  const required = PATH_PERMISSION_MAP[pathname] || [];
  const module = PATH_MODULE_MAP[pathname] || null;
  return (
    <div className="page-container">
      <div className="card full-width" role="alert" style={{ textAlign: 'center', padding: '48px' }}>
        <p className="stat-label">403 — Accès refusé</p>
        <h1 style={{ margin: '8px 0 12px' }}>{t('accessDenied.title', undefined, 'Module non accessible')}</h1>
        <p className="text-muted" style={{ maxWidth: '560px', margin: '0 auto 12px' }}>
          {t(
            'accessDenied.body',
            { path: pathname, module: module || '—', permissions: required.join(', ') || '—' },
            `La page ${pathname} nécessite ${
              module ? `le module « ${module} » de votre abonnement` : 'une autorisation'
            }${required.length ? ` et la permission (${required.join(', ')})` : ''}. ` +
              `Contactez votre administrateur ou changez d'abonnement. Aucune redirection silencieuse n'a eu lieu.`
          )}
        </p>
        <div style={{ display: 'flex', gap: '10px', justifyContent: 'center', flexWrap: 'wrap', marginTop: '12px' }}>
          <a className="btn-primary" href="/dashboard">Retour au tableau de bord</a>
          <a className="btn-secondary" href="/subscription">Voir mon abonnement</a>
        </div>
      </div>
    </div>
  );
};

const ProtectedRoute = ({ children }) => {
  const {
    isAuthenticated,
    loading,
    user,
    mustChangePassword,
    subscription,
    subscriptionLoading,
    getAllowedModules,
    hasAnyPermission,
    hasPermission,
    hasRole,
  } = useAuth();
  const location = useLocation();
  const { t } = useTranslation();

  const hasToken = !!authStorage.getAccessToken();
  const shouldAllow = isAuthenticated || hasToken;

  if (loading) {
    return <div>{t('common.loading')}</div>;
  }

  if (!shouldAllow) {
    return <Navigate to="/login" replace />;
  }

  // Si l'utilisateur doit changer son mot de passe, on le force vers l'écran
  // de changement obligatoire (sauf s'il est déjà sur cet écran).
  if (mustChangePassword && location.pathname !== '/first-change-password') {
    return <Navigate to="/first-change-password" replace />;
  }

  const role = (user?.role || '').toLowerCase();
  if (role === 'user' && !user?.tenant_id) {
    return <Navigate to="/" replace />;
  }

  const isSuperAdmin = role === 'super_admin';
  if (isSuperAdmin) {
    return children;
  }

  const isSubscriptionPage = location.pathname === '/subscription';
  const hasActiveSubscription = subscription &&
    (subscription.statut === 'actif' || subscription.statut === 'ACTIF' || subscription.statut === 'ACTIVE');

  const isAdminPath = ADMIN_PATHS.includes(location.pathname);

  if (!isAdminPath && !isSubscriptionPage && !subscriptionLoading && !hasActiveSubscription) {
    return <Navigate to="/subscription" replace />;
  }

  // Garde de permission explicite : acces direct par URL (cas 7 RBAC).
  // Source unique : shared/utils/navPermissions.js::canAccessRoute.
  if (user && Array.isArray(user.permissions)) {
    const ctx = {
      isSuperAdmin,
      hasAnyPermission,
      hasPermission,
      hasRole,
      allowedModules: getAllowedModules(),
      roleFallbackFor: roleFallbackForPath,
    };
    const ok = canAccessRoute(location.pathname, PATH_PERMISSION_MAP, ctx, {
      pathModuleMap: PATH_MODULE_MAP,
      skipModuleGatePaths: ADMIN_PATHS,
    });
    if (!ok) {
      // P1-3 : jamais de retour muet au dashboard — écran 403 explicite.
      return <AccessDenied pathname={location.pathname} />;
    }
  }

  return children;
};

// Modale « limite de plan » — libellés traduits via i18n (design inchangé).
const PlanLimitModal = ({ message, onClose }) => {
  const { t } = useTranslation();
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{t('planLimit.title')}</h2>
          <button onClick={onClose} className="btn-close">×</button>
        </div>
        <div className="modal-body">
          <p>{message}</p>
        </div>
        <div className="modal-footer">
          <button
            type="button"
            onClick={() => { onClose(); window.location.href = '/subscription'; }}
            className="btn-primary"
          >
            {t('planLimit.change')}
          </button>
          <button
            type="button"
            onClick={onClose}
            className="btn-secondary"
          >
            {t('planLimit.close')}
          </button>
        </div>
      </div>
    </div>
  );
};

function App() {
  // useRealtimeSync();
  const [planLimitModal, setPlanLimitModal] = useState({ open: false, message: '' });

  useEffect(() => {
    const handler = (e) => {
      setPlanLimitModal({ open: true, message: e.detail?.message || 'Limite du plan atteinte' });
    };
    window.addEventListener('plan-limit-reached', handler);
    return () => window.removeEventListener('plan-limit-reached', handler);
  }, []);

  return (
    <LanguageProvider>
      <SyncProvider>
        <NotificationProvider>
          <CartProvider>
            <BrowserRouter>
              <div className="app">
              <Suspense fallback={<div className="page-loading" role="status" aria-live="polite">Chargement…</div>}>
                <Routes>
                <Route path="/" element={<Home />} />
                <Route path="/login" element={<Login />} />
                <Route path="/register" element={<Register />} />
                <Route path="/register/simple" element={<RegisterUser />} />
                <Route path="/register/company" element={<RegisterCompany />} />
                <Route path="/forgot-password" element={<ForgotPassword />} />
                <Route path="/reset-password/:token" element={<ResetPassword />} />
                <Route path="/first-change-password" element={<FirstChangePassword />} />
                <Route path="/first-login-change" element={<FirstChangePassword />} />

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
                  <Route path="payment-settings" element={<PaymentSettings />} />
                  <Route path="delivery" element={<Delivery />} />
                  <Route path="hr" element={<HR />} />
                  <Route path="accounting" element={<Accounting />} />
                  <Route path="documents" element={<Documents />} />
                  <Route path="purchases" element={<Purchases />} />
                  <Route path="super-admin" element={<SuperAdmin />} />
                  <Route path="super-admin/profile" element={<SuperAdminProfile />} />
                  <Route path="profile" element={<Profile />} />
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
              </Suspense>
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
                <PlanLimitModal
                  message={planLimitModal.message}
                  onClose={() => setPlanLimitModal({ open: false, message: '' })}
                />
              )}
            </div>
          </BrowserRouter>
        </CartProvider>
      </NotificationProvider>
        </SyncProvider>
    </LanguageProvider>
);
}

export default App;
