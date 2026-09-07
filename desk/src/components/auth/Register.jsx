// src/components/auth/Register.jsx
import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useAuth } from '../../contexts/AuthContext';
import './Auth.css';

const Register = () => {
  const navigate = useNavigate();
  const { register } = useAuth();

  const handleSimpleUser = () => {
    navigate('/register/simple');
  };

  const handleCompany = () => {
    navigate('/register/company');
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="auth-login"
    >
      <main className="auth-login__layout">
        <section
          className="auth-login__context"
          aria-labelledby="register-choice-title"
        >
          <span className="auth-login__context-divider" aria-hidden="true" />
          <span className="auth-login__context-orbit auth-login__context-orbit--large" aria-hidden="true" />
          <span className="auth-login__context-orbit auth-login__context-orbit--small" aria-hidden="true" />

          <div className="auth-login__context-inner">
            <div className="auth-login__brand-row">
              <Link to="/" className="auth-login__brand" aria-label="ERP Pro accueil">
                <span className="auth-login__brand-mark" aria-hidden="true">EP</span>
                <span className="auth-login__brand-name">ERP Pro</span>
              </Link>
              <span className="auth-login__brand-meta">Créer votre compte</span>
            </div>

            <div className="auth-login__context-content">
              <p className="auth-login__eyebrow">
                <span aria-hidden="true" />
                Choisissez votre type de compte
              </p>
              <h1 id="register-choice-title">
                Rejoignez ERP Pro en deux temps
              </h1>
              <p className="auth-login__context-copy">
                Selon votre activité, deux parcours d’inscription sont proposés.
                Chaque parcours possède un formulaire et des accès adaptés.
              </p>
            </div>

            <footer className="auth-login__context-footer">
              <span>© {new Date().getFullYear()} ERP Pro</span>
              <span className="auth-login__watermark" aria-hidden="true">
                ERP PRO · PILOTAGE · PRÉCISION
              </span>
            </footer>
          </div>
        </section>

        <section
          className="auth-login__form-panel"
          aria-labelledby="register-choice-form-title"
        >
          <div className="auth-login__form-container">
            <div className="auth-login__form-header">
              <span>Création de compte</span>
              <Link to="/" className="auth-login__back-link">
                Retour à l'accueil
              </Link>
            </div>

            <div className="auth-login__form-intro">
              <p className="auth-login__eyebrow auth-login__eyebrow--light">
                Votre profil
              </p>
              <h2 id="register-choice-form-title">Quel compte créer ?</h2>
              <p>
                Sélectionnez le type de profil qui correspond à votre activité.
                Les deux formulaires sont différents.
              </p>
            </div>

            <div className="register-choice-grid">
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                type="button"
                className="register-choice-card register-choice-card--user"
                onClick={handleSimpleUser}
                aria-label="Créer un compte utilisateur simple"
              >
                  <div className="register-choice-card__icon" aria-hidden="true">
                    <i className="ti ti-user" />
                  </div>
                <h3>Utilisateur simple</h3>
                 <p>
                  Accès au catalogue public, création de commandes et suivi de
                  vos achats. Inscription sans condition stricte.
                 </p>
                <span className="register-choice-card__cta">Créer mon compte</span>
              </motion.button>

              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                type="button"
                className="register-choice-card register-choice-card--company"
                onClick={handleCompany}
                aria-label="Créer un compte entreprise / grossiste"
              >
                  <div className="register-choice-card__icon" aria-hidden="true">
                    <i className="ti ti-building" />
                  </div>
                <h3>Entreprise / Grossiste</h3>
                <p>
                  Créez votre société, choisissez un abonnement selon l’état de
                  votre entreprise et accédez aux fonctions opérationnelles du
                  site.
                </p>
                <span className="register-choice-card__cta">Créer mon entreprise</span>
              </motion.button>
            </div>

            <div className="auth-login__register-prompt">
              <p>
                Vous avez déjà un compte ?{' '}
                <Link to="/login">Se connecter</Link>
              </p>
            </div>
          </div>
        </section>
      </main>
    </motion.div>
  );
};

export default Register;

export const registerUser = async (register, data) => {
  return register({ ...data, profile_type: 'simple' });
};

export const registerCompany = async (register, data) => {
  return register({ ...data, profile_type: 'company' });
};
