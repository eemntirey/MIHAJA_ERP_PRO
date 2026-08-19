// src/pages/Contact.jsx
import React, { useState } from 'react';
import { toast } from 'react-toastify';
import { Icon } from '../components/common/Icon';
import './Pages.css';

const Contact = () => {
  const [form, setForm] = useState({ name: '', email: '', message: '' });
  const [sending, setSending] = useState(false);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    setSending(true);
    setTimeout(() => {
      toast.success('Message envoyé avec succès');
      setForm({ name: '', email: '', message: '' });
      setSending(false);
    }, 800);
  };

  return (
    <div className="home-page">
      <div className="home-content page-container">
        <div className="page-header">
          <div>
            <h1>Contact</h1>
            <p>Une question ? Notre équipe vous répond dans les plus brefs délais.</p>
          </div>
        </div>

        <div className="card" style={{ maxWidth: 720 }}>
          <form className="form-grid" onSubmit={handleSubmit}>
            <div className="form-group">
              <label htmlFor="contact-name">Nom complet</label>
              <input
                id="contact-name"
                name="name"
                type="text"
                value={form.name}
                onChange={handleChange}
                placeholder="Jean Dupont"
                required
              />
            </div>
            <div className="form-group">
              <label htmlFor="contact-email">Email</label>
              <input
                id="contact-email"
                name="email"
                type="email"
                value={form.email}
                onChange={handleChange}
                placeholder="jean@hotel.fr"
                required
              />
            </div>
            <div className="form-group full-width">
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
            <div className="form-group full-width">
              <button type="submit" className="btn-primary" disabled={sending}>
                {sending ? 'Envoi...' : 'Envoyer le message'}
              </button>
            </div>
          </form>

          <hr className="public-divider" />

          <div className="public-list">
            <div className="public-list-item">
              <Icon name="mail" />
              <div>
                <div className="public-list-item__primary">Email</div>
                <div className="public-list-item__secondary">contact@erppro.mg</div>
              </div>
            </div>
            <div className="public-list-item">
              <Icon name="phone" />
              <div>
                <div className="public-list-item__primary">Téléphone</div>
                <div className="public-list-item__secondary">+261 34 12 345 67</div>
              </div>
            </div>
            <div className="public-list-item">
              <Icon name="map-pin" />
              <div>
                <div className="public-list-item__primary">Adresse</div>
                <div className="public-list-item__secondary">Antananarivo, Madagascar</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Contact;
