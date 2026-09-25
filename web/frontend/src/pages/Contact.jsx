// src/pages/Contact.jsx
import React, { useState } from 'react';
import { toast } from 'react-toastify';
import { Link } from 'react-router-dom';
import { publicCatalogueService } from '../services/api';
import Seo from '../components/Seo';
import '../styles/landing.css';

const CONTACT_SEO_DATA = {
  '@context': 'https://schema.org',
  '@type': 'ContactPage',
  name: 'Contact | MIHAJA ERP PRO',
  url: 'https://mihaja-erp-frontend-796e-qdh1.onrender.com/contact',
  description: 'Contactez l’équipe MIHAJA ERP PRO pour toute question sur la solution ERP SaaS.',
};

const Contact = () => {
  const [form, setForm] = useState({ name: '', email: '', message: '' });
  const [sending, setSending] = useState(false);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (sending) return;

    const name = form.name.trim();
    const email = form.email.trim();
    const message = form.message.trim();
    if (!name || !email || !message) {
      toast.error('Veuillez remplir tous les champs.');
      return;
    }

    try {
      setSending(true);
      await publicCatalogueService.sendContactMessage({ name, email, message });
      toast.success('Message envoyé avec succès');
      setForm({ name: '', email: '', message: '' });
    } catch (err) {
      const msg = err.response?.data?.message || 'Impossible d’envoyer votre message pour le moment.';
      toast.error(msg);
    } finally {
      setSending(false);
    }
  };

  return (
    <>
      <Seo
        title="Contact | MIHAJA ERP PRO"
        description="Contactez l’équipe MIHAJA ERP PRO pour toute question sur la solution ERP SaaS."
        canonical="https://mihaja-erp-frontend-796e-qdh1.onrender.com/contact"
        structuredData={CONTACT_SEO_DATA}
      />
      <div className="landing-contact">
      <div className="landing-container">
        <header className="landing-public-page-header">
          <Link to="/" className="brand" aria-label="MIHAJA ERP PRO accueil">
            <span className="brand-icon">EP</span>
            <span className="brand-name">ERP Pro</span>
          </Link>
          <nav aria-label="Navigation principale">
            <Link to="/" className="public-nav-link">Accueil</Link>
            <Link to="/catalogue" className="public-nav-link">Catalogue</Link>
            <Link to="/telechargements" className="public-nav-link">Téléchargements</Link>
          </nav>
        </header>
        <div className="landing-section-header">
          <h2 className="landing-section-title" id="contact-titre">Contact</h2>
          <p className="landing-section-subtitle">
            Une question ? Notre équipe vous répond dans les plus brefs délais.
          </p>
        </div>

        <div className="landing-contact-card">
          <form className="landing-contact-form" onSubmit={handleSubmit}>
            <div className="landing-form-row">
              <div className="landing-form-group">
                <label htmlFor="contact-name">Nom complet</label>
                <input
                  id="contact-name"
                  name="name"
                  type="text"
                  value={form.name}
                  onChange={handleChange}
                  placeholder="Jean Rakoto"
                  required
                />
              </div>
              <div className="landing-form-group">
                <label htmlFor="contact-email">Email</label>
                <input
                  id="contact-email"
                  name="email"
                  type="email"
                  value={form.email}
                  onChange={handleChange}
                  placeholder="jean@exemple.mg"
                  required
                />
              </div>
            </div>
            <div className="landing-form-group">
              <label htmlFor="contact-message">Message</label>
              <textarea
                id="contact-message"
                name="message"
                value={form.message}
                onChange={handleChange}
                placeholder="Votre message..."
                rows="5"
                required
              />
            </div>
            <button type="submit" className="landing-btn landing-btn-primary" disabled={sending}>
              {sending ? 'Envoi...' : 'Envoyer le message'}
            </button>
          </form>
        </div>
      </div>
      </div>
    </>
  );
};

export default Contact;
