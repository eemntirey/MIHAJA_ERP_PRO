import React, { useState, useEffect } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { useNotifications } from '../../contexts/NotificationContext';
import DashboardRail from './DashboardRail';
import DarkModeToggle from './DarkModeToggle';
import ChatInput from './ChatInput';
import DesktopLayout from './DesktopLayout';
import { useMediaQuery } from '../../hooks/useMediaQuery';
import { authService, saleService, stockService, factureService, dashboardService } from '../../services/api';
import { toast } from 'react-toastify';
import './MainLayout.css';
import './DashboardRail.css';

const MainLayout = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const isDashboardView = location.pathname === '/dashboard';
  const isAIView = location.pathname === '/ai';
  const [darkMode, setDarkMode] = useState(() => {
    try {
      const stored = localStorage.getItem('dark_mode');
      return stored ? stored === 'true' : false;
    } catch {
      return false;
    }
  });
  const { user, setUser, logout, hasRole } = useAuth();

  const isSuperAdmin = hasRole('SUPER_ADMIN');
  const isDesktop = useMediaQuery('(min-width: 1280px)');

  const [counters, setCounters] = useState({ sales: 0, stock: 0, invoices: 0, salesToday: 0 });
  const { notifications, unreadCount, markAsRead, markAllAsRead } = useNotifications();

  const toggleDarkMode = (next) => {
    setDarkMode(next);
    try {
      localStorage.setItem('dark_mode', String(next));
    } catch {
      // ignore storage errors
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const [isEditingName, setIsEditingName] = useState(false);
  const [nameForm, setNameForm] = useState({ prenom: '', nom: '' });

  const handleStartEditName = () => {
    setNameForm({
      prenom: user?.prenom || '',
      nom: user?.nom || '',
    });
    setIsEditingName(true);
  };

  const handleUpdateNameField = (field, value) => {
    setNameForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSaveName = async () => {
    try {
      await authService.updateMe({ prenom: nameForm.prenom, nom: nameForm.nom });
      setUser((prev) => ({
        ...prev,
        prenom: nameForm.prenom,
        nom: nameForm.nom,
      }));
      setIsEditingName(false);
      toast.success('Nom mis à jour');
    } catch (err) {
      toast.error('Erreur lors de la mise à jour');
    }
  };

  useEffect(() => {
    let active = true;

    const safeCount = (value) => {
      if (value == null) return 0;
      if (typeof value === 'number') return value;
      if (Array.isArray(value)) return value.length;
      if (typeof value === 'object') {
        return value.count ?? value.total ?? value.nombre ?? 0;
      }
      return 0;
    };

    const load = async () => {
      const [sales, stock, factures, dash] = await Promise.allSettled([
        saleService.getSummary(),
        stockService.getAlerts(),
        factureService.getAll({ statut: 'impaye' }),
        dashboardService.getStats(),
      ]);

      if (!active) return;

      const next = {
        sales: sales.status === 'fulfilled' ? safeCount(sales.value?.data) : 0,
        stock: stock.status === 'fulfilled' ? safeCount(stock.value?.data) : 0,
        invoices: factures.status === 'fulfilled' ? safeCount(factures.value?.data) : 0,
        salesToday: 0,
      };

      if (dash.status === 'fulfilled') {
        const d = dash.value?.data || {};
        next.salesToday = safeCount(d.ventes_jour ?? d.ventesAujourdhui ?? d.sales_today);
      }

      setCounters(next);
    };

    load();

    return () => {
      active = false;
    };
  }, []);

  if (isDesktop) {
    return (
      <DesktopLayout
        darkMode={darkMode}
        onToggleDarkMode={toggleDarkMode}
        onLogout={handleLogout}
        counters={counters}
        notifications={notifications}
        unreadCount={unreadCount}
        onMarkAsRead={markAsRead}
        onMarkAllAsRead={markAllAsRead}
      />
    );
  }

  return (
    <div className="main-layout" data-theme={darkMode ? 'dark' : undefined} data-ai={isAIView ? 'true' : undefined}>
      <DashboardRail
        user={user}
        onLogout={handleLogout}
        isSuperAdmin={isSuperAdmin}
        isEditingName={isEditingName}
        onStartEditName={handleStartEditName}
        onSaveName={handleSaveName}
        nameForm={nameForm}
        onUpdateNameField={handleUpdateNameField}
        darkMode={darkMode}
        onToggleDarkMode={toggleDarkMode}
        counters={counters}
        notifications={notifications}
        unreadCount={unreadCount}
        onMarkAsRead={markAsRead}
        onMarkAllAsRead={markAllAsRead}
      />

      <main className="main-content">
        <Outlet />
      </main>

      {!isDashboardView && !isAIView && (
        <>
          <DarkModeToggle enabled={darkMode} onChange={toggleDarkMode} />
          <ChatInput />
        </>
      )}
    </div>
  );
};

export default MainLayout;
