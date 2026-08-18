import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import Budgets from './Budgets';
import { getBudgets, createBudget, updateBudget, deleteBudget } from '../api/budgetApi';
import { getCategories } from '../api/categoryApi';
import { getTransactionSummary } from '../api/transactionApi';

vi.mock('../api/budgetApi', () => ({
  getBudgets: vi.fn(),
  getBudgetAlerts: vi.fn(),
  createBudget: vi.fn(),
  updateBudget: vi.fn(),
  deleteBudget: vi.fn(),
}));

vi.mock('../api/categoryApi', () => ({
  getCategories: vi.fn(),
}));

vi.mock('../api/transactionApi', () => ({
  getTransactionSummary: vi.fn(),
}));

vi.mock('../api/aiApi', () => ({
  getBudgetRecommendations: vi.fn(),
  applyBudgetRecommendations: vi.fn(),
}));

const mockCategories = [
  { id: 1, name: 'Ăn uống', type: 'expense', icon: 'food', color: '#C87941', is_active: true },
  { id: 2, name: 'Di chuyển', type: 'expense', icon: 'transport', color: '#38bdf8', is_active: true },
  { id: 3, name: 'Lương', type: 'income', icon: 'salary', color: '#10b981', is_active: true },
];

const mockBudgetNormal = {
  id: 101,
  user_id: 1,
  category_id: 1,
  category: mockCategories[0],
  amount: 1000000,
  month: 8,
  year: 2026,
  spent_amount: 500000,
  remaining_amount: 500000,
  percentage_used: 50.0,
  status: 'normal',
  created_at: '2026-08-01T00:00:00',
};

const mockBudgetWarning = {
  id: 102,
  user_id: 1,
  category_id: 2,
  category: mockCategories[1],
  amount: 1000000,
  month: 8,
  year: 2026,
  spent_amount: 850000,
  remaining_amount: 150000,
  percentage_used: 85.0,
  status: 'warning',
  created_at: '2026-08-01T00:00:00',
};

const mockBudgetResponse = {
  month: 8,
  year: 2026,
  total_budget: 2000000,
  total_spent: 1350000,
  total_remaining: 650000,
  items: [mockBudgetNormal, mockBudgetWarning],
};

const renderPage = () => {
  return render(
    <MemoryRouter initialEntries={['/budgets']}>
      <Budgets />
    </MemoryRouter>
  );
};

