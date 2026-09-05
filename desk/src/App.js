// src/App.js
import React, { Suspense, useState, useEffect } from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

import { useTheme } from './hooks/useTheme';
import { useAuth } from './contexts/AuthContext';
import { SyncProvider } from '../../shared/contexts/SyncContext';
import { useRealtimeSync } from '../../shared/hooks/useRealtimeSync';
import { DesktopProvider } from './contexts/DesktopContext';
import { CartProvider } from './contexts/CartContext';
import { NotificationProvider } from './contexts/NotificationContext';
import { authStorage } from '../../shared/storage/authStorage';
import { canAccessRoute } from '@shared/utils/navPermissions';
import { PATH_PERMISSION_MAP, PATH_MODULE_MAP, ADMIN_PATHS, NAV_ITEMS } from '@shared/navConfig';

// Layout
import DesktopLayout from './components/layout/DesktopLayout';

// Error boundary (évite l'écran blanc en cas d'erreur React)
import ErrorBoundary from './components/common/ErrorBoundary';

// Boutique connectee (pages protegees par ProtectedRoute)
const Cart = React.lazy(() => import('./pages/Cart'));
const Checkout = React.lazy(() => import('./pages/Checkout'));
const OrderTracking = React.lazy(() => import('./pages/OrderTracking'));
const UserOrders = React.lazy(() => import('./pages/UserOrders'));

// Pages protÃ©gÃ©es
const Dashboard = React.lazy(() => import('./pages/Dashboard'));
const Products = React.lazy(() => import('./pages/Products'));
const Clients = React.lazy(() => import('./pages/Clients'));
const Sales = React.lazy(() => import('./pages/Sales'));
const Invoices = React.lazy(() => import('./pages/Invoices'));
const Payments = React.lazy(() => import('./pages/Payments'));
const Inventory = React.lazy(() => import('./pages/Inventory'));
const Suppliers = React.lazy(() => import('./pages/Suppliers'));
const Purchases = React.lazy(() => import('./pages/Purchases'));
const Delivery = React.lazy(() => import('./pages/Delivery'));
const HR = React.lazy(() => import('./pages/HR'));
const Accounting = React.lazy(() => import('./pages/Accounting'));
const Documents = React.lazy(() => import('./pages/Documents'));
const AI = React.lazy(() => import('./pages/AI'));
const Subscription = React.lazy(() => import('./pages/Subscription'));
const SuperAdmin = React.lazy(() => import('./pages/SuperAdmin'));
const SuperAdminProfile = React.lazy(() => import('./pages/SuperAdminProfile'));
const Roles = React.lazy(() => import('./pages/Roles'));
const Permissions = React.lazy(() => import('./pages/Permissions'));
const Users = React.lazy(() => import('./pages/Users'));

// Authentification
const Login = React.lazy(() => import('./components/auth/Login'));
const Register = React.lazy(() => import('./components/auth/Register'));
const RegisterUser = React.lazy(() => import('./components/auth/RegisterUser'));
const RegisterCompany = React.lazy(() => import('./components/auth/RegisterCompany'));
const ForgotPassword = React.lazy(() => import('./components/auth/ForgotPassword'));
const ResetPassword = React.lazy(() => import('./components/auth/ResetPassword'));
const FirstChangePassword = React.lazy(() => import('./components/auth/FirstChangePassword'));

const AuthSuspense = ({ children }) => (
  <Suspense fallback={<div className="auth-loading">Chargementâ€¦</div>}>
    {children}
  </Suspense>
);

const PageSuspense = ({ children }) => (
  <Suspense fallback={<div className="page-loading">Chargementâ€¦</div>}>
    {children}
  </Suspense>
);

// Routes boutique accessibles aux utilisateurs simples connectÃ©s
const STOREFRONT_PREFIXES = ['/cart', '/checkout', '/order-tracking', '/mes-commandes'];

// Source unique pour les maps de permissions/modules/chemins admin :
// importees depuis shared/navConfig. La definition locale a ete supprimee
// pour eviter toute divergence avec la sidebar / le backend.

