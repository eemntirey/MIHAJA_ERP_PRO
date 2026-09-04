// src/components/auth/ResetPassword.jsx
import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';
import { motion } from 'framer-motion';
import { useNavigate, useParams, Link } from 'react-router-dom';
import { toast } from 'react-toastify';
import { authService } from '../../services/api';
import './Auth.css';

const resetSchema = yup.object().shape({
  password: yup
    .string()
    .required('Mot de passe requis')
    .min(8, 'Minimum 8 caractères')
    .matches(
      /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/,
      'Doit contenir majuscule, minuscule et chiffre'
    ),
  confirmPassword: yup
    .string()
    .oneOf([yup.ref('password'), null], 'Les mots de passe doivent correspondre'),
});

const ResetPassword = () => {
  const { token } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [resetSuccess, setResetSuccess] = useState(false);
  const [tokenValid, setTokenValid] = useState(null); // null = checking, true/false
  const [tokenError, setTokenError] = useState('');
  const [countdown, setCountdown] = useState(null);
  const [countdownExpired, setCountdownExpired] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({
    resolver: yupResolver(resetSchema),
  });

  // Verification prealable du token et demarrage du compte a rebours
  React.useEffect(() => {
    const verifyAndCount = async () => {
      if (!token) return;
      try {
        const result = await authService.verifyResetToken(token);
        if (result.success) {
          setTokenValid(true);
          const fallbackTtl = parseInt(
            (typeof process !== 'undefined' && process.env && process.env.REACT_APP_PASSWORD_RESET_TTL_MINUTES) || '60',
            10
          );
          const ttlMinutes = result.data?.remaining_seconds
            ? Math.ceil(result.data.remaining_seconds / 60)
            : fallbackTtl;
          setCountdown(ttlMinutes * 60);
        } else {
          setTokenValid(false);
          setTokenError(result.error || 'Token invalide ou expiré');
        }
      } catch {
        setTokenValid(false);
        setTokenError('Impossible de vérifier le token');
      }
    };
    verifyAndCount();
  }, [token]);

  // Compte a rebours
  React.useEffect(() => {
    if (!countdown && countdown !== 0) return;
    if (countdown <= 0) {
      setCountdownExpired(true);
      setTokenError('Ce lien de réinitialisation a expiré');
      setTokenValid(false);
      return;
    }
    const interval = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(interval);
  }, [countdown]);

  const onSubmit = async (data) => {
    if (tokenValid !== true) {
      toast.error('Token de réinitialisation invalide ou expiré');
      return;
    }
    try {
      setLoading(true);
      await authService.resetPassword(token, data.password);
      setResetSuccess(true);
      toast.success('Mot de passe réinitialisé avec succès !');
      
      setTimeout(() => {
        navigate('/login');
      }, 3000);
    } catch (error) {
      toast.error('Erreur lors de la réinitialisation');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-wrapper">
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="auth-card"
        >
          <div className="auth-header">
            <div className="auth-logo">
              <span className="logo-icon"></span>
              <h1>Nouveau mot de passe</h1>
            </div>
            <p className="auth-subtitle">
              {resetSuccess
                ? 'Votre mot de passe a été réinitialisé'
                : 'Créez un nouveau mot de passe sécurisé'}
            </p>
          </div>

          {tokenValid === false && (
            <div className="error-message" style={{ marginBottom: "1rem", textAlign: "center" }}>
              <p>{tokenError}</p>
              <p style={{ fontSize: "0.85em", marginTop: "0.5rem" }}>
                Veuillez{" "}
                <Link to="/forgot-password" style={{ color: "#4f46e5" }}>
                  demander un nouveau lien
                </Link>
              </p>
            </div>
          )}

          {tokenValid === null && (
            <div style={{ textAlign: "center", padding: "1rem 0" }}>
              <span className="auth-login__spinner" aria-hidden="true" />
              <p>Verification du lien...</p>
            </div>
          )}

          {tokenValid === true && !resetSuccess && countdown !== null && !countdownExpired && (
            <p style={{ fontSize: "0.85em", color: "#6b7280", textAlign: "center", marginBottom: "0.75rem" }}>
              Expire dans {Math.floor(countdown / 60)}:{String(countdown % 60).padStart(2, "0")}
            </p>
          )}

          {resetSuccess ? (
            <div className="success-message">
              <div className="success-icon"></div>
              <h3>Réinitialisation réussie !</h3>
              <p>Vous allez être redirigé vers la page de connexion...</p>
              <Link to="/login" className="auth-button link-button">
                Se connecter
              </Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit(onSubmit)} className="auth-form">
              <div className="form-group">
                <label htmlFor="password">Nouveau mot de passe</label>
                <input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  {...register('password')}
                  className={errors.password ? 'error' : ''}
                />
                {errors.password && (
                  <span className="error-message">{errors.password.message}</span>
                )}
              </div>

              <div className="form-group">
                <label htmlFor="confirmPassword">Confirmer le mot de passe</label>
                <input
                  id="confirmPassword"
                  type="password"
                  placeholder="••••••••"
                  {...register('confirmPassword')}
                  className={errors.confirmPassword ? 'error' : ''}
                />
                {errors.confirmPassword && (
                  <span className="error-message">{errors.confirmPassword.message}</span>
                )}
              </div>

              <button type="submit" className="auth-button" disabled={loading}>
                {loading ? 'Réinitialisation...' : 'Réinitialiser le mot de passe'}
              </button>
            </form>
          )}

          <div className="auth-footer">
            <Link to="/login" className="back-link">
              ← Retour à la connexion
            </Link>
          </div>
        </motion.div>
      </div>
    </div>
  );
};

export default ResetPassword;