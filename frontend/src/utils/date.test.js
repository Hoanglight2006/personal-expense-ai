import { describe, expect, it } from 'vitest';
import {
  formatDateTimeVn,
  formatDateVn,
  formatTimeVn,
  formatTransactionDateTime,
  parseIsoDate,
} from './date';

describe('Date & Timezone Utilities for Vietnam', () => {
  it('correctly parses and formats naive UTC strings into Vietnam local time (+7 hours)', () => {
    // 06:29 UTC should become 13:29 Vietnam time
    expect(formatDateTimeVn('2026-10-28T06:29:00')).toBe('28/10/2026 13:29');
    expect(formatTimeVn('2026-10-28T06:29:00')).toBe('13:29');

    // 05:48 UTC should become 12:48 Vietnam time
    expect(formatDateTimeVn('2026-10-28 05:48:00')).toBe('28/10/2026 12:48');
    expect(formatTimeVn('2026-10-28 05:48:00')).toBe('12:48');
  });

  it('correctly formats date-only string YYYY-MM-DD', () => {
    expect(formatDateVn('2026-10-28')).toBe('28/10/2026');
  });

  it('combines transaction_date and created_at into DD/MM/YYYY HH:mm', () => {
    expect(formatTransactionDateTime('2026-10-28', '2026-10-28T06:29:00Z')).toBe('28/10/2026 13:29');
    expect(formatTransactionDateTime('2026-10-28', null)).toBe('28/10/2026');
  });

  it('handles null or empty inputs gracefully', () => {
    expect(parseIsoDate(null)).toBeNull();
    expect(formatDateVn(null)).toBe('—');
    expect(formatDateTimeVn(null)).toBe('—');
    expect(formatTimeVn(null)).toBe('');
  });
});

