// src/components/layout/DesktopLayout.jsx
import React, { useState, useEffect, useCallback } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import DesktopSidebar from './DesktopSidebar';
import DesktopTopBar from './DesktopTopBar';
import TitleBar from './TitleBar';
import CommandPalette from './CommandPalette';
import SplitView from './SplitView';
import FAB from '../desktop/FAB';
import { useDesktop } from '../../contexts/DesktopContext';
import { useKeyboardShortcuts } from '../../hooks/useKeyboardShortcuts';
import { useMediaQuery } from '../../hooks/useMediaQuery';
import { useAuth } from '../../contexts/AuthContext';
import { saleService, stockService, factureService, dashboardService } from '../../services/api';
import './DesktopLayout.css';

const IS_ELECTRON = typeof window !== 'undefined' && !!window.electron;

// Modules éligibles à la vue séparée (Plan §3.1).
const SPLIT_MODULES = ['/products', '/clients', '/sales', '/invoices', '/inventory'];

const DesktopLayout = ({ darkMode, onToggleDarkMode, onLogout }) => {
  const location = useLocation();
  const isAIView = location.pathname === '/ai';
  const { user } = useAuth();

  const { commandPaletteOpen, setCommandPaletteOpen, splitView, setSplitWidth } = useDesktop();

  const moduleKey = `/${location.pathname.split('/')[1] || ''}`;
  const showSplit = !isAIView && SPLIT_MODULES.includes(moduleKey) && !!splitView[moduleKey]?.enabled;

  const isMobile = useMediaQuery('(max-width: 767px)');
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [counters, setCounters] = useState({ sales: 0, stock: 0, invoices: 0, salesToday: 0 });

  const toggleCollapsed = useCallback(() => {
    setCollapsed((prev) => {
      const next = !prev;
      try {
        localStorage.setItem('desk_sidebar_collapsed', String(next));
      } catch {
        // ignore storage errors
      }
      return next;
    });
  }, []);

  const toggleSidebar = useCallback(() => {
    if (isMobile) {
      setMobileOpen((prev) => !prev);
    } else {
      toggleCollapsed();
    }
  }, [isMobile, toggleCollapsed]);

  const closeMobileSidebar = useCallback(() => setMobileOpen(false), []);

  // Raccourcis clavier globaux (CMD+K, CMD+B, CMD+1-9)
  useKeyboardShortcuts({ onToggleSidebar: toggleSidebar });

  useEffect(() => {
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) {
      meta.setAttribute('content', darkMode ? '#0f172a' : '#fafafa');
    }
  }, [darkMode]);

  useEffect(() => {
    if (!isMobile) {
      setMobileOpen(false);
    }
  }, [isMobile]);

  useEffect(() => {
    if (!user) return;

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
        // L'API renvoie { message, stats: { ventes_aujourdhui, ... } }.
        const d = dash.value?.data?.stats || dash.value?.data || {};
        next.salesToday = safeCount(
          d.ventes_aujourdhui ?? d.ventes_jour ?? d.ventesAujourdhui ?? d.sales_today
        );
      }

      setCounters(next);
    };

    load();

    return () => {
      active = false;
    };
  }, [user]);

  const sidebarClassName = [
    'desktop-sidebar',
    isMobile && mobileOpen ? 'is-mobile-open' : '',
    collapsed && !isMobile ? 'collapsed' : '',
  ].filter(Boolean).join(' ');

  return (
    <div
      className={`main-layout desktop-layout${collapsed && !isMobile ? ' is-collapsed' : ''}${IS_ELECTRON ? ' electron' : ''}`}
      data-theme={darkMode ? 'dark' : undefined}
      data-ai={isAIView ? 'true' : undefined}
    >
      {IS_ELECTRON && false && <TitleBar />}
      <DesktopSidebar
        className={sidebarClassName}
        collapsed={collapsed}
        counters={counters}
        onToggleCollapse={toggleCollapsed}
        onOpenPalette={() => setCommandPaletteOpen(true)}
        onLogout={onLogout}
        darkMode={darkMode}
        onToggleDarkMode={onToggleDarkMode}
      />

      {isMobile && mobileOpen && (
        <div className="sidebar-backdrop" onClick={closeMobileSidebar} />
      )}

      <div className="desktop-main">
        <DesktopTopBar
          darkMode={darkMode}
          onToggleDarkMode={onToggleDarkMode}
          counters={counters}
          onOpenPalette={() => setCommandPaletteOpen(true)}
          onToggleSidebar={toggleSidebar}
          collapsed={collapsed}
          isMobile={isMobile}
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

      {!isAIView && <FAB />}

      <CommandPalette open={commandPaletteOpen} onClose={() => setCommandPaletteOpen(false)} />
    </div>
  );
};

export default DesktopLayout;
