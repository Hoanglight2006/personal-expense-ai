import { useCallback, useEffect, useMemo, useState } from 'react';
import { createPortal } from 'react-dom';
import { formatVndDecimal } from '../utils/money';
import { useModalLock } from '../hooks/useModalLock';
import WarningPopup from './WarningPopup';

const formatDate = (value) => {
  if (!value) return '—';
  const [year, month, day] = value.split('-').map(Number);
  return new Intl.DateTimeFormat('vi-VN', {
    day: '2-digit', month: '2-digit', year: 'numeric',
  }).format(new Date(year, month - 1, day));
};

const ExcelPreviewModal = ({ data, categories, submitting, apiError, onCancel, onConfirm }) => {
  useModalLock(true, onCancel);
  const initialValidRows = useMemo(() => {
    return data
      .filter((row) => !row.is_duplicate)
      .map((row) => {
        let catId = row.category_id;
        if (catId) {
          const cat = categories.find((c) => c.id === catId);
          if (!cat || cat.is_active === false || cat.type !== row.type) {
            catId = null;
          }
        }
        if (!catId) {
          // Attempt to find a fallback category strictly matching the type
          const matchingCat = categories.find(
            (c) => c.is_active !== false && c.type === row.type
          );
          catId = matchingCat ? matchingCat.id : null;
        }
        return {
          ...row,
          category_id: catId,
        };
      });
  }, [data, categories]);

  const [rows, setRows] = useState(initialValidRows);
  const [warningPopup, setWarningPopup] = useState('');
  const duplicateCount = data.length - initialValidRows.length;

  const invalidRowsCount = useMemo(() => {
    return rows.filter((row) => {
      if (!row.category_id) return true;
      const cat = categories.find((c) => c.id === row.category_id);
      return !cat || cat.is_active === false || cat.type !== row.type;
    }).length;
  }, [rows, categories]);

  useEffect(() => {
    if (apiError) setWarningPopup(apiError);
  }, [apiError]);

  const closeWarningPopup = useCallback(() => setWarningPopup(''), []);

  const handleCategoryChange = (index, newCategoryId) => {
    setRows((prev) =>
      prev.map((r, i) => (i === index ? { ...r, category_id: newCategoryId } : r))
    );
  };

  const handleConfirm = () => {
    if (invalidRowsCount > 0) return;
    onConfirm(rows);
  };

  return createPortal(
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
          {invalidRowsCount > 0 && (
            <p className="text-error" role="alert">
              Có <strong>{invalidRowsCount}</strong> dòng chưa chọn danh mục phù hợp. Vui lòng chọn danh mục trước khi nhập.
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
                const matchingCategories = categories.filter(
                  (c) => c.is_active !== false && c.type === row.type
                );
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
                        <option value="" disabled>
                          {matchingCategories.length > 0 ? '-- Chọn danh mục --' : '-- Không có danh mục cùng loại --'}
                        </option>
                        {matchingCategories.map((c) => (
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
            disabled={submitting || rows.length === 0 || invalidRowsCount > 0}
          >
            {submitting ? 'Đang nhập...' : `Nhập ${rows.length} giao dịch`}
          </button>
        </div>
      </div>
      <WarningPopup
        isOpen={Boolean(warningPopup)}
        message={warningPopup}
        onClose={closeWarningPopup}
      />
    </div>,
    document.body
  );
};

export default ExcelPreviewModal;
