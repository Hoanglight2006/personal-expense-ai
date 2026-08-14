import { memo } from 'react';
import CategoryIcon from './CategoryIcon';
import { formatVndDecimal } from '../utils/money';
import { paymentMethodLabel } from '../constants/paymentMethods';

const formatDate = (value) => {
  if (!value) return '—';
  const [year, month, day] = value.split('-').map(Number);
  return new Intl.DateTimeFormat('vi-VN', {
    day: '2-digit', month: '2-digit', year: 'numeric',
  }).format(new Date(year, month - 1, day));
};

const TransactionCard = ({
  transaction,
  index = 0,
  onEdit,
  onTrash,
  onRestore,
  onDuplicate,
  onDeletePermanently,
  busy,
  isTrashView = false,
  hideActions = false,
}) => {
  const isIncome = transaction.type === 'income';
  const cat = transaction.category;

  return (
    <article
      className={`txn-card${transaction.is_deleted ? ' txn-card-deleted' : ''}`}
      style={{
        '--txn-card-delay': `${Math.min(index, 12) * 18}ms`,
        '--category-color': cat?.color || '#D69A23',
      }}
    >
      <div className="txn-card-left">
        {cat && (
          <CategoryIcon
            icon={cat.icon}
            color={cat.color}
            className="txn-card-icon"
            loading="lazy"
          />
        )}
        <div className="txn-card-info">
          <div className="txn-card-top-row">
            <span className={`txn-type-badge ${isIncome ? 'txn-type-income' : 'txn-type-expense'}`}>
              {isIncome ? 'Thu' : 'Chi'}
            </span>
            <span className="txn-category-name">{cat?.name || '—'}</span>
            {cat && !cat.is_active && (
              <span className="txn-category-hidden-badge">Ẩn</span>
            )}
          </div>
          {transaction.description && (
            <p className="txn-description">{transaction.description}</p>
          )}
          <div className="txn-meta">
            <span>{formatDate(transaction.transaction_date)}</span>
            <span className="txn-meta-sep">·</span>
            <span>{paymentMethodLabel(transaction.payment_method)}</span>
          </div>
        </div>
      </div>

      <div className="txn-card-right">
        <strong className={`txn-amount ${isIncome ? 'txn-amount-income' : 'txn-amount-expense'}`}>
          {isIncome ? '+' : '−'}{formatVndDecimal(transaction.amount)}
        </strong>
        {!hideActions && (
          <div className="txn-card-actions">
            {isTrashView ? (
              <>
                <button type="button" className="btn-soft-success btn-sm" onClick={() => onRestore?.(transaction)} disabled={busy}>
                  Khôi phục
                </button>
                <button type="button" className="btn-soft-danger btn-sm" onClick={() => onDeletePermanently?.(transaction)} disabled={busy}>
                  Xóa
                </button>
              </>
            ) : (
              <>
                <button type="button" className="btn-secondary btn-sm" onClick={() => onEdit?.(transaction)} disabled={busy} title="Chỉnh sửa">
                  ✏️ Sửa
                </button>
                <button type="button" className="btn-secondary btn-sm" style={{ color: '#0d9488', borderColor: '#ccfbf1', background: '#f0fdfa' }} onClick={() => onDuplicate?.(transaction)} disabled={busy} title="Tạo bản sao">
                  📋 Sao chép
                </button>
                <button type="button" className="btn-soft-danger btn-sm" onClick={() => onTrash?.(transaction)} disabled={busy} title="Xóa">
                  🗑️ Xóa
                </button>
              </>
            )}
          </div>
        )}
      </div>
    </article>
  );
};

export default memo(TransactionCard);
