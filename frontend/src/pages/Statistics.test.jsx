import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import Statistics from './Statistics';
import * as categoryApi from '../api/categoryApi';
import * as aiApi from '../api/aiApi';

vi.mock('../api/categoryApi', () => ({
  getCategoryStatistics: vi.fn(),
}));

vi.mock('../api/aiApi', () => ({
  getMonthlyTrend: vi.fn(),
  generateMonthlyReport: vi.fn(),
}));

describe('Statistics Page & AI Trends', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    categoryApi.getCategoryStatistics.mockResolvedValue({
      items: [
        {
          id: 1,
          name: 'Ăn uống',
          type: 'expense',
          icon: 'utensils',
          color: '#FF5722',
          total: 2500000,
          percentage: 50.0,
          transaction_count: 5,
        },
      ],
      total_expense: 5000000,
    });

    aiApi.getMonthlyTrend.mockResolvedValue({
      months_count: 6,
      average_monthly_income: 15000000,
      average_monthly_expense: 8000000,
      average_monthly_savings: 7000000,
      average_savings_rate: 46.7,
      items: [
        {
          month: '2026-03',
          year: 2026,
          month_num: 3,
          label: 'Thg 03/2026',
          total_income: 15000000,
          total_expense: 8000000,
          net_savings: 7000000,
          savings_rate: 46.7,
          top_category: 'Ăn uống',
          top_category_amount: 3000000,
        },
      ],
    });

    aiApi.generateMonthlyReport.mockResolvedValue({
      month: '2026-08',
      financial_health_score: 85,
      health_status: 'Xuất sắc',
      total_income: 20000000,
      total_expense: 10000000,
      net_savings: 10000000,
      savings_rate: 50.0,
      overview: 'Tài chính tháng này rất tốt.',
      trend_analysis: 'Chi tiêu ăn uống kiểm soát tốt.',
      top_categories: [{ name: 'Ăn uống', amount: 3000000, percentage: 30.0, color: '#FF5722' }],
      adjustments: ['Duy trì tỷ lệ tiết kiệm', 'Đầu tư thêm quỹ dự phòng', 'Kiểm soát mua sắm'],
      conclusion: 'Tiếp tục phát huy!',
      raw_markdown: '# Báo cáo tháng 8',
      generated_at: '2026-08-17T12:00:00Z',
    });
  });

  it('renders 5 unified dashboard tabs and defaults to monthly view', async () => {
    render(<Statistics />);

    expect(screen.getByRole('tab', { name: /Tổng quan/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /Xu hướng/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /Báo Cáo AI/i })).toBeInTheDocument();
  });

  it('switches to Trend tab and renders intelligent trends dashboard', async () => {
    render(<Statistics />);

    const trendTab = screen.getByRole('tab', { name: /Xu hướng/i });
    fireEvent.click(trendTab);

    await waitFor(() => {
      expect(aiApi.getMonthlyTrend).toHaveBeenCalledWith(3, expect.any(AbortSignal));
    });

    await waitFor(() => {
      expect(screen.getByText('Trợ Lý Tài Chính Thông Minh')).toBeInTheDocument();
      expect(screen.getByText('Thu nhập TB')).toBeInTheDocument();
      expect(screen.getByText('Chi tiêu TB')).toBeInTheDocument();
      expect(screen.getByText('Dự báo chi tháng')).toBeInTheDocument();
      expect(
        screen.getByText('Biểu Đồ Biến Động Dòng Tiền 3 Tháng')
      ).toBeInTheDocument();
    });

    const incomeInfoButton = screen.getByRole('button', {
      name: 'Xem giải thích Thu nhập trung bình',
    });
    fireEvent.click(incomeInfoButton);
    expect(screen.getByRole('tooltip')).toHaveTextContent(
      'Tổng thu nhập bình quân mỗi tháng trong chu kỳ 3 tháng gần nhất.'
    );
    expect(incomeInfoButton).toHaveAttribute('aria-expanded', 'true');

    fireEvent.click(incomeInfoButton);
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();

    // Toggle details button
    const toggleBtn = screen.getByRole('button', { name: /Xem bảng số liệu chi tiết từng tháng/i });
    fireEvent.click(toggleBtn);
    expect(screen.getByText('Thặng Dư / Tiết Kiệm')).toBeInTheDocument();
  });

  it('switches to AI Report tab, shows options, and generates report on confirmation', async () => {
    render(<Statistics />);

    const aiTab = screen.getByRole('tab', { name: /Báo Cáo AI/i });
    fireEvent.click(aiTab);

    // Shows options config card first
    expect(screen.getByText('Tùy Chọn Sinh Báo Cáo Tài Chính AI')).toBeInTheDocument();
    expect(screen.getByText('Phân tích toàn diện')).toBeInTheDocument();
    expect(screen.getByText('Tối ưu tiết kiệm')).toBeInTheDocument();

    // Click confirm generate button
    const confirmBtn = screen.getByRole('button', { name: /Xác Nhận & Sinh Báo Cáo AI/i });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(aiApi.generateMonthlyReport).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(screen.getByText('Xuất sắc')).toBeInTheDocument();
      expect(screen.getByText('Tài chính tháng này rất tốt.')).toBeInTheDocument();
      expect(screen.getByText('1. Tóm Tắt Tổng Quan')).toBeInTheDocument();
    });
  });
});
