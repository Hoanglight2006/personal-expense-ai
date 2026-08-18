import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import Transactions from './Transactions';
import {
  createTransaction,
  getTransactions,
  importTransactions,
  parseExcel,
} from '../api/transactionApi';
import { getCategories } from '../api/categoryApi';

vi.mock('../api/transactionApi', () => ({
  getTransactions: vi.fn(),
  createTransaction: vi.fn(),
  updateTransaction: vi.fn(),
  trashTransaction: vi.fn(),
  duplicateTransaction: vi.fn(),
  parseExcel: vi.fn(),
  importTransactions: vi.fn(),
}));

vi.mock('../api/categoryApi', () => ({ getCategories: vi.fn() }));

vi.mock('../components/TransactionCard', () => ({
  default: ({ transaction }) => <div>{transaction.description}</div>,
}));
vi.mock('../components/ConfirmModal', () => ({ default: () => null }));
vi.mock('../components/CustomDatePicker', () => ({
  default: ({ value, onChange }) => <input value={value} onChange={onChange} />,
}));
vi.mock('../components/CustomSelect', () => ({
  default: ({ value, onChange, options }) => (
    <select value={value} onChange={onChange}>
      {options.map((option) => (
        <option key={option.value} value={option.value}>{option.label}</option>
      ))}
    </select>
  ),
}));
vi.mock('../components/TransactionFormModal', () => ({
  default: ({ onExcelUpload, onSubmit, categoriesReady }) => (
    <div role="dialog">
      <input aria-label="Tải Excel" type="file" onChange={onExcelUpload} />
      <button
        type="button"
        onClick={() => onSubmit({ amount: '1000.00', type: 'expense', category_id: 1 })}
      >
        Lưu giao dịch test
      </button>
      <span>{categoriesReady ? 'categories-ready' : 'categories-blocked'}</span>
    </div>
  ),
}));
vi.mock('../components/ExcelPreviewModal', () => ({
  default: ({ data, apiError, onConfirm, submitting }) => (
    <div role="dialog">
      {apiError && <div role="alert">{apiError}</div>}
      <button type="button" disabled={submitting} onClick={() => onConfirm(data)}>
        Xác nhận nhập
      </button>
    </div>
  ),
}));

const categories = [
  { id: 1, name: 'Ăn uống', type: 'expense', is_active: true },
  { id: 2, name: 'Cũ', type: 'expense', is_active: false },
];

const renderPage = () => render(
  <MemoryRouter initialEntries={['/transactions']}>
    <Transactions />
  </MemoryRouter>,
);

