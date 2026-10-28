import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import TransactionCard from './TransactionCard';

describe('TransactionCard saving allocation display and timestamp formatting', () => {
  it('renders allocated saving goal name, amount, and formatted date-time for income transaction', () => {
    const txn = {
      id: 101,
      amount: '10000000.00',
      type: 'income',
      category_id: 1,
      category: { id: 1, name: 'Lương', icon: 'salary', color: '#10b981', is_active: true },
      transaction_date: '2026-10-28',
      created_at: '2026-10-28T06:29:00Z',
      description: 'Lương tháng 10',
      payment_method: 'bank_transfer',
      is_deleted: false,
      saving_goal_id: 5,
      saving_goal_name: 'Mua laptop',
      saving_goal_amount: '2000000.00',
      movement_type: null,
    };

    render(
      <MemoryRouter>
        <TransactionCard transaction={txn} />
      </MemoryRouter>
    );

    // Verify saving goal badge with allocation amount
    expect(screen.getByText(/Mua laptop/i)).toBeInTheDocument();
    expect(screen.getByText(/Trích 2\.000\.000/i)).toBeInTheDocument();

    // Verify main amount and net available amount into wallet
    expect(screen.getByText(/\+10\.000\.000/i)).toBeInTheDocument();
    expect(screen.getByText(/Vào ví: \+8\.000\.000/i)).toBeInTheDocument();

    // Verify date and local time (+7 hours Vietnam time -> 13:29)
    expect(screen.getByText(/28\/10\/2026 13:29/i)).toBeInTheDocument();
  });

  it('renders transfer transaction with goal name, link to saving goals, and formatted time', () => {
    const txn = {
      id: 1000000001,
      amount: '500000.00',
      type: 'transfer',
      category_id: 0,
      category: { id: 0, name: 'Hũ tiết kiệm', icon: 'savings', color: '#6366f1', is_active: true },
      transaction_date: '2026-10-28',
      created_at: '2026-10-28T05:48:00Z',
      description: 'Nạp vào hũ: Mua laptop',
      payment_method: 'cash',
      is_deleted: false,
      saving_goal_id: 5,
      saving_goal_name: 'Mua laptop',
      saving_goal_amount: '500000.00',
      movement_type: 'deposit',
    };

    render(
      <MemoryRouter>
        <TransactionCard transaction={txn} />
      </MemoryRouter>
    );

    expect(screen.getByText('Tiết kiệm')).toBeInTheDocument();
    expect(screen.getByText('🎯 Xem hũ')).toBeInTheDocument();
    expect(screen.getByText(/−500\.000/i)).toBeInTheDocument();
    expect(screen.getByText(/28\/10\/2026 12:48/i)).toBeInTheDocument();
  });
});
