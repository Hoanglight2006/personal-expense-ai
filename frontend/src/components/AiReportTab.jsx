import React, { useState, useEffect, useMemo } from 'react';
import { generateMonthlyReport } from '../api/aiApi';
import CustomSelect from './CustomSelect';

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

const FOCUS_OPTIONS = [
  {
    id: 'comprehensive',
    icon: '📊',
    title: 'Phân tích toàn diện',
    desc: 'Đánh giá đầy đủ thu nhập, chi tiêu, số dư và chấm điểm sức khỏe tài chính.',
  },
  {
    id: 'saving',
    icon: '💡',
    title: 'Tối ưu tiết kiệm',
    desc: 'Tập trung tìm kiếm các khoản chi lãng phí và gợi ý cắt giảm chi tiêu tối đa.',
  },
  {
    id: 'risk',
    icon: '🛡️',
    title: 'Cảnh báo rủi ro & An toàn',
    desc: 'Kiểm tra tỷ lệ bội chi, cảnh báo thâm hụt và xây dựng quỹ dự phòng.',
  },
];

const MONTH_OPTIONS = Array.from({ length: 12 }, (_, i) => ({
  value: i + 1,
  label: `Tháng ${String(i + 1).padStart(2, '0')}`,
}));

const AiReportTab = ({ defaultMonth }) => {
  const initialDate = useMemo(() => {
    if (defaultMonth && /^\d{4}-\d{2}$/.test(defaultMonth)) {
      const [y, m] = defaultMonth.split('-').map(Number);
      return { month: m, year: y };
    }
    const now = new Date();
    return { month: now.getMonth() + 1, year: now.getFullYear() };
  }, [defaultMonth]);

  const [targetMonth, setTargetMonth] = useState(initialDate.month);
  const [targetYear, setTargetYear] = useState(initialDate.year);
  const [focusOption, setFocusOption] = useState('comprehensive');
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [hasGenerated, setHasGenerated] = useState(false);
  const [showConfig, setShowConfig] = useState(true);
  const [copied, setCopied] = useState(false);

  const yearOptions = useMemo(() => {
    const baseYear = targetYear || new Date().getFullYear();
    const years = [baseYear - 2, baseYear - 1, baseYear, baseYear + 1, baseYear + 2];
    return Array.from(new Set(years)).map((y) => ({
      value: y,
      label: `Năm ${y}`,
    }));
  }, [targetYear]);

  useEffect(() => {
    if (defaultMonth && /^\d{4}-\d{2}$/.test(defaultMonth)) {
      const [y, m] = defaultMonth.split('-').map(Number);
      setTargetMonth(m);
      setTargetYear(y);
    }
  }, [defaultMonth]);

  const selectedMonth = `${targetYear}-${String(targetMonth).padStart(2, '0')}`;

  const handleGenerate = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await generateMonthlyReport(selectedMonth);
      setReport(data);
      setHasGenerated(true);
      setShowConfig(false);
    } catch (err) {
      setError(err.response?.data?.detail || 'Không thể tạo báo cáo AI lúc này. Vui lòng thử lại sau.');
    } finally {
      setLoading(false);
    }
  };

  const handleCopyMarkdown = async () => {
    if (!report?.raw_markdown) return;
    try {
      await navigator.clipboard.writeText(report.raw_markdown);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch {
      // fallback
    }
  };

  const monthDisplay = `Tháng ${String(targetMonth).padStart(2, '0')}/${targetYear}`;

  return (
    <div className="ai-report-tab-container fade-in">
      {/* Options Configuration Card */}
      {showConfig && (
        <div className="ai-config-card">
          <div className="ai-config-header">
            <div className="ai-config-badge">✨ FinAI Analytics Hub</div>
            <h2>Tùy Chọn Sinh Báo Cáo Tài Chính AI</h2>
            <p>Chọn mốc thời gian và trọng tâm phân tích mà bạn mong muốn AI tập trung đánh giá.</p>
          </div>

          <div className="ai-config-body">
            {/* 1. Chọn tháng và năm */}
            <div className="ai-config-section">
              <label className="ai-config-label">1. Chọn thời gian phân tích:</label>
              <div className="ai-month-year-selectors">
                <div className="ai-select-field">
                  <span className="ai-select-prefix">Tháng:</span>
                  <div className="ai-custom-select-wrap">
                    <CustomSelect
                      value={targetMonth}
                      onChange={(e) => setTargetMonth(Number(e.target.value))}
                      options={MONTH_OPTIONS}
                    />
                  </div>
                </div>
                <div className="ai-select-field">
                  <span className="ai-select-prefix">Năm:</span>
                  <div className="ai-custom-select-wrap">
                    <CustomSelect
                      value={targetYear}
                      onChange={(e) => setTargetYear(Number(e.target.value))}
                      options={yearOptions}
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* 2. Trọng tâm phân tích */}
            <div className="ai-config-section">
              <label className="ai-config-label">2. Chọn trọng tâm phân tích:</label>
              <div className="ai-focus-options-grid">
                {FOCUS_OPTIONS.map((opt) => (
                  <button
                    key={opt.id}
                    type="button"
                    className={`ai-focus-card ${focusOption === opt.id ? 'active' : ''}`}
                    onClick={() => setFocusOption(opt.id)}
                  >
                    <span className="focus-card-icon">{opt.icon}</span>
                    <div className="focus-card-info">
                      <strong>{opt.title}</strong>
                      <p>{opt.desc}</p>
                    </div>
                    <span className="focus-card-radio">
                      {focusOption === opt.id && <i className="radio-checked" />}
                    </span>
                  </button>
                ))}
              </div>
            </div>

            {error && <div className="error-message" role="alert">{error}</div>}

            {/* Submit Action */}
            <div className="ai-config-actions">
              <button
                type="button"
                className="btn-ai-generate-confirm"
                onClick={handleGenerate}
                disabled={loading}
              >
                {loading ? (
                  <>
                    <span className="ai-spinner-inline" />
                    FinAI đang phân tích dữ liệu...
                  </>
                ) : (
                  <>
                    <span>🚀</span>
                    Xác Nhận & Sinh Báo Cáo AI ({monthDisplay})
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Loading Skeleton if generating */}
      {loading && !showConfig && (
        <div className="ai-tab-loading-state">
          <div className="ai-spinner" />
          <h3>FinAI đang phân tích dòng tiền {monthDisplay}...</h3>
          <p>Hệ thống đang tổng hợp dữ liệu giao dịch, tính toán điểm sức khỏe tài chính và viết báo cáo chuyên sâu.</p>
        </div>
      )}

      {/* Display Generated Report */}
      {hasGenerated && report && !loading && (
        <div className="ai-report-view-card fade-in">
          {/* Top Bar with Score & Re-configure button */}
          <div className="ai-report-view-header">
            <div className="ai-report-view-title">
              <span className="ai-badge-sub">✨ Báo Cáo Tài Chính AI</span>
              <h2>Phân Tích Chi Tiêu {monthDisplay}</h2>
              <p>Trọng tâm: {FOCUS_OPTIONS.find((o) => o.id === focusOption)?.title || 'Toàn diện'}</p>
            </div>

            <div className="ai-report-view-meta">
              <div
                className={`health-score-pill ${getScoreColorClass(report.financial_health_score)}`}
                aria-label={`Điểm sức khỏe tài chính ${report.financial_health_score} trên 100, ${report.health_status}`}
              >
                <span className="score-caption">Sức khỏe tài chính</span>
                <span className="score-result">
                  <span className="score-val">{report.financial_health_score}</span>
                  <span className="score-max">/100</span>
                </span>
                <span className="score-status">{report.health_status}</span>
              </div>
              <button
                type="button"
                className="btn-reconfigure-ai"
                onClick={() => setShowConfig(!showConfig)}
              >
                {showConfig ? 'Ẩn tùy chọn' : '⚙️ Đổi Tùy Chọn'}
              </button>
            </div>
          </div>

          {/* 4 Financial Tiles */}
          <div className="report-stats-grid">
            <div className="stat-tile income">
              <span className="stat-tile-icon" aria-hidden="true">↗</span>
              <div className="stat-tile-content">
                <span className="stat-tile-label">Tổng Thu Nhập</span>
                <strong className="stat-tile-value text-emerald">{formatCurrency(report.total_income)}</strong>
              </div>
            </div>
            <div className="stat-tile expense">
              <span className="stat-tile-icon" aria-hidden="true">↘</span>
              <div className="stat-tile-content">
                <span className="stat-tile-label">Tổng Chi Tiêu</span>
                <strong className="stat-tile-value text-rose">{formatCurrency(report.total_expense)}</strong>
              </div>
            </div>
            <div className="stat-tile savings">
              <span className="stat-tile-icon" aria-hidden="true">◆</span>
              <div className="stat-tile-content">
                <span className="stat-tile-label">Tiết Kiệm Ròng</span>
                <strong className={`stat-tile-value ${report.net_savings >= 0 ? 'text-emerald' : 'text-rose'}`}>
                  {formatCurrency(report.net_savings)}
                </strong>
              </div>
            </div>
            <div className="stat-tile rate">
              <span className="stat-tile-icon" aria-hidden="true">%</span>
              <div className="stat-tile-content">
                <span className="stat-tile-label">Tỷ Lệ Tiết Kiệm</span>
                <strong className="stat-tile-value text-indigo">{report.savings_rate}%</strong>
              </div>
            </div>
          </div>

          {/* Deep Insights */}
          <div className="ai-sections-grid">
            <article className="ai-section-box overview">
              <div className="section-box-header">
                <span className="box-icon">📋</span>
                <h3>1. Tóm Tắt Tổng Quan</h3>
              </div>
              <p className="ai-section-text">{report.overview}</p>
            </article>

            <article className="ai-section-box trend">
              <div className="section-box-header">
                <span className="box-icon">📈</span>
                <h3>2. Phân Tích Xu Hướng & Cơ Cấu</h3>
              </div>
              <p className="ai-section-text">{report.trend_analysis}</p>
            </article>
          </div>

          {/* Recommendations / Adjustments */}
          {report.adjustments?.length > 0 && (
            <div className="ai-adjustments-card">
              <div className="adjustments-header">
                <span className="box-icon">🎯</span>
                <h3>3. Lời Khuyên & Kế Hoạch Điều Chỉnh Tài Chính</h3>
              </div>
              <ul className="adjustments-list">
                {report.adjustments.map((item, idx) => (
                  <li key={idx} className="adjustment-item">
                    <span className="adj-bullet">{idx + 1}</span>
                    <p>{item}</p>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Conclusion & Copy Actions */}
          <div className="ai-report-view-footer">
            <div className="ai-conclusion-quote">
              <span className="quote-icon">💡</span>
              <p>{report.conclusion}</p>
            </div>

            <div className="ai-report-actions">
              <button
                type="button"
                className="btn-copy-report"
                onClick={handleCopyMarkdown}
              >
                {copied ? '✅ Đã sao chép Markdown' : '📋 Sao Chép Báo Cáo'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AiReportTab;