const deferred = () => {
  let resolve;
  let reject;
  const promise = new Promise((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
};

beforeEach(() => {
  vi.clearAllMocks();
  getTransactions.mockResolvedValue({ items: [], total_count: 0 });
  getCategories.mockResolvedValue({ items: categories });
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('Transactions page safeguards', () => {
  it('shows a retry state instead of an empty list after loading fails', async () => {
    const user = userEvent.setup();
    getTransactions
      .mockRejectedValueOnce({ response: { data: { detail: 'Tải giao dịch thất bại.' } } })
      .mockResolvedValueOnce({ items: [], total_count: 0 });
    renderPage();

    expect(await screen.findByRole('alert')).toHaveTextContent('Tải giao dịch thất bại.');
    expect(screen.queryByText('Chưa có giao dịch nào')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Thử lại' }));
    expect(await screen.findByText('Chưa có giao dịch nào')).toBeInTheDocument();
    expect(getTransactions).toHaveBeenCalledTimes(2);
  });

  it('includes hidden categories in the historical transaction filter', async () => {
    renderPage();
    expect(await screen.findByRole('option', { name: 'Cũ (đã ẩn)' })).toBeInTheDocument();
  });

  it('debounces transaction searches instead of requesting on every keystroke', async () => {
    renderPage();
    await waitFor(() => expect(getTransactions).toHaveBeenCalledTimes(1));

    fireEvent.change(screen.getByPlaceholderText('Tìm theo ghi chú...'), {
      target: { value: 'cà phê' },
    });
    expect(getTransactions).toHaveBeenCalledTimes(1);

    await waitFor(() => expect(getTransactions).toHaveBeenCalledTimes(2));
    expect(getTransactions.mock.calls[1][0]).toMatchObject({ search: 'cà phê', page: 1 });
  });

  it('ignores an older manual reload after a newer filtered request finishes', async () => {
    const user = userEvent.setup();
    const staleReload = deferred();
    const filteredReload = deferred();
    createTransaction.mockResolvedValue({ id: 10 });
    getTransactions
      .mockResolvedValueOnce({ items: [], total_count: 0 })
      .mockImplementationOnce(() => staleReload.promise)
      .mockImplementationOnce(() => filteredReload.promise);

    const { container } = renderPage();
    await waitFor(() => expect(getTransactions).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(container.querySelector('.add-txn-button')).toBeEnabled());

    await user.click(container.querySelector('.add-txn-button'));
    await user.click(screen.getByRole('button', { name: 'Lưu giao dịch test' }));
    await waitFor(() => expect(getTransactions).toHaveBeenCalledTimes(2));

    await user.selectOptions(screen.getByLabelText('Loại'), 'income');
    await waitFor(() => expect(getTransactions).toHaveBeenCalledTimes(3));

    filteredReload.resolve({
      items: [{ id: 2, description: 'Kết quả lọc mới' }],
      total_count: 1,
    });
    expect(await screen.findByText('Kết quả lọc mới')).toBeInTheDocument();

    staleReload.resolve({
      items: [{ id: 1, description: 'Kết quả cũ' }],
      total_count: 1,
    });
    await waitFor(() => {
      expect(screen.queryByText('Kết quả cũ')).not.toBeInTheDocument();
      expect(screen.getByText('Kết quả lọc mới')).toBeInTheDocument();
    });
  });

  it('shows category loading errors and retries them', async () => {
    const user = userEvent.setup();
    getCategories
      .mockRejectedValueOnce({ response: { data: { detail: 'Danh mục lỗi.' } } })
      .mockResolvedValueOnce({ items: categories });
    const { container } = renderPage();

    expect(await screen.findByText(/Không thể tải danh mục: Danh mục lỗi/)).toBeInTheDocument();
    expect(container.querySelector('.add-txn-button')).toBeDisabled();
    await user.click(screen.getByRole('button', { name: 'Thử lại' }));
    await waitFor(() => expect(getCategories).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(container.querySelector('.add-txn-button')).toBeEnabled());
  });

  it('reuses the Excel idempotency key after a failed response', async () => {
    const user = userEvent.setup();
    const randomUuid = vi.spyOn(crypto, 'randomUUID').mockReturnValue('stable-import-key');
    parseExcel.mockResolvedValue({
      items: [{
        amount: '1000.00',
        type: 'expense',
        category_id: 1,
        transaction_date: '2026-08-18',
        description: 'Bữa sáng',
        payment_method: 'cash',
      }],
    });
    importTransactions
      .mockRejectedValueOnce({ response: { data: { detail: 'Mất phản hồi.' } } })
      .mockResolvedValueOnce({ success_count: 1, error_count: 0 });

    const { container } = renderPage();
    await waitFor(() => expect(container.querySelector('.add-txn-button')).toBeEnabled());
    await user.click(container.querySelector('.add-txn-button'));
    fireEvent.change(screen.getByLabelText('Tải Excel'), {
      target: { files: [new File(['rows'], 'statement.xlsx')] },
    });

    const confirm = await screen.findByRole('button', { name: 'Xác nhận nhập' });
    await user.click(confirm);
    await waitFor(() => expect(importTransactions).toHaveBeenCalledTimes(1));
    expect(await screen.findByRole('alert')).toHaveTextContent('Mất phản hồi.');
    await user.click(screen.getByRole('button', { name: 'Xác nhận nhập' }));
    await waitFor(() => expect(importTransactions).toHaveBeenCalledTimes(2));

    const firstKey = importTransactions.mock.calls[0][0].idempotency_key;
    const secondKey = importTransactions.mock.calls[1][0].idempotency_key;
    expect(firstKey).toBe('stable-import-key');
    expect(secondKey).toBe(firstKey);
    expect(randomUuid).toHaveBeenCalledTimes(1);
    randomUuid.mockRestore();
  });
});
