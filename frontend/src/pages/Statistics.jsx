import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { getCategoryStatistics } from '../api/categoryApi';
import CategoryInsights from '../components/CategoryInsights';
import CustomDatePicker from '../components/CustomDatePicker';

const pad = (value) => String(value).padStart(2, '0');
const localDateValue = (date) => `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
const formatVnDate = (isoStr) => {
  if (!isoStr) return '';
  const [y, m, d] = isoStr.split('-');
  return `${d}/${m}/${y}`;
};
const currentMonthValue = () => {
  const now = new Date();
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}`;
};

const monthRange = (month) => {
  if (!/^\d{4}-\d{2}$/.test(month)) return { startDate: '', endDate: '' };
  const [year, monthNumber] = month.split('-').map(Number);
  return {
    startDate: `${year}-${pad(monthNumber)}-01`,
    endDate: localDateValue(new Date(year, monthNumber, 0)),
  };
};

const recentDaysRange = (days) => {
  const end = new Date();
  const start = new Date(end);
  start.setDate(start.getDate() - days + 1);
  return { startDate: localDateValue(start), endDate: localDateValue(end) };
};

const apiMessage = (error) => {
  const detail = error?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map((item) => item.msg).filter(Boolean).join(' ');
  if (!error?.response) {
    return navigator.onLine
      ? 'Không thể kết nối đến máy chủ. Hãy kiểm tra backend hoặc cấu hình mạng.'
      : 'Thiết bị đang mất kết nối mạng.';
  }
  if (error.response.status >= 500) {
    return 'Máy chủ gặp lỗi khi xử lý dữ liệu. Vui lòng thử lại.';
  }
  return `Yêu cầu thất bại (HTTP ${error.response.status}).`;
};

