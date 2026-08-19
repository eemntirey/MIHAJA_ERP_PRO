// src/components/auth/ResetPassword.jsx
import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';
import { motion } from 'framer-motion';
import { useNavigate, useParams, Link } from 'react-router-dom';
import { toast } from 'react-toastify';
import { authService } from '../../services/api';
import DarkModeToggle from '../../components/layout/DarkModeToggle';
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

const ResetPassword = ({ darkMode, onToggleDarkMode }) => {
  const { token } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [resetSuccess, setResetSuccess] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({
    resolver: yupResolver(resetSchema),
  });

  const onSubmit = async (data) => {
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
    <div className="auth-container" data-theme={darkMode ? 'dark' : undefined}>
      <div className="auth-wrapper">
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="auth-card"
        >
          <div className="auth-header">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div className="auth-logo">
                <span className="logo-icon"></span>
                <h1>Nouveau mot de passe</h1>
              </div>
              <DarkModeToggle enabled={darkMode} onChange={onToggleDarkMode} />
            </div>
            <p className="auth-subtitle">
              {resetSuccess
                ? 'Votre mot de passe a été réinitialisé'
                : 'Créez un nouveau mot de passe sécurisé'}
            </p>
          </div>

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