import React, { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import './GuidedOnboarding.css';

const GUIDE_VERSION = 'v1';
const STORAGE_PREFIX = 'erp-guided-onboarding';

const ALL_STEPS = [
  {
    id: 'dashboard',
    title: 'Votre point de départ',
    text: 'Le tableau de bord rassemble vos indicateurs, votre activité récente et les actions à traiter.',
    actionLabel: 'Rester sur le tableau de bord',
    href: '/dashboard',
    module: 'dashboard',
    icon: 'ti-layout-dashboard',
  },
  {
    id: 'products',
    title: '1. Créez votre catalogue',
    text: 'Commencez par enregistrer vos produits, leurs prix, leurs unités et leurs seuils de stock.',
    actionLabel: 'Ouvrir Produits',
    href: '/products',
    module: 'produits',
    icon: 'ti-package',
  },
  {
    id: 'clients',
    title: '2. Ajoutez vos clients',
    text: 'Vos ventes et votre suivi commercial partent de fiches clients simples et identifiables.',
    actionLabel: 'Ouvrir Clients',
    href: '/clients',
    module: 'clients',
    icon: 'ti-users',
  },
  {
    id: 'purchases',
    title: '3. Alimentez votre stock',
    text: 'Enregistrez vos achats et vos réceptions pour que le stock évolue automatiquement.',
    actionLabel: 'Ouvrir Achats',
    href: '/purchases',
    module: 'achats',
    icon: 'ti-shopping-bag',
  },
  {
    id: 'sales',
    title: '4. Enregistrez vos ventes',
    text: 'Choisissez un client, ajoutez les produits et laissez MIHAJA calculer les totaux.',
    actionLabel: 'Ouvrir Ventes',
    href: '/sales',
    module: 'ventes',
    icon: 'ti-shopping-cart',
  },
  {
    id: 'invoices',
    title: '5. Suivez vos factures',
    text: 'Une vente peut produire sa facture. Depuis les factures, vous suivez les paiements et les restes à régler.',
    actionLabel: 'Ouvrir Factures',
    href: '/invoices',
    module: 'factures',
    icon: 'ti-file-invoice',
  },
  {
    id: 'ai',
    title: '6. Utilisez l’assistant IA',
    text: 'Demandez les priorités du moment, les alertes de stock ou une lecture de votre activité.',
    actionLabel: 'Ouvrir l’assistant IA',
    href: '/ai',
    module: 'ia',
    icon: 'ti-sparkles',
  },
];

const getStorageKey = (user) =>
  `${STORAGE_PREFIX}:${GUIDE_VERSION}:${user?.tenant_id || user?.tenant?.id || user?.id || user?.email || 'session'}`;

const GuidedOnboarding = ({ open, onClose }) => {
  const { user, getAllowedModules } = useAuth();
  const allowedModules = getAllowedModules();
  const [stepIndex, setStepIndex] = useState(0);

  const steps = useMemo(() => {
    if (!Array.isArray(allowedModules)) return ALL_STEPS;
    return ALL_STEPS.filter((step) => step.module === 'dashboard' || allowedModules.includes(step.module));
  }, [allowedModules]);

  if (!open || steps.length === 0) return null;

  const safeIndex = Math.min(stepIndex, steps.length - 1);
  const step = steps[safeIndex];
  const isFirst = safeIndex === 0;
  const isLast = safeIndex === steps.length - 1;
  const progress = ((safeIndex + 1) / steps.length) * 100;

  const finish = () => {
    try {
      localStorage.setItem(getStorageKey(user), 'completed');
    } catch {
      // Le guide reste disponible si le stockage navigateur est indisponible.
    }
    onClose();
  };

  const next = () => {
    if (isLast) {
      finish();
      return;
    }
    setStepIndex((value) => value + 1);
  };

  const skip = () => {
    try {
      localStorage.setItem(getStorageKey(user), 'skipped');
    } catch {
      // ignore
    }
    onClose();
  };

  return (
    <div className="guided-onboarding" role="dialog" aria-modal="true" aria-labelledby="guided-onboarding-title">
      <div className="guided-onboarding__backdrop" onClick={skip} />
      <section className="guided-onboarding__dialog">
        <div className="guided-onboarding__progress">
          <span style={{ width: `${progress}%` }} />
        </div>

        <div className="guided-onboarding__header">
          <div className="guided-onboarding__eyebrow">
            <i className={`ti ${step.icon}`} aria-hidden="true" />
            <span>Première utilisation</span>
          </div>
          <button type="button" className="guided-onboarding__close" onClick={skip} aria-label="Fermer le guide">
            <i className="ti ti-x" aria-hidden="true" />
          </button>
        </div>

        <div className="guided-onboarding__body">
          <p className="guided-onboarding__step">Étape {safeIndex + 1} sur {steps.length}</p>
          <h2 id="guided-onboarding-title">{step.title}</h2>
          <p className="guided-onboarding__text">{step.text}</p>

          <Link className="guided-onboarding__action" to={step.href} onClick={onClose}>
            <span>{step.actionLabel}</span>
            <i className="ti ti-arrow-up-right" aria-hidden="true" />
          </Link>
        </div>

        <div className="guided-onboarding__footer">
          <button type="button" className="guided-onboarding__skip" onClick={skip}>
            Passer le guide
          </button>
          <div className="guided-onboarding__navigation">
            <button type="button" className="guided-onboarding__secondary" onClick={() => setStepIndex((value) => Math.max(0, value - 1))} disabled={isFirst}>
              Précédent
            </button>
            <button type="button" className="guided-onboarding__primary" onClick={next}>
              {isLast ? 'Terminer' : 'Suivant'}
              <i className={`ti ${isLast ? 'ti-check' : 'ti-arrow-right'}`} aria-hidden="true" />
            </button>
          </div>
        </div>
      </section>
    </div>
  );
};

export const shouldOpenGuidedOnboarding = (user) => {
  if (!user) return false;
  try {
    return !localStorage.getItem(getStorageKey(user));
  } catch {
    return true;
  }
};

export default GuidedOnboarding;
