// desk/src/pages/SyncConflicts.jsx
import React, { useEffect, useState } from 'react';
import api from '../services/desktopApi';

export default function SyncConflicts() {
  const [conflicts, setConflicts] = useState([]);

  useEffect(() => {
    api.get('/sync/conflicts').then((r) => setConflicts(r.data.conflicts || [])).catch(() => {});
  }, []);

  const resolve = (id, resolution) => {
    api.post(`/sync/conflicts/${id}/resolve`, { resolution })
      .then(() => setConflicts(conflicts.map((c) => c.id === id ? { ...c, resolved_as: resolution } : c)))
      .catch(() => {});
  };

  return (
    <div className="p-6">
      <h1 className="text-xl font-bold mb-4">Conflits de synchronisation</h1>
      {conflicts.length === 0 ? (
        <p className="text-gray-500">Aucun conflit en attente.</p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b">
              <th className="text-left p-2">Entité</th>
              <th className="text-left p-2">PK</th>
              <th className="text-left p-2">Résolu</th>
            </tr>
          </thead>
          <tbody>
            {conflicts.map((c) => (
              <tr key={c.id} className="border-b">
                <td className="p-2">{c.entity}</td>
                <td className="p-2">{c.entity_pk}</td>
                <td className="p-2">{c.resolved_as || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
