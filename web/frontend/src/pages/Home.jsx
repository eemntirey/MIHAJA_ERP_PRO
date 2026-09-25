// src/pages/Home.jsx
import React, { useEffect, useState, useRef, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { toast } from 'react-toastify';
import { publicCatalogueService, authService } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import { useCart } from '../contexts/CartContext';
import Seo from '../components/Seo';
import './Pages.css';

const HOME_SEO_DATA = {
  '@context': 'https://schema.org',
  '@graph': [
    {
      '@type': 'Organization',
      name: 'MIHAJA ERP PRO',
      url: 'https://mihaja-erp-frontend-796e-qdh1.onrender.com/',
      description: 'ERP SaaS pour les entreprises à Madagascar.',
    },
    {
      '@type': 'WebSite',
      name: 'MIHAJA ERP PRO',
      url: 'https://mihaja-erp-frontend-796e-qdh1.onrender.com/',
      inLanguage: 'fr',
    },
  ],
};

const getNotifKind = (notif) => {
  const text = `${notif?.message || notif || ''}`.toLowerCase();
  if (/(livr|reçu|termin|valid|confirm|expédi|expedi|ok|succès|succes)/.test(text)) return 'success';
  if (/(annul|retard|erreur|échec|echec|relanc|impay|attention|rappel)/.test(text)) return 'warning';
  return 'info';
};

const FEATURES = [
  {
    icon: 'ti ti-package',
    title: 'Gestion des stocks',
    desc: 'Suivi en temps réel de vos inventaires, alertes de rupture et seuils de réapprovisionnement automatiques.',
  },
  {
    icon: 'ti ti-receipt',
    title: 'Facturation rapide',
    desc: 'Génération automatique de factures, devis et bons de commande conformes à la réglementation malgache.',
  },
  {
    icon: 'ti ti-users',
    title: 'Gestion clientèle',
    desc: 'Base de données centralisée de vos clients, historique des achats et programmes de fidélité.',
  },
  {
    icon: 'ti ti-chart-bar',
    title: 'Tableau de bord',
    desc: 'Indicateurs clés de performance, graphiques dynamiques et rapports pour piloter votre activité.',
  },
  {
    icon: 'ti ti-truck-delivery',
    title: 'Livraison & suivi',
    desc: 'Gestion des livraisons, suivi des commandes en temps réel et notifications automatiques.',
  },
  {
    icon: 'ti ti-device-mobile',
    title: 'Multi-plateforme',
    desc: 'Accessible depuis ordinateur, tablette et mobile. Application de bureau pour une utilisation intensive.',
  },
];

const STATS = [
  { value: '500+', label: 'Entreprises actives' },
  { value: '10 000+', label: 'Produits gérés' },
  { value: '99.9%', label: 'Disponibilité' },
  { value: '24/7', label: 'Support technique' },
];

const TESTIMONIALS = [
  {
    name: 'Rakoto Jean',
    role: 'Directeur, Teknisyo SARL',
    text: 'ERP Pro a transformé notre gestion des stocks. Nous avons réduit les pertes de 40% en seulement 3 mois.',
    avatar: 'RJ',
  },
  {
    name: 'Rasoa Hélène',
    role: 'Gérante, Boutique Tolagnaro',
    text: 'La facturation est devenue un jeu d\'enfant. Je recommande vivement cette solution pour toute PME à Madagascar.',
    avatar: 'RH',
  },
  {
    name: 'Andry Rabe',
    role: 'Chef comptable, MadaImport',
    text: 'Le tableau de bord nous donne une visibilité instantanée sur notre activité. Un outil indispensable.',
    avatar: 'AR',
  },
];

const Home = () => {
  const { user, isAuthenticated, setUser, logout } = useAuth();
  const { addItem, totalItems } = useCart();
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [notifications, setNotifications] = useState([]);
  const [trackingRef, setTrackingRef] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [showUserCartouche, setShowUserCartouche] = useState(false);
  const [editingName, setEditingName] = useState(false);
  const [nameForm, setNameForm] = useState({ prenom: '', nom: '' });
  const userMenuRef = useRef(null);

  const isUser = user?.role === 'USER' || user?.role === 'user';
  const role = (user?.role || '').toLowerCase();

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
      if (!ref) {
        const res = await publicCatalogueService.getMesCommandes();
        const commandes = res.data?.commandes || [];
        setNotifications(commandes.map((c) => ({
          message: `${c.reference} — ${(c.statut || '').replace('_', ' ')}`,
          created_at: c.created_at,
          statut: c.statut,
          reference: c.reference,
        })));
        return;
      }
      const response = await publicCatalogueService.getNotifications(ref);
      setNotifications(response.data?.notifications || response.data || []);
    } catch (err) {
      console.error('Error fetching notifications:', err);
      const status = err.response?.status;
      if (ref && status === 404) {
        toast.error('Aucune commande trouvée pour cette référence.');
      } else if (status !== 401) {
        toast.error('Impossible de charger vos commandes.');
      }
      setNotifications([]);
    }
  };

  const handleTrackOrder = (e) => {
    e.preventDefault();
    const ref = (trackingRef || '').trim();
    if (!ref) {
      toast.warn('Saisissez une référence de commande.');
      return;
    }
    fetchNotifications(ref);
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
    <>
      <Seo
        title="MIHAJA ERP PRO | ERP SaaS pour les entreprises à Madagascar"
        description="MIHAJA ERP PRO est un ERP SaaS pour gérer stocks, ventes, achats, factures, clients et livraisons pour les entreprises à Madagascar."
        canonical="https://mihaja-erp-frontend-796e-qdh1.onrender.com/"
        structuredData={HOME_SEO_DATA}
      />
      <div className="home-page">
      {/* ── Header ── */}
      <header className="public-header">
        <Link to="/" className="brand">
          <span className="brand-icon">EP</span>
          <span className="brand-name">ERP Pro</span>
        </Link>
        <nav className="public-nav">
          <a href="#telechargements" className="public-nav-link">Téléchargements</a>
          {isAuthenticated ? (
            <>
              {isUser && (
                <div className="user-cartouche-wrapper" ref={userMenuRef}>
                  <button
                    type="button"
                    className="user-cartouche-trigger"
                    onClick={openUserMenu}
                    aria-haspopup="true"
                    aria-expanded={showUserCartouche}
                  >
                    <span className="user-cartouche-avatar" aria-hidden="true">
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
                        <div className="user-cartouche-avatar-large" aria-hidden="true">
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
               {!isUser && (
                 <Link to="/dashboard" className="public-nav-link">Tableau de bord</Link>
               )}
               {isUser && (
                 <Link to="/cart" className="public-nav-link btn-cart-link" aria-label="Mon panier">
                   Panier
                   {totalItems > 0 && (
                     <span className="cart-badge">{totalItems}</span>
                   )}
                 </Link>
               )}
             </>
           ) : (
            <>
              <Link to="/catalogue" className="public-nav-link">Catalogue</Link>
              <a href="#telechargements" className="public-nav-link">Télécharger</a>
              <Link to="/login" className="public-nav-link btn-nav-login">Connexion</Link>
              <Link to="/register" className="public-nav-link btn-nav-register">S'inscrire</Link>
            </>
          )}
        </nav>
      </header>

      {/* ── Main Content ── */}
      <main className="home-content">
        {/* ── Hero Section ── */}
        {!isAuthenticated && (
          <section className="vit-hero">
            <div className="vit-hero__bg">
              <div className="vit-hero__orb vit-hero__orb--1" />
              <div className="vit-hero__orb vit-hero__orb--2" />
              <div className="vit-hero__orb vit-hero__orb--3" />
            </div>
            <div className="vit-hero__inner">
              <span className="vit-hero__badge">
                <i className="ti ti-sparkles" aria-hidden="true" />
                Solution ERP Made in Madagascar
              </span>
              <h1 className="vit-hero__title">
                Gérez votre entreprise
                <span className="vit-hero__title-accent"> en toute simplicité</span>
              </h1>
              <p className="vit-hero__subtitle">
                ERP Pro est la plateforme de gestion intégrée conçue pour les PME malgaches.
                Stocks, facturation, ventes, livraisons — tout est réuni dans un seul outil intuitif.
              </p>
              <div className="vit-hero__actions">
                <Link to="/register/company" className="vit-btn vit-btn--primary vit-btn--lg">
                  <i className="ti ti-rocket" aria-hidden="true" />
                  Commencer gratuitement
                </Link>
                <Link to="/catalogue" className="vit-btn vit-btn--outline vit-btn--lg">
                  <i className="ti ti-eye" aria-hidden="true" />
                  Voir le catalogue
                </Link>
              </div>
              <p className="vit-hero__note">
                <i className="ti ti-shield-check" aria-hidden="true" />
                Essai gratuit 14 jours — Aucune carte bancaire requise
              </p>
            </div>
          </section>
        )}

        {/* ── Authenticated: orders ── */}
        {isUser && isAuthenticated && (
          <section className={`orders-card${notifications.length === 0 ? ' is-empty' : ''}`}>
            <div className="orders-card__header">
              <div className="orders-card__heading">
                <span className="orders-card__icon" aria-hidden="true">
                  <i className="ti ti-package" />
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

            <form onSubmit={handleTrackOrder} className="orders-track">
              <div className="orders-track__field">
                <i className="ti ti-search orders-track__icon" aria-hidden="true" />
                <input
                  type="text"
                  placeholder="Suivre une commande par référence..."
                  value={trackingRef}
                  onChange={(e) => setTrackingRef(e.target.value)}
                  aria-label="Référence de commande"
                />
              </div>
              <button type="submit" className="btn-primary orders-track__btn">
                <i className="ti ti-search" aria-hidden="true" />
                Rechercher
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
                      <span className={`orders-list__status orders-list__status--${type}`} aria-hidden="true">
                        <i className={`ti ${type === 'success' ? 'ti-circle-check' : type === 'warning' ? 'ti-alert-triangle' : 'ti-bell'}`} />
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

        {/* ── Public Sections (unauthenticated) ── */}
        {!isAuthenticated && (
          <>
            {/* ── Stats Bar ── */}
            <section className="vit-stats">
              {STATS.map((s) => (
                <div className="vit-stats__item" key={s.label}>
                  <span className="vit-stats__value">{s.value}</span>
                  <span className="vit-stats__label">{s.label}</span>
                </div>
              ))}
            </section>

            {/* ── Features ── */}
            <section className="vit-features" id="fonctionnalites">
              <div className="vit-section-header">
                <span className="vit-section-tag">Fonctionnalités</span>
                <h2 className="vit-section-title">Tout ce dont vous avez besoin</h2>
                <p className="vit-section-subtitle">
                  Une suite complète d'outils pour gérer chaque aspect de votre activité.
                </p>
              </div>
              <div className="vit-features__grid">
                {FEATURES.map((f) => (
                  <div className="vit-feature-card" key={f.title}>
                    <div className="vit-feature-card__icon">
                      <i className={`ti ${f.icon}`} aria-hidden="true" />
                    </div>
                    <h3 className="vit-feature-card__title">{f.title}</h3>
                    <p className="vit-feature-card__desc">{f.desc}</p>
                  </div>
                ))}
              </div>
            </section>

            {/* ── How it works ── */}
            <section className="vit-how">
              <div className="vit-section-header">
                <span className="vit-section-tag">Comment ça marche</span>
                <h2 className="vit-section-title">Simple, rapide, efficace</h2>
                <p className="vit-section-subtitle">
                  En trois étapes, lancez la gestion de votre entreprise.
                </p>
              </div>
              <div className="vit-how__steps">
                <div className="vit-how__step">
                  <div className="vit-how__number">1</div>
                  <h3>Créez votre compte</h3>
                  <p>Inscription en quelques secondes. Aucune carte bancaire nécessaire pour démarrer.</p>
                </div>
                <div className="vit-how__connector" aria-hidden="true">
                  <i className="ti ti-arrow-right" />
                </div>
                <div className="vit-how__step">
                  <div className="vit-how__number">2</div>
                  <h3>Ajoutez vos produits</h3>
                  <p>Importez votre catalogue ou créez vos fiches produits avec photos et descriptions.</p>
                </div>
                <div className="vit-how__connector" aria-hidden="true">
                  <i className="ti ti-arrow-right" />
                </div>
                <div className="vit-how__step">
                  <div className="vit-how__number">3</div>
                  <h3>Vendez et livrez</h3>
                  <p>Générez vos factures, suivez vos commandes et gérez vos livraisons en un clic.</p>
                </div>
              </div>
            </section>

            {/* ── Registration CTA ── */}
            <section className="vit-register-cta">
              <div className="vit-register-cta__inner">
                <h2 className="vit-register-cta__title">Choisissez votre profil</h2>
                <p className="vit-register-cta__subtitle">
                  Que vous soyez client ou entreprise, ERP Pro s'adapte à vos besoins.
                </p>
                <div className="vit-register-cta__cards">
                  <Link to="/register/simple" className="vit-register-card">
                    <div className="vit-register-card__icon">
                      <i className="ti ti-user" aria-hidden="true" />
                    </div>
                    <h3>Client / Particulier</h3>
                    <p>
                      Parcourez le catalogue, consultez les fiches produits et passez commande
                      en toute simplicité.
                    </p>
                    <span className="vit-register-card__cta">
                      Créer un compte client
                      <i className="ti ti-arrow-right" aria-hidden="true" />
                    </span>
                  </Link>

                  <Link to="/register/company" className="vit-register-card vit-register-card--featured">
                    <div className="vit-register-card__icon">
                      <i className="ti ti-building" aria-hidden="true" />
                    </div>
                    <h3>Entreprise / Grossiste</h3>
                    <p>
                      Accédez au tableau de bord complet : stocks, ventes, factures,
                      livraisons, comptabilité et plus.
                    </p>
                    <span className="vit-register-card__cta">
                      Créer un compte entreprise
                      <i className="ti ti-arrow-right" aria-hidden="true" />
                    </span>
                  </Link>
                </div>
              </div>
            </section>

            {/* ── Testimonials ── */}
            <section className="vit-testimonials">
              <div className="vit-section-header">
                <span className="vit-section-tag">Témoignages</span>
                <h2 className="vit-section-title">Ils nous font confiance</h2>
                <p className="vit-section-subtitle">
                  Découvrez ce que nos clients disent de leur expérience avec ERP Pro.
                </p>
              </div>
              <div className="vit-testimonials__grid">
                {TESTIMONIALS.map((t) => (
                  <div className="vit-testimonial-card" key={t.name}>
                    <div className="vit-testimonial-card__quote">
                      <i className="ti ti-quote" aria-hidden="true" />
                    </div>
                    <p className="vit-testimonial-card__text">{t.text}</p>
                    <div className="vit-testimonial-card__author">
                      <div className="vit-testimonial-card__avatar">{t.avatar}</div>
                      <div>
                        <strong className="vit-testimonial-card__name">{t.name}</strong>
                        <span className="vit-testimonial-card__role">{t.role}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </section>

            {/* ── Downloads ── */}
            <section className="vit-downloads" id="telechargements">
              <div className="vit-section-header">
                <span className="vit-section-tag">
                  <i className="ti ti-download" aria-hidden="true" />
                  Applications
                </span>
                <h2 className="vit-section-title">Téléchargez MIHAJA ERP PRO</h2>
                <p className="vit-section-subtitle">
                  Utilisez MIHAJA ERP PRO sur votre ordinateur dès maintenant.
                </p>
              </div>

              <div className="vit-downloads__grid">
                <a
                  className="vit-download-card"
                  href="https://github.com/eemntirey/MIHAJA_ERP_PRO/releases/download/desktop-latest/MIHAJA-ERP-PRO-Setup.exe"
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label="Télécharger MIHAJA ERP PRO pour Windows"
                >
                  <span className="vit-download-card__icon" aria-hidden="true">
                    <i className="ti ti-brand-windows" />
                  </span>
                  <span className="vit-download-card__content">
                    <strong>Windows — Desktop</strong>
                    <span>Installer MIHAJA ERP PRO pour Windows</span>
                  </span>
                  <i className="ti ti-arrow-down" aria-hidden="true" />
                </a>

                <div className="vit-download-card vit-download-card--disabled" aria-disabled="true">
                  <span className="vit-download-card__icon" aria-hidden="true">
                    <i className="ti ti-brand-android" />
                  </span>
                  <span className="vit-download-card__content">
                    <strong>Android</strong>
                    <span>Bientôt disponible sur Google Play</span>
                  </span>
                  <span className="vit-download-card__status">Bientôt</span>
                </div>

                <div className="vit-download-card vit-download-card--disabled" aria-disabled="true">
                  <span className="vit-download-card__icon" aria-hidden="true">
                    <i className="ti ti-brand-apple" />
                  </span>
                  <span className="vit-download-card__content">
                    <strong>iPhone / iPad</strong>
                    <span>Bientôt disponible sur l’App Store</span>
                  </span>
                  <span className="vit-download-card__status">Bientôt</span>
                </div>
              </div>
            </section>

            {/* ── Final CTA ── */}
            <section className="vit-final-cta">
              <div className="vit-final-cta__inner">
                <h2>Prêt à moderniser votre entreprise ?</h2>
                <p>Rejoignez des centaines d'entreprises qui font déjà confiance à ERP Pro.</p>
                <div className="vit-final-cta__actions">
                  <Link to="/register/company" className="vit-btn vit-btn--primary vit-btn--lg">
                    <i className="ti ti-rocket" aria-hidden="true" />
                    Démarrer maintenant
                  </Link>
                  <Link to="/contact" className="vit-btn vit-btn--glass vit-btn--lg">
                    <i className="ti ti-mail" aria-hidden="true" />
                    Nous contacter
                  </Link>
                </div>
              </div>
            </section>
          </>
        )}

        {/* ── Catalogue (always visible) ── */}
        <section id="catalogue" className="vit-catalogue">
          <div className="vit-section-header">
            <span className="vit-section-tag">
              <i className="ti ti-layout-grid" aria-hidden="true" />
              Catalogue
            </span>
            <h2 className="vit-section-title">Nos produits disponibles</h2>
            <p className="vit-section-subtitle">
              Explorez notre catalogue et découvrez les offres de nos partenaires.
            </p>
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
            <>
              <div className="vit-catalogue-search" role="search">
                <i className="ti ti-search" aria-hidden="true" />
                <input
                  type="search"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Rechercher un produit ou un vendeur..."
                  aria-label="Rechercher dans le catalogue"
                />
                {searchQuery && (
                  <button
                    type="button"
                    className="vit-catalogue-search__clear"
                    onClick={() => setSearchQuery('')}
                    aria-label="Effacer la recherche"
                  >
                    <i className="ti ti-x" aria-hidden="true" />
                  </button>
                )}
              </div>
              <div className="home-products-grid">
              {products.length === 0 ? (
                <div className="card full-width vit-catalogue-empty">
                  <i className="ti ti-package-off vit-catalogue-empty__icon" aria-hidden="true" />
                  <p className="vit-catalogue-empty__text">
                    Aucun produit disponible pour le moment.
                  </p>
                  <p className="vit-catalogue-empty__hint">
                    Revenez bientôt, nos partenaires ajoutent régulièrement de nouveaux articles.
                  </p>
                </div>
              ) : filteredProducts.length === 0 ? (
                <div className="card full-width vit-catalogue-empty">
                  <i className="ti ti-search-off vit-catalogue-empty__icon" aria-hidden="true" />
                  <p className="vit-catalogue-empty__text">
                    Aucun produit ne correspond à « {searchQuery} ».
                  </p>
                  <button
                    type="button"
                    className="vit-btn vit-btn--outline"
                    onClick={() => setSearchQuery('')}
                  >
                    Réinitialiser la recherche
                  </button>
                </div>
              ) : (
                filteredProducts.map((product) => (
                  <div className="vit-product-card" key={product.id}>
                    {product.image_url && (
                      <div className="vit-product-card__image">
                        <img src={product.image_url} alt={product.nom} loading="lazy" />
                      </div>
                    )}
                    <div className="vit-product-card__body">
                      <h3 className="vit-product-card__name">{product.nom}</h3>
                      {product.tenant_nom && (
                        <span className="vit-product-card__seller">
                          <i className="ti ti-building-store" aria-hidden="true" />
                          {product.tenant_nom}
                        </span>
                      )}
                      <p className="vit-product-card__price">
                        {Number(product.prix_vente_ht || product.prix || 0).toLocaleString('fr-MG')} Ar
                      </p>
                      {product.description_courte && (
                        <p className="vit-product-card__desc">{product.description_courte}</p>
                      )}
                      <div className="vit-product-card__actions">
                        <Link
                          to={`/produits/${product.id}`}
                          className="vit-btn vit-btn--outline vit-btn--sm"
                        >
                          <i className="ti ti-eye" aria-hidden="true" />
                          Détails
                        </Link>
                        {isUser && (
                          <button
                            type="button"
                            className="vit-btn vit-btn--primary vit-btn--sm"
                            onClick={() => {
                              addItem(product, 1);
                              toast.success(`${product.nom} ajouté au panier`);
                            }}
                          >
                            <i className="ti ti-shopping-cart-plus" aria-hidden="true" />
                            Ajouter
                          </button>
                        )}
                        {!isAuthenticated && (
                          <Link
                            to={`/produits/${product.id}`}
                            className="vit-btn vit-btn--primary vit-btn--sm"
                          >
                            <i className="ti ti-shopping-cart" aria-hidden="true" />
                            Voir le produit
                          </Link>
                        )}
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
            </>
          )}
        </section>
      </main>

      {/* ── Footer ── */}
      {!isAuthenticated && (
        <footer className="vit-footer">
          <div className="vit-footer__inner">
            <div className="vit-footer__top">
              <div className="vit-footer__brand">
                <Link to="/" className="brand">
                  <span className="brand-icon">EP</span>
                  <span className="brand-name">ERP Pro</span>
                </Link>
                <p className="vit-footer__tagline">
                  La solution de gestion intégrée pour les entreprises malgaches.
                  Simple, puissante, accessible.
                </p>
              </div>

              <div className="vit-footer__links">
                <div className="vit-footer__col">
                  <h4>Plateforme</h4>
                  <Link to="/catalogue">Catalogue</Link>
                  <Link to="/register/company">Inscription entreprise</Link>
                  <Link to="/register/simple">Inscription client</Link>
                  <Link to="/login">Connexion</Link>
                </div>
                <div className="vit-footer__col">
                  <h4>Ressources</h4>
                  <a href="#telechargements">Télécharger les applications</a>
                  <Link to="/documentation">Documentation</Link>
                  <a href="mailto:support@mihaja.mg">Support technique</a>
                  <a href="tel:+261340000000">Contact commercial</a>
                </div>
                <div className="vit-footer__col">
                  <h4>Entreprise</h4>
                  <Link to="/contact">Contactez-nous</Link>
                  <Link to="/terms">Mentions légales</Link>
                  <Link to="/privacy">Politique de confidentialité</Link>
                </div>
              </div>
            </div>

            <div className="vit-footer__bottom">
              <p>&copy; {new Date().getFullYear()} ERP Pro — MIHAJA. Tous droits réservés.</p>
              <p className="vit-footer__location">
                <i className="ti ti-map-pin" aria-hidden="true" />
                Antananarivo, Madagascar
              </p>
            </div>
          </div>
        </footer>
      )}
      </div>
    </>
  );
};

export default Home;
