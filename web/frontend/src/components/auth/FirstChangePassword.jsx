// src/components/auth/FirstChangePassword.jsx
// Écran obligatoire présenté à l'utilisateur après sa première connexion
// quand son compte a un mot de passe temporaire.
// L'utilisateur est bloqué sur cet écran tant qu'il n'a pas défini
// un nouveau mot de passe conforme à la politique de sécurité.
import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import AuthLeftPanel from './AuthLeftPanel';
import './Auth.css';

const firstChangeSchema = yup.object().shape({
  password: yup
    .string()
    .required('Mot de passe requis')
    .min(8, 'Minimum 8 caractères')
    .matches(
      /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/,
      'Doit contenir au moins une majuscule, une minuscule et un chiffre'
    ),
  confirmPassword: yup
    .string()
    .required('Confirmation requise')
    .oneOf(
      [yup.ref('password'), null],
      'Les mots de passe doivent correspondre'
    ),
});

const FirstChangePassword = () => {
  const navigate = useNavigate();
  const { firstChangePassword, user, loading } = useAuth();
  const [showPassword, setShowPassword] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({
    resolver: yupResolver(firstChangeSchema),
  });

  const onSubmit = async (data) => {
    const result = await firstChangePassword(data.password);
    if (result.success) {
      // Redirection vers le dashboard (ou la page appropriée au rôle)
      navigate('/dashboard');
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
          aria-labelledby="first-change-context-title"
        >
          <AuthLeftPanel />
        </section>

        <section
          className="auth-login__form-panel"
          aria-labelledby="first-change-form-title"
        >
          <div className="auth-login__form-container">
            <div className="auth-login__form-header">
              <span>Première connexion</span>
            </div>

            <div className="auth-login__form-intro">
              <p className="auth-login__eyebrow auth-login__eyebrow--light">
                Bienvenue{user?.prenom ? `, ${user.prenom}` : user?.username ? `, ${user.username}` : ''}
              </p>
              <h2 id="first-change-form-title">Définir votre mot de passe</h2>
              <p>
                Votre mot de passe actuel est temporaire. Pour accéder à
                l'ERP, vous devez définir un nouveau mot de passe sécurisé.
              </p>
            </div>

            <form
              onSubmit={handleSubmit(onSubmit)}
              className="auth-login__form"
              noValidate
            >
              <div className="auth-login__field">
                <label htmlFor="first-change-password">Nouveau mot de passe</label>
                <div className="auth-login__input-wrap">
                  <i className="ti ti-lock" aria-hidden="true" />
                  <input
                    id="first-change-password"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="Ex: MySecure123"
                    autoComplete="new-password"
                    aria-invalid={Boolean(errors.password)}
                    aria-describedby={errors.password ? 'first-change-password-error' : 'first-change-password-hint'}
                    {...register('password')}
                  />
                  <button
                    type="button"
                    className="auth-login__password-toggle"
                    onClick={() => setShowPassword((v) => !v)}
                    aria-label={showPassword ? 'Masquer le mot de passe' : 'Afficher le mot de passe'}
                  >
                    <i
                      className={showPassword ? 'ti ti-eye-off' : 'ti ti-eye'}
                      aria-hidden="true"
                    />
                  </button>
                </div>
                {errors.password && (
                  <span id="first-change-password-error" className="auth-login__error" role="alert">
                    {errors.password.message}
                  </span>
                )}
                <span id="first-change-password-hint" className="auth-login__hint">
                  Minimum 8 caractères, incluant majuscule, minuscule et chiffre
                </span>
              </div>

              <div className="auth-login__field">
                <label htmlFor="first-change-confirm">Confirmer le mot de passe</label>
                <div className="auth-login__input-wrap">
                  <i className="ti ti-lock" aria-hidden="true" />
                  <input
                    id="first-change-confirm"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="Confirmez le mot de passe"
                    autoComplete="new-password"
                    aria-invalid={Boolean(errors.confirmPassword)}
                    aria-describedby={errors.confirmPassword ? 'first-change-confirm-error' : undefined}
                    {...register('confirmPassword')}
                  />
                </div>
                {errors.confirmPassword && (
                  <span id="first-change-confirm-error" className="auth-login__error" role="alert">
                    {errors.confirmPassword.message}
                  </span>
                )}
              </div>

              <button
                type="submit"
                className="auth-login__submit"
                disabled={loading}
                aria-busy={loading}
              >
                {loading ? (
                  <>
                    <span className="auth-login__spinner" aria-hidden="true" />
                    <span>Enregistrement...</span>
                  </>
                ) : (
                  <>
                    <span>Définir mon mot de passe</span>
                    <i className="ti ti-arrow-up-right" aria-hidden="true" />
                  </>
                )}
              </button>
            </form>

            <p className="auth-login__security">
              <i className="ti ti-shield-check" aria-hidden="true" />
              Mot de passe chiffré et sécurisé
            </p>
          </div>
        </section>
      </main>
    </motion.div>
  );
};

export default FirstChangePassword;


