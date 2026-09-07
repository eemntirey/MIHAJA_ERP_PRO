
// src/contexts/NotificationContext.jsx

import React, { createContext, useState, useContext, useEffect, useCallback } from 'react';
import { notificationService } from '../services/api';
import { tokenStore } from '../../shared/storage/tokenStore';

const NotificationContext = createContext();

export const useNotifications = () => {
    const context = useContext(NotificationContext);
    if (!context) {
        throw new Error('useNotifications must be used within a NotificationProvider');
    }
    return context;
};

export const NotificationProvider = ({ children }) => {
    const [notifications, setNotifications] = useState([]);
    const [loading, setLoading] = useState(true);

    const load = useCallback(async () => {
        if (!tokenStore.getAccessToken()) {
            setLoading(false);
            return;
        }
        try {
            const res = await notificationService.getAll();
            const data = res?.data || [];
            setNotifications(Array.isArray(data) ? data : []);
        } catch {
            setNotifications([]);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        let active = true;
        const handleLogout = () => {
            active = false;
            setNotifications([]);
            setLoading(false);
        };
        window.addEventListener('auth:logout', handleLogout);

        load();

        return () => {
            active = false;
            window.removeEventListener('auth:logout', handleLogout);
        };
    }, [load]);

    // Polling léger (30s) : garde le badge et la liste de la boîte de
    // notification à jour sans rechargement de la page.
    useEffect(() => {
        const interval = setInterval(() => {
            if (typeof document === 'undefined' || document.visibilityState === 'visible') {
                load();
            }
        }, 30000);
        return () => clearInterval(interval);
    }, [load]);

    const addNotification = useCallback(async (notification) => {
        try {
            const res = await notificationService.create(notification);
            const created = res?.data || notification;
            setNotifications((prev) => [created, ...prev]);
            return created;
        } catch {
            const fallback = {
                id: Date.now(),
                title: notification.title || 'Notification',
                message: notification.message || '',
                type: notification.type || 'info',
                read: false,
                read_at: null,
                link: notification.link || null,
                user_id: notification.user_id || null,
                tenant_id: notification.tenant_id || null,
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString(),
                is_active: true,
            };
            setNotifications((prev) => [fallback, ...prev]);
            return fallback;
        }
    }, []);

    const markAsRead = useCallback(async (id) => {
        setNotifications((prev) =>
            prev.map((n) =>
                n.id === id ? { ...n, read: true, read_at: n.read_at || new Date().toISOString() } : n
            )
        );
        try {
            await notificationService.markAsRead(id);
        } catch {
            // silent fallback
        }
    }, []);

    const markAllAsRead = useCallback(async () => {
        setNotifications((prev) =>
            prev.map((n) => ({ ...n, read: true, read_at: n.read_at || new Date().toISOString() }))
        );
        try {
            await notificationService.markAllAsRead();
        } catch {
            // silent fallback
        }
    }, []);

    const removeNotification = useCallback(async (id) => {
        setNotifications((prev) => prev.filter((n) => n.id !== id));
        try {
            await notificationService.delete(id);
        } catch {
            // silent fallback
        }
    }, []);

    const unreadCount = notifications.filter((n) => !n.read).length;

    const value = {
        notifications,
        loading,
        unreadCount,
        addNotification,
        markAsRead,
        markAllAsRead,
        removeNotification,
        refresh: load,
    };

    return (
        <NotificationContext.Provider value={value}>
            {children}
        </NotificationContext.Provider>
    );
};
