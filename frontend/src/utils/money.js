export const decimalToCents = (value) => {
  const match = String(value ?? '0').trim().match(/^(-?)(\d+)(?:\.(\d+))?$/);
  if (!match) return 0n;
  const [, sign, integer, fraction = ''] = match;
  const cents = (BigInt(integer) * 100n) + BigInt(fraction.slice(0, 2).padEnd(2, '0'));
  return sign === '-' ? -cents : cents;
};

export const centsToDecimal = (cents) => {
  const absolute = cents < 0n ? -cents : cents;
  const sign = cents < 0n ? '-' : '';
  return `${sign}${absolute / 100n}.${String(absolute % 100n).padStart(2, '0')}`;
};

export const formatVndDecimal = (value) => {
  const match = String(value ?? '0').trim().match(/^(-?)(\d+)(?:\.(\d+))?$/);
  if (!match) return '—';
  const [, sign, rawInteger, rawFraction = ''] = match;
  const integer = rawInteger.replace(/^0+(?=\d)/, '').replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  const fraction = rawFraction.slice(0, 2).padEnd(2, '0');
  const decimalPart = fraction === '00' ? '' : `,${fraction.replace(/0+$/, '')}`;
  return `${sign}${integer}${decimalPart}\u00a0₫`;
};

export const percentageOf = (part, total) => {
  if (total <= 0n || part <= 0n) return 0;
  return Number((part * 1000n) / total) / 10;
};
