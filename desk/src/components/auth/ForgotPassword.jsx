// src/components/auth/ForgotPassword.jsx
import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { toast } from 'react-toastify';
import { authService } from '../../services/api';
import DarkModeToggle from '../../components/layout/DarkModeToggle';
import './Auth.css';

const forgotSchema = yup.object().shape({
  email: yup
    .string()
    .email('Email invalide')
    .required('Email requis'),
});

const ForgotPassword = ({ darkMode, onToggleDarkMode }) => {
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({
    resolver: yupResolver(forgotSchema),
  });

  const onSubmit = async (data) => {
    try {
      setLoading(true);
      await authService.forgotPassword(data.email);
      setSent(true);
      toast.success('Si un compte existe avec cet email, un lien de réinitialisation a été envoyé.');
    } catch (error) {
      toast.error('Erreur lors de la demande de réinitialisation');
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
                <h1>Mot de passe oublié</h1>
              </div>
              <DarkModeToggle enabled={darkMode} onChange={onToggleDarkMode} />
            </div>
            <p className="auth-subtitle">
              {sent
                ? 'Vérifiez votre boîte mail'
                : 'Entrez votre email pour réinitialiser votre mot de passe'}
            </p>
          </div>

          {sent ? (
            <div className="success-message">
              <div className="success-icon"></div>
              <h3>Email envoyé !</h3>
              <p>
                Si un compte existe avec cet email, vous recevrez un lien de réinitialisation.
              </p>
              <Link to="/login" className="auth-button link-button">
                Retour à la connexion
              </Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit(onSubmit)} className="auth-form">
              <div className="form-group">
                <label htmlFor="email">Adresse email</label>
                <div className="input-wrapper">
                  <span className="input-icon"></span>
                  <input
                    id="email"
                    type="email"
                    placeholder="exemple@entreprise.com"
                    {...register('email')}
                    className={errors.email ? 'error' : ''}
                  />
                </div>
                {errors.email && (
                  <span className="error-message">{errors.email.message}</span>
                )}
              </div>

              <button type="submit" className="auth-button" disabled={loading}>
                {loading ? 'Envoi en cours...' : 'Envoyer le lien'}
              </button>
            </form>
          )}

          <div className="auth-footer">
            <p>
              <Link to="/login" className="back-link">
                ← Retour à la connexion
              </Link>
            </p>
          </div>
        </motion.div>
      </div>
    </div>
  );
};

export default ForgotPassword;
