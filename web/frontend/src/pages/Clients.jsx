// src/pages/Clients.jsx
import React, { useState, useEffect } from 'react';
import { clientService } from '../services/api';
import { toast } from 'react-toastify';
import ClientModal from '../components/ClientModal';
import { CLIENT_TYPES, CLIENT_TYPE_LABELS } from '../constants/erpConstants';
import './Pages.css';

const Clients = () => {
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [showModal, setShowModal] = useState(false);
  const [currentClient, setCurrentClient] = useState(null);

  const [typeFilter, setTypeFilter] = useState('');
  const [searchTerm, setSearchTerm] = useState('');

  const fetchClients = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await clientService.getAll({});
      setClients(response.data?.clients || response.data || []);
    } catch (err) {
      console.error('Error fetching clients:', err);
      const msg = err.response?.data?.message || 'Échec du chargement des clients';
      setError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchClients();
  }, []);

  const openModal = (client = null) => {
    setCurrentClient(client);
    setShowModal(true);
  };

  const closeModal = () => {
    setShowModal(false);
    setCurrentClient(null);
  };

  const handleDelete = async (id) => {
    if (window.confirm('Êtes-vous sûr de vouloir supprimer ce client ? Cette action est irréversible.')) {
      try {
        await clientService.delete(id);
        toast.success('Client supprimé avec succès');
        fetchClients();
      } catch (err) {
        console.error('Error deleting client:', err);
        const msg = err.response?.data?.message || 'Échec de la suppression du client';
        toast.error(msg);
      }
    }
  };

  const formatPhone = (phone) => {
    if (!phone) return 'N/A';
    const digits = phone.replace(/\D/g, '');
    if (digits.startsWith('261')) {
      const rest = digits.slice(3);
      if (rest.length === 9) {
        return `+261 ${rest.slice(0, 2)} ${rest.slice(2, 4)} ${rest.slice(4, 7)} ${rest.slice(7)}`;
      }
      return `+261 ${rest.replace(/(\d{2})(\d{2})(\d{3})(\d{2})/, '$1 $2 $3 $4')}`;
    }
    if (digits.startsWith('0')) {
      return digits.replace(/(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})/, '$1 $2 $3 $4 $5');
    }
    return digits.replace(/(\d{3})(\d{3})(\d{4})/, '$1 $2 $3');
  };

  const getClientTypeBadge = (type) => {
    const entry = CLIENT_TYPES.find(t => t.value === type);
    const labels = {
      boutique: { label: 'Boutique', class: 'success' },
      epicerie: { label: 'Épicerie', class: 'warning' },
      revendeur: { label: 'Revendeur', class: 'info' },
      semi_grossiste: { label: 'Semi-grossiste', class: 'success' },
      grossiste: { label: 'Grossiste', class: 'success' },
      supermarche: { label: 'Supermarché', class: 'warning' },
      restaurant: { label: 'Restaurant', class: 'info' },
      hotel: { label: 'Hôtel', class: 'info' },
      entreprise: { label: 'Entreprise', class: 'success' },
      institution: { label: 'Institution', class: 'info' },
      particulier: { label: 'Particulier', class: 'info' },
    };
    return labels[type] || (entry ? { label: entry.label, class: 'info' } : { label: type, class: 'info' });
  };

  const formatAddress = (client) => {
    const parts = [client.adresse_facturation, client.code_postal_facturation, client.ville_facturation, client.pays_facturation || client.pays].filter(Boolean);
    return parts.length > 0 ? parts.join(', ') : 'N/A';
  };

  const filteredClients = clients.filter(client => {
    const matchesType = !typeFilter || client.type === typeFilter;
    const matchesSearch = !searchTerm ||
      client.nom?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      client.prenom?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      client.email?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      client.code?.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesType && matchesSearch;
  });

  const totalPurchases = clients.reduce((sum, c) => sum + (c.total_achats || 0), 0);
  const avgPurchases = clients.length > 0 ? totalPurchases / clients.length : 0;

  if (loading && clients.length === 0) {
    return (
      <div className="page-container">
        <div className="loading-screen">
          <div className="spinner-large"></div>
          <p>Chargement des clients...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-container">
        <div className="alert error">
          <p>{error}</p>
          <button onClick={fetchClients} className="btn-primary">Réessayer</button>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1>Clients</h1>
          <p>Gestion du portefeuille clients et prospects</p>
        </div>
        <div className="header-actions">
          <button onClick={() => openModal()} className="btn-primary">
            + Ajouter un client
          </button>
          <button onClick={fetchClients} className="btn-secondary" disabled={loading}>
            Rafraîchir
          </button>
        </div>
      </div>

      <div className="stats-grid mini">
        <div className="stat-card">
          <div className="stat-value">{clients.length}</div>
          <div className="stat-label">Total des clients</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">
            {clients.filter(c => c.type === 'entreprise').length}
          </div>
          <div className="stat-label">Entreprises</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">
            {clients.filter(c => c.type === 'particulier').length}
          </div>
          <div className="stat-label">Particuliers</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{avgPurchases.toFixed(2)} Ar</div>
          <div className="stat-label">Panier moyen</div>
        </div>
      </div>

      <div className="card filter-card">
        <div className="filter-controls">
          <div className="search-box">
            <input
              type="text"
              placeholder="Rechercher un client..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
            <span className="search-icon"><i className="ti ti-search" aria-hidden="true" /></span>
          </div>
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="form-select"
          >
            <option value="">Tous les types</option>
            {CLIENT_TYPES.map((t) => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="card full-width">
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Nom</th>
                <th>Type</th>
                <th>Email</th>
                <th>Téléphone</th>
                <th>Adresse</th>
                <th>Commandes</th>
                <th>Total achats</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredClients.length === 0 ? (
                <tr>
                  <td colSpan="9" className="text-center">
                    Aucun client trouvé
                  </td>
                </tr>
              ) : (
                filteredClients.map(client => (
                  <tr key={client.id}>
                    <td>#{client.id}</td>
                    <td>{(client.nom || '')} {client.prenom && ` ${client.prenom}`}</td>
                    <td>
                      <span className={`badge ${getClientTypeBadge(client.type).class}`}>
                        {getClientTypeBadge(client.type).label}
                      </span>
                    </td>
                    <td>{client.email || 'N/A'}</td>
                    <td>{formatPhone(client.telephone)}</td>
                    <td>{formatAddress(client)}</td>
                    <td>{client.total_commandes || 0}</td>
                    <td>{(client.total_achats || 0).toFixed(2)} Ar</td>
                    <td>
                      <button
                        onClick={() => openModal(client)}
                        className="btn-small btn-edit"
                        title="Modifier"
                      >
                        <i className="ti ti-edit" aria-hidden="true" />
                      </button>
                      <button
                        onClick={() => handleDelete(client.id)}
                        className="btn-small btn-delete"
                        title="Supprimer"
                      >
                        <i className="ti ti-trash" aria-hidden="true" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {showModal && (
        <ClientModal
          client={currentClient}
          onClose={closeModal}
          onSuccess={() => {
            fetchClients();
            closeModal();
          }}
        />
      )}
    </div>
  );
};

export default Clients;
