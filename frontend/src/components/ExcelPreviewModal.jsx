import { useMemo } from 'react';
import { formatVndDecimal } from '../utils/money';

const formatDate = (value) => {
  if (!value) return '—';
  const [year, month, day] = value.split('-').map(Number);
  return new Intl.DateTimeFormat('vi-VN', {
    day: '2-digit', month: '2-digit', year: 'numeric',
  }).format(new Date(year, month - 1, day));
};

const ExcelPreviewModal = ({ data, categories, submitting, onCancel, onConfirm }) => {
  const validRows = useMemo(() => data.filter((row) => !row.is_duplicate), [data]);
  const duplicateCount = data.length - validRows.length;

  const getCategoryName = (id) => {
    if (!id) return 'Chưa phân loại';
    return categories.find((c) => c.id === id)?.name || 'Chưa phân loại';
  };

  return (
    <div className="modal-backdrop">
      <div className="category-modal excel-preview-modal" role="dialog" aria-label="Xem trước sao kê">
        <div className="modal-header">
          <h2>Xem trước sao kê MBBank</h2>
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
                <th>Danh mục (Dự đoán)</th>
                <th>Nội dung</th>
              </tr>
            </thead>
            <tbody>
              {validRows.map((row, idx) => {
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
                    <td>{getCategoryName(row.category_id)}</td>
                    <td className="text-truncate" title={row.description}>{row.description}</td>
                  </tr>
                );
              })}
              {validRows.length === 0 && (
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
            onClick={() => onConfirm(validRows)} 
            disabled={submitting || validRows.length === 0}
          >
            {submitting ? 'Đang nhập...' : `Nhập ${validRows.length} giao dịch`}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ExcelPreviewModal;
