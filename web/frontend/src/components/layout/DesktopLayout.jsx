import React, { useState, useEffect, useCallback } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import DesktopSidebar from './DesktopSidebar';
import TopBar from './TopBar';
import CommandPalette from './CommandPalette';
import DarkModeToggle from './DarkModeToggle';
import ChatInput from './ChatInput';
import { saleService, stockService, factureService, dashboardService } from '../../services/api';
import './DesktopLayout.css';

const DesktopLayout = ({ darkMode, onToggleDarkMode, onLogout, counters, notifications, unreadCount, onMarkAsRead, onMarkAllAsRead }) => {
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
          unreadCount={unreadCount}
          onMarkAsRead={onMarkAsRead}
          onMarkAllAsRead={onMarkAllAsRead}
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
