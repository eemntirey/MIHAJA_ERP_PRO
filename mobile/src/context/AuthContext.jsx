// src/context/AuthContext.jsx
// Contexte d'authentification mobile — équivalent de
// shared/contexts/AuthContext.jsx (web/desktop) adapté à React Native :
// - restauration de session depuis SecureStore/AsyncStorage au démarrage
// - login via POST /auth/login (JWT access + refresh)
// - gestion du flag must_change_password (première connexion)
// - déconnexion forcée quand le refresh échoue (services/api.js)

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from 'react';
import { authService } from '../services/services';
import { setUnauthorizedHandler } from '../services/api';
import { session } from '../storage/session';

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth doit être utilisé dans un AuthProvider');
  }
  return context;
};

export function AuthProvider({ children }) {
  const [booting, setBooting] = useState(true);
  const [user, setUser] = useState(null);
  const [tenant, setTenant] = useState(null);
  const [mustChangePassword, setMustChangePassword] = useState(false);

  // Purge locale de la session (appelé par le refresh qui échoue aussi).
  const clearSession = useCallback(async () => {
    await session.clear();
    setUser(null);
    setTenant(null);
    setMustChangePassword(false);
  }, []);

  // Le client API notifie quand la session n'est plus valide.
  useEffect(() => {
    setUnauthorizedHandler(() => {
      clearSession();
    });
  }, [clearSession]);

  // Bootstrap : restaure la session persistée, puis resynchronise /auth/me.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [token, storedUser, storedTenant] = await Promise.all([
          session.getAccessToken(),
          session.getUser(),
          session.getTenant(),
        ]);

        if (!token || !storedUser) {
          await session.clear();
        } else if (!cancelled) {
          setUser(storedUser);
          setMustChangePassword(Boolean(storedUser.must_change_password));
          if (storedTenant) setTenant(storedTenant);

          // Revalidation silencieuse : si le réseau est indisponible on
          // conserve la session locale, si le token est révoqué le
          // refresh échouera et déclenchera la déconnexion.
          try {
            const { data } = await authService.me();
            if (!cancelled && data?.user) {
              setUser(data.user);
              await session.setUser(data.user);
              if (data.tenant) {
                setTenant(data.tenant);
                await session.setTenant(data.tenant);
              }
            }
          } catch {
            // réseau indisponible : session locale conservée
          }
        }
      } finally {
        if (!cancelled) setBooting(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  /**
   * Connexion. Lève une erreur (message lisible) en cas d'échec.
   * POST /auth/login → {access_token, refresh_token, user, tenant,
   * must_change_password}
   */
  const login = useCallback(async (identifier, password) => {
    const { data } = await authService.login({
      username: identifier,
      password,
    });

    const {
      access_token,
      refresh_token,
      user: userData,
      tenant: tenantData,
      must_change_password: mustChangeFlagRoot,
    } = data || {};

    if (!access_token || !userData) {
      throw new Error('Réponse de connexion invalide (jetons manquants)');
    }

    // Le flag peut venir à la racine ou dans l'objet user : valeur la plus stricte.
    const mustChange = Boolean(mustChangeFlagRoot ?? userData.must_change_password);
    const normalizedUser = { ...userData, must_change_password: mustChange };

    await session.setTokens({ access_token, refresh_token });
    await session.setUser(normalizedUser);
    if (tenantData) await session.setTenant(tenantData);

    setUser(normalizedUser);
    setTenant(tenantData || null);
    setMustChangePassword(mustChange);

    return { mustChangePassword: mustChange };
  }, []);

  /** Déconnexion : best-effort côté backend puis purge locale. */
  const logout = useCallback(async () => {
    try {
      await authService.logout();
    } catch {
      // on déconnecte localement même si l'API est injoignable
    }
    await clearSession();
  }, [clearSession]);

  /** Met à jour l'utilisateur (ex: après changement de mot de passe). */
  const updateUser = useCallback(async (updatedUser) => {
    setUser(updatedUser);
    await session.setUser(updatedUser);
  }, []);

  const value = {
    booting,
    user,
    tenant,
    isAuthenticated: Boolean(user),
    mustChangePassword,
    login,
    logout,
    updateUser,
    setMustChangePassword,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export default AuthContext;
