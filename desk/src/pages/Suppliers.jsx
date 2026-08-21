// src/pages/Suppliers.jsx
import React, { useState, useEffect } from 'react';
import { fournisseurService, productService } from '../services/api';
import { toast } from 'react-toastify';
import { SUPPLIER_TYPES, SUPPLIER_TYPE_LABELS } from '../constants/erpConstants';
import './Pages.css';

const Suppliers = () => {
  const [suppliers, setSuppliers] = useState([]);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  const [showModal, setShowModal] = useState(false);
  const [currentSupplier, setCurrentSupplier] = useState(null);
  const [formData, setFormData] = useState({
    code: '',
    raison_sociale: '',
    nom_commercial: '',
    email: '',
    telephone: '',
    adresse: '',
    ville: '',
    code_postal: '',
    pays: 'Madagascar',
    type: 'fournisseur_local',
    siret: '',
    contact_nom: '',
    contact_email: '',
  });

  const [searchTerm, setSearchTerm] = useState('');

  const fetchSuppliers = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await fournisseurService.getAll({});
      setSuppliers(response.data?.fournisseurs || response.data || []);
    } catch (err) {
      console.error('Error fetching suppliers:', err);
      const msg = err.response?.data?.message || 'Échec du chargement des fournisseurs';
      setError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  const fetchProducts = async () => {
    try {
      const response = await productService.getAll({});
      setProducts(response.data?.produits || response.data || []);
    } catch (err) {
      console.error('Error fetching products:', err);
    }
  };

  useEffect(() => {
    fetchSuppliers();
    fetchProducts();
  }, []);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const openModal = (supplier = null) => {
    setCurrentSupplier(supplier);
    setFormData(supplier ? {
      code: supplier.code || '',
      raison_sociale: supplier.raison_sociale || '',
      nom_commercial: supplier.nom_commercial || '',
      email: supplier.email || '',
      telephone: supplier.telephone || '',
      adresse: supplier.adresse || '',
      ville: supplier.ville || '',
      code_postal: supplier.code_postal || '',
      pays: supplier.pays || 'Madagascar',
      type: supplier.type || 'fournisseur_local',
      siret: supplier.siret || '',
      contact_nom: supplier.contact_nom || '',
      contact_email: supplier.contact_email || '',
    } : {
      code: '',
      raison_sociale: '',
      nom_commercial: '',
      email: '',
      telephone: '',
      adresse: '',
      ville: '',
      code_postal: '',
      pays: 'Madagascar',
      type: 'fournisseur_local',
      siret: '',
      contact_nom: '',
      contact_email: '',
    });
    setShowModal(true);
  };

  const closeModal = () => {
    setShowModal(false);
    setCurrentSupplier(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (currentSupplier) {
        await fournisseurService.update(currentSupplier.id, formData);
        toast.success('Fournisseur mis à jour avec succès');
      } else {
        await fournisseurService.create(formData);
        toast.success('Fournisseur créé avec succès');
      }
      fetchSuppliers();
      closeModal();
    } catch (err) {
      console.error('Error saving supplier:', err);
      const msg = err.response?.data?.message || 'Échec de la sauvegarde du fournisseur';
      toast.error(msg);
    }
  };

  const handleDelete = async (id) => {
    if (window.confirm('Êtes-vous sûr de vouloir supprimer ce fournisseur ?')) {
      try {
        await fournisseurService.delete(id);
        toast.success('Fournisseur supprimé avec succès');
        fetchSuppliers();
      } catch (err) {
        console.error('Error deleting supplier:', err);
        const msg = err.response?.data?.message || 'Échec de la suppression du fournisseur';
        toast.error(msg);
      }
    }
  };

  const filteredSuppliers = suppliers.filter(supplier => {
    return supplier.raison_sociale?.toLowerCase().includes(searchTerm.toLowerCase()) ||
           supplier.email?.toLowerCase().includes(searchTerm.toLowerCase()) ||
           supplier.ville?.toLowerCase().includes(searchTerm.toLowerCase());
  });

  const getSupplierProductsCount = (supplierId) => {
    return products.filter(p => p.fournisseur_id === supplierId).length;
  };

  if (loading && suppliers.length === 0) {
    return (
      <div className="page-container">
        <div className="loading-screen">
          <div className="spinner-large"></div>
          <p>Chargement des fournisseurs...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-container">
        <div className="alert error">
          <p>{error}</p>
          <button onClick={fetchSuppliers} className="btn-primary">Réessayer</button>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1>Fournisseurs</h1>
          <p>Annuaire fournisseurs et contacts</p>
        </div>
        <div className="header-actions">
          <button onClick={() => openModal()} className="btn-primary">
            + Ajouter un fournisseur
          </button>
          <button onClick={fetchSuppliers} className="btn-secondary" disabled={loading}>
            Rafraîchir
          </button>
        </div>
      </div>

      <div className="stats-grid mini">
        <div className="stat-card">
          <div className="stat-value">{suppliers.length}</div>
          <div className="stat-label">Total fournisseurs</div>
        </div>
      </div>

      <div className="card filter-card">
        <div className="filter-controls">
          <div className="search-box">
            <input
              type="text"
              placeholder="Rechercher un fournisseur..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
            <span className="search-icon"><i className="ti ti-search" aria-hidden="true" /></span>
          </div>
        </div>
      </div>

      <div className="card full-width">
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Nom</th>
                <th>Type</th>
                <th>Email</th>
                <th>Téléphone</th>
                <th>Ville</th>
                <th>Contact</th>
                <th>Nb produits</th>
                <th>CA</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredSuppliers.length === 0 ? (
                  <tr>
                    <td colSpan="9" className="text-center">
                      Aucun fournisseur trouvé
                    </td>
                  </tr>
              ) : (
                filteredSuppliers.map(supplier => (
                  <tr key={supplier.id}>
                    <td>{supplier.raison_sociale}</td>
                    <td>{SUPPLIER_TYPE_LABELS[supplier.type] || supplier.type || 'N/A'}</td>
                    <td>{supplier.email || 'N/A'}</td>
                    <td>{supplier.telephone || 'N/A'}</td>
                    <td>{supplier.ville || 'N/A'}</td>
                    <td>{supplier.contact_nom || 'N/A'}</td>
                    <td>{getSupplierProductsCount(supplier.id)}</td>
                    <td>{supplier.chiffre_affaires ? supplier.chiffre_affaires.toFixed(2) + ' Ar' : '0.00 Ar'}</td>
                    <td>
                        <button 
                          onClick={() => openModal(supplier)} 
                          className="btn-small btn-edit"
                          title="Modifier"
                        >
                          <i className="ti ti-edit" aria-hidden="true" />
                        </button>
                        <button 
                          onClick={() => handleDelete(supplier.id)} 
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
              <h2>{currentSupplier ? 'Modifier le fournisseur' : 'Ajouter un nouveau fournisseur'}</h2>
              <button onClick={closeModal} className="btn-close">×</button>
            </div>
            <form onSubmit={handleSubmit} className="modal-form">
              <div className="form-grid">
                <div className="form-group">
                  <label>Code fournisseur *</label>
                  <input 
                    type="text" 
                    name="code" 
                    value={formData.code}
                    onChange={handleChange}
                    required
                    placeholder="Code fournisseur"
                  />
                </div>
                <div className="form-group">
                  <label>Raison sociale *</label>
                  <input 
                    type="text" 
                    name="raison_sociale" 
                    value={formData.raison_sociale}
                    onChange={handleChange}
                    required
                    placeholder="Raison sociale du fournisseur"
                  />
                </div>
                <div className="form-group">
                  <label>Nom commercial</label>
                  <input 
                    type="text" 
                    name="nom_commercial" 
                    value={formData.nom_commercial}
                    onChange={handleChange}
                    placeholder="Nom commercial"
                  />
                </div>
                <div className="form-group">
                  <label>Type de fournisseur</label>
                  <select 
                    name="type" 
                    value={formData.type}
                    onChange={handleChange}
                  >
                    {SUPPLIER_TYPES.map((t) => (
                      <option key={t.value} value={t.value}>{t.label}</option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label>Email</label>
                  <input 
                    type="email" 
                    name="email" 
                    value={formData.email}
                    onChange={handleChange}
                    placeholder="contact@fournisseur.com"
                  />
                </div>
                <div className="form-group">
                  <label>Téléphone</label>
                  <input 
                    type="tel" 
                    name="telephone" 
                    value={formData.telephone}
                    onChange={handleChange}
                    placeholder="+261 34 00 000 00"
                  />
                </div>
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
                <div className="form-group full-width">
                  <label>Adresse</label>
                  <input 
                    type="text" 
                    name="adresse" 
                    value={formData.adresse}
                    onChange={handleChange}
                    placeholder="Rue, numéro"
                  />
                </div>
                <div className="form-group">
                  <label>Code postal</label>
                  <input 
                    type="text" 
                    name="code_postal" 
                    value={formData.code_postal}
                    onChange={handleChange}
                     placeholder="101"
                  />
                </div>
                <div className="form-group">
                  <label>Ville</label>
                  <input 
                    type="text" 
                    name="ville" 
                    value={formData.ville}
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
                <div className="form-group">
                  <label>Nom du contact</label>
                  <input 
                    type="text" 
                    name="contact_nom" 
                    value={formData.contact_nom}
                    onChange={handleChange}
                    placeholder="Jean Rakoto"
                  />
                </div>
                <div className="form-group">
                  <label>Email du contact</label>
                  <input 
                    type="email" 
                    name="contact_email" 
                    value={formData.contact_email}
                    onChange={handleChange}
                    placeholder="contact@fournisseur.com"
                  />
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" onClick={closeModal} className="btn-secondary">
                  Annuler
                </button>
                <button type="submit" className="btn-primary" disabled={!formData.raison_sociale}>
                  {currentSupplier ? 'Mettre à jour' : 'Ajouter'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Suppliers;
