import React, { useState, useEffect, useContext, useRef } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { getCategories } from '../api/categoryApi';
import { getTransactions } from '../api/transactionApi';
import TransactionCard from '../components/TransactionCard';
import InitialBalanceModal from '../components/InitialBalanceModal';
import { AuthContext } from '../context/auth-context';

const Dashboard = () => {
  const { user, setUser } = useContext(AuthContext);
  const [metrics, setMetrics] = useState({ income: 0, expense: 0 });
  const [recentTransactions, setRecentTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isBalanceModalOpen, setIsBalanceModalOpen] = useState(false);
  const [toastMessage, setToastMessage] = useState('');
  const balanceCardRef = useRef(null);
  const location = useLocation();
  const navigate = useNavigate();

  // Auto-dismiss toast
  useEffect(() => {
    if (!toastMessage) return;
    const timer = setTimeout(() => setToastMessage(''), 3500);
    return () => clearTimeout(timer);
  }, [toastMessage]);

  // Auto-open initial balance modal for new users or upon registration
  useEffect(() => {
    if (!user) return;
    const storageKey = `initial_balance_prompted_${user.id}`;
    const hasBeenPrompted = localStorage.getItem(storageKey);
    const isExplicitlyRequested = location.state?.openInitialBalance;

    if (isExplicitlyRequested || (!hasBeenPrompted && Number(user.initial_balance || 0) === 0)) {
      setIsBalanceModalOpen(true);
      localStorage.setItem(storageKey, 'true');
      if (location.state?.openInitialBalance) {
        navigate(location.pathname, { replace: true, state: {} });
      }
    }
  }, [user, location, navigate]);

  useEffect(() => {
    let cancelled = false;
    
    const fetchDashboardData = async () => {
      setLoading(true);
      try {
        const [catData, txnData] = await Promise.all([
          getCategories({ status: 'all' }),
          getTransactions({ page: 1, page_size: 5 })
        ]);
        
        if (cancelled) return;

        let totalIncome = 0;
        let totalExpense = 0;
        
        if (catData?.items) {
          catData.items.forEach(c => {
            totalIncome += Number(c.income_amount || 0);
            totalExpense += Number(c.expense_amount || 0);
          });
        }
        
        setMetrics({
          income: totalIncome,
          expense: totalExpense,
        });
        
        setRecentTransactions(txnData?.items || []);
      } catch (err) {
        console.error('Failed to fetch dashboard data', err);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    
    fetchDashboardData();
    return () => { cancelled = true; };
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

  const initialBalance = Number(user?.initial_balance || 0);
  const totalBalance = initialBalance + metrics.income - metrics.expense;
  const totalActivity = metrics.income + metrics.expense;
  const incomePercent = totalActivity > 0 ? (metrics.income / totalActivity) * 100 : 50;
  const expensePercent = totalActivity > 0 ? (metrics.expense / totalActivity) * 100 : 50;

  const handleCloseModal = () => {
    setIsBalanceModalOpen(false);
    setTimeout(() => {
      balanceCardRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }, 60);
  };

  const handleBalanceUpdated = (updatedUser) => {
    if (setUser) setUser(updatedUser);
    setToastMessage('Đã cập nhật số dư ban đầu thành công! 💰');
    setTimeout(() => {
      balanceCardRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }, 60);
  };

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
          <div className="dashboard-metrics-grid">
            <div className="metric-card balance-card" ref={balanceCardRef}>
              <div className="metric-content">
                <div className="metric-title-row">
                  <span className="metric-title">Số dư khả dụng</span>
                  <button
                    type="button"
                    className="btn-edit-initial-balance"
                    onClick={() => setIsBalanceModalOpen(true)}
                    title="Chỉnh sửa số dư ban đầu"
                  >
                    ✏️ {initialBalance > 0 ? 'Sửa số dư gốc' : 'Cài số dư gốc'}
                  </button>
                </div>
                <h2 className={`metric-value ${totalBalance < 0 ? 'text-error' : ''}`}>
                  {formatMoney(totalBalance)}
                </h2>
                <div className="metric-subtext">
                  {initialBalance > 0 ? (
                    <span>Đã bao gồm <strong>{formatMoney(initialBalance)}</strong> có sẵn</span>
                  ) : (
                    <button
                      type="button"
                      className="subtext-prompt-btn"
                      onClick={() => setIsBalanceModalOpen(true)}
                    >
                      + Khai báo số dư có sẵn trong ví
                    </button>
                  )}
                </div>
              </div>
            </div>
            
            <div className="metric-card income-card">
              <div className="metric-content">
                <span className="metric-title">Tổng thu (Tất cả)</span>
                <h2 className="metric-value text-success">{formatMoney(metrics.income)}</h2>
              </div>
            </div>
            
            <div className="metric-card expense-card">
              <div className="metric-content">
                <span className="metric-title">Tổng chi (Tất cả)</span>
                <h2 className="metric-value text-error">{formatMoney(metrics.expense)}</h2>
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
          
          <div className="dashboard-recent">
            <div className="recent-header">
              <h2>Giao dịch gần đây</h2>
              <Link to="/transactions" className="btn-ghost">Xem tất cả →</Link>
            </div>
            
            <div className="recent-list">
              {recentTransactions.length > 0 ? (
                recentTransactions.map(txn => (
                  <TransactionCard 
                    key={txn.id} 
                    transaction={txn}
                    hideActions={true}
                  />
                ))
              ) : (
                <div className="empty-state">
                  <p>Chưa có giao dịch nào.</p>
                  <Link to="/transactions" state={{ openAddModal: true }} className="btn-secondary">
                    Thêm giao dịch đầu tiên
                  </Link>
                </div>
              )}
            </div>
          </div>
        </>
      )}

      {/* Initial Balance Modal */}
      <InitialBalanceModal
        isOpen={isBalanceModalOpen}
        onClose={handleCloseModal}
        currentInitialBalance={user?.initial_balance}
        onUpdated={handleBalanceUpdated}
      />
    </div>
  );
};

export default Dashboard;
