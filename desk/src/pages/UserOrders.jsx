import React, { useEffect, useState } from 'react';
import { Link, Navigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import { publicCatalogueService } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import './Pages.css';

const getNotifKind = (notif) => {
  const text = `${notif?.message || notif || ''}`.toLowerCase();
  if (/(livr|reçu|termin|valid|confirm|expédi|expedi|ok|succès|succes)/.test(text)) return 'success';
  if (/(annul|retard|erreur|échec|echec|relanc|impay|attention|rappel)/.test(text)) return 'warning';
  return 'info';
};

const UserOrders = () => {
  const { isAuthenticated, user, loading } = useAuth();
  const [notifications, setNotifications] = useState([]);
  const [trackingRef, setTrackingRef] = useState('');
  const [searching, setSearching] = useState(false);

  useEffect(() => {
    if (isAuthenticated) {
      fetchNotifications();
    }
  }, []);

  const fetchNotifications = async (ref) => {
    try {
      setSearching(true);
      const response = await publicCatalogueService.getNotifications(ref || undefined);
      setNotifications(response.data?.notifications || response.data || []);
    } catch (err) {
      console.error('Error fetching notifications:', err);
      if (err.response?.status === 401) {
        toast.error('Session expirée. Veuillez vous reconnecter.');
      }
    } finally {
      setSearching(false);
    }
  };

  const handleTrack = (e) => {
    e.preventDefault();
    fetchNotifications(trackingRef);
  };

  if (loading) {
    return (
      <div className="page-container">
        <div className="loading-screen">
          <div className="spinner-large"></div>
          <p>Chargement...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1>Mes commandes</h1>
          <p>Suivez vos achats et vos notifications</p>
        </div>
        <Link to="/" className="btn-secondary">
          Retour à l'accueil
        </Link>
      </div>

      <div className="orders-card">
        <form onSubmit={handleTrack} className="orders-track">
          <div className="orders-track__field">
            <i className="ti ti-search orders-track__icon" aria-hidden="true" />
            <input
              type="text"
              placeholder="Suivre une commande par référence..."
              value={trackingRef}
              onChange={(e) => setTrackingRef(e.target.value)}
            />
          </div>
          <button type="submit" className="btn-primary orders-track__btn" disabled={searching}>
            <i className="ti ti-search" aria-hidden="true" />
            {searching ? 'Recherche...' : 'Rechercher'}
          </button>
        </form>

        {notifications.length === 0 ? (
          <div className="orders-empty">
            <span className="orders-empty__icon" aria-hidden="true">
              <i className="ti ti-bell-off" />
            </span>
            <p className="orders-empty__text">Aucune notification pour le moment.</p>
            <span className="orders-empty__hint">
              Les mises à jour de vos commandes apparaîtront ici.
            </span>
          </div>
        ) : (
          <ul className="orders-list">
            {notifications.map((notif, idx) => {
              const type = getNotifKind(notif);
              return (
                <li className="orders-list__item" key={idx}>
                  <span
                    className={`orders-list__status orders-list__status--${type}`}
                    aria-hidden="true"
                  >
                    <i
                      className={`ti ${
                        type === 'success'
                          ? 'ti-circle-check'
                          : type === 'warning'
                            ? 'ti-alert-triangle'
                            : 'ti-bell'
                      }`}
                    />
                  </span>
                  <div className="orders-list__body">
                    <p className="orders-list__primary">{notif.message || notif}</p>
                    {notif.created_at && (
                      <p className="orders-list__secondary">{notif.created_at}</p>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
};

export default UserOrders;
