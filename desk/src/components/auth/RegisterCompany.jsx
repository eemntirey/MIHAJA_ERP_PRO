// src/components/auth/RegisterCompany.jsx
import React, { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';
import { motion } from 'framer-motion';
import { Link, useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import { useAuth } from '../../contexts/AuthContext';
import { plansService } from '../../shared/services/api';
import DarkModeToggle from '../../components/layout/DarkModeToggle';
import AuthLeftPanel from './AuthLeftPanel';
import './Auth.css';

const formatPlanPrice = (plan) => {
  if (plan.prix === 0 || plan.prix === null || plan.prix === undefined) {
    return 'Gratuit';
  }
  return `${Number(plan.prix).toLocaleString('fr-FR')} Ar`;
};

const formatPlanDuration = (plan) => {
  if (plan.duree_jours === -1) return 'durée illimitée';
  return `${plan.duree_jours} jours`;
};

const registerSchema = yup.object().shape({
  nom_entreprise: yup.string().required('Le nom de l\'entreprise est requis'),
  email: yup.string().email('Email invalide').required('Email requis'),
  nom: yup.string().required('Nom requis'),
  prenom: yup.string().required('Prénom requis'),
  password: yup
    .string()
    .required('Mot de passe requis')
    .min(8, 'Minimum 8 caractères')
    .matches(
      /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/,
      'Doit contenir une majuscule, une minuscule et un chiffre'
    ),
  confirmPassword: yup
    .string()
    .oneOf([yup.ref('password'), null], 'Les mots de passe doivent correspondre'),
  plan: yup.string().required('Choisissez un plan'),
  acceptTerms: yup.boolean().oneOf([true], 'Vous devez accepter les conditions'),
});

const RegisterCompany = ({ darkMode, onToggleDarkMode }) => {
  const navigate = useNavigate();
  const { register: registerAuth, loading: authLoading } = useAuth();
  const [loading, setLoading] = useState(false);
  const [plans, setPlans] = useState([]);
  const [plansLoading, setPlansLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const loadPlans = async () => {
      try {
        const response = await plansService.getPublicPlans();
        if (!cancelled) {
          const list = response?.data?.plans || response?.plans || [];
          setPlans(list);
        }
      } catch (err) {
        if (!cancelled) {
          toast.error("Impossible de charger les plans. Réessayez plus tard.");
        }
      } finally {
        if (!cancelled) {
          setPlansLoading(false);
        }
      }
    };
    loadPlans();
    return () => {
      cancelled = true;
    };
  }, []);

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm({
    resolver: yupResolver(registerSchema),
    defaultValues: { plan: '' },
  });

  const password = watch('password');

  const checkPasswordStrength = (pwd) => {
    let score = 0;
    if (pwd.length >= 8) score++;
    if (pwd.match(/[a-z]/)) score++;
    if (pwd.match(/[A-Z]/)) score++;
    if (pwd.match(/\d/)) score++;
    if (pwd.match(/[^a-zA-Z\d]/)) score++;
    return score;
  };

  const getStrengthColor = (score) => {
    const colors = ['#ff4444', '#ff8800', '#ffcc00', '#44cc44', '#00aa00'];
    return colors[Math.min(Math.max(score - 1, 0), 4)];
  };

  const getStrengthLabel = (score) => {
    const labels = ['Très faible', 'Faible', 'Moyen', 'Fort', 'Très fort'];
    return labels[Math.min(Math.max(score - 1, 0), 4)];
  };

  const onSubmit = async (data) => {
    const payload = {
      profile_type: 'company',
      username: data.email,
      email: data.email,
      password: data.password,
      nom: data.nom,
      prenom: data.prenom,
      telephone: data.telephone_entreprise,
      nom_entreprise: data.nom_entreprise,
      telephone_entreprise: data.telephone_entreprise,
      email_contact: data.email,
      domaine: data.domaine,
      adresse: data.adresse,
      ville: data.ville,
      code_postal: data.code_postal,
       pays: data.pays || 'Madagascar',
       plan: data.plan,
    };

    const result = await registerAuth(payload);

    if (result && result.success) {
      toast.success('Entreprise créée avec succès !');
      setTimeout(() => {
        navigate('/subscription');
      }, 2000);
    }
  };

  const passwordStrength = password ? checkPasswordStrength(password) : 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="auth-login auth-register"
      data-theme={darkMode ? 'dark' : undefined}
    >
      <main className="auth-login__layout">
        <section
          className="auth-login__context"
          aria-labelledby="auth-login-context-title"
        >
          <AuthLeftPanel />
        </section>

        <section
          className="auth-login__form-panel"
          aria-labelledby="register-company-form-title"
        >
          <div className="auth-login__form-container">
            <div className="auth-login__form-header">
              <span>Création d'entreprise</span>
              <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
                <DarkModeToggle enabled={darkMode} onChange={onToggleDarkMode} />
                <Link to="/register" className="auth-login__back-link">
                  ← Changer de type
                </Link>
              </div>
            </div>

            <div className="auth-login__form-intro">
              <p className="auth-login__eyebrow auth-login__eyebrow--light">
                Informations de l'entreprise
              </p>
              <h2 id="register-company-form-title">Inscription entreprise / grossiste</h2>
              <p>
                Finalisez votre inscription : renseignez vos coordonnées, choisissez
                votre plan d'abonnement. Le paiement finalise l'accès opérationnel.
              </p>
            </div>

            <form
              onSubmit={handleSubmit(onSubmit)}
              className="auth-login__form"
              noValidate
            >
          <div className="auth-login__field">
            <label htmlFor="register-company-name">Nom de l'entreprise *</label>
            <div className="auth-login__input-wrap auth-login__input-wrap--plain">
              <input
                id="register-company-name"
                type="text"
                placeholder="Mada Distribution SARL"
                {...register('nom_entreprise')}
                className={errors.nom_entreprise ? 'error' : ''}
                aria-invalid={Boolean(errors.nom_entreprise)}
              />
            </div>
            {errors.nom_entreprise && (
              <span className="auth-login__error" role="alert">
                {errors.nom_entreprise.message}
              </span>
            )}
          </div>

          <div className="form-row">
            <div className="auth-login__field">
              <label htmlFor="register-company-prenom">Prénom du responsable *</label>
              <div className="auth-login__input-wrap auth-login__input-wrap--plain">
                <input
                  id="register-company-prenom"
                  type="text"
                  placeholder="Sophie"
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
              <label htmlFor="register-company-nom">Nom du responsable *</label>
              <div className="auth-login__input-wrap auth-login__input-wrap--plain">
                <input
                  id="register-company-nom"
                  type="text"
                  placeholder="Martin"
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
          </div>

          <div className="auth-login__field">
            <label htmlFor="register-company-email">Email professionnel *</label>
            <div className="auth-login__input-wrap">
              <i className="ti ti-mail" aria-hidden="true" />
              <input
                id="register-company-email"
                type="email"
                placeholder="contact@entreprise.mg"
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
            <label htmlFor="register-company-telephone">Téléphone de l'entreprise (optionnel)</label>
            <div className="auth-login__input-wrap">
              <i className="ti ti-phone" aria-hidden="true" />
              <input
                id="register-company-telephone"
                type="tel"
                placeholder="+261 34 12 345 67"
                {...register('telephone_entreprise')}
              />
            </div>
          </div>

          <div className="auth-login__field">
            <label htmlFor="register-company-domaine">Domaine (optionnel)</label>
            <div className="auth-login__input-wrap auth-login__input-wrap--plain">
              <input
                id="register-company-domaine"
                type="text"
                placeholder="entreprise.mg"
                {...register('domaine')}
              />
            </div>
          </div>

          <div className="auth-login__field">
            <label htmlFor="register-company-adresse">Adresse *</label>
            <div className="auth-login__input-wrap auth-login__input-wrap--plain">
              <input
                id="register-company-adresse"
                type="text"
                placeholder="12 Rue de la Paix"
                {...register('adresse')}
                className={errors.adresse ? 'error' : ''}
                aria-invalid={Boolean(errors.adresse)}
              />
            </div>
            {errors.adresse && (
              <span className="auth-login__error" role="alert">
                {errors.adresse.message}
              </span>
            )}
          </div>

          <div className="form-row">
            <div className="auth-login__field">
              <label htmlFor="register-company-ville">Ville *</label>
              <div className="auth-login__input-wrap auth-login__input-wrap--plain">
                <input
                  id="register-company-ville"
                  type="text"
                  placeholder="Antananarivo"
                  {...register('ville')}
                  className={errors.ville ? 'error' : ''}
                  aria-invalid={Boolean(errors.ville)}
                />
              </div>
              {errors.ville && (
                <span className="auth-login__error" role="alert">
                  {errors.ville.message}
                </span>
              )}
            </div>

            <div className="auth-login__field">
              <label htmlFor="register-company-cp">Code postal *</label>
              <div className="auth-login__input-wrap auth-login__input-wrap--plain">
                <input
                  id="register-company-cp"
                  type="text"
                  placeholder="101"
                  {...register('code_postal')}
                  className={errors.code_postal ? 'error' : ''}
                  aria-invalid={Boolean(errors.code_postal)}
                />
              </div>
              {errors.code_postal && (
                <span className="auth-login__error" role="alert">
                  {errors.code_postal.message}
                </span>
              )}
            </div>
          </div>

          <div className="auth-login__field">
            <label htmlFor="register-company-plan">Plan d'abonnement *</label>
            <div className="auth-login__input-wrap auth-login__input-wrap--plain auth-login__select-wrap">
              <i className="ti ti-chevron-down" aria-hidden="true" />
              <select
                id="register-company-plan"
                {...register('plan')}
                className={errors.plan ? 'error' : ''}
                aria-invalid={Boolean(errors.plan)}
                disabled={plansLoading || plans.length === 0}
              >
                {plansLoading && (
                  <option value="">Chargement des plans...</option>
                )}
                {!plansLoading && plans.length === 0 && (
                  <option value="">Aucun plan disponible</option>
                )}
                {!plansLoading && plans.map((plan) => (
                  <option key={plan.code} value={plan.code}>
                    {plan.label} — {formatPlanPrice(plan)} ({formatPlanDuration(plan)})
                  </option>
                ))}
              </select>
            </div>
            {errors.plan && (
              <span className="auth-login__error" role="alert">
                {errors.plan.message}
              </span>
            )}
          </div>

          <div className="auth-login__field">
            <label htmlFor="register-company-password">Mot de passe *</label>
            <div className="auth-login__input-wrap">
              <i className="ti ti-lock" aria-hidden="true" />
              <input
                id="register-company-password"
                type="password"
                placeholder="••••••••"
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
            <label htmlFor="register-company-confirm">Confirmer le mot de passe *</label>
            <div className="auth-login__input-wrap">
              <i className="ti ti-lock" aria-hidden="true" />
              <input
                id="register-company-confirm"
                type="password"
                placeholder="••••••••"
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
            <input type="checkbox" id="register-company-terms" {...register('acceptTerms')} />
            <label htmlFor="register-company-terms">
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
                <span>Création de l'entreprise...</span>
              </>
            ) : (
              <>
                <span>Créer mon entreprise</span>
              </>
            )}
          </button>
        </form>

        <div className="auth-login__register-prompt">
          <p>
            Vous préférez un compte simple ?{' '}
            <Link to="/register/simple">Créer un compte utilisateur</Link>
          </p>
        </div>
          </div>
        </section>
      </main>
    </motion.div>
  );
};

export default RegisterCompany;
