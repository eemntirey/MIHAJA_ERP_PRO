import React, { useState, useEffect, useCallback } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import DesktopSidebar from './DesktopSidebar';
import TopBar from './TopBar';
import CommandPalette from './CommandPalette';
import DarkModeToggle from './DarkModeToggle';
import ChatInput from './ChatInput';
import { saleService, stockService, factureService, dashboardService } from '../../services/api';
import './DesktopLayout.css';

// Wrapper conditionnel activé uniquement en desktop (Plan §1, §2, §10.1).
// Récupère les compteurs temps réel pour badges (sidebar) et indicateurs (topbar).
const DesktopLayout = ({ darkMode, onToggleDarkMode, onLogout }) => {
  const location = useLocation();
  const isAIView = location.pathname === '/ai';

  const [collapsed, setCollapsed] = useState(() => {
    try {
      return localStorage.getItem('desktop_sidebar_collapsed') === 'true';
    } catch {
      return false;
    }
  });
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [counters, setCounters] = useState({ sales: 0, stock: 0, invoices: 0, salesToday: 0 });
  const [notifications, setNotifications] = useState([]);

  const toggleCollapsed = useCallback(() => {
    setCollapsed((prev) => {
      const next = !prev;
      try {
        localStorage.setItem('desktop_sidebar_collapsed', String(next));
      } catch {
        // ignore storage errors
      }
      return next;
    });
  }, []);

  // CMD+K / CTRL+K : ouverture de la command palette.
  useEffect(() => {
    const onKey = (event) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        setPaletteOpen((open) => !open);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  // Compteurs temps réel (tolérant aux erreurs réseau/shape API).
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

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        const res = await dashboardService.getAlerts();
        if (!active) return;
        const data = res?.data;
        const list = Array.isArray(data) ? data : data?.alertes || data?.notifications || [];
        setNotifications(Array.isArray(list) ? list.slice(0, 8) : []);
      } catch {
        // silence : les notifications sont optionnelles
      }
    };
    load();
    return () => {
      active = false;
    };
  }, []);

  return (
    <div
      className={`main-layout desktop-layout${collapsed ? ' is-collapsed' : ''}`}
      data-theme={darkMode ? 'dark' : undefined}
      data-ai={isAIView ? 'true' : undefined}
    >
      <DesktopSidebar
        collapsed={collapsed}
        counters={counters}
        onToggleCollapse={toggleCollapsed}
        onOpenPalette={() => setPaletteOpen(true)}
        onLogout={onLogout}
        darkMode={darkMode}
        onToggleDarkMode={onToggleDarkMode}
      />

      <div className="desktop-main">
        <TopBar
          counters={counters}
          notifications={notifications}
          onOpenPalette={() => setPaletteOpen(true)}
          onToggleSidebar={toggleCollapsed}
          collapsed={collapsed}
          darkMode={darkMode}
          onToggleDarkMode={onToggleDarkMode}
          onLogout={onLogout}
        />

        <main className="main-content desktop-content">
          <Outlet />
        </main>
      </div>

      {!isAIView && (
        <>
          <DarkModeToggle enabled={darkMode} onChange={onToggleDarkMode} />
          <ChatInput />
        </>
      )}

      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
    </div>
  );
};

export default DesktopLayout;
