import React, { createContext, useState, useContext, useEffect } from 'react';
import { toast } from 'react-toastify';
import { superAdminAuthService, superAdminApi } from '../services/api';

const SuperAdminAuthContext = createContext();

export const useSuperAdminAuth = () => {
  const context = useContext(SuperAdminAuthContext);
  if (!context) {
    throw new Error('useSuperAdminAuth must be used within a SuperAdminAuthProvider');
  }
  return context;
};

export const SuperAdminAuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    const validateSession = async () => {
      const token = localStorage.getItem('super_admin_access_token');
      const userData = localStorage.getItem('super_admin_user');

      if (token && userData) {
        try {
          const parsedUser = JSON.parse(userData);
          superAdminApi.defaults.headers.common.Authorization = `Bearer ${token}`;

          await superAdminAuthService.confirmSession();
          setUser(parsedUser);
          setIsAuthenticated(true);
        } catch {
          localStorage.removeItem('super_admin_access_token');
          localStorage.removeItem('super_admin_refresh_token');
          localStorage.removeItem('super_admin_user');
          delete superAdminApi.defaults.headers.common.Authorization;
          setUser(null);
          setIsAuthenticated(false);
        }
      }
      setLoading(false);
    };

    validateSession();
  }, []);

  const login = async (email, password) => {
    try {
      setLoading(true);
      const response = await superAdminAuthService.login(email, password);
      const { access_token, refresh_token, user: userData } = response.data || {};

      if (!access_token || !userData) {
        throw new Error('Réponse invalide du serveur');
      }

      if (userData.role !== 'super_admin') {
        throw new Error('Accès réservé au Super Admin uniquement');
      }

      localStorage.setItem('super_admin_access_token', access_token);
      if (refresh_token) {
        localStorage.setItem('super_admin_refresh_token', refresh_token);
      }
      localStorage.setItem('super_admin_user', JSON.stringify(userData));

      setUser(userData);
      setIsAuthenticated(true);
      superAdminApi.defaults.headers.common.Authorization = `Bearer ${access_token}`;

      toast.success('Connexion Super Admin réussie');
      return { success: true };
    } catch (error) {
      const message = error.response?.data?.message || error.message || 'Échec de la connexion';
      toast.error(message);
      localStorage.removeItem('super_admin_access_token');
      localStorage.removeItem('super_admin_user');
      setUser(null);
      setIsAuthenticated(false);
      return { success: false, error: message };
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    try {
      await superAdminAuthService.logout();
    } catch {
      // silent
    }

    localStorage.removeItem('super_admin_access_token');
    localStorage.removeItem('super_admin_refresh_token');
    localStorage.removeItem('super_admin_user');
    delete superAdminApi.defaults.headers.common.Authorization;
    setUser(null);
    setIsAuthenticated(false);
    toast.info('Déconnexion réussie');
  };

  const updateProfile = (data) => {
    const merged = { ...(user || {}), ...data };
    setUser(merged);
    localStorage.setItem('super_admin_user', JSON.stringify(merged));
  };

  const value = {
    user,
    loading,
    isAuthenticated,
    login,
    logout,
    updateProfile,
  };

  return (
    <SuperAdminAuthContext.Provider value={value}>
      {children}
    </SuperAdminAuthContext.Provider>
  );
};
