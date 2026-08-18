import React, { useEffect, useId, useRef, useState } from 'react';
import DatePicker, { registerLocale } from 'react-datepicker';
import { vi } from 'date-fns/locale/vi';
import { format, parse } from 'date-fns';
import { shift } from '@floating-ui/react';
import 'react-datepicker/dist/react-datepicker.css';
import { announcePopupOpen, subscribeToPopupOpen } from '../utils/popupCoordinator';

registerLocale('vi', vi);

const CustomDatePicker = ({
  value,
  onChange,
  disabled,
  placeholderText,
  monthMode = false,
  open,
  onCalendarOpen,
  onCalendarClose,
  minDate,
  maxDate,
  popperPlacement = 'bottom-start',
  id,
  hasError = false,
}) => {
  const popupId = useId();
  const pickerRef = useRef(null);
  const scrollGuardRef = useRef(null);
  const isControlled = typeof open === 'boolean';
  const [calendarOpen, setCalendarOpen] = useState(Boolean(open));
  const [viewMode, setViewMode] = useState('days'); // 'days' | 'months' | 'years'
  const [yearRangeStart, setYearRangeStart] = useState(() => {
    const y = new Date().getFullYear();
    return Math.floor(y / 12) * 12;
  });

  useEffect(() => {
    if (isControlled) return undefined;
    return subscribeToPopupOpen((event) => {
      if (event.detail !== popupId) pickerRef.current?.setOpen(false);
    });
  }, [isControlled, popupId]);

  useEffect(() => {
    if (isControlled) setCalendarOpen(open);
  }, [isControlled, open]);

  useEffect(() => {
    const guard = scrollGuardRef.current;
    if (!guard) return undefined;

    const blockWheel = (event) => {
      event.preventDefault();
      event.stopPropagation();
    };

    guard.addEventListener('wheel', blockWheel, { passive: false });
    return () => guard.removeEventListener('wheel', blockWheel);
  }, []);

  useEffect(() => {
    if (!calendarOpen) return undefined;

    const blockCalendarWheel = (event) => {
      if (!(event.target instanceof Element) || !event.target.closest('.custom-datepicker-popper')) return;
      event.preventDefault();
      event.stopPropagation();
    };

    document.addEventListener('wheel', blockCalendarWheel, { capture: true, passive: false });
    return () => document.removeEventListener('wheel', blockCalendarWheel, { capture: true });
  }, [calendarOpen]);

  let selectedDate = null;
  if (value) {
    try {
      selectedDate = parse(value, monthMode ? 'yyyy-MM' : 'yyyy-MM-dd', new Date());
    } catch {
      selectedDate = null;
    }
  }

  const handleChange = (date) => {
    if (date) {
      onChange({ target: { value: format(date, monthMode ? 'yyyy-MM' : 'yyyy-MM-dd') } });
    } else {
      onChange({ target: { value: '' } });
    }
  };

  const handleCalendarOpen = () => {
    setCalendarOpen(true);
    setViewMode('days');
    announcePopupOpen(popupId);
    onCalendarOpen?.();
  };

  const handleCalendarClose = () => {
    setCalendarOpen(false);
    setViewMode('days');
    onCalendarClose?.();
  };

  const months = [
    'Thg 1', 'Thg 2', 'Thg 3', 'Thg 4', 'Thg 5', 'Thg 6',
    'Thg 7', 'Thg 8', 'Thg 9', 'Thg 10', 'Thg 11', 'Thg 12',
  ];

  return (
    <div ref={scrollGuardRef} className="custom-datepicker-scroll-guard">
      <DatePicker
      ref={pickerRef}
      selected={selectedDate}
      onChange={handleChange}
      dateFormat={monthMode ? "'Tháng' MM, yyyy" : "dd/MM/yyyy"}
      locale="vi"
      disabled={disabled}
      id={id}
      ariaInvalid={hasError}
      placeholderText={placeholderText || (monthMode ? "Chọn tháng" : "dd/mm/yyyy")}
      className={`custom-datepicker-input ${hasError ? 'input-error' : ''}`.trim()}
      popperClassName="custom-datepicker-popper"
      popperPlacement={popperPlacement}
      open={open}
      onCalendarOpen={handleCalendarOpen}
      onCalendarClose={handleCalendarClose}
      closeOnScroll
      minDate={minDate ? parse(minDate, 'yyyy-MM-dd', new Date()) : undefined}
      maxDate={maxDate ? parse(maxDate, 'yyyy-MM-dd', new Date()) : undefined}
      popperProps={{ strategy: 'fixed' }}
      popperModifiers={[shift({ padding: 10, crossAxis: true })]}
      showPopperArrow={false}
      isClearable={false}
      shouldCloseOnSelect={true}
      showMonthYearPicker={monthMode}
      renderCustomHeader={({
        date,
        changeYear,
        changeMonth,
        decreaseMonth,
        increaseMonth,
        prevMonthButtonDisabled,
        nextMonthButtonDisabled,
      }) => (
        <div className="custom-datepicker-header-container">
          <div className="custom-datepicker-header">
            <button
              type="button"
              className="custom-datepicker-nav-btn"
              onClick={decreaseMonth}
              disabled={prevMonthButtonDisabled}
              aria-label="Tháng trước"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="15 18 9 12 15 6"></polyline></svg>
            </button>

            <div className="custom-datepicker-pills-wrap">
              {!monthMode && (
                <button
                  type="button"
                  className={`custom-datepicker-pill-btn ${viewMode === 'months' ? 'active' : ''}`}
                  onClick={() => setViewMode((m) => (m === 'months' ? 'days' : 'months'))}
                >
                  {format(date, "'Tháng' MM", { locale: vi })}
                  <span className="pill-arrow">▾</span>
                </button>
              )}

              <button
                type="button"
                className={`custom-datepicker-pill-btn ${viewMode === 'years' ? 'active' : ''}`}
                onClick={() => {
                  setYearRangeStart(Math.floor(date.getFullYear() / 12) * 12);
                  setViewMode((m) => (m === 'years' ? 'days' : 'years'));
                }}
              >
                {date.getFullYear()}
                <span className="pill-arrow">▾</span>
              </button>
            </div>

            <button
              type="button"
              className="custom-datepicker-nav-btn"
              onClick={increaseMonth}
              disabled={nextMonthButtonDisabled}
              aria-label="Tháng sau"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 18 15 12 9 6"></polyline></svg>
            </button>
          </div>

          {viewMode === 'months' && (
            <div className="custom-picker-grid-overlay">
              <div className="grid-overlay-header">
                <span className="grid-overlay-title">Chọn Tháng</span>
                <button
                  type="button"
                  className="grid-overlay-close-btn"
                  onClick={() => setViewMode('days')}
                  aria-label="Đóng chọn tháng"
                >
                  ✕
                </button>
              </div>
              <div className="months-chip-grid">
                {months.map((m, idx) => {
                  const isCurrent = date.getMonth() === idx;
                  return (
                    <button
                      key={m}
                      type="button"
                      className={`grid-chip-item ${isCurrent ? 'chip-selected' : ''}`}
                      onClick={() => {
                        changeMonth(idx);
                        setViewMode('days');
                      }}
                    >
                      {m}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {viewMode === 'years' && (
            <div className="custom-picker-grid-overlay">
              <div className="grid-overlay-header">
                <div className="grid-range-nav">
                  <button
                    type="button"
                    className="custom-datepicker-nav-btn"
                    onClick={() => setYearRangeStart((s) => s - 12)}
                    aria-label="12 năm trước"
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="15 18 9 12 15 6"></polyline></svg>
                  </button>
                  <span className="grid-overlay-title">{yearRangeStart} – {yearRangeStart + 11}</span>
                  <button
                    type="button"
                    className="custom-datepicker-nav-btn"
                    onClick={() => setYearRangeStart((s) => s + 12)}
                    aria-label="12 năm sau"
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="9 18 15 12 9 6"></polyline></svg>
                  </button>
                </div>
                <button
                  type="button"
                  className="grid-overlay-close-btn"
                  onClick={() => setViewMode('days')}
                  aria-label="Đóng chọn năm"
                >
                  ✕
                </button>
              </div>
              <div className="years-chip-grid">
                {Array.from({ length: 12 }, (_, i) => yearRangeStart + i).map((yr) => {
                  const isCurrent = date.getFullYear() === yr;
                  return (
                    <button
                      key={yr}
                      type="button"
                      className={`grid-chip-item ${isCurrent ? 'chip-selected' : ''}`}
                      onClick={() => {
                        changeYear(yr);
                        setViewMode('days');
                      }}
                    >
                      {yr}
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}
      portalId="root-portal"
        fixedHeight
      />
    </div>
  );
};

export default React.memo(CustomDatePicker);
