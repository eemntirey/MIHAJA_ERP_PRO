import React, { useState } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import DashboardRail from './DashboardRail';
import DarkModeToggle from './DarkModeToggle';
import ChatInput from './ChatInput';
import DesktopLayout from './DesktopLayout';
import { useMediaQuery } from '../../hooks/useMediaQuery';
import { authService } from '../../services/api';
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

  // Expérience desktop native activée uniquement >= 1280px (Plan §1).
  if (isDesktop) {
    return (
      <DesktopLayout
        darkMode={darkMode}
        onToggleDarkMode={toggleDarkMode}
        onLogout={handleLogout}
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
