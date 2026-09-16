import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import { useSuperAdminAuth } from '../contexts/SuperAdminAuthContext';
import { superAdminAuthService } from '../services/api';
import './LoginPage.css';

const LoginPage = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  // Erreur inline : le toast seul peut etre perdu (ex: rechargement de page),
  // ce message lui reste toujours visible sous le formulaire.
  const [error, setError] = useState('');
  const { login, isAuthenticated } = useSuperAdminAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (!email || !password) {
      const msg = 'Email et mot de passe requis';
      setError(msg);
      toast.error(msg);
      return;
    }

    setLoading(true);
    let result;
    try {
      result = await login(email, password);
    } catch (err) {
      result = {
        success: false,
        error: err?.message || 'Erreur de connexion au serveur',
      };
    }
    setLoading(false);

    if (result.success) {
      navigate('/', { replace: true });
    } else if (result.error) {
      // Affiche l'erreur inline (toujours visible) en plus du toast.
      setError(result.error);
    }
  };

  return (
    <div className="sa-login-page">
      <div className="sa-login-card">
        <div className="sa-login-header">
          <h1>MIHAJA ERP</h1>
          <p className="sa-login-subtitle">Console Super Admin</p>
        </div>

        <form onSubmit={handleSubmit} className="sa-login-form">
          <div className="form-group">
            <label htmlFor="email">Email ou nom d'utilisateur</label>
            <input
              id="email"
              type="text"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="superadmin ou superadmin@mihaja.mg"
              autoComplete="username"
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Mot de passe</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              autoComplete="current-password"
            />
          </div>

          {error && (
            <div className="sa-login-error" role="alert">
              {error}
            </div>
          )}

          <button type="submit" className="sa-login-btn" disabled={loading}>
            {loading ? 'Connexion...' : 'Se connecter'}
          </button>
        </form>

        <p className="sa-login-footer">
          Accès réservé aux Super Administrateurs uniquement
        </p>
      </div>
    </div>
  );
};

export default LoginPage;
