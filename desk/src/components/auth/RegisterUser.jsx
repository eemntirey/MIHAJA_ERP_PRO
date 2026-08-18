// src/components/auth/RegisterUser.jsx
import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';
import { motion } from 'framer-motion';
import { Link, useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import { useAuth } from '../../contexts/AuthContext';
import './Auth.css';

const registerSchema = yup.object().shape({
  nom: yup.string().required('Nom requis'),
  prenom: yup.string().required('Prénom requis'),
  email: yup.string().email('Email invalide').required('Email requis'),
  password: yup
    .string()
    .required('Mot de passe requis')
    .min(6, 'Minimum 6 caractères'),
  confirmPassword: yup
    .string()
    .oneOf([yup.ref('password'), null], 'Les mots de passe doivent correspondre'),
  telephone: yup.string(),
  acceptTerms: yup.boolean().oneOf([true], 'Vous devez accepter les conditions'),
});

const RegisterUser = () => {
  const navigate = useNavigate();
  const { register: registerAuth, loading: authLoading } = useAuth();
  const [loading, setLoading] = useState(false);

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm({
    resolver: yupResolver(registerSchema),
  });

  const password = watch('password');

  const checkPasswordStrength = (pwd) => {
    let score = 0;
    if (pwd.length >= 6) score++;
    if (pwd.match(/[a-z]/)) score++;
    if (pwd.match(/[A-Z]/)) score++;
    if (pwd.match(/\d/)) score++;
    if (pwd.match(/[^a-zA-Z\d]/)) score++;
    return score;
  };

  const getStrengthLabel = (score) => {
    const labels = ['Très faible', 'Faible', 'Moyen', 'Fort', 'Très fort'];
    return labels[Math.min(Math.max(score - 1, 0), 4)];
  };

  const getStrengthColor = (score) => {
    const colors = ['#ff4444', '#ff8800', '#ffcc00', '#44cc44', '#00aa00'];
    return colors[Math.min(Math.max(score - 1, 0), 4)];
  };

  const onSubmit = async (data) => {
    const payload = {
      profile_type: 'simple',
      username: data.email,
      email: data.email,
      password: data.password,
      nom: data.nom,
      prenom: data.prenom,
      telephone: data.telephone,
    };

    const result = await registerAuth(payload);

    if (result && result.success) {
      navigate('/');
    }
  };

  const passwordStrength = password ? checkPasswordStrength(password) : 0;

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
          aria-labelledby="register-user-title"
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
              <span className="auth-login__brand-meta">Espace utilisateur</span>
            </div>

            <div className="auth-login__context-content">
              <p className="auth-login__eyebrow">
                <span aria-hidden="true" />
                Simple utilisateur
              </p>
              <h1 id="register-user-title">
                Créez votre compte utilisateur
              </h1>
              <p className="auth-login__context-copy">
                 Accédez au catalogue public des grossistes, ajoutez des produits à
                 votre panier et suivez vos commandes.
              </p>
            </div>

            <footer className="auth-login__context-footer">
              <span>© {new Date().getFullYear()} ERP Pro</span>
              <span className="auth-login__watermark" aria-hidden="true">
                ERP PRO · CATALOGUE · COMMANDES
              </span>
            </footer>
          </div>
        </section>

        <section
          className="auth-login__form-panel"
          aria-labelledby="register-user-form-title"
        >
          <div className="auth-login__form-container">
            <div className="auth-login__form-header">
              <span>Compte simple</span>
              <Link to="/register" className="auth-login__back-link">
                ← Changer de type
              </Link>
            </div>

            <div className="auth-login__form-intro">
              <p className="auth-login__eyebrow auth-login__eyebrow--light">
                Informations personnelles
              </p>
              <h2 id="register-user-form-title">Inscription utilisateur</h2>
              <p>
                 Aucune condition stricte. Inscrivez-vous et accédez immédiatement
                 au catalogue public.
              </p>
            </div>

            <form
              onSubmit={handleSubmit(onSubmit)}
              className="auth-login__form"
              noValidate
            >
              <div className="auth-login__field">
                <label htmlFor="register-user-prenom">Prénom *</label>
                <div className="auth-login__input-wrap auth-login__input-wrap--plain">
                  <input
                    id="register-user-prenom"
                    type="text"
                    placeholder="Jean"
                    autoComplete="given-name"
                    {...register('prenom')}
                    className={errors.prenom ? 'error' : ''}
                    aria-invalid={Boolean(errors.prenom)}
                  />
                </div>
                {errors.prenom && (
                  <span className="auth-login__error" role="alert">
                    {errors.prenom.message}
                  </span>
                )}
              </div>

              <div className="auth-login__field">
                <label htmlFor="register-user-nom">Nom *</label>
                <div className="auth-login__input-wrap auth-login__input-wrap--plain">
                  <input
                    id="register-user-nom"
                    type="text"
                    placeholder="Dupont"
                    autoComplete="family-name"
                    {...register('nom')}
                    className={errors.nom ? 'error' : ''}
                    aria-invalid={Boolean(errors.nom)}
                  />
                </div>
                {errors.nom && (
                  <span className="auth-login__error" role="alert">
                    {errors.nom.message}
                  </span>
                )}
              </div>

              <div className="auth-login__field">
                <label htmlFor="register-user-email">Adresse email *</label>
                <div className="auth-login__input-wrap">
                  <i className="ti ti-mail" aria-hidden="true" />
                  <input
                    id="register-user-email"
                    type="email"
                    placeholder="jean.dupont@email.com"
                    autoComplete="email"
                    {...register('email')}
                    className={errors.email ? 'error' : ''}
                    aria-invalid={Boolean(errors.email)}
                  />
                </div>
                {errors.email && (
                  <span className="auth-login__error" role="alert">
                    {errors.email.message}
                  </span>
                )}
              </div>

              <div className="auth-login__field">
                <label htmlFor="register-user-telephone">Téléphone (optionnel)</label>
                <div className="auth-login__input-wrap">
                  <i className="ti ti-phone" aria-hidden="true" />
                  <input
                    id="register-user-telephone"
                    type="tel"
                    placeholder="+261 34 12 345 67"
                    autoComplete="tel"
                    {...register('telephone')}
                  />
                </div>
              </div>

              <div className="auth-login__field">
                <label htmlFor="register-user-password">Mot de passe *</label>
                <div className="auth-login__input-wrap">
                  <i className="ti ti-lock" aria-hidden="true" />
                  <input
                    id="register-user-password"
                    type="password"
                    placeholder="••••••"
                    autoComplete="new-password"
                    {...register('password')}
                    className={errors.password ? 'error' : ''}
                    aria-invalid={Boolean(errors.password)}
                  />
                </div>
                {password && password.length > 0 && (
                  <div className="password-strength">
                    <div className="strength-bar">
                      <div
                        className="strength-progress"
                        style={{
                          width: `${(passwordStrength / 5) * 100}%`,
                          backgroundColor: getStrengthColor(passwordStrength),
                        }}
                      />
                    </div>
                    <span style={{ color: getStrengthColor(passwordStrength) }}>
                      {getStrengthLabel(passwordStrength)}
                    </span>
                  </div>
                )}
                {errors.password && (
                  <span className="auth-login__error" role="alert">
                    {errors.password.message}
                  </span>
                )}
              </div>

              <div className="auth-login__field">
                <label htmlFor="register-user-confirm">Confirmer le mot de passe *</label>
                <div className="auth-login__input-wrap">
                  <i className="ti ti-lock" aria-hidden="true" />
                  <input
                    id="register-user-confirm"
                    type="password"
                    placeholder="••••••"
                    autoComplete="new-password"
                    {...register('confirmPassword')}
                    className={errors.confirmPassword ? 'error' : ''}
                    aria-invalid={Boolean(errors.confirmPassword)}
                  />
                </div>
                {errors.confirmPassword && (
                  <span className="auth-login__error" role="alert">
                    {errors.confirmPassword.message}
                  </span>
                )}
              </div>

              <div className="auth-login__field checkbox-group">
                <input type="checkbox" id="register-user-terms" {...register('acceptTerms')} />
                <label htmlFor="register-user-terms">
                  J'accepte les{' '}
                  <Link to="/terms" className="terms-link">
                    conditions d'utilisation
                  </Link>{' '}
                  et la{' '}
                  <Link to="/privacy" className="terms-link">
                    politique de confidentialité
                  </Link>
                </label>
                {errors.acceptTerms && (
                  <span className="auth-login__error" role="alert">
                    {errors.acceptTerms.message}
                  </span>
                )}
              </div>

              <button type="submit" className="auth-login__submit" disabled={loading || authLoading}>
                {loading || authLoading ? (
                  <>
                    <span className="auth-login__spinner" aria-hidden="true" />
                    <span>Création du compte...</span>
                  </>
                ) : (
                  <>
                    <span>Créer mon compte et accéder au catalogue</span>
                  </>
                )}
              </button>
            </form>

            <div className="auth-login__register-prompt">
              <p>
                Vous préférez un compte entreprise ?{' '}
                <Link to="/register/company">Créer une entreprise</Link>
              </p>
            </div>
          </div>
        </section>
      </main>
    </motion.div>
  );
};

export default RegisterUser;
