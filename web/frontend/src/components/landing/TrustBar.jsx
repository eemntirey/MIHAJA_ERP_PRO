// src/components/landing/TrustBar.jsx
import React from 'react';
import '../../styles/landing.css';

const TrustBar = () => {
  const items = [
    {
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <rect x="1" y="3" width="15" height="13" />
          <polygon points="16 8 20 8 23 11 23 16 16 16 16 8" />
          <circle cx="5.5" cy="18.5" r="2.5" />
          <circle cx="18.5" cy="18.5" r="2.5" />
        </svg>
      ),
      title: 'Livraison rapide',
       text: 'Livraison rapide dans tout Madagascar',
    },
    {
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
          <path d="M7 11V7a5 5 0 0 1 10 0v4" />
        </svg>
      ),
      title: 'Paiement sécurisé',
      text: 'Transactions chiffrées et protégées',
    },
    {
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
        </svg>
      ),
      title: 'Qualité certifiée',
      text: 'Produits sélectionnés pour les hôtels',
    },
    {
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </svg>
      ),
      title: 'Support 7j/7',
      text: 'Équipe dédiée à votre service',
    },
  ];

  return (
    <section className="landing-trust" aria-label="Confiance">
      <div className="landing-container">
        <div className="landing-trust-grid">
          {items.map((item, index) => (
            <div className="landing-trust-item" key={index}>
              <span className="landing-trust-icon">{item.icon}</span>
              <span className="landing-trust-text">
                <strong>{item.title}</strong>
                <span>{item.text}</span>
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default TrustBar;
