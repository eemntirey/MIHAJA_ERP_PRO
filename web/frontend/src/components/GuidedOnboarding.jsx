import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  clientService,
  commandeAchatService,
  factureService,
  productService,
  saleService,
} from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import './GuidedOnboarding.css';

const GUIDE_VERSION = 'v2';
const STORAGE_PREFIX = 'erp-guided-onboarding';
export const ONBOARDING_ACTION_EVENT = 'erp:onboarding-action';

const STEPS = [
  {
    id: 'products',
    title: 'Préparez votre catalogue',
    text: 'Créez au moins un produit avec son prix et son unité. Ce catalogue servira ensuite aux achats et aux ventes.',
    actionLabel: 'Créer mon premier produit',
    href: '/products',
    module: 'produits',
    icon: 'ti-package',
    context: 'Dans Produits, cliquez sur « Nouveau produit ». Le guide détectera automatiquement la création.',
  },
  {
    id: 'clients',
    title: 'Ajoutez votre premier client',
    text: 'Une fiche client suffit pour démarrer vos ventes et garder un historique propre.',
    actionLabel: 'Ajouter un client',
    href: '/clients',
    module: 'clients',
    icon: 'ti-users',
    context: 'Dans Clients, créez une fiche. Vous n’avez pas besoin de renseigner un identifiant technique.',
  },
  {
    id: 'purchases',
    title: 'Alimentez le stock',
    text: 'Enregistrez votre premier achat ou une réception pour que le stock commence à vivre dans MIHAJA.',
    actionLabel: 'Enregistrer un achat',
    href: '/purchases',
    module: 'achats',
    icon: 'ti-shopping-bag',
    context: 'Créez une commande puis enregistrez la réception. Le stock est mis à jour automatiquement.',
  },
  {
    id: 'sales',
    title: 'Faites votre première vente',
    text: 'Ajoutez un client, vos produits, puis enregistrez la vente. Les montants sont calculés automatiquement.',
    actionLabel: 'Créer une vente',
    href: '/sales',
    module: 'ventes',
    icon: 'ti-shopping-cart',
    context: 'Dans Ventes, choisissez un client et ajoutez les produits vendus. Le guide suivra la création.',
  },
  {
    id: 'invoices',
    title: 'Suivez votre facturation',
    text: 'Après une vente, créez ou vérifiez la facture et enregistrez un paiement lorsque nécessaire.',
    actionLabel: 'Ouvrir les factures',
    href: '/invoices',
    module: 'factures',
    icon: 'ti-file-invoice',
    context: 'Depuis une vente ou Factures, créez une facture. Sa présence sera détectée automatiquement.',
  },
  {
    id: 'ai',
    title: 'Faites travailler l’assistant IA',
    text: 'Posez une question métier sur vos ventes, votre stock ou vos priorités pour découvrir l’assistant.',
    actionLabel: 'Tester l’assistant IA',
    href: '/ai',
    module: 'ia',
    icon: 'ti-sparkles',
    context: 'Posez simplement une question. Dès que l’assistant répond, cette étape passe automatiquement en terminée.',
  },
];

const getStorageKey = (user) =>
  `${STORAGE_PREFIX}:${GUIDE_VERSION}:${user?.tenant_id || user?.tenant?.id || user?.id || user?.email || 'session'}`;

const emptyProgress = () => Object.fromEntries(STEPS.map((step) => [step.id, false]));

const readProgress = (user) => {
  const progress = emptyProgress();
  try {
    const raw = localStorage.getItem(getStorageKey(user));
    const parsed = raw ? JSON.parse(raw) : null;
    if (parsed?.steps && typeof parsed.steps === 'object') {
      Object.keys(progress).forEach((id) => {
        progress[id] = parsed.steps[id] === true;
      });
    }
  } catch {
    // Le guide reste fonctionnel sans localStorage.
  }
  return progress;
};

const persistState = (user, steps, status = 'started') => {
  try {
    localStorage.setItem(getStorageKey(user), JSON.stringify({
      status,
      steps,
      updated_at: new Date().toISOString(),
    }));
  } catch {
    // ignore storage errors
  }
};

const readCount = (data, collectionKey) => {
  if (typeof data?.total === 'number') return data.total;
  if (typeof data?.count === 'number') return data.count;
  if (Array.isArray(data?.[collectionKey])) return data[collectionKey].length;
  if (Array.isArray(data)) return data.length;
  return 0;
};

export const markOnboardingAction = (action) => {
  if (!action) return;
  window.dispatchEvent(new CustomEvent(ONBOARDING_ACTION_EVENT, {
    detail: { action },
  }));
};

