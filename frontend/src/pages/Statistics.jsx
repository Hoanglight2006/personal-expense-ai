import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { getCategoryStatistics } from '../api/categoryApi';
import CategoryInsights from '../components/CategoryInsights';
import CustomDatePicker from '../components/CustomDatePicker';
import MonthlyTrendChart from '../components/MonthlyTrendChart';
import AiReportTab from '../components/AiReportTab';

const pad = (value) => String(value).padStart(2, '0');
const localDateValue = (date) => `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
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

  // Main Dashboard View Tabs: 'overview', 'expense', 'income', 'trend', 'aiReport'
  const [activeTab, setActiveTab] = useState('overview');

  // Date Filter Mode: 'month' (default) vs 'period' (custom/preset days)
  const [dateMode, setDateMode] = useState('month'); // 'month', 'recent7', 'recent30', 'custom'
  const [month, setMonth] = useState(currentMonthValue);
  const initialRange = useMemo(() => monthRange(currentMonthValue()), []);
  const [customStart, setCustomStart] = useState(initialRange.startDate);
  const [customEnd, setCustomEnd] = useState(initialRange.endDate);
  const [activePopup, setActivePopup] = useState(null);

  const selectedRange = useMemo(
    () => (dateMode === 'month' ? monthRange(month) : { startDate: customStart, endDate: customEnd }),
    [dateMode, month, customStart, customEnd],
  );

  const loadStatistics = useCallback(async (signal) => {
    if (activeTab === 'trend' || activeTab === 'aiReport') return;
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
  }, [selectedRange, activeTab]);

  useEffect(() => {
    const abortController = new AbortController();
    loadStatistics(abortController.signal);
    return () => abortController.abort();
  }, [loadStatistics]);

  return (
    <div className="statistics-page fade-in">
      {/* 1. Senior Executive Header */}
      <section className="stats-hero-section">
        <div className="stats-hero-title">
          <span className="stats-eyebrow">BÁO CÁO & PHÂN TÍCH TÀI CHÍNH</span>
          <h1>Thống kê & Báo cáo</h1>
          <p>Phân tích trực quan dòng tiền, cơ cấu thu chi và biến động tài chính theo thời gian thực.</p>
        </div>
      </section>

      {/* 2. Unified 5-View Dashboard Tabs */}
      <section className="stats-tabs-bar-section">
        <div className="stats-unified-tabs" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === 'overview'}
            className={`stats-tab-item ${activeTab === 'overview' ? 'active' : ''}`}
            onClick={() => setActiveTab('overview')}
          >
            <span className="stats-tab-icon">⚖️</span> Tổng quan
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === 'expense'}
            className={`stats-tab-item ${activeTab === 'expense' ? 'active' : ''}`}
            onClick={() => setActiveTab('expense')}
          >
            <span className="stats-tab-icon">📉</span> Thống kê Chi tiêu
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === 'income'}
            className={`stats-tab-item ${activeTab === 'income' ? 'active' : ''}`}
            onClick={() => setActiveTab('income')}
          >
            <span className="stats-tab-icon">📈</span> Thống kê Thu nhập
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === 'trend'}
            className={`stats-tab-item ${activeTab === 'trend' ? 'active' : ''}`}
            onClick={() => setActiveTab('trend')}
          >
            <span className="stats-tab-icon">📊</span> Xu hướng
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === 'aiReport'}
            className={`stats-tab-item tab-ai-highlight ${activeTab === 'aiReport' ? 'active' : ''}`}
            onClick={() => setActiveTab('aiReport')}
          >
            <span className="stats-tab-icon">✨</span> Báo Cáo AI
          </button>
        </div>
      </section>

      {/* 3. Date Filter Toolbar (Directly below tabs for overview, expense, income) */}
      {activeTab !== 'trend' && activeTab !== 'aiReport' && (
        <div className="stats-filter-toolbar fade-in">
          <div className="stats-filter-toolbar-left">
            <span className="filter-toolbar-label">Khoảng thời gian:</span>
            {/* Type Switcher: Theo tháng vs Khoảng ngày */}
            <div className="stats-date-pill-tabs" role="group" aria-label="Kiểu chọn thời gian">
              <button
                type="button"
                className={dateMode === 'month' ? 'active' : ''}
                onClick={() => {
                  setDateMode('month');
                  setActivePopup(null);
                }}
              >
                Theo tháng
              </button>
              <button
                type="button"
                className={dateMode !== 'month' ? 'active' : ''}
                onClick={() => {
                  if (dateMode === 'month') {
                    setDateMode('recent30');
                    const r = recentDaysRange(30);
                    setCustomStart(r.startDate);
                    setCustomEnd(r.endDate);
                  }
                  setActivePopup(null);
                }}
              >
                Khoảng ngày
              </button>
            </div>
          </div>

          <span className="filter-toolbar-divider" />

          <div className="stats-filter-toolbar-right">
            {/* Mode: Theo tháng */}
            {dateMode === 'month' ? (
              <>
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
                    className="stats-return-current"
                    onClick={() => {
                      setMonth(currentMonthValue());
                      setActivePopup(null);
                    }}
                    title="Quay về tháng hiện tại"
                  >
                    Tháng này
                  </button>
                )}
              </>
            ) : (
              /* Mode: Khoảng ngày */
              <div className="stats-period-nav-group">
                <div className="stats-quick-periods" role="group" aria-label="Chọn nhanh">
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

                {dateMode === 'custom' && (
                  <div className="stats-custom-dates-inputs">
                    <CustomDatePicker
                      value={customStart}
                      onChange={(e) => setCustomStart(e.target.value)}
                      maxDate={customEnd}
                      popperPlacement="bottom-start"
                      open={activePopup === 'startDate'}
                      onCalendarOpen={() => setActivePopup('startDate')}
                      onCalendarClose={() => setActivePopup(null)}
                    />
                    <span className="date-sep">→</span>
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
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* 3. Main Dashboard Content */}
      <main className="stats-main-content">
        {activeTab === 'aiReport' ? (
          <AiReportTab defaultMonth={month} />
        ) : activeTab === 'trend' ? (
          <MonthlyTrendChart />
        ) : (
          <>
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
                  <CategoryInsights
                    categories={period.items}
                    viewType={activeTab}
                    onViewTypeChange={setActiveTab}
                  />
                </div>
              )}

              {!loading && !period && !error && (
                <div className="empty-state">
                  <p>Chưa có dữ liệu thống kê cho khoảng thời gian này.</p>
                </div>
              )}
            </div>
          </>
        )}
      </main>
    </div>
  );
};

export default Statistics;
