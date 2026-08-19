// src/components/layout/DesktopLayout.jsx
import React, { useState, useEffect, useCallback } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import DesktopSidebar from './DesktopSidebar';
import TopBar from './TopBar';
import TitleBar from './TitleBar';
import CommandPalette from './CommandPalette';
import DarkModeToggle from './DarkModeToggle';
import ChatInput from './ChatInput';
import SplitView from './SplitView';
import FAB from '../desktop/FAB';
import { useDesktop } from '../../contexts/DesktopContext';
import { saleService, stockService, factureService, dashboardService } from '../../services/api';
import './DesktopLayout.css';

const IS_ELECTRON = typeof window !== 'undefined' && !!window.electron;

// Modules éligibles à la vue séparée (Plan §3.1).
const SPLIT_MODULES = ['/products', '/clients', '/sales', '/invoices', '/inventory'];

const DesktopLayout = ({ darkMode, onToggleDarkMode, onLogout }) => {
  const location = useLocation();
  const isAIView = location.pathname === '/ai';

  const { sidebarCollapsed, toggleSidebar, notifications, setCommandPaletteOpen, splitView, setSplitWidth } = useDesktop();

  const moduleKey = `/${location.pathname.split('/')[1] || ''}`;
  const showSplit = !isAIView && SPLIT_MODULES.includes(moduleKey) && !!splitView[moduleKey]?.enabled;

  const [collapsed, setCollapsed] = useState(() => {
    try {
      return localStorage.getItem('desktop_sidebar_collapsed') === 'true';
    } catch {
      return false;
    }
  });
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [counters, setCounters] = useState({ sales: 0, stock: 0, invoices: 0, salesToday: 0 });

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

  return (
    <div
      className={`main-layout desktop-layout${collapsed ? ' is-collapsed' : ''}`}
      data-theme={darkMode ? 'dark' : undefined}
      data-ai={isAIView ? 'true' : undefined}
    >
      {IS_ELECTRON && <TitleBar />}
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
          {showSplit ? (
            <SplitView
              module={moduleKey}
              leftWidth={splitView[moduleKey].leftWidth}
              onResizeWidth={(w) => setSplitWidth(moduleKey, w)}
              left={<Outlet />}
              right={
                <div className="split-view__right-empty">
                  <i className="ti ti-layout-sidebar" aria-hidden="true" />
                  <span>Sélectionnez un élément pour afficher le détail</span>
                </div>
              }
            />
          ) : (
            <Outlet />
          )}
        </main>
      </div>

      {!isAIView && (
        <>
          <DarkModeToggle enabled={darkMode} onChange={onToggleDarkMode} />
          <ChatInput />
          <FAB />
        </>
      )}

      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
    </div>
  );
};

export default DesktopLayout;
