import { render, screen, waitFor, fireEvent, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import SavingGoals from './SavingGoals';
import {
  getSavingGoals,
  getSavingGoalById,
  createSavingGoal,
  updateSavingGoal,
  deleteSavingGoal,
  contributeToGoal,
  withdrawFromGoal,
} from '../api/savingGoalApi';

vi.mock('../api/savingGoalApi', () => ({
  getSavingGoals: vi.fn(),
  getSavingGoalById: vi.fn(),
  createSavingGoal: vi.fn(),
  updateSavingGoal: vi.fn(),
  deleteSavingGoal: vi.fn(),
  contributeToGoal: vi.fn(),
  withdrawFromGoal: vi.fn(),
}));

vi.mock('../api/transactionApi', () => ({
  getTransactionSummary: vi.fn().mockResolvedValue({
    total_balance: 50000000,
    available_balance: 50000000,
    saving_balance: 0,
    all_time_income: 100000000,
    all_time_expense: 50000000,
  }),
}));

const mockGoalActive = {
  id: 1,
  user_id: 1,
  name: 'Mua laptop mới',
  target_amount: 25000000,
  current_amount: 10000000,
  deadline: '2026-12-31',
  status: 'active',
  progress_percentage: 40.0,
  remaining_amount: 15000000,
  days_remaining: 136,
  contributions: [
    {
      id: 101,
      saving_goal_id: 1,
      amount: 10000000,
      source: 'manual',
      note: 'Khoản nạp ban đầu',
      created_at: '2026-08-01T10:00:00',
    },
  ],
  withdrawals: [],
  created_at: '2026-08-10T10:00:00',
};

const mockGoalCompleted = {
  id: 2,
  user_id: 1,
  name: 'Khóa học thiết kế',
  target_amount: 5000000,
  current_amount: 5000000,
  deadline: '2026-09-01',
  status: 'completed',
  progress_percentage: 100.0,
  remaining_amount: 0,
  days_remaining: 15,
  contributions: [
    {
      id: 102,
      saving_goal_id: 2,
      amount: 5000000,
      source: 'manual',
      note: 'Đã hoàn thành',
      created_at: '2026-08-05T12:00:00',
    },
  ],
  withdrawals: [],
  created_at: '2026-08-05T12:00:00',
};

const mockListResponse = {
  total_target_amount: 30000000,
  total_current_amount: 15000000,
  total_goals_count: 2,
  active_goals_count: 1,
  completed_goals_count: 1,
  items: [mockGoalActive, mockGoalCompleted],
};

const renderPage = () => {
  return render(
    <MemoryRouter initialEntries={['/saving-goals']}>
      <SavingGoals />
    </MemoryRouter>
  );
};

describe('SavingGoals Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getSavingGoals.mockResolvedValue(mockListResponse);
    getSavingGoalById.mockResolvedValue(mockGoalActive);
  });

  it('renders summary metrics and goal cards correctly', async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Mua laptop mới')).toBeInTheDocument();
    });

    expect(screen.getByText('Mục tiêu tiết kiệm')).toBeInTheDocument();
    expect(screen.getByText('Khóa học thiết kế')).toBeInTheDocument();

    // Check KPI summary values
    expect(screen.getByText('50%')).toBeInTheDocument(); // 15M / 30M = 50%
    expect(screen.getByText(/1 đang chạy/i)).toBeInTheDocument();
    expect(screen.getByText(/1 hoàn thành/i)).toBeInTheDocument();

    // Check badges
    expect(screen.getAllByText(/Đang tích lũy/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/Đã hoàn thành/i).length).toBeGreaterThanOrEqual(1);
  });

  it('filters goals instantly in memory when switching tabs without extra network calls', async () => {
    const user = userEvent.setup();
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Mua laptop mới')).toBeInTheDocument();
    });
    expect(screen.getByText('Khóa học thiết kế')).toBeInTheDocument();

    // Click 'Đã hoàn thành' tab
    const completedTab = screen.getByRole('tab', { name: /Đã hoàn thành/i });
    await user.click(completedTab);

    // Active goal is filtered out instantly, completed goal remains
    expect(screen.queryByText('Mua laptop mới')).not.toBeInTheDocument();
    expect(screen.getByText('Khóa học thiết kế')).toBeInTheDocument();

    // Click 'Đang tích lũy' tab
    const activeTab = screen.getByRole('tab', { name: /Đang tích lũy/i });
    await user.click(activeTab);

    expect(screen.getByText('Mua laptop mới')).toBeInTheDocument();
    expect(screen.queryByText('Khóa học thiết kế')).not.toBeInTheDocument();

    // Only 1 initial API call was made
    expect(getSavingGoals).toHaveBeenCalledTimes(1);
  });

  it('renders empty state when no goals exist', async () => {
    getSavingGoals.mockResolvedValue({
      total_target_amount: 0,
      total_current_amount: 0,
      total_goals_count: 0,
      active_goals_count: 0,
      completed_goals_count: 0,
      items: [],
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Chưa có mục tiêu tiết kiệm nào')).toBeInTheDocument();
    });
    expect(screen.getByText('Tạo mục tiêu đầu tiên')).toBeInTheDocument();
  });

  it('opens create modal and submits a new saving goal', async () => {
    const user = userEvent.setup();
    createSavingGoal.mockResolvedValue({
      ...mockGoalActive,
      id: 3,
      name: 'Quỹ du lịch Phú Quốc',
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Mua laptop mới')).toBeInTheDocument();
    });

    const createBtn = screen.getByRole('button', { name: /Tạo mục tiêu/i });
    await user.click(createBtn);

    // Modal open
    expect(screen.getByRole('dialog', { name: 'Tạo mục tiêu tiết kiệm mới' })).toBeInTheDocument();

    // Fill form
    const nameInput = screen.getByPlaceholderText(/Ví dụ: Mua laptop mới/i);
    const amountInput = screen.getByPlaceholderText('Ví dụ: 20000000');

    await user.type(nameInput, 'Quỹ du lịch Phú Quốc');
    await user.type(amountInput, '15000000');

    const submitBtn = screen.getByRole('button', { name: 'Tạo mục tiêu' });
    await user.click(submitBtn);

    await waitFor(() => {
      expect(createSavingGoal).toHaveBeenCalledWith(
        expect.objectContaining({
          name: 'Quỹ du lịch Phú Quốc',
          target_amount: 15000000,
        })
      );
    });
  });

  it('opens deposit modal and submits money to goal', async () => {
    const user = userEvent.setup();
    contributeToGoal.mockResolvedValue({
      ...mockGoalActive,
      current_amount: 12000000,
      progress_percentage: 48.0,
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Mua laptop mới')).toBeInTheDocument();
    });

    const laptopCard = screen.getByText('Mua laptop mới').closest('article');
    const depositBtn = within(laptopCard).getByRole('button', { name: /\+ Nạp tiền/i });
    await user.click(depositBtn);

    // Modal is open
    expect(screen.getByRole('dialog', { name: 'Nạp tiền tiết kiệm' })).toBeInTheDocument();

    // Enter deposit amount
    const amountInput = screen.getByPlaceholderText('Nhập số tiền...');
    await user.type(amountInput, '2000000');

    const noteInput = screen.getByPlaceholderText(/Ví dụ: Trích từ tiền thưởng/i);
    await user.type(noteInput, 'Thưởng tháng 8');

    const confirmBtn = screen.getByRole('button', { name: 'Xác nhận nạp tiền' });
    await user.click(confirmBtn);

    await waitFor(() => {
      expect(contributeToGoal).toHaveBeenCalledWith(1, {
        amount: 2000000,
        note: 'Thưởng tháng 8',
      });
    });
  });

  it('shows an over-balance deposit warning as a popup and returns focus to amount', async () => {
    const user = userEvent.setup();
    renderPage();
    const laptopCard = (await screen.findByText('Mua laptop mới')).closest('article');
    await user.click(within(laptopCard).getByRole('button', { name: /\+ Nạp tiền/i }));

    const amountInput = screen.getByPlaceholderText('Nhập số tiền...');
    await user.type(amountInput, '99999999');
    await user.click(screen.getByRole('button', { name: 'Xác nhận nạp tiền' }));

    const popup = screen.getByRole('alertdialog', { name: 'Không thể thực hiện' });
    expect(popup).toHaveTextContent('vượt quá số dư khả dụng');
    expect(screen.getAllByText(/vượt quá số dư khả dụng/)).toHaveLength(1);
    expect(amountInput).toHaveClass('input-error');
    await user.click(within(popup).getByRole('button', { name: 'Đã hiểu' }));
    await waitFor(() => expect(amountInput).toHaveFocus());
  });

  it('opens withdrawal modal and returns part of the saved amount', async () => {
    const user = userEvent.setup();
    withdrawFromGoal.mockResolvedValue({
      ...mockGoalActive,
      current_amount: 8000000,
      remaining_amount: 17000000,
      withdrawals: [
        {
          id: 201,
          saving_goal_id: 1,
          amount: 2000000,
          note: 'Chi phí khẩn cấp',
          created_at: '2026-08-18T10:00:00',
        },
      ],
    });

    renderPage();
    const laptopCard = (await screen.findByText('Mua laptop mới')).closest('article');
    await user.click(within(laptopCard).getByRole('button', { name: /Rút tiền/i }));

    expect(screen.getByRole('dialog', { name: 'Rút tiền tiết kiệm' })).toBeInTheDocument();
    const amountInput = screen.getByPlaceholderText('Nhập số tiền muốn rút...');
    await user.type(amountInput, '2000000');
    await user.type(
      screen.getByPlaceholderText(/Ví dụ: Chi phí khẩn cấp/i),
      'Chi phí khẩn cấp'
    );
    await user.click(screen.getByRole('button', { name: 'Xác nhận rút tiền' }));

    await waitFor(() => {
      expect(withdrawFromGoal).toHaveBeenCalledWith(1, {
        amount: 2000000,
        note: 'Chi phí khẩn cấp',
        idempotency_key: expect.any(String),
      });
    });
  });

  it('shows a popup and refocuses amount when withdrawal exceeds saved money', async () => {
    const user = userEvent.setup();
    renderPage();
    const laptopCard = (await screen.findByText('Mua laptop mới')).closest('article');
    await user.click(within(laptopCard).getByRole('button', { name: /Rút tiền/i }));

    const amountInput = screen.getByPlaceholderText('Nhập số tiền muốn rút...');
    await user.type(amountInput, '11000000');
    await user.click(screen.getByRole('button', { name: 'Xác nhận rút tiền' }));

    const popup = screen.getByRole('alertdialog', { name: 'Không thể thực hiện' });
    expect(popup).toHaveTextContent('vượt quá số tiền đang tích lũy');
    expect(screen.getAllByText(/vượt quá số tiền đang tích lũy/)).toHaveLength(1);
    expect(amountInput).toHaveClass('input-error');
    expect(withdrawFromGoal).not.toHaveBeenCalled();
    await user.click(within(popup).getByRole('button', { name: 'Đã hiểu' }));
    await waitFor(() => expect(amountInput).toHaveFocus());
  });

  it('reuses the same withdrawal idempotency key when retrying after a network error', async () => {
    const user = userEvent.setup();
    withdrawFromGoal
      .mockRejectedValueOnce(new Error('Network timeout'))
      .mockResolvedValue({
        ...mockGoalActive,
        current_amount: 8000000,
      });

    renderPage();
    const laptopCard = (await screen.findByText('Mua laptop mới')).closest('article');
    await user.click(within(laptopCard).getByRole('button', { name: /Rút tiền/i }));
    await user.type(screen.getByPlaceholderText('Nhập số tiền muốn rút...'), '2000000');
    await user.click(screen.getByRole('button', { name: 'Xác nhận rút tiền' }));

    const popup = await screen.findByRole('alertdialog', { name: 'Không thể thực hiện' });
    await user.click(within(popup).getByRole('button', { name: 'Đã hiểu' }));
    await user.click(screen.getByRole('button', { name: 'Xác nhận rút tiền' }));

    await waitFor(() => expect(withdrawFromGoal).toHaveBeenCalledTimes(2));
    const firstPayload = withdrawFromGoal.mock.calls[0][1];
    const retryPayload = withdrawFromGoal.mock.calls[1][1];
    expect(firstPayload.idempotency_key).toBeTruthy();
    expect(retryPayload.idempotency_key).toBe(firstPayload.idempotency_key);
  });

  it('opens edit modal and updates a goal', async () => {
    const user = userEvent.setup();
    updateSavingGoal.mockResolvedValue({
      ...mockGoalActive,
      name: 'Mua MacBook Pro M4',
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Mua laptop mới')).toBeInTheDocument();
    });

    const editBtn = screen.getByLabelText('Sửa Mua laptop mới');
    await user.click(editBtn);

    expect(screen.getByRole('dialog', { name: 'Chỉnh sửa mục tiêu tiết kiệm' })).toBeInTheDocument();

    const nameInput = screen.getByPlaceholderText(/Ví dụ: Mua laptop mới/i);
    fireEvent.change(nameInput, { target: { value: 'Mua MacBook Pro M4' } });

    const submitBtn = screen.getByRole('button', { name: 'Cập nhật' });
    await user.click(submitBtn);

    await waitFor(() => {
      expect(updateSavingGoal).toHaveBeenCalledWith(
        1,
        expect.objectContaining({
          name: 'Mua MacBook Pro M4',
        })
      );
    });
  });

  it('does not display edit button and disables deposit button for completed goals', async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Khóa học thiết kế')).toBeInTheDocument();
    });

    const completedCard = screen.getByText('Khóa học thiết kế').closest('article');
    // Edit button should not be present on completed cards
    expect(within(completedCard).queryByLabelText(/Sửa Khóa học thiết kế/i)).not.toBeInTheDocument();

    // Deposit button should show '✓ Đã hoàn thành' and be disabled
    const depositBtn = within(completedCard).getByRole('button', { name: /✓ Đã hoàn thành/i });
    expect(depositBtn).toBeDisabled();
    expect(within(completedCard).getByRole('button', { name: /Rút tiền/i })).toBeEnabled();
  });

  it('opens history modal and displays contributions timeline', async () => {
    const user = userEvent.setup();
    getSavingGoalById.mockResolvedValue({
      ...mockGoalActive,
      withdrawals: [
        {
          id: 201,
          saving_goal_id: 1,
          amount: 500000,
          note: 'Rút thử nghiệm',
          created_at: '2026-08-18T10:00:00',
        },
      ],
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Mua laptop mới')).toBeInTheDocument();
    });

    const historyBtns = screen.getAllByRole('button', { name: /📜 Lịch sử/i });
    await user.click(historyBtns[0]);

    await waitFor(() => {
      expect(screen.getByRole('dialog', { name: 'Lịch sử nạp và rút tiền' })).toBeInTheDocument();
    });

    expect(screen.getByText('“Khoản nạp ban đầu”')).toBeInTheDocument();
    expect(screen.getByText('Nạp thủ công')).toBeInTheDocument();
    expect(screen.getByText('Rút tiền')).toBeInTheDocument();
    expect(screen.getByText('“Rút thử nghiệm”')).toBeInTheDocument();
  });

  it('deletes a goal after confirmation', async () => {
    const user = userEvent.setup();
    deleteSavingGoal.mockResolvedValue({ detail: 'Đã xóa mục tiêu tiết kiệm thành công.' });

    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Mua laptop mới')).toBeInTheDocument();
    });

    const deleteBtn = screen.getByLabelText('Xóa Mua laptop mới');
    await user.click(deleteBtn);

    // Confirm modal opens
    expect(screen.getByText('Xóa mục tiêu tiết kiệm?')).toBeInTheDocument();

    const confirmBtn = screen.getByRole('button', { name: 'Xóa mục tiêu' });
    await user.click(confirmBtn);

    await waitFor(() => {
      expect(deleteSavingGoal).toHaveBeenCalledWith(1);
    });
  });
});
