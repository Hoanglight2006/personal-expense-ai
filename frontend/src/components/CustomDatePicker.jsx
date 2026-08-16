import React, { useEffect, useId, useRef } from 'react';
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
}) => {
  const popupId = useId();
  const pickerRef = useRef(null);
  const isControlled = typeof open === 'boolean';

  useEffect(() => {
    if (isControlled) return undefined;
    return subscribeToPopupOpen((event) => {
      if (event.detail !== popupId) pickerRef.current?.setOpen(false);
    });
  }, [isControlled, popupId]);

  // value is expected to be 'YYYY-MM-DD' or 'YYYY-MM' (if monthMode)
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
    announcePopupOpen(popupId);
    onCalendarOpen?.();
  };

  const handleCalendarClose = () => {
    onCalendarClose?.();
  };

  return (
    <DatePicker
      ref={pickerRef}
      selected={selectedDate}
      onChange={handleChange}
      dateFormat={monthMode ? "'Tháng' MM, yyyy" : "dd/MM/yyyy"}
      locale="vi"
      disabled={disabled}
      placeholderText={placeholderText || (monthMode ? "Chọn tháng" : "dd/mm/yyyy")}
      className="custom-datepicker-input"
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
      renderCustomHeader={({ date, decreaseMonth, increaseMonth, prevMonthButtonDisabled, nextMonthButtonDisabled }) => (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '4px 8px 12px', borderBottom: '1px solid rgba(0,0,0,0.05)', marginBottom: '8px' }}>
          <button
            type="button"
            className="custom-datepicker-nav-btn"
            onClick={decreaseMonth}
            disabled={prevMonthButtonDisabled}
            aria-label="Tháng trước"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="15 18 9 12 15 6"></polyline></svg>
          </button>
          <div className="react-datepicker__current-month" style={{ margin: 0, fontSize: '1.15rem', fontWeight: 800, color: 'var(--text-color)' }}>
            {format(date, monthMode ? "yyyy" : "MMMM, yyyy", { locale: vi })}
          </div>
          <button
            type="button"
            className="custom-datepicker-nav-btn"
            onClick={increaseMonth}
            disabled={nextMonthButtonDisabled}
            aria-label="Tháng sau"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 18 15 12 9 6"></polyline></svg>
          </button>
        </div>
      )}
      portalId="root-portal"
      fixedHeight
    />
  );
};

export default CustomDatePicker;
