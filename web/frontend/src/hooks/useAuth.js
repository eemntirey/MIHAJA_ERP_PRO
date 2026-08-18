// src/hooks/useAuth.js
import { useAuth } from '../contexts/AuthContext';

export const useAuthHook = () => {
  const auth = useAuth();
  return auth;
};

// Hook pour vérifier les permissions
export const usePermission = (permission) => {
  const { user } = useAuth();
  if (!user || !user.permissions) return false;
  return user.permissions.includes(permission);
};

// Hook pour vérifier les rôles
export const useRole = (role) => {
  const { user } = useAuth();
  if (!user) return false;
  return (user.role || '').toLowerCase() === String(role).toLowerCase();
};