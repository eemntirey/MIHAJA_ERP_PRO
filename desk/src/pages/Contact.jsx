// src/pages/Contact.jsx
import React, { useState } from 'react';
import { toast } from 'react-toastify';
import '../styles/landing.css';

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
    <div className="landing-contact">
      <div className="landing-container">
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
                  placeholder="jean@hotel.fr"
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
  );
};

export default Contact;
