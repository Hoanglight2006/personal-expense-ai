import { useState, useMemo } from 'react';
import { formatVndDecimal } from '../utils/money';
import { useModalLock } from '../hooks/useModalLock';

const formatDate = (value) => {
  if (!value) return '—';
  const [year, month, day] = value.split('-').map(Number);
  return new Intl.DateTimeFormat('vi-VN', {
    day: '2-digit', month: '2-digit', year: 'numeric',
  }).format(new Date(year, month - 1, day));
};

const ExcelPreviewModal = ({ data, categories, submitting, onCancel, onConfirm }) => {
  useModalLock(true, onCancel);
  const initialValidRows = useMemo(() => {
    return data
      .filter((row) => !row.is_duplicate)
      .map((row) => {
        let catId = row.category_id;
        if (!catId) {
          // Attempt to find a fallback category matching the type
          const matchingCat = categories.find(
            (c) => c.is_active !== false && c.type === row.type
          ) || categories.find((c) => c.is_active !== false);
          catId = matchingCat ? matchingCat.id : null;
        }
        return {
          ...row,
          category_id: catId,
        };
      });
  }, [data, categories]);

  const [rows, setRows] = useState(initialValidRows);
  const duplicateCount = data.length - initialValidRows.length;

  const handleCategoryChange = (index, newCategoryId) => {
    setRows((prev) =>
      prev.map((r, i) => (i === index ? { ...r, category_id: newCategoryId } : r))
    );
  };

  const handleConfirm = () => {
    // Ensure every row has a valid category_id fallback
    const finalRows = rows.map((row) => {
      if (row.category_id) return row;
      const fallback = categories.find((c) => c.is_active !== false && c.type === row.type)
        || categories.find((c) => c.is_active !== false);
      return {
        ...row,
        category_id: fallback ? fallback.id : (categories[0]?.id || 1),
      };
    });
    onConfirm(finalRows);
  };

  return (
    <div className="modal-backdrop">
      <div className="category-modal excel-preview-modal" role="dialog" aria-label="Xem trước sao kê">
        <div className="modal-header">
          <h2>Xem trước dữ liệu sao kê</h2>
          <button type="button" className="modal-close" onClick={onCancel} aria-disabled={submitting}>✕</button>
        </div>

        <div className="excel-summary">
          <p>Tìm thấy <strong>{data.length}</strong> giao dịch hợp lệ từ file sao kê.</p>
          {duplicateCount > 0 && (
            <p className="text-warning">
              Đã tự động bỏ qua <strong>{duplicateCount}</strong> giao dịch trùng lặp.
            </p>
          )}
        </div>

        <div className="excel-preview-table-container">
          <table className="excel-preview-table">
            <thead>
              <tr>
                <th>Ngày</th>
                <th>Loại</th>
                <th>Số tiền</th>
                <th>Danh mục</th>
                <th>Nội dung</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, idx) => {
                const isIncome = row.type === 'income';
                return (
                  <tr key={idx}>
                    <td className="nowrap">{formatDate(row.transaction_date)}</td>
                    <td>
                      <span className={`txn-type-badge ${isIncome ? 'txn-type-income' : 'txn-type-expense'}`}>
                        {isIncome ? 'Thu' : 'Chi'}
                      </span>
                    </td>
                    <td className={`nowrap font-bold ${isIncome ? 'text-success' : 'text-danger'}`}>
                      {isIncome ? '+' : '-'}{formatVndDecimal(row.amount)}
                    </td>
                    <td>
                      <select
                        className={`excel-category-select ${!row.category_id ? 'unselected' : ''}`}
                        value={row.category_id || ''}
                        onChange={(e) => handleCategoryChange(idx, Number(e.target.value))}
                        aria-label={`Danh mục cho dòng ${idx + 1}`}
                      >
                        <option value="" disabled>-- Chọn danh mục --</option>
                        {categories
                          .filter((c) => c.is_active !== false && c.type === row.type)
                          .map((c) => (
                            <option key={c.id} value={c.id}>
                              {c.name}
                            </option>
                          ))}
                      </select>
                    </td>
                    <td className="text-truncate" title={row.description}>{row.description}</td>
                  </tr>
                );
              })}
              {rows.length === 0 && (
                <tr>
                  <td colSpan="5" className="text-center text-muted py-4">
                    Tất cả giao dịch trong file đều đã tồn tại trên hệ thống.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="txn-form-actions">
          <button type="button" className="btn-secondary" onClick={onCancel} disabled={submitting}>
            Hủy bỏ
          </button>
          <button 
            type="button" 
            className="btn-primary" 
            onClick={handleConfirm} 
            disabled={submitting || rows.length === 0}
          >
            {submitting ? 'Đang nhập...' : `Nhập ${rows.length} giao dịch`}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ExcelPreviewModal;

