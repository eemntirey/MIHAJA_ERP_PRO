// src/components/landing/Testimonials.jsx
import React from 'react';
import '../../styles/landing.css';

const Testimonials = () => {
  const stars = (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" stroke="none">
      <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
    </svg>
  );

  const testimonials = [
    {
      quote: 'ERP Pro a transformé notre gestion des commandes. La livraison est rapide et le support impeccable.',
      name: 'Marie Dupont',
      hotel: 'Hôtel Le Grand Paris',
    },
    {
      quote: 'Interface intuitive, catalogue complet. Nous gagnons un temps précieux au quotidien.',
      name: 'Jean Lefèvre',
      hotel: 'Hôtel Riviera Nice',
    },
    {
      quote: 'Le suivi en temps réel est un vrai plus. Je recommande vivement pour les professionnels.',
      name: 'Sophie Bernard',
      hotel: 'Palais des Congrès Lyon',
    },
  ];

  return (
    <section className="landing-section" aria-labelledby="testimonials-titre">
      <div className="landing-container">
        <div className="landing-section-header">
          <h2 className="landing-section-title" id="testimonials-titre">Ils nous font confiance</h2>
          <p className="landing-section-subtitle">
            Découvrez les retours d’expérience de nos clients hôteliers.
          </p>
        </div>

        <div className="landing-testimonials-grid">
          {testimonials.map((item, index) => (
            <div className="landing-testimonial-card" key={index}>
              <div className="landing-testimonial-stars" aria-label="5 étoiles">
                {Array.from({ length: 5 }).map((_, i) => (
                  <span key={i}>{stars}</span>
                ))}
              </div>
              <p className="landing-testimonial-quote">"{item.quote}"</p>
              <div>
                <div className="landing-testimonial-author">{item.name}</div>
                <div className="landing-testimonial-hotel">{item.hotel}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default Testimonials;
