// src/components/layout/NotificationDropdown.jsx
import React from 'react';
import { useDesktop } from '../../contexts/DesktopContext';
import './NotificationDropdown.css';

const NotificationDropdown = ({ onClose }) => {
  const { notifications, markNotificationRead } = useDesktop();

  return (
    <div className="notif-dropdown" onClick={(e) => e.stopPropagation()}>
      <div className="notif-dropdown-header">
        <h3>Notifications</h3>
        <span className="notif-dropdown-count">{notifications.filter((n) => !n.read).length} non lues</span>
      </div>
      <div className="notif-dropdown-list">
        {notifications.length === 0 ? (
          <div className="notif-dropdown-empty">Aucune notification</div>
        ) : (
          notifications.map((notif) => (
            <div
              key={notif.id}
              className={`notif-dropdown-item ${!notif.read ? 'unread' : ''}`}
              onClick={() => markNotificationRead(notif.id)}
            >
              <div className="notif-dropdown-item-icon">
                <i className="ti ti-bell" aria-hidden="true" />
              </div>
              <div className="notif-dropdown-item-body">
                <p className="notif-dropdown-item-title">{notif.title}</p>
                <p className="notif-dropdown-item-message">{notif.message}</p>
                <span className="notif-dropdown-item-time">{notif.time}</span>
              </div>
            </div>
          ))
        )}
      </div>
      <div className="notif-dropdown-footer">
        <button className="notif-dropdown-action" onClick={onClose}>Fermer</button>
      </div>
    </div>
  );
};

export default NotificationDropdown;
