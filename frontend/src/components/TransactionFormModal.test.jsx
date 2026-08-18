import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import TransactionFormModal from './TransactionFormModal';
import { getTransactionSummary } from '../api/transactionApi';
import { getSavingGoals } from '../api/savingGoalApi';

vi.mock('../api/transactionApi', () => ({
  scanImage: vi.fn(),
  getTransactionSummary: vi.fn(),
}));

vi.mock('../api/savingGoalApi', () => ({
  getSavingGoals: vi.fn().mockResolvedValue({ items: [] }),
}));

it('shows an over-balance expense warning as a popup', async () => {
  const user = userEvent.setup();
  const onSubmit = vi.fn();
  getTransactionSummary.mockResolvedValue({ available_balance: 100000 });
  render(
    <TransactionFormModal
      transaction={null}
      categories={[{
        id: 1,
        name: 'Ăn uống',
        type: 'expense',
        icon: 'food',
        color: '#D69A23',
        is_active: true,
      }]}
      submitting={false}
      apiError=""
      onClose={vi.fn()}
      onSubmit={onSubmit}
      prefillData={{
        amount: '200000',
        type: 'expense',
        category_id: 1,
        transaction_date: '2026-08-18',
        description: '',
        payment_method: 'cash',
      }}
      onExcelUpload={vi.fn()}
      isExcelLoading={false}
      categoriesReady
    />,
  );

  await waitFor(() => expect(getTransactionSummary).toHaveBeenCalled());
  expect(getSavingGoals).not.toHaveBeenCalled();
  await user.click(screen.getByRole('button', { name: 'Thêm giao dịch' }));
  const popup = screen.getByRole('alertdialog', { name: 'Không thể thực hiện' });
  expect(popup).toHaveTextContent('vượt quá số dư khả dụng');
  expect(screen.getAllByText(/vượt quá số dư khả dụng/)).toHaveLength(1);
  expect(onSubmit).not.toHaveBeenCalled();

  await user.click(within(popup).getByRole('button', { name: 'Đã hiểu' }));
  await waitFor(() => expect(screen.getByPlaceholderText('0.00')).toHaveFocus());
});
