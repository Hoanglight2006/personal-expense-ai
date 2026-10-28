import React, { Component } from 'react';

class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    if (process.env.NODE_ENV !== 'production') {
      console.error('ErrorBoundary caught an error:', error, errorInfo);
    }
  }

  handleReload = () => {
    this.setState({ hasError: false, error: null });
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            minHeight: '60vh',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '2rem',
            textAlign: 'center',
            fontFamily: 'inherit',
          }}
          role="alert"
        >
          <div
            style={{
              fontSize: '3rem',
              marginBottom: '1rem',
            }}
          >
            ⚠️
          </div>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '0.5rem', color: '#1f2937' }}>
            Đã có lỗi xảy ra khi hiển thị giao diện
          </h2>
          <p style={{ color: '#4b5563', maxWidth: '480px', marginBottom: '1.5rem', lineHeight: 1.5 }}>
            Hệ thống gặp sự cố không mong muốn. Dữ liệu của bạn vẫn an toàn. Vui lòng bấm nút bên dưới để tải lại trang.
          </p>
          <button
            type="button"
            onClick={this.handleReload}
            style={{
              padding: '0.625rem 1.5rem',
              borderRadius: '0.5rem',
              backgroundColor: '#0284c7',
              color: '#ffffff',
              fontWeight: 600,
              border: 'none',
              cursor: 'pointer',
              transition: 'background-color 0.2s',
            }}
          >
            Tải lại trang
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;