const Statistics = () => {
  const [period, setPeriod] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [filterMode, setFilterMode] = useState('month'); // 'month' or 'period'
  const [dateMode, setDateMode] = useState('month');
  const [month, setMonth] = useState(currentMonthValue);
  const initialRange = useMemo(() => monthRange(currentMonthValue()), []);
  const [customStart, setCustomStart] = useState(initialRange.startDate);
  const [customEnd, setCustomEnd] = useState(initialRange.endDate);

  // Mutual exclusivity: only one popup open at a time
  // Values: null, 'select', 'monthPicker', 'startDate', 'endDate'
  const [activePopup, setActivePopup] = useState(null);

  const selectedRange = useMemo(
    () => filterMode === 'month' ? monthRange(month) : { startDate: customStart, endDate: customEnd },
    [filterMode, month, customStart, customEnd],
  );

  const loadStatistics = useCallback(async (signal) => {
    if (!selectedRange.startDate || !selectedRange.endDate) {
      setPeriod(null);
      setError('Vui lòng chọn đầy đủ ngày bắt đầu và ngày kết thúc.');
      setLoading(false);
      return;
    }
    if (selectedRange.startDate > selectedRange.endDate) {
      setPeriod(null);
      setError('Ngày bắt đầu không được sau ngày kết thúc.');
      setLoading(false);
      return;
    }

    setLoading(true);
    setError('');
    try {
      const stats = await getCategoryStatistics(
        { start_date: selectedRange.startDate, end_date: selectedRange.endDate },
        signal,
      );
      setPeriod(stats);
    } catch (err) {
      if (err.name !== 'CanceledError' && err.message !== 'canceled') {
        setPeriod(null);
        setError(apiMessage(err));
      }
    } finally {
      setLoading(false);
    }
  }, [selectedRange]);

  useEffect(() => {
    const abortController = new AbortController();
    loadStatistics(abortController.signal);
    return () => abortController.abort();
  }, [loadStatistics]);

  return (
    <div className="statistics-page fade-in">
      <section className="statistics-hero">
        <div className="statistics-title">
          <span className="eyebrow">Báo cáo & Xu hướng</span>
          <h1>Thống kê & Báo cáo</h1>
          <p>Phân tích trực quan dòng tiền, cơ cấu thu chi và biến động tài chính.</p>
        </div>

        <div className="statistics-toolbar" aria-label="Bộ lọc thống kê">
          {/* Mode Tabs — chọn cái này thì tắt hoàn toàn cái kia */}
          <div className="stats-mode-tabs" role="tablist">
            <button
              type="button"
              role="tab"
              aria-selected={filterMode === 'month'}
              className={`stats-mode-tab ${filterMode === 'month' ? 'active' : ''}`}
              onClick={() => {
                setFilterMode('month');
                setDateMode('month');
                setActivePopup(null);
              }}
            >
              📅 Theo tháng
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={filterMode === 'period'}
              className={`stats-mode-tab ${filterMode === 'period' ? 'active' : ''}`}
              onClick={() => {
                setFilterMode('period');
                if (dateMode === 'month') {
                  setDateMode('recent30');
                  const r = recentDaysRange(30);
                  setCustomStart(r.startDate);
                  setCustomEnd(r.endDate);
                }
                setActivePopup(null);
              }}
            >
              ⏱️ Khoảng ngày
            </button>
          </div>

          {/* Mode: Theo tháng — chỉ hiện DatePicker, KHÔNG hiện Select */}
          {filterMode === 'month' && (
            <div className="stats-month-controls">
              <div className="stats-month-nav-group">
                <button
                  type="button"
                  className="stats-nav-arrow"
                  onClick={() => {
                    const [y, m] = month.split('-').map(Number);
                    const prev = new Date(y, m - 2, 1);
                    setMonth(`${prev.getFullYear()}-${pad(prev.getMonth() + 1)}`);
                    setActivePopup(null);
                  }}
                  title="Tháng trước"
                  aria-label="Tháng trước"
                >
                  ‹
                </button>
                <div className="stats-month-picker-wrap">
                  <CustomDatePicker
                    monthMode
                    value={month}
                    onChange={(e) => setMonth(e.target.value)}
                    open={activePopup === 'monthPicker'}
                    onCalendarOpen={() => setActivePopup('monthPicker')}
                    onCalendarClose={() => setActivePopup(null)}
                  />
                </div>
                <button
                  type="button"
                  className="stats-nav-arrow"
                  onClick={() => {
                    const [y, m] = month.split('-').map(Number);
                    const next = new Date(y, m, 1);
                    setMonth(`${next.getFullYear()}-${pad(next.getMonth() + 1)}`);
                    setActivePopup(null);
                  }}
                  title="Tháng sau"
                  aria-label="Tháng sau"
                >
                  ›
                </button>
              </div>
              {month !== currentMonthValue() && (
                <button
                  type="button"
                  className="btn-return-today stats-return-current"
                  onClick={() => {
                    setMonth(currentMonthValue());
                    setActivePopup(null);
                  }}
                  title="Quay về tháng hiện tại"
                >
                  Tháng này
                </button>
              )}
            </div>
          )}

          {/* Mode: Khoảng ngày — preset dạng nút, chỉ hiện ô ngày khi chọn tùy chỉnh */}
          {filterMode === 'period' && (
            <div className="stats-period-controls">
              <div className="stats-quick-periods" role="group" aria-label="Chọn nhanh khoảng ngày">
                <button
                  type="button"
                  className={dateMode === 'recent7' ? 'active' : ''}
                  onClick={() => {
                    const range = recentDaysRange(7);
                    setDateMode('recent7');
                    setCustomStart(range.startDate);
                    setCustomEnd(range.endDate);
                    setActivePopup(null);
                  }}
                >
                  7 ngày
                </button>
                <button
                  type="button"
                  className={dateMode === 'recent30' ? 'active' : ''}
                  onClick={() => {
                    const range = recentDaysRange(30);
                    setDateMode('recent30');
                    setCustomStart(range.startDate);
                    setCustomEnd(range.endDate);
                    setActivePopup(null);
                  }}
                >
                  30 ngày
                </button>
                <button
                  type="button"
                  className={dateMode === 'custom' ? 'active' : ''}
                  onClick={() => {
                    setDateMode('custom');
                    setActivePopup(null);
                  }}
                >
                  Tùy chỉnh
                </button>
              </div>

              {dateMode !== 'custom' && (
                <div className="stats-range-badge" aria-label="Khoảng thời gian áp dụng">
                  <span>Áp dụng</span>
                  <strong>{formatVnDate(customStart)} – {formatVnDate(customEnd)}</strong>
                </div>
              )}

              {dateMode === 'custom' && (
                <div className="stats-date-range">
                  <div className="stats-filter-field">
                    <span className="filter-label">Từ ngày</span>
                    <CustomDatePicker
                      value={customStart}
                      onChange={(e) => setCustomStart(e.target.value)}
                      maxDate={customEnd}
                      popperPlacement="bottom-start"
                      open={activePopup === 'startDate'}
                      onCalendarOpen={() => setActivePopup('startDate')}
                      onCalendarClose={() => setActivePopup(null)}
                    />
                  </div>
                  <div className="stats-filter-field">
                    <span className="filter-label">Đến ngày</span>
                    <CustomDatePicker
                      value={customEnd}
                      onChange={(e) => setCustomEnd(e.target.value)}
                      minDate={customStart}
                      popperPlacement="bottom-end"
                      open={activePopup === 'endDate'}
                      onCalendarOpen={() => setActivePopup('endDate')}
                      onCalendarClose={() => setActivePopup(null)}
                    />
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </section>

      {error && <div className="error-message" role="alert">{error}</div>}

      <div className="statistics-content">
        {loading && !period && (
          <div className="statistics-loading loading-state">
            <div className="spinner" aria-hidden="true" />
            <p>Đang tải dữ liệu...</p>
          </div>
        )}

        {period && (
          <div className={`statistics-result ${loading ? 'is-loading' : ''}`} aria-busy={loading}>
            <CategoryInsights categories={period.items} />
          </div>
        )}

        {!loading && !period && !error && (
          <div className="empty-state">
            <p>Chưa có dữ liệu thống kê cho khoảng thời gian này.</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default Statistics;
