
// shared/contexts/AuthContext.jsx
// Contexte d'authentification unique pour web et desktop.
// Le build web importe ce fichier depuis shared/, le build desktop aussi.

import React, { createContext, useState, useContext, useEffect, useCallback } from 'react';
import { toast } from 'react-toastify';
import api, { authService, subscriptionService } from '../services/api';
import { authStorage, AUTH_KEYS } from '../storage/authStorage';
import { runMigration } from '../utils/migrateLocalStorage';
import { getDeviceId } from '../utils/deviceId';

export const AuthContext = createContext();

export const useAuth = () => {
    const context = useContext(AuthContext);

    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }

    return context;
};

export const AuthProvider = ({ children, fetchSubscriptionOnInit = true }) => {
    const [user, setUser] = useState(null);
    const [tenant, setTenant] = useState(null);
    const [loading, setLoading] = useState(true);
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [subscription, setSubscription] = useState(null);
    const [subscriptionLoading, setSubscriptionLoading] = useState(false);
    const [mustChangePassword, setMustChangePassword] = useState(false);

    useEffect(() => {
        const handleForcedLogout = () => {
            setUser(null);
            setTenant(null);
            setIsAuthenticated(false);
            setSubscription(null);
            setSubscriptionLoading(false);
            setMustChangePassword(false);
        };

        window.addEventListener('auth:logout', handleForcedLogout);

        return () => {
            window.removeEventListener('auth:logout', handleForcedLogout);
        };
    }, []);

    useEffect(() => {
        const token = authStorage.getAccessToken();
        const userData = authStorage.getUser();
        const tenantData = authStorage.getTenant();
        const subscriptionData = authStorage.getSubscription();

        if (token && userData) {
            try {
                setUser(userData);
                setIsAuthenticated(true);
                // Restaurer le flag must_change_password depuis les donnees
                // utilisateur persistees (storage local / localStorage).
                setMustChangePassword(Boolean(userData.must_change_password));

                if (tenantData) {
                    setTenant(tenantData);
                }

                if (subscriptionData) {
                    setSubscription(subscriptionData);
                } else if (fetchSubscriptionOnInit) {
                    setSubscriptionLoading(true);
                }
            } catch (error) {
                authStorage.clear();
                setUser(null);
                setTenant(null);
                setSubscription(null);
                setSubscriptionLoading(false);
                setIsAuthenticated(false);
            }
        } else {
            setUser(null);
            setTenant(null);
            setSubscription(null);
            setSubscriptionLoading(false);
            setIsAuthenticated(false);
            setMustChangePassword(false);
        }

        setLoading(false);
    }, []);

    useEffect(() => {
        runMigration().catch(() => {
            // migration silencieuse
        });
    }, []);

    const getRedirectPath = (userData) => {
        if (!userData) return '/login';

        const role = (userData.role || '').toLowerCase();
        const hasTenant = !!userData.tenant_id || !!userData.tenant?.id;

        if (role === 'super_admin') {
            return '/super-admin';
        }

        if (role === 'livreur') {
            return '/delivery';
        }

        if (['admin', 'manager', 'sales', 'stock', 'accountant'].includes(role) || hasTenant) {
            return '/dashboard';
        }

        if (role === 'user' && !hasTenant) {
            return '/';
        }

        return '/dashboard';
    };

    const register = async (payload) => {
        try {
            setLoading(true);

            const response = await authService.register(payload);
            const { access_token, refresh_token, user: userData, tenant: tenantData } = response.data || {};

            if (!access_token || !userData) {
                throw new Error("Réponse d'inscription invalide (tokens manquants)");
            }

            authStorage.setAccessToken(access_token);
            if (refresh_token) {
                authStorage.setRefreshToken(refresh_token);
            }
            authStorage.setUser(userData);
            if (tenantData) {
                authStorage.setTenant(tenantData);
                setTenant(tenantData);
            }

            setUser(userData);
            setIsAuthenticated(true);
            if (userData?.tenant_id || userData?.tenant?.id) {
                setSubscriptionLoading(true);
            }

            toast.success('Compte créé avec succès !');

            return {
                success: true,
                user: userData,
                redirectPath: getRedirectPath(userData),
            };
        } catch (error) {
            console.error('Erreur inscription:', error);
            const message =
                error.response?.data?.message ||
                error.message ||
                'Erreur lors de la création du compte';
            toast.error(message);
            return { success: false, error: message };
        } finally {
            setLoading(false);
        }
    };

    const login = async (email, password) => {
        try {
            setLoading(true);

            const response = await authService.login({
                username: email,
                password: password,
            });

            const {
                access_token,
                refresh_token,
                user: userData,
                tenant: tenantData,
                must_change_password: mustChange,
            } = response.data || {};

            if (!access_token) {
                throw new Error('Le serveur a répondu sans access_token');
            }

            if (!userData) {
                throw new Error('Le serveur a répondu sans données utilisateur');
            }

            // Le backend peut renvoyer le flag au niveau racine (compat ascendante)
            // ou l'integrer dans l'objet user. On prend la valeur la plus stricte.
            const mustChangeFlag = Boolean(
                mustChange ?? userData?.must_change_password
            );

            // S'assurer que userData inclut le flag pour les rechargements de page
            const normalizedUser = { ...userData, must_change_password: mustChangeFlag };

            authStorage.setAccessToken(access_token);

            if (refresh_token) {
                authStorage.setRefreshToken(refresh_token);
            }

            authStorage.setUser(normalizedUser);

            if (tenantData) {
                authStorage.setTenant(tenantData);
            }

            setUser(normalizedUser);
            setTenant(tenantData || null);
            setIsAuthenticated(true);
            setMustChangePassword(mustChangeFlag);
            if (normalizedUser?.tenant_id || normalizedUser?.tenant?.id) {
                setSubscriptionLoading(true);
            }

            // Si l'utilisateur doit changer son mot de passe, on force la
            // redirection vers l'ecran dedie (le ProtectedRoute s'occupera
            // aussi de blquer l'acces aux autres routes).
            const redirectPath = mustChangeFlag
                ? '/first-change-password'
                : getRedirectPath(normalizedUser);

            toast.success('Connexion réussie !');

            return {
                success: true,
                user: normalizedUser,
                redirectPath,
                mustChangePassword: mustChangeFlag,
            };

        } catch (error) {
            console.error('Erreur login:', error);
            console.error('Réponse erreur:', error.response?.data);

            const message =
                error.response?.data?.message ||
                error.response?.data?.error ||
                error.message ||
                'Erreur de connexion';

            toast.error(message);

            authStorage.clear();

            setUser(null);
            setTenant(null);
            setSubscription(null);
            setIsAuthenticated(false);

            return {
                success: false,
                error: message,
            };

        } finally {
            setLoading(false);
        }
    };

    const logout = async () => {
        try {
            await authService.logout();
        } catch {
            // Silencieux : le logout backend peut échouer si le token est déjà expiré
        }

        authStorage.clear();

        delete api.defaults.headers.common.Authorization;

        setUser(null);
        setTenant(null);
        setSubscription(null);
        setSubscriptionLoading(false);
        setIsAuthenticated(false);
        setMustChangePassword(false);

        window.dispatchEvent(new Event('auth:logout'));

        toast.info('Déconnexion réussie');
    };

    const fetchSubscriptionStatus = useCallback(async () => {
        if (fetchSubscriptionStatus._inflight) {
            return fetchSubscriptionStatus._inflight;
        }
        const inflight = (async () => {
            try {
                const response = await subscriptionService.getMonAbonnement();
                const sub = response.data?.abonnement || null;
                console.log('[AuthContext] fetchSubscriptionStatus', sub);
                setSubscription(sub);
                if (sub) {
                    authStorage.setSubscription(sub);
                } else {
                    authStorage.remove(AUTH_KEYS.SUBSCRIPTION);
                }
            } catch (err) {
                const status = err.response?.status;
                // Ne pas déconnecter sur erreur serveur (500), garder l'abonnement existant
                if (status && status >= 500) {
                    console.warn('[AuthContext] fetchSubscriptionStatus server error, keeping cached subscription:', status);
                    return;
                }
                console.error('[AuthContext] fetchSubscriptionStatus error', err);
            setSubscription(null);
            authStorage.remove(AUTH_KEYS.SUBSCRIPTION);
        }
    })();
    fetchSubscriptionStatus._inflight = inflight;
    try {
        await inflight;
    } finally {
        fetchSubscriptionStatus._inflight = null;
        setSubscriptionLoading(false);
    }
}, []);

    useEffect(() => {
        if (isAuthenticated && fetchSubscriptionOnInit && (user?.tenant_id || user?.tenant?.id)) {
            const t = setTimeout(() => {
                fetchSubscriptionStatus();
            }, 50);
            return () => clearTimeout(t);
        }
    }, [isAuthenticated, fetchSubscriptionStatus, fetchSubscriptionOnInit, user]);

    const getAllowedModules = () => {
        if (!subscription) {
            return null;
        }
        if (Array.isArray(subscription.modules)) {
            return subscription.modules;
        }
        if (typeof subscription.modules === 'string') {
            return subscription.modules.split(',').map(m => m.trim()).filter(Boolean);
        }
        return null;
    };

    const hasPermission = (permission) => {
        if (!user || !user.permissions) {
            return false;
        }

        // Le super_admin recoit ['*'] du backend : toutes les permissions.
        if (user.permissions.includes('*')) {
            return true;
        }

        // Support du wildcard par module (ex. 'sales.*' couvre 'sales.view').
        if (permission.includes('.')) {
            const moduleWildcard = `${permission.split('.')[0]}.*`;
            if (user.permissions.includes(moduleWildcard)) {
                return true;
            }
        }

        return user.permissions.includes(permission);
    };

    /**
     * True si l'utilisateur possede AU MOINS UNE des permissions listees.
     * Utilise pour la visibilite declarative des modules de la sidebar :
     * une liste vide retourne false (module masque).
     */
    const hasAnyPermission = (permissions) => {
        if (!Array.isArray(permissions) || permissions.length === 0) {
            return false;
        }
        return permissions.some((permission) => hasPermission(permission));
    };

    const hasAllPermissions = (permissions) => {
        if (!user) {
            return false;
        }
        if (!Array.isArray(permissions) || permissions.length === 0) {
            return true;
        }
        return permissions.every((permission) => hasPermission(permission));
    };

    /**
     * Verifie qu'un module est disponible dans le plan de l'utilisateur
     * (via la subscription). null = pas d'info (subscription pas chargee
     * ou super_admin) -> autorise.
     */
    const isModuleEnabled = (moduleName) => {
        if (!moduleName) {
            return true;
        }
        if (!subscription) {
            return true;
        }
        const modules = getAllowedModules();
        if (modules === null) {
            return true;
        }
        return modules.includes(moduleName);
    };

    const hasRole = (role) => {
        if (!user) {
            return false;
        }

        return (user.role || '').toLowerCase() === String(role).toLowerCase();
    };

    /**
     * Changement de mot de passe (volontaire) pour un utilisateur connecté.
     * Apres un succes, le flag mustChangePassword reste a false (et un email
     * de notification est envoye cote backend).
     */
    const changePassword = async (oldPassword, newPassword) => {
        try {
            const response = await authService.changePassword(oldPassword, newPassword);
            toast.success('Mot de passe modifié avec succès');
            return { success: true, data: response.data };
        } catch (error) {
            const message =
                error.response?.data?.message ||
                error.response?.data?.error ||
                error.message ||
                'Erreur lors de la modification du mot de passe';
            toast.error(message);
            return { success: false, error: message };
        }
    };

    /**
     * Changement obligatoire du mot de passe (première connexion).
     * L'utilisateur n'a pas d'ancien mot de passe a fournir.
     * Apres succes, le flag mustChangePassword est mis a false cote client
     * (et un email de notification est envoye cote backend).
     */
    const firstChangePassword = async (newPassword) => {
        try {
            // Utilisation du pattern useForm + onSubmit pour gérer confirm_password
            const response = await authService.firstChangePassword(newPassword);
            toast.success('Mot de passe défini avec succès');
            const updatedUser = response.data?.user || user;
            const normalizedUser = { ...updatedUser, must_change_password: false };
            setUser(normalizedUser);
            setMustChangePassword(false);
            authStorage.setUser(normalizedUser);
            return { success: true, user: normalizedUser };
        } catch (error) {
            const message =
                error.response?.data?.message ||
                error.response?.data?.error ||
                error.message ||
                'Erreur lors du changement de mot de passe';
            toast.error(message);
            return { success: false, error: message };
        }
    };

const value = {
        user,
        setUser,
        tenant,
        setTenant,
        loading,
        isAuthenticated,
        subscription,
        setSubscription,
        subscriptionLoading,
        login,
        register,
        logout,
        hasPermission,
        hasAnyPermission,
        hasAllPermissions,
        hasRole,
        isModuleEnabled,
        getRedirectPath,
        fetchSubscriptionStatus,
        getAllowedModules,
        // Gestion du changement de mot de passe
        mustChangePassword,
        setMustChangePassword,
        changePassword,
        firstChangePassword,
    };

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
};
