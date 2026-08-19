// src/components/layout/NotificationDropdown.jsx
import React, { useCallback } from 'react';
import { useDesktop } from '../../contexts/DesktopContext';
import './NotificationDropdown.css';

const formatTime = (value) => {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  const diff = (Date.now() - date.getTime()) / 1000;
  if (diff < 60) return "a l'instant";
  if (diff < 3600) return `il y a ${Math.floor(diff / 60)} min`;
  if (diff < 86400) return `il y a ${Math.floor(diff / 3600)} h`;
  return date.toLocaleDateString();
};

/**
 * Affiche les notifications depuis DesktopContext (state local).
 * L'endpoint /notifications n'existe pas cote backend ; on evite tout appel reseau.
 */
const NotificationDropdown = ({ onClose }) => {
  const { notifications, markNotificationRead } = useDesktop();

  const items = notifications.map((n) => ({
    id: n.id,
    title: n.titre || n.title || 'Notification',
    message: n.message || n.contenu || n.detail || n.description || '',
    time: typeof n.time === 'string' && !n.time.includes('T')
      ? n.time
      : formatTime(n.created_at || n.date || n.time),
    read: !!(n.lu || n.read),
  }));

  const unread = items.filter((n) => !n.read).length;

  const markRead = useCallback((id) => {
    markNotificationRead(id);
  }, [markNotificationRead]);

  const markAll = useCallback(() => {
    notifications.forEach((n) => {
      if (!n.read) markNotificationRead(n.id);
    });
  }, [notifications, markNotificationRead]);

  return (
    <div className="notif-dropdown" onClick={(e) => e.stopPropagation()}>
      <div className="notif-dropdown-header">
        <h3>Notifications</h3>
        <span className="notif-dropdown-count">{unread} non lue(s)</span>
      </div>

      <div className="notif-dropdown-list">
        {items.length === 0 && (
          <div className="notif-dropdown-empty">Aucune notification</div>
        )}
        {items.map((notif) => (
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
