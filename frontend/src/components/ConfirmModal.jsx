import React, { useRef } from 'react';
import { useModalLock } from '../hooks/useModalLock';

const ConfirmModal = ({ isOpen, title, message, onConfirm, onCancel, confirmText = 'Xóa', cancelText = 'Hủy', isDanger = true }) => {
  const overlayRef = useRef(null);
  useModalLock(isOpen, onCancel);

  if (!isOpen) return null;

  return (
    <div className="modal-backdrop" ref={overlayRef} onMouseDown={(e) => { if (e.target === overlayRef.current) onCancel(); }}>
      <div className={`category-modal bounce-modal ${isDanger ? 'danger-modal' : ''}`} style={{ maxWidth: '460px', textAlign: 'center', padding: '32px 24px', margin: 'auto' }}>
        <div style={{ fontSize: '3rem', marginBottom: '16px' }}>{isDanger ? '⚠️' : '❓'}</div>
        <h2 style={{ marginBottom: '12px', fontSize: '1.4rem' }}>{title}</h2>
        <p style={{ color: 'var(--text-muted)', marginBottom: '24px', lineHeight: '1.5' }}>{message}</p>
        <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
          <button type="button" className="btn-secondary" style={{ whiteSpace: 'nowrap' }} onClick={onCancel}>{cancelText}</button>
          <button type="button" className={isDanger ? 'btn-primary' : 'btn-primary'} style={isDanger ? { background: '#ef4444', color: '#fff', border: 'none', boxShadow: '0 4px 12px rgba(239, 68, 68, 0.3)', whiteSpace: 'nowrap' } : { whiteSpace: 'nowrap' }} onClick={onConfirm}>{confirmText}</button>
        </div>
      </div>
    </div>
  );
};

export default ConfirmModal;
