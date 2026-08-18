// src/pages/Clients.jsx
import React, { useState, useEffect } from 'react';
import { clientService } from '../services/api';
import { toast } from 'react-toastify';
import './Pages.css';

const Clients = () => {
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  const [showModal, setShowModal] = useState(false);
  const [currentClient, setCurrentClient] = useState(null);
  const [formData, setFormData] = useState({
    code: '',
    nom: '',
    prenom: '',
    email: '',
    telephone: '',
    adresse_facturation: '',
    ville_facturation: '',
    code_postal_facturation: '',
    pays: 'Madagascar',
    type: 'particulier',
    siret: '',
    numero_tva: '',
  });

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

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const openModal = (client = null) => {
    setCurrentClient(client);
    setFormData(client ? {
      code: client.code || '',
      nom: client.nom || '',
      prenom: client.prenom || '',
      email: client.email || '',
      telephone: client.telephone || '',
      adresse_facturation: client.adresse_facturation || '',
      ville_facturation: client.ville_facturation || '',
      code_postal_facturation: client.code_postal_facturation || '',
      pays: client.pays || 'Madagascar',
      type: client.type || 'particulier',
      siret: client.siret || '',
      numero_tva: client.numero_tva || '',
    } : {
      code: '',
      nom: '',
      prenom: '',
      email: '',
      telephone: '',
      adresse_facturation: '',
      ville_facturation: '',
      code_postal_facturation: '',
      pays: 'Madagascar',
      type: 'particulier',
      siret: '',
      numero_tva: '',
    });
    setShowModal(true);
  };

  const closeModal = () => {
    setShowModal(false);
    setCurrentClient(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (currentClient) {
        await clientService.update(currentClient.id, formData);
        toast.success('Client mis à jour avec succès');
      } else {
        await clientService.create(formData);
        toast.success('Client créé avec succès');
      }
      fetchClients();
      closeModal();
    } catch (err) {
      console.error('Error saving client:', err);
      const msg = err.response?.data?.message || 'Échec de la sauvegarde du client';
      toast.error(msg);
    }
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
    if (phone.startsWith('0')) {
      return phone.replace(/(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})/, '$1 $2 $3 $4 $5');
    }
    return phone.replace(/(\d{3})(\d{3})(\d{4})/, '$1 $2 $3');
  };

  const getClientTypeBadge = (type) => {
    const types = {
      particulier: { label: 'Particulier', class: 'info' },
      professionnel: { label: 'Professionnel', class: 'success' },
    };
    return types[type] || types.particulier;
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
            {clients.filter(c => c.type === 'professionnel').length}
          </div>
          <div className="stat-label">Professionnels</div>
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
            <option value="particulier">Particulier</option>
            <option value="professionnel">Professionnel</option>
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
        <div className="modal-overlay" onClick={closeModal}>
          <div className="modal large" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>{currentClient ? 'Modifier le client' : 'Ajouter un nouveau client'}</h2>
              <button onClick={closeModal} className="btn-close">×</button>
            </div>
            <form onSubmit={handleSubmit} className="modal-form">
              <div className="form-grid">
                <div className="form-group">
                  <label>Code client *</label>
                  <input 
                    type="text" 
                    name="code" 
                    value={formData.code}
                    onChange={handleChange}
                    required
                    placeholder="Code client"
                  />
                </div>
                <div className="form-group">
                  <label>Type de client *</label>
                  <select 
                    name="type" 
                    value={formData.type}
                    onChange={handleChange}
                    required
                  >
                    <option value="particulier">Particulier</option>
                    <option value="professionnel">Professionnel</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Nom *</label>
                  <input 
                    type="text" 
                    name="nom" 
                    value={formData.nom}
                    onChange={handleChange}
                    required
                    placeholder="Nom"
                  />
                </div>
                <div className="form-group">
                  <label>Prénom</label>
                  <input 
                    type="text" 
                    name="prenom" 
                    value={formData.prenom}
                    onChange={handleChange}
                    placeholder="Prénom"
                  />
                </div>
                <div className="form-group">
                  <label>Email</label>
                  <input 
                    type="email" 
                    name="email" 
                    value={formData.email}
                    onChange={handleChange}
                    placeholder="client@email.com"
                  />
                </div>
                <div className="form-group">
                  <label>Téléphone</label>
                  <input 
                    type="tel" 
                    name="telephone" 
                    value={formData.telephone}
                    onChange={handleChange}
                    placeholder="0612345678"
                  />
                </div>
                <div className="form-group full-width">
                  <label>Adresse</label>
                  <input 
                    type="text" 
                    name="adresse_facturation" 
                    value={formData.adresse_facturation}
                    onChange={handleChange}
                    placeholder="Rue, numéro"
                  />
                </div>
                <div className="form-group">
                  <label>Code postal</label>
                  <input 
                    type="text" 
                    name="code_postal_facturation" 
                    value={formData.code_postal_facturation}
                    onChange={handleChange}
                     placeholder="101"
                  />
                </div>
                <div className="form-group">
                  <label>Ville</label>
                  <input 
                    type="text" 
                    name="ville_facturation" 
                    value={formData.ville_facturation}
                    onChange={handleChange}
                     placeholder="Antananarivo"
                  />
                </div>
                <div className="form-group">
                  <label>Pays</label>
                  <input 
                    type="text" 
                    name="pays" 
                    value={formData.pays}
                    onChange={handleChange}
                     placeholder="Madagascar"
                  />
                </div>
                
                {formData.type === 'professionnel' && (
                  <>
                    <div className="form-group">
                      <label>SIRET</label>
                      <input 
                        type="text" 
                        name="siret" 
                        value={formData.siret}
                        onChange={handleChange}
                        placeholder="123 456 789 00010"
                      />
                    </div>
                  <div className="form-group">
                    <label>TVA Intracommunautaire</label>
                    <input 
                      type="text" 
                      name="numero_tva" 
                      value={formData.numero_tva}
                      onChange={handleChange}
                      placeholder="FRXX 123456789"
                    />
                  </div>
                  </>
                )}
              </div>
              <div className="modal-footer">
                <button type="button" onClick={closeModal} className="btn-secondary">
                  Annuler
                </button>
                <button type="submit" className="btn-primary" disabled={!formData.nom}>
                  {currentClient ? 'Mettre à jour' : 'Ajouter'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Clients;
