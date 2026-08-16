import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getTransactions, getTransactionSummary } from '../api/transactionApi';
import { getBudgetAlerts } from '../api/budgetApi';
import TransactionCard from '../components/TransactionCard';
import CategoryIcon from '../components/CategoryIcon';

const Dashboard = () => {
  const [summary, setSummary] = useState({
    available_balance: 0,
    all_time_income: 0,
    all_time_expense: 0,
    month_income: 0,
    month_expense: 0,
    month_net: 0,
  });
  const [recentTransactions, setRecentTransactions] = useState([]);
  const [budgetAlerts, setBudgetAlerts] = useState({ count: 0, items: [] });
  const [loading, setLoading] = useState(true);
  const [toastMessage, setToastMessage] = useState('');

  // Auto-dismiss toast
  useEffect(() => {
    if (!toastMessage) return;
    const timer = setTimeout(() => setToastMessage(''), 3500);
    return () => clearTimeout(timer);
  }, [toastMessage]);

  const fetchDashboardData = async (signal) => {
    setLoading(true);
    try {
      const [sumData, txnData, alertData] = await Promise.all([
        getTransactionSummary(signal),
        getTransactions({ page: 1, page_size: 5 }, signal),
        getBudgetAlerts({}, signal).catch(() => ({ count: 0, items: [] })),
      ]);

      if (sumData) {
        setSummary({
          available_balance: Number(sumData.available_balance || 0),
          all_time_income: Number(sumData.all_time_income || 0),
          all_time_expense: Number(sumData.all_time_expense || 0),
          month_income: Number(sumData.month_income || 0),
          month_expense: Number(sumData.month_expense || 0),
          month_net: Number(sumData.month_net || 0),
        });
      }

      setRecentTransactions(txnData?.items || []);
      if (alertData) {
        setBudgetAlerts({
          count: alertData.count || 0,
          items: alertData.items || [],
        });
      }
    } catch (err) {
      if (err.code !== 'ERR_CANCELED') {
        console.error('Failed to fetch dashboard data', err);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const controller = new AbortController();
    fetchDashboardData(controller.signal);
    return () => controller.abort();
  }, []);

  const formatMoney = (amount) => {
    return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(amount);
  };

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Chào buổi sáng ☀️';
    if (hour < 18) return 'Chào buổi chiều 🌤️';
    return 'Chào buổi tối 🌙';
  };

  const totalBalance = summary.available_balance;
  const totalActivity = summary.month_income + summary.month_expense;
  const incomePercent = totalActivity > 0 ? (summary.month_income / totalActivity) * 100 : 50;
  const expensePercent = totalActivity > 0 ? (summary.month_expense / totalActivity) * 100 : 50;

  return (
    <div className="dashboard-page fade-in">
      {toastMessage && (
        <div className="dashboard-toast-banner" role="status">
          <span className="toast-icon">✨</span>
          <span className="toast-text">{toastMessage}</span>
          <button
            type="button"
            className="toast-dismiss-btn"
            onClick={() => setToastMessage('')}
            aria-label="Đóng thông báo"
          >
            ✕
          </button>
        </div>
      )}

      <div className="dashboard-hero">
        <div className="dashboard-hero-content">
          <h1>{getGreeting()}</h1>
          <p className="hero-quote">"Một đồng tiết kiệm được là một đồng kiếm được." - Benjamin Franklin</p>
        </div>
        <Link to="/transactions" state={{ openAddModal: true }} className="btn-primary dashboard-add-btn">
          <span className="btn-icon">⚡</span>
          Thêm giao dịch ngay
        </Link>
      </div>
      
      {loading ? (
        <div className="dashboard-loading">
          <div className="spinner" />
          <p>Đang tải dữ liệu tổng quan...</p>
        </div>
      ) : (
        <>
          {budgetAlerts.count > 0 && (
            <div className="dashboard-budget-alert-banner" role="alert">
              <div className="alert-banner-header">
                <div className="alert-banner-title">
                  <span className="alert-banner-icon">⚠️</span>
                  <div>
                    <strong>Cảnh báo ngân sách ({budgetAlerts.count} danh mục)</strong>
                    <p>Có danh mục chi tiêu đã chạm ngưỡng cảnh báo (≥ 80%) hoặc vượt hạn mức trong tháng này.</p>
                  </div>
                </div>
                <Link to="/budgets" className="alert-banner-btn">
                  <span>Quản lý ngân sách</span>
                  <span className="btn-arrow">→</span>
                </Link>
              </div>

              <div className="alert-banner-items">
                {budgetAlerts.items.map((item) => (
                  <div
                    key={item.id}
                    className={`alert-mini-card ${item.status === 'exceeded' ? 'mini-exceeded' : 'mini-warning'}`}
                  >
                    <CategoryIcon icon={item.category_icon || 'other'} color={item.category_color || '#D69A23'} />
                    <div className="mini-card-text">
                      <span className="mini-name">{item.category_name}</span>
                      <span className="mini-status">
                        {item.status === 'exceeded' ? `Vượt ${item.percentage_used}%` : `Cảnh báo ${item.percentage_used}%`}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="dashboard-metrics-grid">
            <div className="metric-card balance-card">
              <div className="metric-content">
                <span className="metric-title">Số dư khả dụng</span>
                <h2 className={`metric-value ${totalBalance < 0 ? 'text-error' : ''}`}>
                  {formatMoney(totalBalance)}
                </h2>
                <div className="metric-subtext">
                  <span>Chênh lệch tháng này: <strong className={summary.month_net >= 0 ? 'text-success' : 'text-error'}>{summary.month_net >= 0 ? '+' : ''}{formatMoney(summary.month_net)}</strong></span>
                </div>
              </div>
            </div>
            
            <div className="metric-card income-card">
              <div className="metric-content">
                <span className="metric-title">Thu nhập (Tháng này)</span>
                <h2 className="metric-value text-success">{formatMoney(summary.month_income)}</h2>
                <div className="metric-subtext">
                  <span>Toàn thời gian: <strong>{formatMoney(summary.all_time_income)}</strong></span>
                </div>
              </div>
            </div>
            
            <div className="metric-card expense-card">
              <div className="metric-content">
                <span className="metric-title">Chi tiêu (Tháng này)</span>
                <h2 className="metric-value text-error">{formatMoney(summary.month_expense)}</h2>
                <div className="metric-subtext">
                  <span>Toàn thời gian: <strong>{formatMoney(summary.all_time_expense)}</strong></span>
                </div>
              </div>
            </div>
          </div>

          <div className="dashboard-progress-section">
            <div className="progress-header">
              <h3>Tỷ trọng Thu / Chi</h3>
              <span className="progress-total">Tổng lưu chuyển: {formatMoney(totalActivity)}</span>
            </div>
            <div className="progress-bar-container">
              <div className="progress-bar-income" style={{ width: `${incomePercent}%` }}>
                {incomePercent > 10 && <span>{incomePercent.toFixed(1)}%</span>}
              </div>
              <div className="progress-bar-expense" style={{ width: `${expensePercent}%` }}>
                {expensePercent > 10 && <span>{expensePercent.toFixed(1)}%</span>}
              </div>
            </div>
            <div className="progress-legend">
              <span className="legend-item"><span className="dot dot-income"></span>Thu nhập</span>
              <span className="legend-item"><span className="dot dot-expense"></span>Chi tiêu</span>
            </div>
          </div>
          
          <div className="dashboard-recent-section">
            <div className="dashboard-recent-header">
              <div className="recent-title-group">
                <div className="recent-badge-icon">⚡</div>
                <div>
                  <h2>Giao dịch gần đây</h2>
                  <p className="recent-subtitle">5 giao dịch phát sinh mới nhất trong tài khoản</p>
                </div>
              </div>
              <Link to="/transactions" className="btn-recent-view-all">
                Xem tất cả giao dịch →
              </Link>
            </div>
            
            <div className="dashboard-recent-content">
              {recentTransactions.length > 0 ? (
                <div className="recent-txn-grid">
                  {recentTransactions.map((txn) => (
                    <TransactionCard 
                      key={txn.id} 
                      transaction={txn}
                      hideActions={true}
                    />
                  ))}
                </div>
              ) : (
                <div className="recent-empty-card">
                  <div className="recent-empty-icon-wrap">
                    <span>📜</span>
                  </div>
                  <h3>Chưa có giao dịch phát sinh</h3>
                  <p>Bắt đầu ghi chép các khoản chi tiêu hoặc thu nhập đầu tiên để theo dõi dòng tiền thông minh.</p>
                  <Link to="/transactions" state={{ openAddModal: true }} className="btn-primary btn-recent-add">
                    <span className="btn-icon">⚡</span>
                    Thêm giao dịch đầu tiên
                  </Link>
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default Dashboard;