const roleFallbackForPath = (pathname) => {
  const item = NAV_ITEMS.find((i) => i.path === pathname);
  return Array.isArray(item?.roleFallback) ? item.roleFallback : null;
};

const ProtectedRoute = ({ children }) => {
  const {
    isAuthenticated,
    loading,
    user,
    mustChangePassword,
    subscription,
    getAllowedModules,
    hasAnyPermission,
    hasPermission,
    hasRole,
  } = useAuth();
  const location = useLocation();

  const hasToken = !!authStorage.getAccessToken();
  const shouldAllow = isAuthenticated || hasToken;

  if (loading) {
    return <div className="loading-screen">Chargementâ€¦</div>;
  }

  if (!shouldAllow) {
    return <Navigate to="/login" replace />;
  }

  // Si l'utilisateur doit changer son mot de passe, on le force vers l'ecran
  // de changement obligatoire (sauf s'il est deja sur cet ecran).
  if (mustChangePassword && location.pathname !== '/first-change-password') {
    return <Navigate to="/first-change-password" replace />;
  }

  const role = (user?.role || '').toLowerCase();

  const isStorefront = STOREFRONT_PREFIXES.some(
    (p) => location.pathname === p || location.pathname.startsWith(`${p}/`)
  );

  // Les utilisateurs simples accèdent à la boutique connectée, pas aux modules ERP.
  // Ils sont redirigés vers leurs commandes au lieu d'une page d'accueil.
  if (role === 'user') {
    if (isStorefront) {
      return children;
    }
    return <Navigate to="/mes-commandes" replace />;
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

  // Garde de permission explicite : acces direct par URL (cas 7 RBAC).
  // Source unique : shared/utils/navPermissions.js::canAccessRoute.
  if (user && Array.isArray(user.permissions)) {
    const ctx = {
      isSuperAdmin: role === 'super_admin',
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
      return <Navigate to="/dashboard" replace />;
    }
  }

  return children;
};

const RequireRole = ({ children, role }) => {
  const { hasRole } = useAuth();
  const requiredRoles = Array.isArray(role) ? role : [role];
  const allowed = requiredRoles.some((r) => hasRole(r));
  if (!allowed) {
    return <Navigate to="/dashboard" replace />;
  }
  return children;
};

const App = () => {
  useRealtimeSync();
  const { logout } = useAuth();
  // Gestion centralisÃ©e du thÃ¨me : synchronise la classe `.dark` sur <html>,
  // persiste dans localStorage et met Ã  jour le meta theme-color.
  const [darkMode, toggleDarkMode] = useTheme();
  const [planLimitModal, setPlanLimitModal] = useState({ open: false, message: '' });

  const handleLogout = async () => {
    try {
      await logout();
    } catch {
      // ignore
    }
    window.location.hash = '/login';
  };

  useEffect(() => {
    const handler = (e) => {
      setPlanLimitModal({ open: true, message: e.detail?.message || 'Limite du plan atteinte' });
    };
    window.addEventListener('plan-limit-reached', handler);
    return () => window.removeEventListener('plan-limit-reached', handler);
  }, []);

  return (
    <ErrorBoundary>
      <SyncProvider>
        <DesktopProvider>
          <NotificationProvider>
            <CartProvider>
              <Routes>
               {/* Point d'entree : forcer l'authentification */}
              <Route path="/" element={<Navigate to="/login" replace />} />

              {/* Authentification */}
              <Route path="/login" element={<AuthSuspense><Login darkMode={darkMode} onToggleDarkMode={toggleDarkMode} /></AuthSuspense>} />
              <Route path="/register" element={<AuthSuspense><Register /></AuthSuspense>} />
              <Route path="/register/simple" element={<AuthSuspense><RegisterUser darkMode={darkMode} onToggleDarkMode={toggleDarkMode} /></AuthSuspense>} />
              <Route path="/register/company" element={<AuthSuspense><RegisterCompany darkMode={darkMode} onToggleDarkMode={toggleDarkMode} /></AuthSuspense>} />
              <Route path="/forgot-password" element={<AuthSuspense><ForgotPassword darkMode={darkMode} onToggleDarkMode={toggleDarkMode} /></AuthSuspense>} />
              <Route path="/reset-password/:token" element={<AuthSuspense><ResetPassword darkMode={darkMode} onToggleDarkMode={toggleDarkMode} /></AuthSuspense>} />
                            <Route path="/first-change-password" element={<AuthSuspense><FirstChangePassword darkMode={darkMode} onToggleDarkMode={toggleDarkMode} /></AuthSuspense>} />
              <Route path="/first-login-change" element={<AuthSuspense><FirstChangePassword darkMode={darkMode} onToggleDarkMode={toggleDarkMode} /></AuthSuspense>} />

             {/* Espace protÃ©gÃ© (layout desktop) â€” inclut la boutique connectÃ©e */}
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
                <Route path="dashboard" element={<PageSuspense><Dashboard /></PageSuspense>} />
                <Route path="products" element={<PageSuspense><Products /></PageSuspense>} />
                <Route path="clients" element={<PageSuspense><Clients /></PageSuspense>} />
                <Route path="sales" element={<PageSuspense><Sales /></PageSuspense>} />
                <Route path="invoices" element={<PageSuspense><Invoices /></PageSuspense>} />
                <Route path="payments" element={<PageSuspense><Payments /></PageSuspense>} />
                <Route path="inventory" element={<PageSuspense><Inventory /></PageSuspense>} />
                <Route path="suppliers" element={<PageSuspense><Suppliers /></PageSuspense>} />
                <Route path="purchases" element={<PageSuspense><Purchases /></PageSuspense>} />
                <Route path="delivery" element={<PageSuspense><Delivery /></PageSuspense>} />
                <Route path="hr" element={<PageSuspense><HR /></PageSuspense>} />
                <Route path="accounting" element={<PageSuspense><Accounting /></PageSuspense>} />
                <Route path="documents" element={<PageSuspense><Documents /></PageSuspense>} />
                <Route path="ai" element={<PageSuspense><AI /></PageSuspense>} />
                <Route path="subscription" element={<PageSuspense><Subscription /></PageSuspense>} />
                <Route path="super-admin" element={<PageSuspense><SuperAdmin /></PageSuspense>} />
                <Route path="super-admin/profile" element={<PageSuspense><SuperAdminProfile /></PageSuspense>} />
                <Route path="roles" element={<RequireRole role={['SUPER_ADMIN', 'ADMIN']}><PageSuspense><Roles /></PageSuspense></RequireRole>} />
                <Route path="permissions" element={<RequireRole role={['SUPER_ADMIN', 'ADMIN']}><PageSuspense><Permissions /></PageSuspense></RequireRole>} />
                <Route path="users" element={<RequireRole role={['SUPER_ADMIN', 'ADMIN']}><PageSuspense><Users /></PageSuspense></RequireRole>} />

                {/* Boutique connectÃ©e (utilisateurs simples + autres rÃ´les) */}
                <Route path="cart" element={<PageSuspense><Cart /></PageSuspense>} />
                <Route path="checkout" element={<PageSuspense><Checkout /></PageSuspense>} />
                <Route path="order-tracking/:ref" element={<PageSuspense><OrderTracking /></PageSuspense>} />
                <Route path="mes-commandes" element={<PageSuspense><UserOrders /></PageSuspense>} />
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
              theme={darkMode ? "dark" : "light"}
            />

            {planLimitModal.open && (
              <div className="modal-overlay" onClick={() => setPlanLimitModal({ open: false, message: '' })}>
                <div className="modal" onClick={(e) => e.stopPropagation()}>
                  <div className="modal-header">
                    <h2>Limite du plan atteinte</h2>
                    <button onClick={() => setPlanLimitModal({ open: false, message: '' })} className="btn-close">Ã—</button>
                  </div>
                  <div className="modal-body">
                    <p>{planLimitModal.message}</p>
                  </div>
                  <div className="modal-footer">
                    <button
                      type="button"
                      onClick={() => { setPlanLimitModal({ open: false, message: '' }); window.location.hash = '/subscription'; }}
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
          </CartProvider>
        </NotificationProvider>
      </DesktopProvider>
    </SyncProvider>
    </ErrorBoundary>
  );
};

export default App;
