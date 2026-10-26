import React, { useState, useMemo, useRef } from 'react';
import { getBudgetRecommendations, applyBudgetRecommendations } from '../api/aiApi';
import CategoryIcon from './CategoryIcon';
import CustomSelect from './CustomSelect';

const formatCurrency = (val) => {
  const num = Number(val) || 0;
  return new Intl.NumberFormat('vi-VN').format(num) + ' đ';
};

const STRATEGY_OPTIONS = [
  {
    id: 'smart',
    icon: '🎯',
    title: 'Cân đối thông minh (50/30/20)',
    desc: 'Phân bổ hạn mức tối ưu dựa trên mức chi trung bình quá khứ và mục tiêu tiết kiệm 20%.',
    factor: 1.0,
  },
  {
    id: 'strict',
    icon: '⚡',
    title: 'Thắt chặt tiết kiệm',
    desc: 'Cắt giảm 15% hạn mức cho các danh mục không thiết yếu nhằm gia tăng tối đa tiền tiết kiệm.',
    factor: 0.85,
  },
  {
    id: 'flexible',
    icon: '🌊',
    title: 'Linh hoạt theo thực tế',
    desc: 'Giữ hạn mức sát với thực tế chi tiêu quá khứ với biên độ an toàn +10%.',
    factor: 1.1,
  },
];

const LOOKBACK_OPTIONS = [
  { value: 1, label: '1 tháng gần nhất (Xu hướng mới)' },
  { value: 3, label: '3 tháng gần nhất (Khuyên dùng)' },
  { value: 6, label: '6 tháng gần nhất (Dài hạn ổn định)' },
];

const MONTH_OPTIONS = Array.from({ length: 12 }, (_, i) => ({
  value: i + 1,
  label: `Tháng ${String(i + 1).padStart(2, '0')}`,
}));

const customSmoothScroll = (element, duration = 350, offset = 32) => {
  if (!element) {
    window.scrollTo({ top: 0, behavior: 'smooth' });
    return;
  }
  const targetPosition = element.getBoundingClientRect().top + window.scrollY - offset;
  const startPosition = window.scrollY;
  const distance = targetPosition - startPosition;
  let startTime = null;

  const easeOutQuart = (t) => 1 - Math.pow(1 - t, 4);

  const animation = (currentTime) => {
    if (startTime === null) startTime = currentTime;
    const timeElapsed = currentTime - startTime;
    const progress = Math.min(timeElapsed / duration, 1);
    window.scrollTo(0, startPosition + distance * easeOutQuart(progress));
    if (timeElapsed < duration) {
      requestAnimationFrame(animation);
    }
  };
  requestAnimationFrame(animation);
};

