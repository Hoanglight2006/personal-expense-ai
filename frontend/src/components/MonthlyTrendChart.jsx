import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { getMonthlyTrend } from '../api/aiApi';

const formatCurrency = (val) => {
  const num = Math.round(Number(val) || 0);
  return new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 0 }).format(num) + ' đ';
};

const MonthlyTrendChart = () => {
  const [monthCount, setMonthCount] = useState(3); // Default to 3 months
  const [trendData, setTrendData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [hoveredBarIndex, setHoveredBarIndex] = useState(null);
  const [showTableDetails, setShowTableDetails] = useState(false);
  const [activeMetricInfo, setActiveMetricInfo] = useState(null);
  const metricsRef = useRef(null);

  useEffect(() => {
    if (!activeMetricInfo) return undefined;

    const closeOnOutsidePress = (event) => {
      if (!metricsRef.current?.contains(event.target)) {
        setActiveMetricInfo(null);
      }
    };
    const closeOnEscape = (event) => {
      if (event.key === 'Escape') setActiveMetricInfo(null);
    };

    document.addEventListener('pointerdown', closeOnOutsidePress);
    document.addEventListener('keydown', closeOnEscape);
    return () => {
      document.removeEventListener('pointerdown', closeOnOutsidePress);
      document.removeEventListener('keydown', closeOnEscape);
    };
  }, [activeMetricInfo]);

  const fetchTrends = useCallback(async (months = monthCount, signal) => {
    setLoading(true);
    setError('');
    try {
      const data = await getMonthlyTrend(months, signal);
      setTrendData(data);
    } catch (err) {
      if (err.name !== 'CanceledError' && err.message !== 'canceled') {
        setError(err.response?.data?.detail || 'Không thể tải dữ liệu xu hướng.');
      }
    } finally {
      setLoading(false);
    }
  }, [monthCount]);

  useEffect(() => {
    const controller = new AbortController();
    fetchTrends(monthCount, controller.signal);
    return () => controller.abort();
  }, [monthCount, fetchTrends]);

  // Max value for Cashflow Bar Chart
  const maxVal = useMemo(() => {
    if (!trendData?.items?.length) return 1000000;
    const peak = Math.max(
      ...trendData.items.map((item) =>
        Math.max(Number(item.total_income) || 0, Number(item.total_expense) || 0)
      )
    );
    return peak > 0 ? peak * 1.15 : 1000000;
  }, [trendData]);

  const prediction = trendData?.prediction_data;
  const anomalies = trendData?.anomaly_items || [];
  const items = trendData?.items || [];

  return (
    <div className="monthly-trend-container fade-in">
      {/* 1. Control Toolbar (Chu kỳ phân tích) */}
      <div className="stats-filter-toolbar trend-filter-toolbar">
        <div className="stats-filter-toolbar-left">
          <span className="filter-toolbar-label">Chu kỳ phân tích:</span>
          <div className="stats-date-pill-tabs" role="group" aria-label="Chọn chu kỳ xu hướng">
            <button
              type="button"
              className={monthCount === 3 ? 'active' : ''}
              onClick={() => setMonthCount(3)}
            >
              3 tháng
            </button>
            <button
              type="button"
              className={monthCount === 6 ? 'active' : ''}
              onClick={() => setMonthCount(6)}
            >
              6 tháng
            </button>
            <button
              type="button"
              className={monthCount === 12 ? 'active' : ''}
              onClick={() => setMonthCount(12)}
            >
              12 tháng
            </button>
          </div>
        </div>

        <span className="filter-toolbar-divider" />

        <div className="stats-filter-toolbar-right">
          <button
            type="button"
            className="stats-return-current"
            onClick={() => fetchTrends(monthCount)}
            disabled={loading}
            title="Làm mới dữ liệu xu hướng"
          >
            {loading ? '⏳ Đang tải...' : '🔄 Làm mới'}
          </button>
        </div>
      </div>

      {loading && !trendData && (
        <div className="trend-loading loading-state">
          <div className="spinner" aria-hidden="true" />
          <p>Đang tổng hợp xu hướng tài chính {monthCount} tháng...</p>
        </div>
      )}

      {error && !trendData && (
        <div className="trend-error error-message" role="alert">
          <span>{error}</span>
          <button type="button" className="btn-secondary" onClick={() => fetchTrends(monthCount)}>
            Thử lại
          </button>
        </div>
      )}

      {trendData && (
        <>
          {/* 2. Unified Hero Card: Tóm tắt thông minh & Dự báo gọn gàng */}
          <section className="trend-minimal-hero-card">
            <div className="minimal-hero-header">
              <div className="minimal-hero-badge">
                <span className="sparkle-icon">✨</span>
                <span>Trợ Lý Tài Chính Thông Minh</span>
              </div>
              {prediction && (
                <span className={`forecast-status-tag tag-${prediction.risk_level}`}>
                  {prediction.risk_level === 'danger'
                    ? '🚨 Nguy cơ vượt ngân sách'
                    : prediction.risk_level === 'warning'
                    ? '⚠️ Cận hạn mức'
                    : '✅ Chi tiêu an toàn'}
                </span>
              )}
            </div>

            <p className="minimal-hero-summary">{trendData.smart_summary}</p>

            {/* Cảnh báo danh mục đột biến (nếu có) */}
            {anomalies.length > 0 && (
              <div className="minimal-anomaly-alert">
                <span className="alert-icon">⚠️</span>
                <span>
                  Lưu ý: Danh mục <strong>{anomalies[0].category_name}</strong> tăng đột biến{' '}
                  <strong>+{anomalies[0].diff_percent}%</strong> so với TB 3 tháng (+
                  {formatCurrency(anomalies[0].diff_amount)}).
                </span>
              </div>
            )}

            {/* 4 chỉ số cốt lõi căn chỉnh thẳng hàng tuyệt đối */}
            <div className="minimal-hero-metrics" ref={metricsRef}>
              <div className="hero-metric-item">
                <div className="metric-title-row">
                  <span className="metric-title">Thu nhập TB</span>
                  <button
                    type="button"
                    className="metric-info-badge"
                    aria-label="Xem giải thích Thu nhập trung bình"
                    aria-expanded={activeMetricInfo === 'income'}
                    aria-describedby={activeMetricInfo === 'income' ? 'metric-info-income' : undefined}
                    onClick={() => setActiveMetricInfo((current) => current === 'income' ? null : 'income')}
                  >i</button>
                  {activeMetricInfo === 'income' && (
                    <span className="metric-info-tooltip" id="metric-info-income" role="tooltip">
                      Tổng thu nhập bình quân mỗi tháng trong chu kỳ {monthCount} tháng gần nhất.
                    </span>
                  )}
                </div>
                <strong className="metric-number text-emerald">
                  {formatCurrency(trendData.average_monthly_income)}
                </strong>
                <span className="metric-subtitle">BQ {monthCount} tháng qua</span>
              </div>

              <div className="hero-metric-item">
                <div className="metric-title-row">
                  <span className="metric-title">Chi tiêu TB</span>
                  <button
                    type="button"
                    className="metric-info-badge"
                    aria-label="Xem giải thích Chi tiêu trung bình"
                    aria-expanded={activeMetricInfo === 'expense'}
                    aria-describedby={activeMetricInfo === 'expense' ? 'metric-info-expense' : undefined}
                    onClick={() => setActiveMetricInfo((current) => current === 'expense' ? null : 'expense')}
                  >i</button>
                  {activeMetricInfo === 'expense' && (
                    <span className="metric-info-tooltip" id="metric-info-expense" role="tooltip">
                      Tổng chi phí bình quân mỗi tháng trong chu kỳ {monthCount} tháng gần nhất.
                    </span>
                  )}
                </div>
                <strong className="metric-number text-rose">
                  {formatCurrency(trendData.average_monthly_expense)}
                </strong>
                <span className="metric-subtitle">BQ {monthCount} tháng qua</span>
              </div>

              <div className="hero-metric-item">
                <div className="metric-title-row">
                  <span className="metric-title">Dự báo chi tháng</span>
                  <button
                    type="button"
                    className="metric-info-badge"
                    aria-label="Xem giải thích Dự báo chi tháng"
                    aria-expanded={activeMetricInfo === 'forecast'}
                    aria-describedby={activeMetricInfo === 'forecast' ? 'metric-info-forecast' : undefined}
                    onClick={() => setActiveMetricInfo((current) => current === 'forecast' ? null : 'forecast')}
                  >i</button>
                  {activeMetricInfo === 'forecast' && (
                    <span className="metric-info-tooltip" id="metric-info-forecast" role="tooltip">
                      Ước tính tổng số tiền bạn sẽ tiêu hết tháng này nếu giữ nguyên tốc độ tiêu tiền mỗi ngày.
                    </span>
                  )}
                </div>
                <strong className="metric-number">
                  {prediction ? formatCurrency(prediction.projected_end_month_spend) : '—'}
                </strong>
                <span className="metric-subtitle">
                  {prediction
                    ? `~${formatCurrency(prediction.daily_burn_rate)}/ngày`
                    : 'Theo tốc độ tiêu'}
                </span>
              </div>

              <div className="hero-metric-item">
                <div className="metric-title-row">
                  <span className="metric-title">Tỷ lệ tiết kiệm TB</span>
                  <button
                    type="button"
                    className="metric-info-badge"
                    aria-label="Xem giải thích Tỷ lệ tiết kiệm trung bình"
                    aria-expanded={activeMetricInfo === 'savings'}
                    aria-describedby={activeMetricInfo === 'savings' ? 'metric-info-savings' : undefined}
                    onClick={() => setActiveMetricInfo((current) => current === 'savings' ? null : 'savings')}
                  >i</button>
                  {activeMetricInfo === 'savings' && (
                    <span className="metric-info-tooltip" id="metric-info-savings" role="tooltip">
                      Tỷ lệ phần trăm tiền tiết kiệm còn giữ lại được so với tổng thu nhập.
                    </span>
                  )}
                </div>
                <strong className="metric-number text-primary">
                  {trendData.average_savings_rate || 0}%
                </strong>
                <span className="metric-subtitle">Thặng dư / Thu nhập</span>
              </div>
            </div>
          </section>

          {/* 3. Biểu Đồ Dòng Tiền Rõ Ràng & Trực Quan (Cashflow Chart) */}
          <div className="trend-chart-card fade-in">
            <div className="trend-chart-header">
              <div className="chart-title">
                <h3>Biểu Đồ Biến Động Dòng Tiền {monthCount} Tháng</h3>
                <p>Khoảng cách giữa cột Thu nhập và Chi tiêu thể hiện thặng dư tích lũy</p>
              </div>
              <div className="chart-legend">
                <span className="legend-item income">
                  <span className="legend-dot" /> Thu nhập
                </span>
                <span className="legend-item expense">
                  <span className="legend-dot" /> Chi tiêu
                </span>
              </div>
            </div>

            {/* Bar Chart Grid */}
            <div className="trend-bars-wrapper">
              <div
                className="trend-bars-grid"
                style={{
                  minWidth: items.length > 6 ? `${items.length * 64}px` : '100%',
                }}
              >
                {items.map((item, idx) => {
                  const incomeNum = Number(item.total_income) || 0;
                  const expenseNum = Number(item.total_expense) || 0;
                  const netNum = Number(item.net_savings) || 0;
                  const incomeHeight = Math.min(100, (incomeNum / maxVal) * 100);
                  const expenseHeight = Math.min(100, (expenseNum / maxVal) * 100);
                  const isHovered = hoveredBarIndex === idx;

                  return (
                    <div
                      key={item.month}
                      className={`trend-bar-column ${isHovered ? 'is-active' : ''}`}
                      onMouseEnter={() => setHoveredBarIndex(idx)}
                      onMouseLeave={() => setHoveredBarIndex(null)}
                      onFocus={() => setHoveredBarIndex(idx)}
                      onBlur={() => setHoveredBarIndex(null)}
                      tabIndex={0}
                      role="group"
                      aria-label={`${item.label}: Thu ${formatCurrency(incomeNum)}, Chi ${formatCurrency(expenseNum)}`}
                    >
                      {/* Tooltip on hover */}
                      {isHovered && (
                        <div className="trend-tooltip">
                          <div className="tooltip-title">{item.label}</div>
                          <div className="tooltip-row income">
                            <span>Thu nhập:</span>
                            <strong>{formatCurrency(incomeNum)}</strong>
                          </div>
                          <div className="tooltip-row expense">
                            <span>Chi tiêu:</span>
                            <strong>{formatCurrency(expenseNum)}</strong>
                          </div>
                          <div className="tooltip-row net">
                            <span>Thặng dư:</span>
                            <strong>
                              {formatCurrency(netNum)} ({item.savings_rate}%)
                            </strong>
                          </div>
                          {item.top_category && (
                            <div className="tooltip-top-cat">
                              Chi nhiều nhất: <strong>{item.top_category}</strong> (
                              {formatCurrency(item.top_category_amount)})
                            </div>
                          )}
                        </div>
                      )}

                      {/* Dual Bars */}
                      <div className="bars-container">
                        <div className="bar-track">
                          <div
                            className="bar-fill income-bar"
                            style={{
                              height: `${Math.max(incomeHeight, incomeNum > 0 ? 4 : 0)}%`,
                            }}
                            title={`Thu nhập: ${formatCurrency(incomeNum)}`}
                          />
                        </div>
                        <div className="bar-track">
                          <div
                            className="bar-fill expense-bar"
                            style={{
                              height: `${Math.max(expenseHeight, expenseNum > 0 ? 4 : 0)}%`,
                            }}
                            title={`Chi tiêu: ${formatCurrency(expenseNum)}`}
                          />
                        </div>
                      </div>

                      {/* Footer tags */}
                      <div className="column-footer">
                        <span className="month-tag">{item.label.replace('Thg ', 'T')}</span>
                        <span className={`rate-badge ${netNum >= 0 ? 'positive' : 'negative'}`}>
                          {netNum >= 0 ? `+${item.savings_rate}%` : `-${Math.abs(item.savings_rate)}%`}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* 4. Tùy chọn xem Bảng Chi Tiết (Gọn gàng, chỉ mở khi cần) */}
          <div className="trend-details-collapsible">
            <button
              type="button"
              className="trend-toggle-details-btn"
              onClick={() => setShowTableDetails(!showTableDetails)}
            >
              <span>{showTableDetails ? '▲ Thu gọn bảng chi tiết' : '▼ Xem bảng số liệu chi tiết từng tháng'}</span>
            </button>

            {showTableDetails && (
              <div className="trend-table-card fade-in">
                <div className="trend-table-responsive">
                  <table className="trend-table">
                    <thead>
                      <tr>
                        <th>Tháng</th>
                        <th className="text-right">Thu Nhập</th>
                        <th className="text-right">Chi Tiêu</th>
                        <th className="text-right">Thặng Dư / Tiết Kiệm</th>
                        <th className="text-center">Tỷ Lệ Tiết Kiệm</th>
                        <th>Danh Mục Chi Lớn Nhất</th>
                      </tr>
                    </thead>
                    <tbody>
                      {items.map((item) => {
                        const net = Number(item.net_savings) || 0;
                        return (
                          <tr key={item.month}>
                            <td>
                              <strong>{item.label}</strong>
                            </td>
                            <td className="text-right text-emerald font-mono">
                              {formatCurrency(item.total_income)}
                            </td>
                            <td className="text-right text-rose font-mono">
                              {formatCurrency(item.total_expense)}
                            </td>
                            <td className={`text-right font-mono ${net >= 0 ? 'text-emerald' : 'text-rose'}`}>
                              {net >= 0 ? `+${formatCurrency(net)}` : formatCurrency(net)}
                            </td>
                            <td className="text-center">
                              <span className={`pill-badge ${net >= 0 ? 'badge-success' : 'badge-danger'}`}>
                                {item.savings_rate}%
                              </span>
                            </td>
                            <td>
                              {item.top_category ? (
                                <span className="top-category-tag">
                                  {item.top_category} ({formatCurrency(item.top_category_amount)})
                                </span>
                              ) : (
                                <span className="text-muted">—</span>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};

export default MonthlyTrendChart;
