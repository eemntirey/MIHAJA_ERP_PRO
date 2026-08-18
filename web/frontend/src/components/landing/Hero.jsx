// src/components/landing/Hero.jsx
import React, { useEffect, useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { publicCatalogueService } from '../../services/api';
import '../../styles/landing.css';

const Hero = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [productCount, setProductCount] = useState(null);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await publicCatalogueService.getProduits();
        const data = response.data;
        const produits = Array.isArray(data) ? data : data?.produits || data?.items || [];
        setProductCount(produits.length);
      } catch (err) {
        console.error('Error fetching public stats:', err);
      }
    };
    fetchStats();
  }, []);

  const handleDiscoverCatalogue = () => {
    navigate('/catalogue');
  };

  const handleTrackOrder = () => {
    if (location.pathname === '/' || location.pathname === '') {
      const suiviSection = document.getElementById('suivi');
      if (suiviSection) {
        suiviSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        setTimeout(() => {
          const trackingInput = document.getElementById('tracking-ref');
          if (trackingInput) {
            trackingInput.focus();
          }
        }, 400);
      }
    } else {
      navigate('/suivi');
    }
  };

  return (
    <section className="landing-hero">
      <div className="landing-container">
        <div className="landing-hero-grid">
          <div>
            <h1 className="landing-hero-title">
              Fournitures pour hôtels,<br />
              <span className="landing-hero-title-gradient">simplifiées.</span>
            </h1>
            <p className="landing-hero-subtitle">
              ERP Pro centralise vos commandes, votre catalogue et votre suivi
              en temps réel pour les professionnels de l&apos;hôtellerie.
            </p>
            <div className="landing-hero-actions">
              <button type="button" onClick={handleDiscoverCatalogue} className="landing-btn landing-btn-primary">
                Découvrir le catalogue
              </button>
              <button type="button" onClick={handleTrackOrder} className="landing-btn landing-btn-outline">
                Suivre ma commande
              </button>
            </div>
          </div>

          <div className="landing-hero-stats">
            <div className="landing-stat-card">
              <div className="landing-stat-value">
                {productCount !== null ? productCount.toLocaleString('mg-MG') : '...'}
              </div>
              <div className="landing-stat-label">Produits disponibles</div>
            </div>
            <div className="landing-stat-card">
              <div className="landing-stat-value">180+</div>
              <div className="landing-stat-label">Hôtels servis</div>
            </div>
            <div className="landing-stat-card">
              <div className="landing-stat-value">48h</div>
              <div className="landing-stat-label">Livraison express</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default Hero;
