import React, { useState, useEffect, useRef } from 'react';
import { updateInitialBalanceApi } from '../api/authApi';

const InitialBalanceModal = ({ isOpen, onClose, currentInitialBalance, onUpdated }) => {
  const [rawValue, setRawValue] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const backdropRef = useRef(null);
  const inputRef = useRef(null);

  // Initialize value and lock body scroll
  useEffect(() => {
    if (isOpen) {
      const initialNum = Number(currentInitialBalance || 0);
      setRawValue(initialNum > 0 ? String(initialNum) : '');
      setError('');

      // Lock body scroll
      const prevOverflow = document.body.style.overflow;
      document.body.style.overflow = 'hidden';

      // Focus input without jumping scroll
      const timer = setTimeout(() => {
        inputRef.current?.focus({ preventScroll: true });
      }, 50);

      return () => {
        document.body.style.overflow = prevOverflow;
        clearTimeout(timer);
      };
    }
  }, [isOpen, currentInitialBalance]);

  // Handle ESC key
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && !loading) {
        onClose();
      }
    };
    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, loading, onClose]);

  if (!isOpen) return null;

  const handleInputChange = (e) => {
    // Keep only numbers
    const cleanDigits = e.target.value.replace(/\D/g, '');
    setRawValue(cleanDigits);
  };

  const handleAddPreset = (amount) => {
    const current = Number(rawValue || 0);
    setRawValue(String(current + amount));
  };

  const handleResetZero = () => {
    setRawValue('0');
  };

  const formattedDisplay = rawValue ? Number(rawValue).toLocaleString('vi-VN') : '0';

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    const numAmount = Number(rawValue || 0);
    if (isNaN(numAmount) || numAmount < 0) {
      setError('Số tiền không hợp lệ.');
      setLoading(false);
      return;
    }

    try {
      const updatedUser = await updateInitialBalanceApi(numAmount);
      if (onUpdated) {
        onUpdated(updatedUser);
      }
      onClose();
    } catch (err) {
      console.error('Failed to update initial balance', err);
      setError('Không thể cập nhật số dư. Vui lòng thử lại!');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="modal-backdrop"
      ref={backdropRef}
      onMouseDown={(e) => {
        if (e.target === backdropRef.current && !loading) {
          onClose();
        }
      }}
    >
      <div className="initial-balance-modal" onClick={(e) => e.stopPropagation()}>
        <div className="initial-balance-modal-header">
          <div className="modal-title-group">
            <div className="modal-icon-badge">💰</div>
            <div>
              <h2>Thiết lập số dư ban đầu</h2>
              <p className="modal-subtitle">
                Khai báo số tiền bạn đang có sẵn trong ví/tài khoản để quản lý tài sản chính xác.
              </p>
            </div>
          </div>
          <button
            type="button"
            className="initial-balance-modal-close"
            onClick={onClose}
            disabled={loading}
            aria-label="Đóng form"
            title="Đóng (ESC)"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>

        {error && <div className="modal-error-alert">{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="form-group" style={{ marginBottom: '20px' }}>
            <label htmlFor="initial-balance-input" className="balance-label">Số dư có sẵn (VNĐ)</label>
            <div className="balance-input-wrapper">
              <input
                ref={inputRef}
                id="initial-balance-input"
                type="text"
                className="balance-large-input"
                placeholder="0"
                value={rawValue ? Number(rawValue).toLocaleString('vi-VN') : ''}
                onChange={handleInputChange}
              />
              <span className="currency-suffix">VNĐ</span>
            </div>
            <p className="input-hint">
              Số tiền bằng chữ: <strong>{formattedDisplay} VNĐ</strong>
            </p>
          </div>

          <div className="preset-buttons">
            <span className="preset-label">Cộng nhanh:</span>
            <button type="button" className="btn-preset" onClick={() => handleAddPreset(1000000)}>+1Tr</button>
            <button type="button" className="btn-preset" onClick={() => handleAddPreset(5000000)}>+5Tr</button>
            <button type="button" className="btn-preset" onClick={() => handleAddPreset(10000000)}>+10Tr</button>
            <button type="button" className="btn-preset btn-preset-zero" onClick={handleResetZero}>Đặt về 0đ</button>
          </div>

          <div className="initial-balance-modal-actions">
            <button
              type="button"
              className="btn-secondary btn-modal-cancel"
              onClick={onClose}
              disabled={loading}
            >
              Hủy
            </button>
            <button
              type="submit"
              className="btn-primary btn-modal-save"
              disabled={loading}
            >
              {loading ? 'Đang lưu...' : 'Lưu số dư'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default InitialBalanceModal;