const GuidedOnboarding = ({ open, onClose }) => {
  const { user, getAllowedModules, hasRole } = useAuth();
  const location = useLocation();
  const allowedModules = getAllowedModules();
  const isSuperAdmin = hasRole('SUPER_ADMIN');
  const steps = useMemo(() => {
    if (!Array.isArray(allowedModules)) return STEPS;
    return STEPS.filter((step) => allowedModules.includes(step.module));
  }, [allowedModules]);

  const [progress, setProgress] = useState(() => readProgress(user));
  const [activeId, setActiveId] = useState(null);
  const [expanded, setExpanded] = useState(true);
  const [checking, setChecking] = useState(false);

  const firstPendingId = useMemo(
    () => steps.find((step) => !progress[step.id])?.id || null,
    [steps, progress]
  );
  const activeStep = steps.find((step) => step.id === (activeId || firstPendingId)) || steps[0];
  const completedCount = steps.filter((step) => progress[step.id]).length;
  const allComplete = steps.length > 0 && completedCount === steps.length;
  const progressPercent = steps.length ? Math.round((completedCount / steps.length) * 100) : 0;
  const activeCompleted = Boolean(activeStep && progress[activeStep.id]);
  const onCurrentPage = Boolean(activeStep && location.pathname === activeStep.href);

  const refreshProgress = useCallback(async () => {
    if (!user || steps.length === 0) return;
    setChecking(true);

    const detected = {};
    const requests = [];

    const addCheck = (id, promise, key) => {
      if (next[id]) return;
      requests.push(
        Promise.resolve(promise)
          .then((response) => {
            const total = readCount(response?.data, key);
            if (total > 0) detected[id] = true;
          })
          .catch(() => {})
      );
    };

    if (steps.some((step) => step.id === 'products')) {
      addCheck('products', productService.getAll(), 'produits');
    }
    if (steps.some((step) => step.id === 'clients')) {
      addCheck('clients', clientService.getAll(), 'clients');
    }
    if (steps.some((step) => step.id === 'purchases')) {
      addCheck('purchases', commandeAchatService.getAll(), 'commandes');
    }
    if (steps.some((step) => step.id === 'sales')) {
      addCheck('sales', saleService.getAll({ limit: 1 }), 'ventes');
    }
    if (steps.some((step) => step.id === 'invoices')) {
      addCheck('invoices', factureService.getAll(), 'factures');
    }

    await Promise.all(requests);

    setProgress((current) => {
      const merged = { ...current, ...detected };
      persistState(user, merged);
      return merged;
    });
    setChecking(false);
  }, [user, steps, progress]);

  useEffect(() => {
    if (!user) return;
    setProgress(readProgress(user));
  }, [user]);

  useEffect(() => {
    if (!open || !user) return;
    const current = readProgress(user);
    persistState(user, current, current && Object.values(current).some(Boolean) ? 'started' : 'started');
    setProgress(current);
    setExpanded(true);
    setActiveId((id) => id || steps.find((step) => !current[step.id])?.id || steps[0]?.id || null);
    refreshProgress();
  }, [open, user]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const handler = (event) => {
      const action = event.detail?.action;
      if (!action || !steps.some((step) => step.id === action)) return;
      setProgress((current) => {
        if (current[action]) return current;
        const next = { ...current, [action]: true };
        if (user) persistState(user, next);
        return next;
      });
      setActiveId(action);
      setExpanded(true);
    };

    window.addEventListener(ONBOARDING_ACTION_EVENT, handler);
    return () => window.removeEventListener(ONBOARDING_ACTION_EVENT, handler);
  }, [steps, user]);

  useEffect(() => {
    if (!open || !allComplete) return;
    if (!user) return;
    persistState(user, progress, 'completed');
  }, [allComplete, open, progress, user]);

  useEffect(() => {
    if (!activeStep || !activeCompleted || allComplete) return undefined;
    const timer = window.setTimeout(() => {
      const next = steps.find((step) => !progress[step.id]);
      if (next) setActiveId(next.id);
    }, 750);
    return () => window.clearTimeout(timer);
  }, [activeStep, activeCompleted, allComplete, progress, steps]);

  if (!open || !user || isSuperAdmin || steps.length === 0) return null;

  const openStep = (step) => {
    setActiveId(step.id);
    setExpanded(false);
  };

  const finish = () => {
    persistState(user, progress, 'completed');
    onClose();
  };

  const skip = () => {
    persistState(user, progress, 'skipped');
    onClose();
  };

  return (
    <div className={`guided-onboarding${expanded ? ' is-expanded' : ' is-collapsed'}`}>
      {expanded ? (
        <section className="guided-onboarding__panel" role="dialog" aria-modal="false" aria-labelledby="guided-onboarding-title">
          <div className="guided-onboarding__accent" />
          <header className="guided-onboarding__header">
            <div>
              <p className="guided-onboarding__eyebrow">
                <i className="ti ti-sparkles" aria-hidden="true" />
                Mise en route MIHAJA
              </p>
              <h2 id="guided-onboarding-title">
                {allComplete ? 'Vous êtes prêt.' : 'Construisons votre premier circuit.'}
              </h2>
            </div>
            <button type="button" className="guided-onboarding__icon-button" onClick={() => setExpanded(false)} aria-label="Réduire le guide">
              <i className="ti ti-minus" aria-hidden="true" />
            </button>
          </header>

          <div className="guided-onboarding__summary">
            <div>
              <strong>{completedCount}/{steps.length}</strong>
              <span>étapes terminées</span>
            </div>
            <div className="guided-onboarding__progress">
              <span style={{ width: `${progressPercent}%` }} />
            </div>
            {checking && <span className="guided-onboarding__checking">Vérification…</span>}
          </div>

          {allComplete ? (
            <div className="guided-onboarding__complete">
              <span className="guided-onboarding__complete-icon"><i className="ti ti-check" aria-hidden="true" /></span>
              <h3>Votre espace est prêt à fonctionner.</h3>
              <p>Catalogue, clients, achats, ventes, facturation et assistant sont maintenant configurés pour démarrer.</p>
              <button type="button" className="guided-onboarding__primary guided-onboarding__primary--full" onClick={finish}>
                Commencer à travailler
                <i className="ti ti-arrow-right" aria-hidden="true" />
              </button>
            </div>
          ) : (
            <>
              <div className="guided-onboarding__body">
                <div className="guided-onboarding__current">
                  <div className="guided-onboarding__step-icon">
                    <i className={`ti ${activeStep?.icon || 'ti-route'}`} aria-hidden="true" />
                  </div>
                  <div>
                    <p className="guided-onboarding__step-label">Prochaine étape</p>
                    <h3>{activeStep?.title}</h3>
                    <p>{onCurrentPage ? activeStep.context : activeStep.text}</p>
                  </div>
                </div>

                <div className="guided-onboarding__steps" aria-label="Progression d’installation">
                  {steps.map((step, index) => {
                    const done = progress[step.id];
                    const active = activeStep?.id === step.id;
                    return (
                      <button
                        type="button"
                        className={`guided-onboarding__step-row${active ? ' is-active' : ''}${done ? ' is-done' : ''}`}
                        key={step.id}
                        onClick={() => openStep(step)}
                      >
                        <span className="guided-onboarding__step-index">
                          {done ? <i className="ti ti-check" aria-hidden="true" /> : index + 1}
                        </span>
                        <span className="guided-onboarding__step-name">{step.title}</span>
                        <i className={`ti ${done ? 'ti-circle-check' : 'ti-chevron-right'}`} aria-hidden="true" />
                      </button>
                    );
                  })}
                </div>
              </div>

              <footer className="guided-onboarding__footer">
                <button type="button" className="guided-onboarding__skip" onClick={skip}>Plus tard</button>
                <div className="guided-onboarding__actions">
                  <Link
                    className="guided-onboarding__primary"
                    to={activeStep.href}
                    onClick={() => openStep(activeStep)}
                  >
                    {onCurrentPage ? 'Continuer ici' : activeStep.actionLabel}
                    <i className="ti ti-arrow-up-right" aria-hidden="true" />
                  </Link>
                  <button
                    type="button"
                    className="guided-onboarding__secondary"
                    onClick={refreshProgress}
                    disabled={checking}
                  >
                    <i className="ti ti-refresh" aria-hidden="true" />
                    Actualiser
                  </button>
                </div>
              </footer>
            </>
          )}
        </section>
      ) : (
        <button type="button" className="guided-onboarding__launcher" onClick={() => setExpanded(true)} aria-label="Ouvrir le guide de mise en route">
          <span className="guided-onboarding__launcher-icon"><i className="ti ti-sparkles" aria-hidden="true" /></span>
          <span className="guided-onboarding__launcher-copy">
            <strong>{allComplete ? 'Mise en route terminée' : `${completedCount}/${steps.length} terminées`}</strong>
            <small>{allComplete ? 'Ouvrir le guide' : 'Poursuivre la mise en route'}</small>
          </span>
          <i className="ti ti-chevron-up" aria-hidden="true" />
        </button>
      )}
    </div>
  );
};

export const shouldOpenGuidedOnboarding = (user) => {
  if (!user || String(user.role || '').toLowerCase() === 'super_admin') return false;
  try {
    const raw = localStorage.getItem(getStorageKey(user));
    if (!raw) return true;
    const parsed = JSON.parse(raw);
    return !['completed', 'skipped'].includes(parsed?.status);
  } catch {
    return true;
  }
};

export default GuidedOnboarding;
