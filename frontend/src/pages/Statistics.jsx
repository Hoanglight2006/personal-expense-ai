import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { getCategoryStatistics } from '../api/categoryApi';
import CategoryInsights from '../components/CategoryInsights';
import CustomDatePicker from '../components/CustomDatePicker';
import CustomSelect from '../components/CustomSelect';

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
  
  const [dateMode, setDateMode] = useState('month');
  const [month, setMonth] = useState(currentMonthValue);
  const initialRange = useMemo(() => monthRange(currentMonthValue()), []);
  const [customStart, setCustomStart] = useState(initialRange.startDate);
  const [customEnd, setCustomEnd] = useState(initialRange.endDate);

  const selectedRange = useMemo(
    () => dateMode === 'month' ? monthRange(month) : { startDate: customStart, endDate: customEnd },
    [dateMode, month, customStart, customEnd],
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
      <div className="statistics-header">
        <div className="statistics-title">
          <h1>Thống kê & Báo cáo</h1>
          <p>Phân tích chi tiết dòng tiền của bạn</p>
        </div>

        <div className="statistics-filters">
          <div className="filter-group">
            <CustomSelect
              value={dateMode}
              onChange={(e) => {
                setDateMode(e.target.value);
                if (e.target.value === 'recent7') {
                  const r = recentDaysRange(7);
                  setCustomStart(r.startDate);
                  setCustomEnd(r.endDate);
                } else if (e.target.value === 'recent30') {
                  const r = recentDaysRange(30);
                  setCustomStart(r.startDate);
                  setCustomEnd(r.endDate);
                } else if (e.target.value === 'thisMonth') {
                  const r = monthRange(currentMonthValue());
                  setCustomStart(r.startDate);
                  setCustomEnd(r.endDate);
                }
              }}
              options={[
                { value: 'month', label: 'Theo tháng' },
                { value: 'recent7', label: '7 ngày qua' },
                { value: 'recent30', label: '30 ngày qua' },
                { value: 'thisMonth', label: 'Tháng này' },
                { value: 'custom', label: 'Tùy chỉnh' },
              ]}
            />
          </div>

          {dateMode === 'month' && (
            <div className="filter-group">
              <CustomDatePicker
                monthMode
                value={month}
                onChange={(e) => setMonth(e.target.value)}
              />
            </div>
          )}
          
          {dateMode !== 'month' && (
            <div className="date-range-group">
              <div className="filter-group">
                <CustomDatePicker
                  value={customStart}
                  onChange={(e) => {
                    setCustomStart(e.target.value);
                    setDateMode('custom');
                  }}
                  maxDate={customEnd}
                />
              </div>
              <span className="date-separator">-</span>
              <div className="filter-group">
                <CustomDatePicker
                  value={customEnd}
                  onChange={(e) => {
                    setCustomEnd(e.target.value);
                    setDateMode('custom');
                  }}
                  minDate={customStart}
                />
              </div>
            </div>
          )}
        </div>
      </div>

      {error && <div className="error-message" role="alert">{error}</div>}

      <div className="statistics-content" style={{ position: 'relative', minHeight: '400px' }}>
        {loading && !period && (
          <div className="loading-state" style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)' }}>
            <div className="spinner" aria-hidden="true" />
            <p>Đang tải dữ liệu...</p>
          </div>
        )}
        
        {period && (
          <div style={{ opacity: loading ? 0.5 : 1, transition: 'opacity 0.3s ease', pointerEvents: loading ? 'none' : 'auto' }}>
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
