// src/components/auth/Login.jsx
import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';
import { motion } from 'framer-motion';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import './Auth.css';

const loginSchema = yup.object().shape({
  email: yup
    .string()
    .email('Email invalide')
    .required('Email requis'),
  password: yup
    .string()
    .required('Mot de passe requis')
    .min(6, 'Minimum 6 caractères'),
});

const Login = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, loading: authLoading } = useAuth();
  const [showPassword, setShowPassword] = useState(false);

  const roleParam = new URLSearchParams(location.search).get('role');
  const roleLabel =
    roleParam === 'company'
      ? 'entreprise'
      : roleParam === 'user'
      ? 'utilisateur simple'
      : null;
  const subtitle = roleLabel
    ? `Se connecter en tant que ${roleLabel}`
    : 'Connectez-vous à votre espace professionnel';
  const submitLabel = roleLabel
    ? `Se connecter en tant que ${roleLabel}`
    : 'Se connecter';

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({
    resolver: yupResolver(loginSchema),
  });

  const onSubmit = async (data) => {
    try {
      const result = await login(data.email, data.password);

      if (result.success) {
        const redirectTo = result.redirectPath || '/dashboard';
        navigate(redirectTo);
      }
    } catch (error) {
      // Les erreurs sont gérées par AuthContext et affichées via ToastContainer.
      console.error('Erreur dans onSubmit:', error);
    }
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
          aria-labelledby="auth-login-context-title"
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
              <span className="auth-login__brand-meta">Gestion intégrée</span>
            </div>

            <div className="auth-login__context-content">
              <p className="auth-login__eyebrow">
                <span aria-hidden="true" />
                Espace professionnel
              </p>
              <h1 id="auth-login-context-title">
                Gardez le contrôle sur chaque décision.
              </h1>
              <p className="auth-login__context-copy">
                Une vue précise de vos ventes, de vos clients et de votre stock
                pour avancer avec confiance, chaque jour.
              </p>

              <div className="auth-login__feature-grid" role="list" aria-label="Modules ERP">
                <div className="auth-login__feature" role="listitem">
                  <i className="ti ti-shopping-cart" aria-hidden="true" />
                  <div>
                    <strong>Ventes</strong>
                    <span>Suivi en temps réel</span>
                  </div>
                </div>
                <div className="auth-login__feature" role="listitem">
                  <i className="ti ti-box" aria-hidden="true" />
                  <div>
                    <strong>Stock</strong>
                    <span>Alertes maîtrisées</span>
                  </div>
                </div>
                <div className="auth-login__feature" role="listitem">
                  <i className="ti ti-file-invoice" aria-hidden="true" />
                  <div>
                    <strong>Factures</strong>
                    <span>Gestion simplifiée</span>
                  </div>
                </div>
              </div>
            </div>

            <footer className="auth-login__context-footer">
              <span>© 2026 ERP Pro</span>
              <span className="auth-login__watermark" aria-hidden="true">
                ERP PRO · PILOTAGE · PRÉCISION
              </span>
              <span className="auth-login__status">
                <span aria-hidden="true" />
                Une gestion plus claire
              </span>
            </footer>
          </div>
        </section>

        <section
          className="auth-login__form-panel"
          aria-labelledby="auth-login-form-title"
        >
          <div className="auth-login__form-container">
            <div className="auth-login__form-header">
              <span>Accès sécurisé</span>
              <Link to="/" className="auth-login__back-link">
                Retour à l'accueil
              </Link>
            </div>

            <div className="auth-login__form-intro">
              <p className="auth-login__eyebrow auth-login__eyebrow--light">
                Votre espace de travail
              </p>
              <h2 id="auth-login-form-title">Connexion</h2>
              <p>{subtitle}</p>
            </div>

            <form
              onSubmit={handleSubmit(onSubmit)}
              className="auth-login__form"
              noValidate
            >
              <div className="auth-login__field">
                <label htmlFor="login-email">Adresse email</label>
                <div className="auth-login__input-wrap">
                  <i className="ti ti-mail" aria-hidden="true" />
                  <input
                    id="login-email"
                    type="email"
                    placeholder="nom@entreprise.fr"
                    autoComplete="email"
                    aria-invalid={Boolean(errors.email)}
                    aria-describedby={errors.email ? 'login-email-error' : undefined}
                    {...register('email')}
                  />
                </div>
                {errors.email && (
                  <span id="login-email-error" className="auth-login__error" role="alert">
                    {errors.email.message}
                  </span>
                )}
              </div>

              <div className="auth-login__field">
                <div className="auth-login__field-label-row">
                  <label htmlFor="login-password">Mot de passe</label>
                  <Link to="/forgot-password" className="auth-login__inline-link">
                    Mot de passe oublié ?
                  </Link>
                </div>
                <div className="auth-login__input-wrap">
                  <i className="ti ti-lock" aria-hidden="true" />
                  <input
                    id="login-password"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="Votre mot de passe"
                    autoComplete="current-password"
                    aria-invalid={Boolean(errors.password)}
                    aria-describedby={errors.password ? 'login-password-error' : undefined}
                    {...register('password')}
                  />
                  <button
                    type="button"
                    className="auth-login__password-toggle"
                    onClick={() => setShowPassword((visible) => !visible)}
                    aria-label={showPassword ? 'Masquer le mot de passe' : 'Afficher le mot de passe'}
                    aria-pressed={showPassword}
                  >
                    <i
                      className={showPassword ? 'ti ti-eye-off' : 'ti ti-eye'}
                      aria-hidden="true"
                    />
                  </button>
                </div>
                {errors.password && (
                  <span id="login-password-error" className="auth-login__error" role="alert">
                    {errors.password.message}
                  </span>
                )}
              </div>

              <label className="auth-login__remember">
                <input type="checkbox" id="login-remember" />
                <span>Se souvenir de moi</span>
              </label>

              <button
                type="submit"
                className="auth-login__submit"
                disabled={authLoading}
                aria-busy={authLoading}
              >
                {authLoading ? (
                  <>
                    <span className="auth-login__spinner" aria-hidden="true" />
                    <span>Connexion...</span>
                  </>
                ) : (
                  <>
                    <span>{submitLabel}</span>
                    <i className="ti ti-arrow-up-right" aria-hidden="true" />
                  </>
                )}
              </button>
            </form>

            <div className="auth-login__divider" aria-hidden="true">
              <span />
              <span>ou</span>
              <span />
            </div>

            <div className="auth-login__social-actions" aria-label="Autres méthodes de connexion">
              <button type="button" className="auth-login__social-button">
                <span aria-hidden="true">G</span>
                Google
              </button>
              <button type="button" className="auth-login__social-button">
                <span aria-hidden="true">M</span>
                Microsoft
              </button>
            </div>

            <p className="auth-login__register-prompt">
              Pas encore de compte ?{' '}
              <Link to="/register">Créer un compte</Link>
            </p>

            <p className="auth-login__security">
              <i className="ti ti-shield-check" aria-hidden="true" />
              Connexion protégée par JWT &amp; SSL
            </p>
          </div>
        </section>
      </main>
    </motion.div>
  );
};

export default Login;
