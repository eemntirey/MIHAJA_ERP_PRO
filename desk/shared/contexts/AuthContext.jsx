
// shared/contexts/AuthContext.jsx
// Contexte d'authentification unique pour web et desktop.
// Le build web importe ce fichier depuis shared/, le build desktop aussi.

import React, { createContext, useState, useContext, useEffect, useCallback } from 'react';
import { toast } from 'react-toastify';
import { authService, subscriptionService } from '../services/api';
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

    useEffect(() => {
        const handleForcedLogout = () => {
            setUser(null);
            setTenant(null);
            setIsAuthenticated(false);
            setSubscription(null);
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

                if (tenantData) {
                    setTenant(tenantData);
                }

                if (subscriptionData) {
                    setSubscription(subscriptionData);
                }
            } catch (error) {
                authStorage.clear();
                setUser(null);
                setTenant(null);
                setSubscription(null);
                setIsAuthenticated(false);
            }
        } else {
            setUser(null);
            setTenant(null);
            setSubscription(null);
            setIsAuthenticated(false);
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

        if (['admin', 'manager', 'sales', 'stock', 'accountant'].includes(role) || hasTenant) {
            return '/dashboard';
        }

        if (role === 'user') {
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

            if (fetchSubscriptionOnInit && (tenantData || userData?.tenant_id)) {
                await fetchSubscriptionStatus();
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

            const deviceId = getDeviceId();

            const response = await authService.login({
                username: email,
                password: password,
                device_id: deviceId,
            });

            const {
                access_token,
                refresh_token,
                user: userData,
                tenant: tenantData,
            } = response.data || {};

            if (!access_token) {
                throw new Error('Le serveur a répondu sans access_token');
            }

            if (!userData) {
                throw new Error('Le serveur a répondu sans données utilisateur');
            }

            authStorage.setAccessToken(access_token);

            if (refresh_token) {
                authStorage.setRefreshToken(refresh_token);
            }

            authStorage.setUser(userData);

            if (tenantData) {
                authStorage.setTenant(tenantData);
            }

            setUser(userData);
            setTenant(tenantData || null);
            setIsAuthenticated(true);

            const redirectPath = getRedirectPath(userData);

            if (fetchSubscriptionOnInit && (tenantData || userData?.tenant_id)) {
                await fetchSubscriptionStatus();
            }

            toast.success('Connexion réussie !');

            return {
                success: true,
                user: userData,
                redirectPath,
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

        setUser(null);
        setTenant(null);
        setSubscription(null);
        setIsAuthenticated(false);

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
        }
    }, []);

    useEffect(() => {
        if (isAuthenticated && fetchSubscriptionOnInit) {
            const t = setTimeout(() => {
                fetchSubscriptionStatus();
            }, 50);
            return () => clearTimeout(t);
        }
    }, [isAuthenticated, fetchSubscriptionStatus, fetchSubscriptionOnInit]);

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

        return user.permissions.includes(permission);
    };

    const hasRole = (role) => {
        if (!user) {
            return false;
        }

        return (user.role || '').toLowerCase() === String(role).toLowerCase();
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
        login,
        register,
        logout,
        hasPermission,
        hasRole,
        getRedirectPath,
        fetchSubscriptionStatus,
        getAllowedModules,
    };

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
};
