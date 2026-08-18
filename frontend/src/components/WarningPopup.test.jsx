import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import WarningPopup from './WarningPopup';

it('renders an accessible warning popup and closes it', async () => {
  const user = userEvent.setup();
  const onClose = vi.fn();
  render(
    <WarningPopup
      isOpen
      message="Số tiền vượt quá số dư khả dụng."
      onClose={onClose}
    />,
  );

  const popup = screen.getByRole('alertdialog', { name: 'Không thể thực hiện' });
  expect(popup).toHaveTextContent('Số tiền vượt quá số dư khả dụng.');
  const closeButton = within(popup).getByRole('button', { name: 'Đã hiểu' });
  await waitFor(() => expect(closeButton).toHaveFocus());
  await user.click(closeButton);
  expect(onClose).toHaveBeenCalledTimes(1);
});
