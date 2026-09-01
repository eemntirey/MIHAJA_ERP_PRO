import React from 'react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    if (typeof console !== 'undefined' && console.error) {
      console.error('[ErrorBoundary] Uncaught React error', error, info);
    }
    if (this.props.onError) {
      try { this.props.onError(error, info); } catch (_) {}
    }
  }

  handleReload = () => {
    if (typeof window !== 'undefined' && window.location) {
      window.location.reload();
    }
  };

  handleReset = () => {
    this.setState({ hasError: false, error: null });
    if (this.props.onReset) {
      try { this.props.onReset(); } catch (_) {}
    }
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback(this.state.error, this.handleReset);
      }
      return (
        <div
          role="alert"
          style={{
            minHeight: '100vh',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '24px',
            fontFamily: 'system-ui, -apple-system, sans-serif',
            background: '#0f172a',
            color: '#e2e8f0',
          }}
        >
          <h1 style={{ fontSize: '20px', marginBottom: '8px', color: '#fff' }}>
            Une erreur est survenue
          </h1>
          <p style={{ marginBottom: '16px', maxWidth: '480px', textAlign: 'center' }}>
            L&apos;application super-admin a rencontre un probleme
            inattendu. Reessayez ou rechargez la page.
          </p>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              type="button"
              onClick={this.handleReset}
              style={{
                padding: '8px 16px',
                background: '#3b82f6',
                color: '#fff',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
              }}
            >
              Reessayer
            </button>
            <button
              type="button"
              onClick={this.handleReload}
              style={{
                padding: '8px 16px',
                background: '#1e293b',
                color: '#e2e8f0',
                border: '1px solid #334155',
                borderRadius: '6px',
                cursor: 'pointer',
              }}
            >
              Recharger la page
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

export default ErrorBoundary;