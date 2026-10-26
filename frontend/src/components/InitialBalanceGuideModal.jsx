import React, { useContext, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { useNavigate } from 'react-router-dom';
import { dismissBalanceGuide } from '../api/authApi';
import { AuthContext } from '../context/auth-context';
import { useModalLock } from '../hooks/useModalLock';
import useBackdropDismiss from '../hooks/useBackdropDismiss';

const InitialBalanceGuideModal = ({ isOpen }) => {
  const { setUser } = useContext(AuthContext);
  const navigate = useNavigate();

  const handleDismiss = useCallback((redirectToAddIncome = false) => {
    // 1. Optimistic dismissal: Close modal instantly (0ms latency)
    setUser((prev) => (prev ? { ...prev, has_seen_initial_balance_guide: true } : null));

    // 2. Immediate navigation if user wants to add initial income
    if (redirectToAddIncome) {
      navigate('/transactions', { state: { openAddModal: true, initialType: 'income' } });
    }

    // 3. Fire-and-forget server sync in background
    dismissBalanceGuide().catch((err) => {
      console.error('Không thể cập nhật cờ đã xem hướng dẫn:', err);
    });
  }, [navigate, setUser]);

  useModalLock(isOpen, () => handleDismiss(false));
  const backdropHandlers = useBackdropDismiss(() => handleDismiss(false));

  if (!isOpen) return null;

  return createPortal(
    <div
      className="modal-backdrop"
      style={{
        zIndex: 9990,
        background: 'rgba(28, 22, 15, 0.65)',
      }}
      {...backdropHandlers}
      role="presentation"
    >
      <div
        className="category-modal"
        style={{
          maxWidth: '520px',
          padding: '32px 28px',
          borderRadius: '24px',
          boxShadow: '0 20px 45px -10px rgba(45, 34, 18, 0.28)',
          background: '#fffdfa',
          willChange: 'transform, opacity',
        }}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="initial-balance-guide-title"
      >
        <div style={{ textAlign: 'center', marginBottom: '20px' }}>
          <div
            style={{
              width: '68px',
              height: '68px',
              margin: '0 auto 14px',
              background: 'linear-gradient(135deg, #fef3c7 0%, #fde68a 100%)',
              border: '2px solid #f59e0b',
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '34px',
              boxShadow: '0 6px 16px rgba(245, 158, 11, 0.25)',
            }}
          >
            🪙
          </div>
          <h2
            id="initial-balance-guide-title"
            style={{
              fontSize: '1.5rem',
              fontWeight: 800,
              color: 'var(--text-color, #2b2319)',
              marginBottom: '6px',
            }}
          >
            Chào mừng bạn đến với FinAI! 🎉
          </h2>
          <p
            style={{
              fontSize: '0.92rem',
              color: 'var(--text-muted, #7c7267)',
            }}
          >
            Khởi tạo số dư ban đầu để bắt đầu quản lý chi tiêu thông minh
          </p>
        </div>

        <div
          style={{
            background: 'rgba(243, 205, 98, 0.12)',
            border: '1px solid rgba(243, 205, 98, 0.35)',
            borderRadius: '16px',
            padding: '18px 20px',
            marginBottom: '24px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px', marginBottom: '12px' }}>
            <span style={{ fontSize: '1.3rem', lineHeight: 1 }}>💡</span>
            <div>
              <strong style={{ display: 'block', color: '#78350f', fontSize: '0.95rem', marginBottom: '4px' }}>
                Nguyên tắc Bảo toàn số dư (Balance Invariance)
              </strong>
              <p style={{ margin: 0, fontSize: '0.88rem', color: '#92400e', lineHeight: 1.5 }}>
                Để tránh tình trạng "chi tiêu vượt quá khả năng thực tế", hệ thống yêu cầu bạn <strong>nhập số dư ban đầu</strong> trước thì mới có thể chi tiêu được.
              </p>
            </div>
          </div>

          <ul
            style={{
              margin: 0,
              paddingLeft: '28px',
              fontSize: '0.86rem',
              color: '#78350f',
              lineHeight: 1.6,
            }}
          >
            <li>Hãy thêm 1 khoản <strong>Thu nhập</strong> đầu tiên (tiền lương, tiền trong ví hoặc tài khoản ngân hàng).</li>
            <li>Số tiền này sẽ trở thành <strong>Số dư khả dụng</strong> giúp bạn tạo ngân sách và chi tiêu an toàn.</li>
          </ul>
        </div>

        <div style={{ display: 'flex', gap: '12px', justifyContent: 'center', flexWrap: 'wrap' }}>
          <button
            type="button"
            className="btn-secondary"
            onClick={() => handleDismiss(false)}
            style={{
              padding: '12px 20px',
              borderRadius: '12px',
              fontWeight: 600,
              fontSize: '0.92rem',
            }}
          >
            Tôi đã hiểu
          </button>
          <button
            type="button"
            className="btn-primary"
            onClick={() => handleDismiss(true)}
            style={{
              padding: '12px 24px',
              borderRadius: '12px',
              fontWeight: 700,
              fontSize: '0.95rem',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <span>⚡</span>
            <span>Thêm thu nhập ngay</span>
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
};

export default React.memo(InitialBalanceGuideModal);
