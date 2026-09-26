// shared/components/SyncStatus/SyncStatus.jsx
// Badge d'état de réplication — uniquement sur le desktop embarqué.

import React, { useEffect, useState } from 'react';
import api from '../../services/api';

export default function SyncStatus() {
  const [state, setState] = useState(null);

  useEffect(() => {
    if (typeof window === 'undefined' || !(window.electron && window.electron.backend)) return undefined;
    let alive = true;
    const poll = async () => {
      try {
        const { data } = await api.get('/sync/local-status', { _forceLocal: true });
        if (alive) setState({ ...data, reachable: true });
      } catch {
        if (alive) setState({ reachable: false, pending_count: '?' });
      }
    };
    poll();
    const id = setInterval(poll, 30000);
    return () => { alive = false; clearInterval(id); };
  }, []);

  if (!state) return null;

  const driftWarning = !!state.clock_drift_warning;

  const label = !state.reachable
    ? 'Serveur local injoignable'
    : !state.online
      ? 'Hors-ligne — données locales uniquement'
      : state.pending_count > 0
        ? `${state.pending_count} modification(s) en attente`
        : 'Synchronisé';

  // L'horloge du poste arbitre les conflits (dernière écriture gagnante) :
  // un décalage avec le serveur doit être visible, pas seulement journalisé.
  const driftLabel = driftWarning
    ? ` — ⚠ horloge du poste décalée de ${Math.round(Math.abs(state.clock_drift_seconds) / 60)} min`
    : '';

  const color = !state.reachable || !state.online ? '#ef4444'
    : (state.pending_count > 0 || driftWarning) ? '#f59e0b' : '#22c55e';

  const title = driftWarning
    ? `${label}${driftLabel}. Corrigez la date/heure du poste : les conflits de synchronisation sont arbitrés par la date la plus récente.`
    : label;

  return (
    <span className="sync-status" title={title} style={{ color, fontWeight: 600 }}>
      ● {label}{driftLabel}
    </span>
  );
}