describe('Budgets Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getCategories.mockResolvedValue({ items: mockCategories });
    getBudgets.mockResolvedValue(mockBudgetResponse);
    getTransactionSummary.mockResolvedValue({ available_balance: 5000000 });
  });

  it('renders budget list and summary metrics correctly', async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Ăn uống')).toBeInTheDocument();
    });

    expect(screen.getByText('Quản lý Ngân sách')).toBeInTheDocument();
    expect(screen.getByText('Di chuyển')).toBeInTheDocument();

    // Check status badges
    expect(screen.getByText(/An toàn \(50%\)/)).toBeInTheDocument();
    expect(screen.getByText(/Cảnh báo 80% \(85%\)/)).toBeInTheDocument();
  });

  it('renders empty state when no budgets exist for month', async () => {
    getBudgets.mockResolvedValue({
      month: 8,
      year: 2026,
      total_budget: 0,
      total_spent: 0,
      total_remaining: 0,
      items: [],
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByText(/Chưa có ngân sách cho Tháng/)).toBeInTheDocument();
    });
  });

  it('opens create modal and creates a new budget', async () => {
    const user = userEvent.setup();
    createBudget.mockResolvedValue({
      id: 103,
      user_id: 1,
      category_id: 2,
      amount: 500000,
      month: 8,
      year: 2026,
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Thiết lập ngân sách')).toBeInTheDocument();
    });

    // Click add budget button
    const addBtn = screen.getByRole('button', { name: /Thiết lập ngân sách/i });
    await user.click(addBtn);

    // Modal is open
    expect(screen.getByRole('dialog', { name: 'Thiết lập ngân sách mới' })).toBeInTheDocument();

    // Enter amount
    const amountInput = screen.getByPlaceholderText('Ví dụ: 1000000');
    await user.type(amountInput, '500000');

    // Submit button
    const submitBtn = screen.getByRole('button', { name: 'Tạo ngân sách' });
    expect(submitBtn).toBeInTheDocument();
  });

  it('opens edit modal to update budget amount', async () => {
    const user = userEvent.setup();
    updateBudget.mockResolvedValue({
      ...mockBudgetNormal,
      amount: 2000000,
    });

    renderPage();

    const editBtns = await screen.findAllByRole('button', { name: /Sửa hạn mức/i });
    await user.click(editBtns[0]);

    const modal = await screen.findByRole('dialog');
    expect(modal).toBeInTheDocument();

    const amountInput = screen.getByPlaceholderText('Ví dụ: 1000000');
    fireEvent.change(amountInput, { target: { value: '2000000' } });

    const form = modal.querySelector('form');
    fireEvent.submit(form);

    await waitFor(() => {
      expect(updateBudget).toHaveBeenCalledWith(102, { amount: 2000000 });
    });
  });

  it('deletes a budget after confirmation', async () => {
    const user = userEvent.setup();
    deleteBudget.mockResolvedValue({ detail: 'Đã xóa ngân sách thành công.' });

    renderPage();

    await waitFor(() => {
      expect(screen.getAllByTitle('Xóa ngân sách')).toHaveLength(2);
    });

    const deleteBtns = screen.getAllByTitle('Xóa ngân sách');
    await user.click(deleteBtns[0]);

    // Confirm modal opens
    expect(screen.getByText('Xóa ngân sách danh mục?')).toBeInTheDocument();

    const confirmBtn = screen.getByRole('button', { name: 'Xóa ngân sách' });
    await user.click(confirmBtn);

    await waitFor(() => {
      expect(deleteBudget).toHaveBeenCalledWith(102);
    });
  });

  it('switches to AI Budget tab, shows options, and generates suggestions on confirmation', async () => {
    const user = userEvent.setup();
    const { getBudgetRecommendations, applyBudgetRecommendations } = await import('../api/aiApi');
    getBudgetRecommendations.mockResolvedValue({
      target_month: 8,
      target_year: 2026,
      total_recommended: 3000000,
      recommendations: [
        {
          category_id: 1,
          category_name: 'Ăn uống',
          category_icon: 'food',
          category_color: '#C87941',
          avg_spent: 2000000,
          last_month_spent: 2200000,
          recommended_amount: 2500000,
          reason: 'Dựa trên mức chi trung bình gần đây.',
        },
      ],
    });
    applyBudgetRecommendations.mockResolvedValue({
      success: true,
      applied_count: 1,
      message: 'Đã áp dụng thành công.',
    });

    renderPage();

    const aiTab = screen.getByRole('tab', { name: /AI Gợi Ý Ngân Sách/i });
    await user.click(aiTab);

    // Shows options config card first
    expect(screen.getByText('Tùy Chọn Sinh Gợi Ý Ngân Sách AI')).toBeInTheDocument();
    expect(screen.getByText('Cân đối thông minh (50/30/20)')).toBeInTheDocument();
    expect(screen.getByText('Thắt chặt tiết kiệm')).toBeInTheDocument();

    // Confirm generation
    const confirmBtn = screen.getByRole('button', { name: /Xác Nhận & Sinh Gợi Ý Ngân Sách/i });
    await user.click(confirmBtn);

    await waitFor(() => {
      expect(screen.getByText('✨ Hạn Mức Đề Xuất Từ AI')).toBeInTheDocument();
      expect(screen.getByText('Dựa trên mức chi trung bình gần đây.')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Xác Nhận Áp Dụng Ngân Sách Này/i })).toBeInTheDocument();
    });

    const amountInput = screen.getByRole('textbox', {
      name: 'Hạn mức đề xuất cho Ăn uống',
    });
    expect(amountInput).toHaveValue('2.500.000');
    await user.clear(amountInput);
    await user.type(amountInput, '1750000');
    expect(amountInput).toHaveValue('1.750.000');
    expect(screen.queryByText('VNĐ')).not.toBeInTheDocument();

    const editAmountButton = screen.getByRole('button', {
      name: 'Sửa hạn mức cho Ăn uống',
    });
    await user.click(editAmountButton);
    expect(amountInput).toHaveFocus();

    const categoryIcon = document.querySelector('.ai-card-category-info .category-icon img');
    expect(categoryIcon).toHaveAttribute('src', expect.stringContaining('food'));

    await user.click(screen.getByRole('button', { name: /Xác Nhận Áp Dụng Ngân Sách Này/i }));
    await waitFor(() => {
      expect(applyBudgetRecommendations).toHaveBeenCalledWith({
        target_month: 8,
        target_year: 2026,
        recommendations: [{ category_id: 1, amount: 1750000 }],
      });
    });
  });

  it('opens the manual budget modal from the AI suggestion tab', async () => {
    const user = userEvent.setup();
    renderPage();

    const aiTab = screen.getByRole('tab', { name: /AI Gợi Ý Ngân Sách/i });
    await user.click(aiTab);
    expect(aiTab).toHaveAttribute('aria-selected', 'true');

    await user.click(screen.getByRole('button', { name: /Thiết lập ngân sách/i }));

    expect(screen.getByRole('dialog', { name: 'Thiết lập ngân sách mới' })).toBeInTheDocument();
    expect(aiTab).toHaveAttribute('aria-selected', 'true');
  });
});
