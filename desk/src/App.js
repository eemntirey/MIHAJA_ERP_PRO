// src/App.js
import React, { Suspense } from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

import { useTheme } from './hooks/useTheme';
import { useAuth } from './contexts/AuthContext';
import { AuthProvider } from './contexts/AuthContext';
import { SyncProvider } from '../../shared/contexts/SyncContext';
import { DesktopProvider } from './contexts/DesktopContext';
import { CartProvider } from './contexts/CartContext';
import { authStorage } from '../../shared/storage/authStorage';

// Layout
import DesktopLayout from './components/layout/DesktopLayout';
import LandingLayout from './components/landing/LandingLayout';

// Pages publiques
const Catalogue = React.lazy(() => import('./pages/Catalogue'));
const Suivi = React.lazy(() => import('./pages/Suivi'));
const Contact = React.lazy(() => import('./pages/Contact'));
const Documentation = React.lazy(() => import('./pages/Documentation'));
const ProductDetail = React.lazy(() => import('./pages/ProductDetail'));
const Cart = React.lazy(() => import('./pages/Cart'));
const Checkout = React.lazy(() => import('./pages/Checkout'));
const OrderTracking = React.lazy(() => import('./pages/OrderTracking'));
const UserOrders = React.lazy(() => import('./pages/UserOrders'));

// Pages protégées
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

const AuthSuspense = ({ children }) => (
  <Suspense fallback={<div className="auth-loading">Chargement…</div>}>
    {children}
  </Suspense>
);

const PageSuspense = ({ children }) => (
  <Suspense fallback={<div className="page-loading">Chargement…</div>}>
    {children}
  </Suspense>
);

// Routes boutique accessibles aux utilisateurs simples connectés
const STOREFRONT_PREFIXES = ['/cart', '/checkout', '/order-tracking', '/mes-commandes'];

// Protection des routes
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

const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading, user, subscription, getAllowedModules } = useAuth();
  const location = useLocation();

  const hasToken = !!authStorage.getAccessToken();
  const shouldAllow = isAuthenticated || hasToken;

  if (loading) {
    return <div className="loading-screen">Chargement…</div>;
  }

  if (!shouldAllow) {
    return <Navigate to="/login" replace />;
  }

  const role = (user?.role || '').toLowerCase();

  const isStorefront = STOREFRONT_PREFIXES.some(
    (p) => location.pathname === p || location.pathname.startsWith(`${p}/`)
  );

  // Les utilisateurs simples accèdent à la boutique connectée, pas aux modules ERP.
  // Ils sont redirigés vers le catalogue (ou leurs commandes) au lieu d'une page d'accueil.
  if (role === 'user') {
    if (isStorefront) {
      return children;
    }
    return <Navigate to="/catalogue" replace />;
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

  const allowedModules = getAllowedModules();
  const requiredModule = PATH_MODULE_MAP[location.pathname];

  if (requiredModule && allowedModules !== null && !allowedModules.includes(requiredModule)) {
    return <Navigate to="/dashboard" replace />;
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
  // Gestion centralisée du thème : synchronise la classe `.dark` sur <html>,
  // persiste dans localStorage et met à jour le meta theme-color.
  const [darkMode, toggleDarkMode] = useTheme();

  const handleLogout = () => {
    try {
      authStorage.clear();
    } catch {
      // ignore
    }
    // HashRouter : naviguer via hash évite le rechargement complet en Electron (file://)
    window.location.hash = '/login';
  };


  return (
    <SyncProvider>
      <AuthProvider>
        <DesktopProvider>
          <CartProvider>
            <Routes>
               {/* Pages publiques (vitrine) avec LandingLayout */}
              <Route element={<LandingLayout darkMode={darkMode} onToggleDarkMode={toggleDarkMode} />}>
                  <Route path="/" element={<Navigate to="/catalogue" replace />} />
                  <Route path="/catalogue" element={<PageSuspense><Catalogue /></PageSuspense>} />
                 <Route path="/suivi" element={<PageSuspense><Suivi /></PageSuspense>} />
                 <Route path="/contact" element={<PageSuspense><Contact /></PageSuspense>} />
                 <Route path="/documentation" element={<PageSuspense><Documentation /></PageSuspense>} />
                 <Route path="/produits/:id" element={<PageSuspense><ProductDetail /></PageSuspense>} />
               </Route>

              {/* Authentification */}
              <Route path="/login" element={<AuthSuspense><Login darkMode={darkMode} onToggleDarkMode={toggleDarkMode} /></AuthSuspense>} />
              <Route path="/register" element={<AuthSuspense><Register /></AuthSuspense>} />
              <Route path="/register/simple" element={<AuthSuspense><RegisterUser darkMode={darkMode} onToggleDarkMode={toggleDarkMode} /></AuthSuspense>} />
              <Route path="/register/company" element={<AuthSuspense><RegisterCompany darkMode={darkMode} onToggleDarkMode={toggleDarkMode} /></AuthSuspense>} />
              <Route path="/forgot-password" element={<AuthSuspense><ForgotPassword darkMode={darkMode} onToggleDarkMode={toggleDarkMode} /></AuthSuspense>} />
              <Route path="/reset-password/:token" element={<AuthSuspense><ResetPassword darkMode={darkMode} onToggleDarkMode={toggleDarkMode} /></AuthSuspense>} />

             {/* Espace protégé (layout desktop) — inclut la boutique connectée */}
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

               {/* Boutique connectée (utilisateurs simples + autres rôles) */}
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
         </CartProvider>
       </DesktopProvider>
     </AuthProvider>
   </SyncProvider>
  );
};

export default App;
