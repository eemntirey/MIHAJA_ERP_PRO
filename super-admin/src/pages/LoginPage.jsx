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
  const { login, isAuthenticated } = useSuperAdminAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email || !password) {
      toast.error('Email et mot de passe requis');
      return;
    }

    setLoading(true);
    const result = await login(email, password);
    setLoading(false);

    if (result.success) {
      navigate('/', { replace: true });
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
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="superadmin@mihaja.mg"
              autoComplete="email"
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
