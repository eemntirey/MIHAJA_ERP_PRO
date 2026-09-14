import React, { useState, useEffect } from 'react';
import Button from './Button';

export const QRCodeDisplay = ({ data, size = 128, label = 'QR Code', onClose }) => {
  const [qrBase64, setQrBase64] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (data) {
      generateQRCode(data);
    }
  }, [data]);

  const generateQRCode = async (qrData) => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`/api/v1/produits/${qrData}/qr-code`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
      });
      if (!response.ok) throw new Error('Failed to generate QR code');
      const result = await response.json();
      setQrBase64(result.qr_code);
    } catch (err) {
      setError(err.message);
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

  if (error) {
    return (
      <div className="qr-code-error">
        <p>Erreur: {error}</p>
        <Button onClick={() => generateQRCode(data)}>Réessayer</Button>
      </div>
    );
  }

  return (
    <div className="qr-code-display">
      <div className="qr-code-header">
        <span>{label}</span>
        {onClose && (
          <Button variant="ghost" size="sm" onClick={onClose}>
            ✕
          </Button>
        )}
      </div>
      <div className="qr-code-container">
        {loading ? (
          <div className="qr-code-loading">Génération...</div>
        ) : qrBase64 ? (
          <img
            src={qrBase64}
            alt={`QR Code pour ${data}`}
            width={size}
            height={size}
            style={{ width: size, height: size }}
          />
        ) : (
          <div className="qr-code-placeholder">Pas de QR code</div>
        )}
      </div>
      {qrBase64 && (
        <Button variant="outline" size="sm" onClick={downloadQRCode}>
          Télécharger
        </Button>
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
  }, [value]);

  const generateQRCode = async (data) => {
    try {
      const response = await fetch(`/api/v1/produits/qr-generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
        body: JSON.stringify({ data }),
      });
      if (!response.ok) throw new Error('Failed to generate');
      const result = await response.json();
      setQrBase64(result.qr_code);
    } catch (err) {
      console.error('QR Code generation failed:', err);
    }
  };

  return qrBase64 ? (
    <img src={qrBase64} alt="QR Code" width={size} height={size} />
  ) : (
    <div style={{ width: size, height: size, display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f5f5f5' }}>
      Chargement...
    </div>
  );
};

export default QRCodeDisplay;