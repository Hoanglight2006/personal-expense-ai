import React, { useState, useEffect, useCallback } from 'react';
import { generateMonthlyReport } from '../api/aiApi';

const formatCurrency = (val) => {
  const num = Number(val) || 0;
  return new Intl.NumberFormat('vi-VN').format(num) + ' đ';
};

const getScoreColorClass = (score) => {
  if (score >= 80) return 'score-excellent';
  if (score >= 65) return 'score-good';
  if (score >= 45) return 'score-warning';
  return 'score-danger';
};

const AiReportModal = ({ isOpen, onClose, month }) => {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [copied, setCopied] = useState(false);

  const loadReport = useCallback(async (signal) => {
    if (!month) return;
    setLoading(true);
    setError('');
    try {
      const data = await generateMonthlyReport(month, signal);
      setReport(data);
    } catch (err) {
      if (err.name !== 'CanceledError' && err.message !== 'canceled') {
        setError(err.response?.data?.detail || 'Không thể tạo báo cáo AI lúc này. Vui lòng thử lại sau.');
      }
    } finally {
      setLoading(false);
    }
  }, [month]);

  useEffect(() => {
    if (isOpen && month) {
      const controller = new AbortController();
      loadReport(controller.signal);
      return () => controller.abort();
    }
  }, [isOpen, month, loadReport]);

  const handleCopyMarkdown = async () => {
    if (!report?.raw_markdown) return;
    try {
      await navigator.clipboard.writeText(report.raw_markdown);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch {
      // Fallback
    }
  };

  if (!isOpen) return null;

  const [y, m] = (month || '').split('-');
  const monthDisplay = m && y ? `Tháng ${m}/${y}` : 'Tháng này';

  return (
    <div className="modal-overlay" onClick={onClose} role="dialog" aria-modal="true">
      <div className="modal-content ai-report-modal-content" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="ai-report-header">
          <div className="ai-report-title-group">
            <div className="ai-badge">✨ AI Financial Intelligence</div>
            <h2>Báo Cáo Phân Tích Chi Tiêu {monthDisplay}</h2>
            <p className="ai-report-subtitle">
              Được tổng hợp và phân tích tự động dựa trên dữ liệu giao dịch thực tế
            </p>
          </div>

          <div className="ai-header-right">
            {report && !loading && (
              <div className={`health-score-badge ${getScoreColorClass(report.financial_health_score)}`}>
                <div className="score-number">{report.financial_health_score}<span>/100</span></div>
                <div className="score-status">{report.health_status}</div>
              </div>
            )}
            <button
              type="button"
              className="modal-close-btn"
              onClick={onClose}
              aria-label="Đóng báo cáo"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="ai-report-body">
          {loading && (
            <div className="ai-report-loading">
              <div className="ai-spinner" />
              <p>FinAI đang phân tích số liệu tài chính {monthDisplay} của bạn...</p>
              <span>Vui lòng chờ trong giây lát</span>
            </div>
          )}

          {error && !loading && (
            <div className="ai-report-error error-message" role="alert">
              <p>{error}</p>
              <button type="button" className="btn-secondary" onClick={() => loadReport()}>
                Thử lại
              </button>
            </div>
          )}

          {report && !loading && (
            <div className="ai-report-content fade-in">
              {/* 4 Financial Stat Tiles */}
              <div className="report-stats-grid">
                <div className="stat-tile income">
                  <span className="stat-tile-label">Tổng Thu Nhập</span>
                  <strong className="stat-tile-value text-emerald">{formatCurrency(report.total_income)}</strong>
                </div>
                <div className="stat-tile expense">
                  <span className="stat-tile-label">Tổng Chi Tiêu</span>
                  <strong className="stat-tile-value text-rose">{formatCurrency(report.total_expense)}</strong>
                </div>
                <div className="stat-tile savings">
                  <span className="stat-tile-label">Thặng Dư Tiết Kiệm</span>
                  <strong className={`stat-tile-value ${Number(report.net_savings) >= 0 ? 'text-emerald' : 'text-rose'}`}>
                    {formatCurrency(report.net_savings)}
                  </strong>
                </div>
                <div className="stat-tile rate">
                  <span className="stat-tile-label">Tỷ Lệ Tiết Kiệm</span>
                  <strong className="stat-tile-value text-amber">{report.savings_rate}%</strong>
                </div>
              </div>

              {/* Section 1: Overview */}
              <div className="report-card">
                <div className="report-card-title">
                  <span className="report-section-icon">📌</span>
                  <h3>1. Tóm Tắt Tổng Quan</h3>
                </div>
                <p className="report-text">{report.overview}</p>
              </div>

              {/* Section 2: Trend Analysis */}
              <div className="report-card">
                <div className="report-card-title">
                  <span className="report-section-icon">📈</span>
                  <h3>2. Phân Tích Xu Hướng & Cơ Cấu Chi Tiêu</h3>
                </div>
                <p className="report-text">{report.trend_analysis}</p>

                {/* Top Categories Bars */}
                {report.top_categories?.length > 0 && (
                  <div className="report-top-categories">
                    <h4>Cơ cấu danh mục chiếm tỷ trọng lớn:</h4>
                    <div className="report-categories-list">
                      {report.top_categories.map((cat, idx) => (
                        <div key={idx} className="report-cat-item">
                          <div className="report-cat-meta">
                            <span className="report-cat-name">{cat.name}</span>
                            <span className="report-cat-amount font-mono">
                              {formatCurrency(cat.amount)} ({cat.percentage}%)
                            </span>
                          </div>
                          <div className="report-cat-bar-bg">
                            <div
                              className="report-cat-bar-fill"
                              style={{
                                width: `${Math.min(100, Math.max(5, cat.percentage))}%`,
                                backgroundColor: cat.color || '#f59e0b',
                              }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Section 3: 3 Actionable Adjustments */}
              <div className="report-card highlight-card">
                <div className="report-card-title">
                  <span className="report-section-icon">💡</span>
                  <h3>3. 3 Điểm Khuyến Nghị Cần Điều Chỉnh</h3>
                </div>
                <div className="report-adjustments-grid">
                  {report.adjustments.map((adj, idx) => (
                    <div key={idx} className="adjustment-item">
                      <div className="adj-number">{idx + 1}</div>
                      <div className="adj-content">
                        <p>{adj}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Section 4: Conclusion */}
              <div className="report-card conclusion-card">
                <div className="report-card-title">
                  <span className="report-section-icon">🎯</span>
                  <h3>4. Lời Khuyên & Mục Tiêu Kế Tiếp</h3>
                </div>
                <p className="report-text conclusion-text">{report.conclusion}</p>
              </div>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="ai-report-footer">
          <div className="footer-left">
            {copied && <span className="copy-success-toast">✓ Đã sao chép báo cáo Markdown!</span>}
          </div>
          <div className="footer-right">
            <button
              type="button"
              className="btn-secondary"
              onClick={handleCopyMarkdown}
              disabled={!report || loading}
            >
              📋 Sao chép Markdown
            </button>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => loadReport()}
              disabled={loading}
            >
              🔄 Sinh lại
            </button>
            <button type="button" className="btn-primary" onClick={onClose}>
              Đóng
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AiReportModal;
