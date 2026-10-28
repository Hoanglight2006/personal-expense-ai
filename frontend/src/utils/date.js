/**
 * Timezone & Date Formatting Utilities for Vietnam (Asia/Ho_Chi_Minh - UTC+7).
 */

export const VIETNAM_TIMEZONE = 'Asia/Ho_Chi_Minh';

/**
 * Safely parse an ISO date/time string from backend.
 * If the string contains date & time without timezone offset (e.g. "2026-10-28T06:29:00"),
 * it represents UTC time stored in MySQL, so we treat it as UTC ('Z') so the browser
 * converts it accurately to Vietnam local time (UTC+7).
 */
export const parseIsoDate = (dateStr) => {
  if (!dateStr) return null;
  if (dateStr instanceof Date) return Number.isNaN(dateStr.getTime()) ? null : dateStr;

  let str = String(dateStr).trim();
  // Date-only format: YYYY-MM-DD
  if (/^\d{4}-\d{2}-\d{2}$/.test(str)) {
    const [y, m, d] = str.split('-').map(Number);
    return new Date(y, m - 1, d);
  }

  // Datetime string
  if (str.includes('T') || str.includes(' ')) {
    str = str.replace(' ', 'T');
    if (!str.endsWith('Z') && !/[+-]\d{2}(:?\d{2})?$/.test(str)) {
      str += 'Z';
    }
  }

  const parsed = new Date(str);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
};

/**
 * Format date to DD/MM/YYYY in Vietnam timezone.
 */
export const formatDateVn = (dateStr) => {
  const d = parseIsoDate(dateStr);
  if (!d) return dateStr || '—';
  const formatter = new Intl.DateTimeFormat('vi-VN', {
    timeZone: VIETNAM_TIMEZONE,
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  });
  const parts = Object.fromEntries(formatter.formatToParts(d).map((p) => [p.type, p.value]));
  return `${parts.day}/${parts.month}/${parts.year}`;
};

/**
 * Format time to HH:mm in Vietnam timezone.
 */
export const formatTimeVn = (dateStr) => {
  const d = parseIsoDate(dateStr);
  if (!d) return '';
  const formatter = new Intl.DateTimeFormat('vi-VN', {
    timeZone: VIETNAM_TIMEZONE,
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  });
  const parts = Object.fromEntries(formatter.formatToParts(d).map((p) => [p.type, p.value]));
  return `${parts.hour}:${parts.minute}`;
};

/**
 * Format full datetime to DD/MM/YYYY HH:mm in Vietnam timezone.
 */
export const formatDateTimeVn = (dateStr) => {
  const d = parseIsoDate(dateStr);
  if (!d) return dateStr || '—';
  const datePart = formatDateVn(d);
  const timePart = formatTimeVn(d);
  return timePart ? `${datePart} ${timePart}` : datePart;
};

/**
 * Format transaction date and creation time:
 * Displays transaction.transaction_date (DD/MM/YYYY) along with transaction.created_at (HH:mm).
 * Example output: "28/10/2026 13:29"
 */
export const formatTransactionDateTime = (transactionDate, createdAt) => {
  const dateFormatted = formatDateVn(transactionDate);
  if (!createdAt) return dateFormatted;
  const timeFormatted = formatTimeVn(createdAt);
  return timeFormatted ? `${dateFormatted} ${timeFormatted}` : dateFormatted;
};

