import { memo } from 'react';
import CategoryIcon from './CategoryIcon';
import { formatVndDecimal } from '../utils/money';

const CategoryCard = ({ category, index = 0, onEdit, onHide, onRestore, onDelete, busy }) => {
  return (
    <article
      className={`category-card${category.is_active ? '' : ' category-card-hidden'}`}
      style={{
        '--category-color': category.color,
        '--card-delay': `${Math.min(index, 8) * 22}ms`,
      }}
    >
      <div className="category-card-top">
        <CategoryIcon
          icon={category.icon}
          color={category.color}
          className="category-card-icon"
          loading="lazy"
        />
        <div className="category-card-title">
          <h2>{category.name}</h2>
          <div className="category-badges">
            {category.is_default && <span className="category-default-badge">Mặc định</span>}
            {!category.is_active && <span className="category-status-hidden">Đã ẩn</span>}
          </div>
        </div>
      </div>

      <div className="category-amount">
        <strong>{formatVndDecimal(category.total_amount)}</strong>
        <span>{category.transaction_count} giao dịch · {category.expense_percentage === null ? '—' : `${category.expense_percentage ?? '0.00'}% tổng chi`}</span>
      </div>

      <div className="category-card-actions">
        <button type="button" className="btn-secondary" onClick={() => onEdit(category)} disabled={busy}>
          Sửa
        </button>
        {category.is_active ? (
          <button type="button" className="btn-soft-danger" onClick={() => onHide(category)} disabled={busy}>
            Ẩn
          </button>
        ) : (
          <button type="button" className="btn-soft-success" onClick={() => onRestore(category)} disabled={busy}>
            Khôi phục
          </button>
        )}
        <button type="button" className="btn-danger" onClick={() => onDelete(category)} disabled={busy} title="Xóa danh mục">
          Xóa
        </button>
      </div>
    </article>
  );
};

export default memo(CategoryCard);
