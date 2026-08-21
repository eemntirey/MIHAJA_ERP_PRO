// src/pages/Home.jsx
import React, { useEffect, useState, useRef, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { toast } from 'react-toastify';
import { publicCatalogueService } from '../services/publicApi';
import { authService } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import { useCart } from '../contexts/CartContext';
import { Icon } from '../components/common/Icon';
import './Pages.css';

const getNotifKind = (notif) => {
  const text = `${notif?.message || notif || ''}`.toLowerCase();
  if (/(livr|reçu|termin|valid|confirm|expédi|expedi|ok|succès|succes)/.test(text)) return 'success';
  if (/(annul|retard|erreur|échec|echec|relanc|impay|attention|rappel)/.test(text)) return 'warning';
  return 'info';
};

const Home = () => {
  const { user, isAuthenticated, setUser, logout } = useAuth();
  const { addItem } = useCart();
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [notifications, setNotifications] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [showUserCartouche, setShowUserCartouche] = useState(false);
  const [editingName, setEditingName] = useState(false);
  const [nameForm, setNameForm] = useState({ prenom: '', nom: '' });
  const userMenuRef = useRef(null);

  const isUser = user?.role === 'USER' || user?.role === 'user';

  useEffect(() => {
    fetchProducts();
    if (isUser && isAuthenticated) {
      fetchNotifications();
    }
  }, []);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (userMenuRef.current && !userMenuRef.current.contains(event.target)) {
        setShowUserCartouche(false);
        setEditingName(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const fetchProducts = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await publicCatalogueService.getProduits();
      const data = response.data?.produits || response.data || [];
      setProducts(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Error fetching public products:', err);
      const msg = err.response?.data?.message || 'Échec du chargement du catalogue';
      setError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  const fetchNotifications = async (ref) => {
    try {
      const response = await publicCatalogueService.getNotifications(ref);
      setNotifications(response.data?.notifications || response.data || []);
    } catch (err) {
      console.error('Error fetching notifications:', err);
    }
  };

  const handleSearch = (e) => {
    e.preventDefault();
    fetchNotifications(searchQuery || undefined);
  };

  const openUserMenu = () => {
    setShowUserCartouche(true);
    setEditingName(false);
    setNameForm({
      prenom: user?.prenom || '',
      nom: user?.nom || '',
    });
  };

  const startEditName = () => {
    setEditingName(true);
  };

  const saveName = async () => {
    try {
      await authService.updateMe({ prenom: nameForm.prenom, nom: nameForm.nom });
      setUser((prev) => ({
        ...prev,
        prenom: nameForm.prenom,
        nom: nameForm.nom,
      }));
      setEditingName(false);
      toast.success('Profil mis à jour');
    } catch (err) {
      toast.error('Erreur lors de la mise à jour');
    }
  };

  const handleLogout = () => {
    logout();
    setShowUserCartouche(false);
    setEditingName(false);
  };

  const filteredProducts = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return products;
    return products.filter((p) => {
      const haystack = `${p.nom || ''} ${p.tenant_nom || ''} ${p.description_courte || ''}`.toLowerCase();
      return haystack.includes(q);
    });
  }, [products, searchQuery]);

  return (
    <div className="home-page">
      <div className="home-content page-container">
        {!isAuthenticated && (
          <section className="home-cta-section">
            <div className="home-cta-card">
              <div className="home-cta-content">
                <h1>Bienvenue sur ERP Pro</h1>
                <p>
                  La plateforme de gestion intégrée pour les entreprises et les particuliers.
                  Accédez au catalogue public ou gérez votre activité avec nos outils ERP.
                </p>
                <div className="home-cta-actions">
                  <Link to="/register" className="btn-primary btn-erp-cta">
                    Se connecter à l'ERP
                  </Link>
                  <Link to="#catalogue" className="btn-secondary">
                    Découvrir le catalogue
                  </Link>
                </div>
              </div>
              <div className="home-cta-visual" aria-hidden="true">
                <div className="home-cta-orb home-cta-orb--1" />
                <div className="home-cta-orb home-cta-orb--2" />
                <div className="home-cta-orb home-cta-orb--3" />
              </div>
            </div>

            <div className="home-profiles-grid">
              <Link to="/register/simple" className="home-profile-card">
                  <div className="home-profile-icon">
                    <Icon name="user" />
                  </div>
                <h3>Utilisateur Simple</h3>
                <p>
                  Inscription rapide. Accédez au catalogue public, consultez les fiches
                  produits et passez commande.
                </p>
                <span className="home-profile-cta">
                  S'inscrire comme client
                  <Icon name="arrow-right" />
                </span>
              </Link>

              <Link to="/register/company" className="home-profile-card">
                  <div className="home-profile-icon">
                    <Icon name="building" />
                  </div>
                <h3>Grossiste / Entreprise</h3>
                <p>
                  Accédez au tableau de bord, à la gestion des stocks, aux ventes,
                  factures et abonnements.
                </p>
                <span className="home-profile-cta">
                  S'inscrire comme entreprise
                  <Icon name="arrow-right" />
                </span>
              </Link>
            </div>
          </section>
        )}

        {isUser && isAuthenticated && (
          <section className="orders-card">
            <div className="orders-card__header">
              <div className="orders-card__heading">
                <span className="orders-card__icon" aria-hidden="true">
                  <Icon name="package" />
                </span>
                <div>
                  <h2 className="orders-card__title">Mes commandes</h2>
                  <p className="orders-card__subtitle">Suivez vos achats et vos notifications</p>
                </div>
              </div>
              {notifications.length > 0 && (
                <span className="orders-card__badge">{notifications.length}</span>
              )}
            </div>

            <form onSubmit={handleSearch} className="orders-track">
              <div className="orders-track__field">
                <Icon name="search" className="orders-track__icon" />
                <input
                  type="text"
                  placeholder="Rechercher un produit par nom ou vendeur..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
              <button type="submit" className="btn-primary orders-track__btn">
                <Icon name="search" />
                Rechercher
              </button>
            </form>

            {notifications.length === 0 ? (
              <div className="orders-empty">
                <span className="orders-empty__icon" aria-hidden="true">
                  <Icon name="bell-off" />
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
                      <span className={`orders-list__status orders-list__status--${type}`} aria-hidden="true">
                        <Icon
                          name={
                            type === 'success'
                              ? 'circle-check'
                              : type === 'warning'
                                ? 'alert-triangle'
                                : 'bell'
                          }
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
          </section>
        )}

        {isAuthenticated && isUser && (
          <div className="user-cartouche-wrapper" ref={userMenuRef}>
            <button
              type="button"
              className="user-cartouche-trigger"
              onClick={openUserMenu}
              aria-haspopup="true"
              aria-expanded={showUserCartouche}
            >
              <span className="user-cartouche-avatar">
                {(user?.prenom?.[0] || 'U').toUpperCase()}
              </span>
              <span className="user-cartouche-greeting">
                Bienvenue, {user?.prenom || 'Utilisateur'}
              </span>
              <span className="user-cartouche-chevron" aria-hidden="true">
                ▾
              </span>
            </button>

            {showUserCartouche && (
              <div className="user-cartouche">
                <div className="user-cartouche-header">
                  <div className="user-cartouche-avatar-large">
                    {(user?.prenom?.[0] || 'U').toUpperCase()}
                  </div>
                  <div className="user-cartouche-meta">
                    {editingName ? (
                      <div className="user-cartouche-edit-form">
                        <input
                          type="text"
                          value={nameForm.prenom}
                          onChange={(e) => setNameForm((prev) => ({ ...prev, prenom: e.target.value }))}
                          placeholder="Prénom"
                          className="user-cartouche-input"
                        />
                        <input
                          type="text"
                          value={nameForm.nom}
                          onChange={(e) => setNameForm((prev) => ({ ...prev, nom: e.target.value }))}
                          placeholder="Nom"
                          className="user-cartouche-input"
                        />
                        <button
                          type="button"
                          className="user-cartouche-save"
                          onClick={saveName}
                        >
                          Enregistrer
                        </button>
                      </div>
                    ) : (
                      <>
                        <strong>{user?.prenom} {user?.nom}</strong>
                        <span>{user?.email}</span>
                        <button
                          type="button"
                          className="user-cartouche-edit"
                          onClick={startEditName}
                        >
                          Modifier mon nom
                        </button>
                      </>
                    )}
                  </div>
                </div>
                <div className="user-cartouche-footer">
                  <Link to="/mes-commandes" className="user-cartouche-orders">
                    Mes commandes
                  </Link>
                  <button
                    type="button"
                    className="user-cartouche-logout"
                    onClick={handleLogout}
                  >
                    Se déconnecter
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        <section id="catalogue">
          <div className="catalog-card">
            <div className="catalog-card__header">
              <span className="catalog-card__icon" aria-hidden="true">
                <Icon name="layout-grid" />
              </span>
              <div>
                <h2 className="catalog-card__title">Catalogue public</h2>
                <p className="catalog-card__subtitle">Découvrez nos produits disponibles</p>
              </div>
            </div>
          </div>

          {loading && (
            <div className="loading-screen">
              <div className="spinner-large"></div>
              <p>Chargement du catalogue...</p>
            </div>
          )}

          {error && (
            <div className="alert error">
              <p>{error}</p>
              <button onClick={fetchProducts} className="btn-primary">Réessayer</button>
            </div>
          )}

          {!loading && !error && (
            <div className="home-products-grid">
              {products.length === 0 ? (
                <div className="card full-width">
                  <p className="text-muted">Aucun produit disponible pour le moment. Aucun vendeur n'est actif.</p>
                </div>
              ) : filteredProducts.length === 0 ? (
                <div className="card full-width catalog-search-empty">
                  <span className="catalog-search-empty__icon" aria-hidden="true">
                    <Icon name="search-off" />
                  </span>
                  <p className="catalog-search-empty__text">
                    Aucun produit ne correspond à « {searchQuery} ».
                  </p>
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => setSearchQuery('')}
                  >
                    Réinitialiser la recherche
                  </button>
                </div>
              ) : (
                filteredProducts.map((product) => (
                  <div className="card product-card" key={product.id}>
                    <div className="product-card__header">
                      <h3>{product.nom}</h3>
                      <span className="badge success">En stock</span>
                    </div>
                    {product.tenant_nom && (
                      <p style={{ fontSize: '12px', color: 'var(--color-text-secondary)', marginBottom: '8px' }}>
                        Vendu par <strong>{product.tenant_nom}</strong>
                      </p>
                    )}
                    <p className="product-card__price">{Number(product.prix_vente_ht || product.prix || 0).toFixed(2)} Ar</p>
                    <p className="text-muted" style={{ fontSize: '12px', marginBottom: '12px' }}>
                      Stock: {product.quantite_stock ?? product.stock ?? 0}
                    </p>
                    {product.description_courte && (
                      <p style={{ fontSize: '13px', marginBottom: '16px', color: 'var(--color-text-secondary)' }}>
                        {product.description_courte}
                      </p>
                    )}
                    {isUser && isAuthenticated ? (
                      <div className="product-card__actions" style={{ display: 'flex', gap: '8px' }}>
                        <Link
                          to={`/produits/${product.id}`}
                          className="btn-secondary"
                          style={{ flex: 1, justifyContent: 'center' }}
                        >
                          Détails
                        </Link>
                        <button
                          type="button"
                          className="btn-primary"
                          style={{ flex: 1, justifyContent: 'center' }}
                          onClick={() => {
                            addItem(product, 1);
                            toast.success(`${product.nom} ajouté au panier`);
                          }}
                          disabled={Number(product.quantite_stock ?? product.stock ?? 0) <= 0}
                        >
                          + Panier
                        </button>
                      </div>
                    ) : (
                      <Link to={`/produits/${product.id}`} className="btn-primary" style={{ width: '100%', justifyContent: 'center' }}>
                        Voir le produit
                      </Link>
                    )}
                  </div>
                ))
              )}
            </div>
          )}
        </section>
      </div>
    </div>
  );
};

export default Home;
