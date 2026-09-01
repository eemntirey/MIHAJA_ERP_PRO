import React from 'react';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({ errorInfo });
    if (typeof console !== 'undefined' && console.error) {
      console.error('ErrorBoundary caught:', error, errorInfo);
    }
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    if (this.props.onReset) {
      this.props.onReset();
    }
  };

  handleReload = () => {
    if (typeof window !== 'undefined' && window.location) {
      window.location.reload();
    }
  };

  render() {
    if (!this.state.hasError) {
      return this.props.children;
    }

    const { fallbackTitle = 'Une erreur est survenue', showDetails = true } = this.props;
    const message =
      (this.state.error && (this.state.error.message || String(this.state.error))) ||
      'Erreur inconnue';

    return (
      <div
        role="alert"
        style={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '24px',
          background: '#f8fafc',
          color: '#0f172a',
          fontFamily: 'system-ui, -apple-system, sans-serif',
        }}
      >
        <div
          style={{
            maxWidth: '560px',
            width: '100%',
            background: '#ffffff',
            border: '1px solid #e2e8f0',
            borderRadius: '8px',
            padding: '24px',
            boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
          }}
        >
          <h1 style={{ margin: '0 0 8px 0', fontSize: '20px', color: '#b91c1c' }}>
            {fallbackTitle}
          </h1>
          <p style={{ margin: '0 0 16px 0', color: '#475569' }}>
            L'interface a rencontré un problème. Vous pouvez réessayer ou revenir à l'accueil.
          </p>
          {showDetails && (
            <pre
              style={{
                background: '#f1f5f9',
                border: '1px solid #e2e8f0',
                borderRadius: '4px',
                padding: '12px',
                fontSize: '12px',
                overflow: 'auto',
                maxHeight: '160px',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
                color: '#0f172a',
              }}
            >
              {message}
            </pre>
          )}
          <div style={{ display: 'flex', gap: '8px', marginTop: '16px', flexWrap: 'wrap' }}>
            <button
              type="button"
              onClick={this.handleReset}
              style={{
                padding: '8px 16px',
                borderRadius: '4px',
                border: 'none',
                background: '#0f172a',
                color: '#ffffff',
                cursor: 'pointer',
                fontSize: '14px',
              }}
            >
              Réessayer
            </button>
            <button
              type="button"
              onClick={this.handleReload}
              style={{
                padding: '8px 16px',
                borderRadius: '4px',
                border: '1px solid #cbd5e1',
                background: '#ffffff',
                color: '#0f172a',
                cursor: 'pointer',
                fontSize: '14px',
              }}
            >
              Recharger la page
            </button>
            <button
              type="button"
              onClick={() => {
                if (typeof window !== 'undefined' && window.location) {
                  window.location.hash = '/login';
                }
              }}
              style={{
                padding: '8px 16px',
                borderRadius: '4px',
                border: '1px solid #cbd5e1',
                background: '#ffffff',
                color: '#0f172a',
                cursor: 'pointer',
                fontSize: '14px',
              }}
            >
              Retour à la connexion
            </button>
          </div>
        </div>
      </div>
    );
  }
}