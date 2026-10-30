import { memo } from 'react';
import { Link } from 'react-router-dom';
import CategoryIcon from './CategoryIcon';
import { formatVndDecimal } from '../utils/money';
import { formatTransactionDateTime } from '../utils/date';
import { paymentMethodLabel } from '../constants/paymentMethods';

const TransactionCard = ({
  transaction,
  onEdit,
  onTrash,
  onRestore,
  onDuplicate,
  onDeletePermanently,
  busy,
  isTrashView = false,
  hideActions = false,
}) => {
  const isTransfer = transaction.type === 'transfer';
  const isWithdraw = transaction.movement_type === 'withdraw';
  const isIncome = transaction.type === 'income';
  const cat = transaction.category;

  const getTypeBadgeClass = () => {
    if (isTransfer) {
      return isWithdraw ? 'txn-type-withdraw' : 'txn-type-saving';
    }
    return isIncome ? 'txn-type-income' : 'txn-type-expense';
  };

  const getTypeBadgeText = () => {
    if (isTransfer) {
      return isWithdraw ? 'Rút quỹ' : 'Tiết kiệm';
    }
    return isIncome ? 'Thu' : 'Chi';
  };

  const getAmountClass = () => {
    if (isTransfer) {
      return isWithdraw ? 'txn-amount-income' : 'txn-amount-saving';
    }
    return isIncome ? 'txn-amount-income' : 'txn-amount-expense';
  };

  const getAmountPrefix = () => {
    if (isTransfer) {
      return isWithdraw ? '+' : '−';
    }
    return isIncome ? '+' : '−';
  };

  const netAvailableAmount = isIncome && transaction.saving_goal_amount
    ? Math.max(0, Number(transaction.amount) - Number(transaction.saving_goal_amount))
    : null;

  return (
    <article
      className={`txn-card${transaction.is_deleted ? ' txn-card-deleted' : ''}`}
    >
      <div className="txn-card-left">
        {cat && (
          <CategoryIcon
            icon={cat.icon}
            color={cat.color}
            className="txn-card-icon"
            loading="lazy"
            compact
          />
        )}
        <div className="txn-card-info">
          <div className="txn-card-top-row">
            <span className={`txn-type-badge ${getTypeBadgeClass()}`}>
              {getTypeBadgeText()}
            </span>
            <span className="txn-category-name">{cat?.name || '—'}</span>
            {cat && (!cat.is_active || cat.is_deleted || cat.deleted_at) && (
              <span className={cat.is_deleted || cat.deleted_at ? 'txn-category-deleted-badge' : 'txn-category-hidden-badge'}>
                {cat.is_deleted || cat.deleted_at ? 'Đã xóa' : 'Ẩn'}
              </span>
            )}
            {transaction.saving_goal_name && (
              <span
                className="txn-saving-alloc-badge"
                title={`Mục tiêu: ${transaction.saving_goal_name}${transaction.saving_goal_amount ? ` · Đã trích: ${formatVndDecimal(transaction.saving_goal_amount)}` : ''}`}
              >
                🎯 {transaction.saving_goal_name}
                {isIncome && transaction.saving_goal_amount ? (
                  <span className="txn-saving-alloc-amount">
                    · Trích {formatVndDecimal(transaction.saving_goal_amount)}
                  </span>
                ) : null}
              </span>
            )}
          </div>
          {transaction.description && (
            <p className="txn-description">{transaction.description}</p>
          )}
          <div className="txn-meta">
            <span>{formatTransactionDateTime(transaction.transaction_date, transaction.created_at)}</span>
            <span className="txn-meta-sep">·</span>
            <span>{paymentMethodLabel(transaction.payment_method)}</span>
          </div>
        </div>
      </div>

      <div className="txn-card-right">
        <div className="txn-amounts-wrap">
          <strong className={`txn-amount ${getAmountClass()}`}>
            {getAmountPrefix()}{formatVndDecimal(transaction.amount)}
          </strong>
          {netAvailableAmount !== null && (
            <span className="txn-amount-net-available" title="Số tiền thực tế cộng vào số dư khả dụng sau khi trích tiết kiệm">
              Vào ví: +{formatVndDecimal(netAvailableAmount)}
            </span>
          )}
        </div>
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
            ) : isTransfer ? (
              <Link to="/saving-goals" className="btn-secondary btn-sm" title="Xem mục tiêu tiết kiệm">
                🎯 Xem hũ
              </Link>
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
