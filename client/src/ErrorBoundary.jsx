import React from 'react';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    // Could send to telemetry here
    // console.error('ErrorBoundary caught', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: '20px', background: '#2b2b2b', borderRadius: '8px' }}>
          <h3 style={{ color: '#ff6b6b' }}>Something went wrong loading the admin UI</h3>
          <p style={{ color: '#ccc' }}>{String(this.state.error)}</p>
          <div style={{ marginTop: '12px' }}>
            <button onClick={() => { this.setState({ hasError: false, error: null }); if (this.props.onReset) this.props.onReset(); else window.location.reload(); }} style={{ marginRight: '8px' }}>Go back</button>
            <button onClick={() => window.location.reload()}>Reload</button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
