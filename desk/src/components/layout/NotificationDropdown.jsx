// src/components/layout/NotificationDropdown.jsx
import React, { useState, useEffect, useCallback } from 'react';
import { notificationService } from '../../services/desktopApi';
import './NotificationDropdown.css';

const formatTime = (value) => {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  const diff = (Date.now() - date.getTime()) / 1000;
  if (diff < 60) return "à l'instant";
  if (diff < 3600) return `il y a ${Math.floor(diff / 60)} min`;
  if (diff < 86400) return `il y a ${Math.floor(diff / 3600)} h`;
  return date.toLocaleDateString();
};

// Accepte les formes de réponse possibles de l'API (tableau, {data}, {items}).
const normalize = (payload) => {
  if (Array.isArray(payload)) return payload;
  if (payload && Array.isArray(payload.data)) return payload.data;
  if (payload && Array.isArray(payload.items)) return payload.items;
  return [];
};

const NotificationDropdown = ({ onClose }) => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await notificationService.getAll();
      setItems(
        normalize(res?.data).map((n) => ({
          id: n.id,
          title: n.titre || n.title || 'Notification',
          message: n.message || n.contenu || n.detail || n.description || '',
          time: formatTime(n.created_at || n.date || n.time),
          read: !!(n.lu || n.read),
        }))
      );
    } catch {
      setError('Impossible de charger les notifications');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const markRead = useCallback(async (id) => {
    setItems((prev) => prev.map((n) => (n.id === id ? { ...n, read: true } : n)));
    try {
      await notificationService.markAsRead(id);
    } catch {
      /* silencieux : l'état local reste la source visuelle */
    }
  }, []);

  const markAll = useCallback(async () => {
    setItems((prev) => prev.map((n) => ({ ...n, read: true })));
    try {
      await notificationService.markAllAsRead();
    } catch {
      /* silencieux */
    }
  }, []);

  const remove = useCallback(async (id) => {
    setItems((prev) => prev.filter((n) => n.id !== id));
    try {
      await notificationService.delete(id);
    } catch {
      /* silencieux */
    }
  }, []);

  const unread = items.filter((n) => !n.read).length;

  return (
    <div className="notif-dropdown" onClick={(e) => e.stopPropagation()}>
      <div className="notif-dropdown-header">
        <h3>Notifications</h3>
        <span className="notif-dropdown-count">{unread} non lue(s)</span>
      </div>

      <div className="notif-dropdown-list">
        {loading && <div className="notif-dropdown-empty">Chargement…</div>}
        {!loading && error && (
          <div className="notif-dropdown-empty notif-dropdown-error">{error}</div>
        )}
        {!loading && !error && items.length === 0 && (
          <div className="notif-dropdown-empty">Aucune notification</div>
        )}
        {!loading &&
          !error &&
          items.map((notif) => (
            <div
              key={notif.id}
              className={`notif-dropdown-item ${!notif.read ? 'unread' : ''}`}
            >
              <div className="notif-dropdown-item-icon">
                <i className="ti ti-bell" aria-hidden="true" />
              </div>
              <div
                className="notif-dropdown-item-body"
                onClick={() => markRead(notif.id)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    markRead(notif.id);
                  }
                }}
              >
                <p className="notif-dropdown-item-title">{notif.title}</p>
                {notif.message && (
                  <p className="notif-dropdown-item-message">{notif.message}</p>
                )}
                {notif.time && (
                  <span className="notif-dropdown-item-time">{notif.time}</span>
                )}
              </div>
              <button
                type="button"
                className="notif-dropdown-item-remove"
                title="Supprimer"
                aria-label="Supprimer la notification"
                onClick={() => remove(notif.id)}
              >
                <i className="ti ti-x" aria-hidden="true" />
              </button>
            </div>
          ))}
      </div>

      <div className="notif-dropdown-footer">
        <button
          type="button"
          className="notif-dropdown-action"
          onClick={markAll}
          disabled={unread === 0}
        >
          Tout marquer comme lu
        </button>
        {onClose && (
          <button type="button" className="notif-dropdown-action" onClick={onClose}>
            Fermer
          </button>
        )}
      </div>
    </div>
  );
};

export default NotificationDropdown;
