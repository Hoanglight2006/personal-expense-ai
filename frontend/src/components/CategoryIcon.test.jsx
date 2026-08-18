import { render } from '@testing-library/react';
import { expect, it } from 'vitest';
import CategoryIcon from './CategoryIcon';

it('uses the compact category asset for transaction cards', () => {
  const { container, rerender } = render(<CategoryIcon icon="food" color="#E76452" compact />);
  const compactSource = container.querySelector('img').getAttribute('src');

  rerender(<CategoryIcon icon="food" color="#E76452" />);
  const fullSource = container.querySelector('img').getAttribute('src');

  expect(compactSource).toContain('/avatars/food.png');
  expect(compactSource).not.toBe(fullSource);
});
