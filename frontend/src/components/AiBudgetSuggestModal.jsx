import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { getBudgetRecommendations, applyBudgetRecommendations } from '../api/aiApi';
import CategoryIcon from './CategoryIcon';

const formatCurrency = (val) => {
  const num = Number(val) || 0;
  return new Intl.NumberFormat('vi-VN').format(num) + ' đ';
};

const AiBudgetSuggestModal = ({ isOpen, onClose, onApplied, selectedMonth }) => {
  const [data, setData] = useState(null);
  const [editedAmounts, setEditedAmounts] = useState({});
  const [loading, setLoading] = useState(false);
  const [applying, setApplying] = useState(false);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  const loadRecommendations = useCallback(async (signal) => {
    setLoading(true);
    setError('');
    setSuccessMsg('');
    try {
      const res = await getBudgetRecommendations(selectedMonth, signal);
      setData(res);
      // Initialize edited amounts
      const initialMap = {};
      (res.recommendations || []).forEach((item) => {
        initialMap[item.category_id] = item.recommended_amount;
      });
      setEditedAmounts(initialMap);
    } catch (err) {
      if (err.name !== 'CanceledError' && err.message !== 'canceled') {
        setError(err.response?.data?.detail || 'Không thể tải gợi ý ngân sách AI lúc này.');
      }
    } finally {
      setLoading(false);
    }
  }, [selectedMonth]);

  useEffect(() => {
    if (isOpen) {
      const controller = new AbortController();
      loadRecommendations(controller.signal);
      return () => controller.abort();
    }
  }, [isOpen, loadRecommendations]);

  const handleAmountChange = (catId, value) => {
    const cleanNum = value.replace(/\D/g, '');
    setEditedAmounts((prev) => ({
      ...prev,
      [catId]: cleanNum === '' ? '' : Number(cleanNum),
    }));
  };

  const totalCalculated = useMemo(() => {
    return Object.values(editedAmounts).reduce((sum, val) => sum + (Number(val) || 0), 0);
  }, [editedAmounts]);

  const handleApply = async () => {
    if (!data?.recommendations?.length || applying) return;

    setApplying(true);
    setError('');
    try {
      const recommendations = data.recommendations
        .filter((r) => Number(editedAmounts[r.category_id]) > 0)
        .map((r) => ({
          category_id: r.category_id,
          amount: Number(editedAmounts[r.category_id]),
        }));

      if (!recommendations.length) {
        setError('Vui lòng chọn ít nhất 1 danh mục có ngân sách lớn hơn 0.');
        setApplying(false);
        return;
      }

      const res = await applyBudgetRecommendations({
        target_month: data.target_month,
        target_year: data.target_year,
        recommendations,
      });

      setSuccessMsg(res.message || 'Đã áp dụng thành công ngân sách!');
      if (onApplied) {
        onApplied(data.target_month, data.target_year);
      }
      setTimeout(() => {
        onClose();
      }, 1500);
    } catch (err) {
      setError(err.response?.data?.detail || 'Có lỗi xảy ra khi áp dụng ngân sách.');
    } finally {
      setApplying(false);
    }
  };

  if (!isOpen) return null;

  const targetDisplay = data ? `Tháng ${String(data.target_month).padStart(2, '0')}/${data.target_year}` : '';

  return (
    <div className="modal-overlay" onClick={onClose} role="dialog" aria-modal="true">
      <div className="modal-content ai-budget-modal-content" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="ai-budget-header">
          <div className="ai-budget-title-group">
            <div className="ai-badge">✨ AI Smart Budgeting</div>
            <h2>Gợi Ý Hạn Mức Ngân Sách {targetDisplay}</h2>
            <p>
              FinAI phân tích lịch sử chi tiêu 1-3 tháng gần đây và đề xuất hạn mức tối ưu theo quy tắc tài chính
            </p>
          </div>
          <button
            type="button"
            className="modal-close-btn"
            onClick={onClose}
            aria-label="Đóng gợi ý ngân sách"
          >
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="ai-budget-body">
          {loading && (
            <div className="ai-budget-loading">
              <div className="ai-spinner" />
              <p>Đang phân tích thói quen chi tiêu và tính toán hạn mức ngân sách...</p>
            </div>
          )}

          {error && !loading && (
            <div className="error-message" role="alert">
              {error}
            </div>
          )}

          {successMsg && (
            <div className="success-banner" role="status">
              ✓ {successMsg}
            </div>
          )}

          {data && !loading && (
            <div className="ai-budget-content fade-in">
              {/* Summary banner */}
              <div className="ai-budget-summary-banner">
                <div className="summary-col">
                  <span>Mục tiêu áp dụng:</span>
                  <strong>{targetDisplay}</strong>
                </div>
                <div className="summary-col">
                  <span>Số danh mục đề xuất:</span>
                  <strong>{data.recommendations?.length || 0} danh mục</strong>
                </div>
                <div className="summary-col highlight">
                  <span>Tổng ngân sách dự kiến:</span>
                  <strong className="text-amber font-mono">{formatCurrency(totalCalculated)}</strong>
                </div>
              </div>

              {/* Category recommendations list */}
              <div className="ai-recs-list">
                {data.recommendations?.map((item) => (
                    <div key={item.category_id} className="ai-rec-card">
                      <div className="ai-rec-header">
                        <div className="ai-rec-cat-info">
                          <CategoryIcon icon={item.category_icon || 'utensils'} color={item.category_color || '#F59E0B'} />
                          <div>
                            <strong className="cat-name">{item.category_name}</strong>
                            <div className="cat-history-chips">
                              <span>Chi TB: {formatCurrency(item.avg_spent)}</span>
                              <span>Tháng trước: {formatCurrency(item.last_month_spent)}</span>
                            </div>
                          </div>
                        </div>

                        {/* Amount input */}
                        <div className="ai-rec-input-group">
                          <label htmlFor={`rec-input-${item.category_id}`}>Hạn mức (VNĐ):</label>
                          <input
                            id={`rec-input-${item.category_id}`}
                            type="text"
                            className="form-input font-mono"
                            value={
                              editedAmounts[item.category_id] === ''
                                ? ''
                                : Number(editedAmounts[item.category_id] ?? item.recommended_amount).toLocaleString('vi-VN')
                            }
                            onChange={(e) => handleAmountChange(item.category_id, e.target.value)}
                          />
                        </div>
                      </div>

                      {/* Reason */}
                      <div className="ai-rec-reason">
                        <span className="reason-icon">💡</span>
                        <p>{item.reason}</p>
                      </div>
                    </div>
                ))}

                {!data.recommendations?.length && (
                  <div className="empty-state">
                    <p>Chưa tìm thấy danh mục chi tiêu nào khả dụng để gợi ý.</p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="ai-budget-footer">
          <button type="button" className="btn-secondary" onClick={onClose} disabled={applying}>
            Hủy
          </button>
          <button
            type="button"
            className="btn-primary btn-ai-apply"
            onClick={handleApply}
            disabled={loading || applying || !data?.recommendations?.length}
          >
            {applying ? 'Đang áp dụng...' : `✨ Áp Dụng Ngân Sách Vào ${targetDisplay}`}
          </button>
        </div>
      </div>
    </div>
  );
};

export default AiBudgetSuggestModal;
