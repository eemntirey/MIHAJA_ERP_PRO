// src/components/ui/QRCode.jsx
// Affichage / génération de QR codes côté desktop. Miroir du composant web
// (web/frontend/src/components/ui/QRCode.jsx) avec le client API partagé
// (token JWT auto-attaché) et le Button local du desk.

import React, { useState, useEffect } from 'react';
import api from '../../services/api';
import Button from './Button';

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: 10,
    padding: 12,
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    width: '100%',
  },
  label: {
    fontWeight: 600,
    color: 'var(--text, #333)',
  },
  placeholder: {
    width: 128,
    height: 128,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'var(--surface-muted, #f5f5f5)',
    color: 'var(--text-muted, #888)',
    borderRadius: 8,
  },
  error: {
    color: 'var(--danger, #c0392b)',
  },
};

export const QRCodeDisplay = ({ data, size = 128, label = 'QR Code', onClose }) => {
  const [qrBase64, setQrBase64] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (data) {
      generateQRCode(data);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data]);

  const generateQRCode = async (produitId) => {
    setLoading(true);
    setError(null);
    try {
      const { data: result } = await api.get(`/produits/${produitId}/qr-code`);
      setQrBase64(result.qr_code);
    } catch (err) {
      setError(err.response?.data?.message || 'Generation du QR code impossible');
    } finally {
      setLoading(false);
    }
  };

  const downloadQRCode = () => {
    if (!qrBase64) return;
    const link = document.createElement('a');
    link.href = qrBase64;
    link.download = `qr-code-${data}.png`;
    link.click();
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <span style={styles.label}>{label}</span>
        {onClose && (
          <Button variant="ghost" size="sm" onClick={onClose} iconOnly aria-label="Fermer">
            ✕
          </Button>
        )}
      </div>
      {loading ? (
        <div style={styles.placeholder}>Génération...</div>
      ) : error ? (
        <div>
          <p style={styles.error}>Erreur : {error}</p>
          <Button variant="secondary" size="sm" onClick={() => generateQRCode(data)}>
            Réessayer
          </Button>
        </div>
      ) : qrBase64 ? (
        <>
          <img
            src={qrBase64}
            alt={`QR Code pour ${data}`}
            width={size}
            height={size}
            style={{ width: size, height: size }}
          />
          <Button variant="outline" size="sm" onClick={downloadQRCode}>
            Télécharger
          </Button>
        </>
      ) : (
        <div style={styles.placeholder}>Pas de QR code</div>
      )}
    </div>
  );
};

export const QRCodeGenerator = ({ value, size = 128 }) => {
  const [qrBase64, setQrBase64] = useState(null);

  useEffect(() => {
    if (value) {
      generateQRCode(value);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  const generateQRCode = async (data) => {
    try {
      const { data: result } = await api.post('/produits/qr-generate', { data });
      setQrBase64(result.qr_code);
    } catch (err) {
      console.error('QR Code generation failed:', err);
    }
  };

  return qrBase64 ? (
    <img src={qrBase64} alt="QR Code" width={size} height={size} />
  ) : (
    <div style={styles.placeholder}>Chargement...</div>
  );
};

export default QRCodeDisplay;