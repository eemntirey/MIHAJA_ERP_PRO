
// src/contexts/AuthContext.jsx

import React, { createContext, useState, useContext, useEffect } from 'react';
import { toast } from 'react-toastify';
import { authService, subscriptionService } from '../services/api';

const AuthContext = createContext();

export const useAuth = () => {
    const context = useContext(AuthContext);

    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }

    return context;
};

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [tenant, setTenant] = useState(null);
    const [loading, setLoading] = useState(true);
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [subscription, setSubscription] = useState(null);

    // Réinitialisation propre sur déconnexion forcée (token expiré/invalide)
    useEffect(() => {
        const handleForcedLogout = () => {
            setUser(null);
            setTenant(null);
            setIsAuthenticated(false);
            setSubscription(null);
        };

        window.addEventListener('auth:logout', handleForcedLogout);

        return () => {
            window.removeEventListener(
                'auth:logout',
                handleForcedLogout
            );
        };
    }, []);

    // Vérification de la session au démarrage
    useEffect(() => {
        const token = localStorage.getItem('access_token');
        const userData = localStorage.getItem('user');
        const tenantData = localStorage.getItem('tenant');
        const subscriptionData = localStorage.getItem('subscription');

        if (token && userData) {
            try {
                const parsedUser = JSON.parse(userData);

                setUser(parsedUser);
                setIsAuthenticated(true);

                if (tenantData) {
                    try {
                        setTenant(JSON.parse(tenantData));
                    } catch (e) {
                        setTenant(null);
                    }
                }

                if (subscriptionData) {
                    try {
                        setSubscription(JSON.parse(subscriptionData));
                    } catch (e) {
                        setSubscription(null);
                    }
                }
            } catch (error) {
                localStorage.removeItem('access_token');
                localStorage.removeItem('refresh_token');
                localStorage.removeItem('user');
                localStorage.removeItem('tenant');
                localStorage.removeItem('subscription');

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

    // Rôle -> redirection post-login
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

    // Inscription + connexion automatique (le backend renvoie les tokens)
    const register = async (payload) => {
        try {
            setLoading(true);

            const response = await authService.register(payload);
            const { access_token, refresh_token, user: userData, tenant: tenantData } = response.data || {};

            if (!access_token || !userData) {
                throw new Error(
                    'Réponse d\'inscription invalide (tokens manquants)'
                );
            }

            localStorage.setItem('access_token', access_token);
            if (refresh_token) {
                localStorage.setItem('refresh_token', refresh_token);
            }
            localStorage.setItem('user', JSON.stringify(userData));
            if (tenantData) {
                localStorage.setItem('tenant', JSON.stringify(tenantData));
                setTenant(tenantData);
            }

            setUser(userData);
            setIsAuthenticated(true);

            // Les utilisateurs simples (sans tenant) n'ont pas d'abonnement
            if (tenantData || userData?.tenant_id) {
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

    // Connexion
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
            } = response.data || {};

            if (!access_token) {
                throw new Error(
                    'Le serveur a répondu sans access_token'
                );
            }

            if (!userData) {
                throw new Error(
                    'Le serveur a répondu sans données utilisateur'
                );
            }

            // Sauvegarde de la session
            localStorage.setItem('access_token', access_token);

            if (refresh_token) {
                localStorage.setItem(
                    'refresh_token',
                    refresh_token
                );
            }

            localStorage.setItem(
                'user',
                JSON.stringify(userData)
            );

            if (tenantData) {
                localStorage.setItem(
                    'tenant',
                    JSON.stringify(tenantData)
                );
            }

            setUser(userData);
            setTenant(tenantData || null);
            setIsAuthenticated(true);

            const redirectPath = getRedirectPath(userData);

            // Les utilisateurs simples (sans tenant) n'ont pas d'abonnement
            if (tenantData || userData?.tenant_id) {
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

            console.error(
                'Réponse erreur:',
                error.response?.data
            );

            const message =
                error.response?.data?.message ||
                error.response?.data?.error ||
                error.message ||
                'Erreur de connexion';

            toast.error(message);

            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            localStorage.removeItem('user');
            localStorage.removeItem('tenant');
            localStorage.removeItem('subscription');

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

    // Déconnexion
    const logout = async () => {
        try {
            await authService.logout();
        } catch {
            // Silencieux : le logout backend peut échouer si le token est déjà expiré
        }

        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user');
        localStorage.removeItem('tenant');
        localStorage.removeItem('subscription');

        setUser(null);
        setTenant(null);
        setSubscription(null);
        setIsAuthenticated(false);

        toast.info('Déconnexion réussie');
    };

    const fetchSubscriptionStatus = async () => {
        try {
            const response = await subscriptionService.getMonAbonnement();
            const sub = response.data?.abonnement || response.data;
            setSubscription(sub);
            if (sub) {
                localStorage.setItem('subscription', JSON.stringify(sub));
            } else {
                localStorage.removeItem('subscription');
            }
        } catch (err) {
            console.error('Error fetching subscription status:', err);
            setSubscription(null);
            localStorage.removeItem('subscription');
        }
    };

    // Vérification permission
    const hasPermission = (permission) => {
        if (!user || !user.permissions) {
            return false;
        }

        return user.permissions.includes(permission);
    };

    // Vérification rôle (insensible à la casse : le backend envoie des valeurs
    // lowercase come 'super_admin' mais le frontend compare parfois 'SUPER_ADMIN')
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
    };

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
};