const AiBudgetTab = ({ currentMonth, currentYear, onApplied }) => {
  const [targetMonth, setTargetMonth] = useState(currentMonth || new Date().getMonth() + 1);
  const [targetYear, setTargetYear] = useState(currentYear || new Date().getFullYear());
  const [strategy, setStrategy] = useState('smart');
  const [lookbackMonths, setLookbackMonths] = useState(3);

  const yearOptions = useMemo(() => {
    const baseYear = targetYear || new Date().getFullYear();
    const years = [baseYear - 2, baseYear - 1, baseYear, baseYear + 1, baseYear + 2];
    return Array.from(new Set(years)).map((y) => ({
      value: y,
      label: `Năm ${y}`,
    }));
  }, [targetYear]);

  const [data, setData] = useState(null);
  const [editedAmounts, setEditedAmounts] = useState({});
  const [loading, setLoading] = useState(false);
  const [applying, setApplying] = useState(false);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [hasGenerated, setHasGenerated] = useState(false);
  const [showConfig, setShowConfig] = useState(true);
  const amountInputRefs = useRef(new Map());
  const configRef = useRef(null);
  const resultsRef = useRef(null);

  const handleToggleConfig = () => {
    setShowConfig(true);
    requestAnimationFrame(() => {
      setTimeout(() => {
        customSmoothScroll(configRef.current, 350, 32);
      }, 50);
    });
  };

  const selectedMonthStr = `${targetYear}-${String(targetMonth).padStart(2, '0')}`;

  const handleGenerate = async () => {
    setLoading(true);
    setError('');
    setSuccessMsg('');
    try {
      const res = await getBudgetRecommendations(selectedMonthStr, lookbackMonths);
      setData(res);

      const stratObj = STRATEGY_OPTIONS.find((s) => s.id === strategy) || STRATEGY_OPTIONS[0];
      const initialMap = {};
      (res.recommendations || []).forEach((item) => {
        const adjusted = Math.round((item.recommended_amount * stratObj.factor) / 10000) * 10000;
        initialMap[item.category_id] = adjusted || 500000;
      });
      setEditedAmounts(initialMap);
      setHasGenerated(true);
      setShowConfig(false);
      requestAnimationFrame(() => {
        setTimeout(() => {
          customSmoothScroll(resultsRef.current, 350, 32);
        }, 50);
      });
    } catch (err) {
      setError(err.response?.data?.detail || 'Không thể tải gợi ý ngân sách AI lúc này.');
    } finally {
      setLoading(false);
    }
  };

  const handleAmountChange = (catId, value) => {
    const cleanNum = value.replace(/\D/g, '');
    setEditedAmounts((prev) => ({
      ...prev,
      [catId]: cleanNum === '' ? '' : Number(cleanNum),
    }));
  };

  const focusAmountInput = (catId) => {
    const input = amountInputRefs.current.get(catId);
    if (!input) return;
    input.focus();
    input.select();
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

      setSuccessMsg(res.message || 'Đã áp dụng thành công ngân sách gợi ý!');
      if (onApplied) {
        onApplied(data.target_month, data.target_year);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Có lỗi xảy ra khi áp dụng ngân sách.');
    } finally {
      setApplying(false);
    }
  };

  return (
    <div className="ai-budget-tab-container fade-in">
      {/* Options Configuration Card */}
      {showConfig && (
        <div className="ai-config-card" ref={configRef}>
          <div className="ai-config-header">
            <div className="ai-config-badge">✨ FinAI Smart Budgeting</div>
            <h2>Tùy Chọn Sinh Gợi Ý Ngân Sách AI</h2>
            <p>Chọn tháng áp dụng, khoảng thời gian đối chiếu và chiến lược tài chính phù hợp.</p>
          </div>

          <div className="ai-config-body">
            {/* 1. Chọn tháng áp dụng */}
            <div className="ai-config-section">
              <label className="ai-config-label">1. Chọn tháng áp dụng ngân sách:</label>
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

            {/* 2. Chọn khoảng thời gian lịch sử đối chiếu */}
            <div className="ai-config-section">
              <label className="ai-config-label">2. Dữ liệu lịch sử đối chiếu:</label>
              <div className="ai-lookback-select-wrap">
                <CustomSelect
                  value={lookbackMonths}
                  onChange={(e) => setLookbackMonths(Number(e.target.value))}
                  options={LOOKBACK_OPTIONS}
                />
              </div>
            </div>

            {/* 3. Chọn chiến lược */}
            <div className="ai-config-section">
              <label className="ai-config-label">3. Chọn chiến lược phân bổ ngân sách:</label>
              <div className="ai-focus-options-grid">
                {STRATEGY_OPTIONS.map((opt) => (
                  <button
                    key={opt.id}
                    type="button"
                    className={`ai-focus-card ${strategy === opt.id ? 'active' : ''}`}
                    onClick={() => setStrategy(opt.id)}
                  >
                    <span className="focus-card-icon">{opt.icon}</span>
                    <div className="focus-card-info">
                      <strong>{opt.title}</strong>
                      <p>{opt.desc}</p>
                    </div>
                    <span className="focus-card-radio">
                      {strategy === opt.id && <i className="radio-checked" />}
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
                    FinAI đang phân tích lịch sử chi tiêu...
                  </>
                ) : (
                  <>
                    <span>🚀</span>
                    Xác Nhận & Sinh Gợi Ý Ngân Sách (Tháng {targetMonth}/{targetYear})
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Loading Skeleton */}
      {loading && !showConfig && (
        <div className="ai-tab-loading-state">
          <div className="ai-spinner" />
          <h3>FinAI đang phân tích lịch sử chi tiêu và tính toán hạn mức...</h3>
          <p>Dựa trên xu hướng {lookbackMonths} tháng gần nhất và chiến lược đã chọn, hệ thống đang xây dựng kế hoạch ngân sách tối ưu cho từng danh mục.</p>
        </div>
      )}

      {/* Display Generated Recommendations */}
      {hasGenerated && data && !loading && (
        <div className="ai-budget-results-card fade-in" ref={resultsRef}>
          <div className="ai-budget-results-header">
            <div className="ai-budget-results-title">
              <span className="ai-badge-sub">✨ Hạn Mức Đề Xuất Từ AI</span>
              <h2>Gợi Ý Ngân Sách Tháng {data.target_month}/{data.target_year}</h2>
              <p>Chiến lược: {STRATEGY_OPTIONS.find((s) => s.id === strategy)?.title || 'Cân đối thông minh'} • Đối chiếu: {lookbackMonths} tháng lịch sử</p>
            </div>

            <div className="ai-budget-results-actions">
              <button
                type="button"
                className="btn-reconfigure-ai"
                onClick={handleToggleConfig}
              >
                ⚙️ Đổi Tùy Chọn
              </button>
            </div>
          </div>

          {/* Metric Bar */}
          <div className="ai-budget-total-bar">
            <div className="total-bar-info">
              <span>Tổng ngân sách dự kiến:</span>
              <strong>{formatCurrency(totalCalculated)}</strong>
            </div>
            <div className="total-bar-hint">
              💡 Bạn có thể chỉnh sửa số tiền trực tiếp ở từng danh mục trước khi bấm áp dụng.
            </div>
          </div>

          {successMsg && <div className="message message-success">{successMsg}</div>}
          {error && <div className="message message-error">{error}</div>}

          {/* Recommendations Cards Grid */}
          <div className="ai-budget-items-grid">
            {data.recommendations?.map((item) => (
              <div key={item.category_id} className="ai-budget-card">
                <div className="ai-budget-card-header">
                  <div className="ai-card-category-info">
                    <CategoryIcon
                      icon={item.category_icon || 'other'}
                      color={item.category_color || '#D69A23'}
                      size="sm"
                    />
                    <strong>{item.category_name}</strong>
                  </div>
                  <div className="ai-card-hist-spend">
                    <span>Đã chi TB: </span>
                    <strong className="font-mono">{formatCurrency(item.avg_spent)}</strong>
                  </div>
                </div>

                <div className="ai-budget-card-input-row">
                  <label htmlFor={`budget-input-${item.category_id}`}>Hạn mức đề xuất:</label>
                  <input
                    ref={(node) => {
                      if (node) amountInputRefs.current.set(item.category_id, node);
                      else amountInputRefs.current.delete(item.category_id);
                    }}
                    id={`budget-input-${item.category_id}`}
                    type="text"
                    inputMode="numeric"
                    autoComplete="off"
                    className="ai-budget-input font-mono"
                    value={
                      editedAmounts[item.category_id] === ''
                        ? ''
                        : Number(editedAmounts[item.category_id] ?? item.recommended_amount).toLocaleString('vi-VN')
                    }
                    onChange={(e) => handleAmountChange(item.category_id, e.target.value)}
                    onFocus={(e) => e.target.select()}
                    aria-label={`Hạn mức đề xuất cho ${item.category_name}`}
                  />
                  <button
                    type="button"
                    className="btn-edit-ai-budget-amount"
                    onClick={() => focusAmountInput(item.category_id)}
                    aria-label={`Sửa hạn mức cho ${item.category_name}`}
                    title="Sửa hạn mức"
                  >
                    ✎
                  </button>
                </div>

                <div className="ai-budget-card-reason">
                  <span className="reason-icon">💡</span>
                  <p>{item.reason}</p>
                </div>
              </div>
            ))}
          </div>

          {/* Bottom Apply Action */}
          <div className="ai-budget-tab-footer">
            <button
              type="button"
              className="btn-reconfigure-bottom"
              onClick={handleToggleConfig}
            >
              ⚙️ Đổi Tùy Chọn Khác
            </button>
            <div className="footer-summary">
              <span>Tổng ngân sách áp dụng:</span>
              <strong className="font-mono text-amber">{formatCurrency(totalCalculated)}</strong>
            </div>
            <button
              type="button"
              className="btn-primary btn-apply-ai-budget"
              onClick={handleApply}
              disabled={applying || totalCalculated === 0}
            >
              {applying ? 'Đang lưu ngân sách...' : '✅ Xác Nhận Áp Dụng Ngân Sách Này'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default AiBudgetTab;
