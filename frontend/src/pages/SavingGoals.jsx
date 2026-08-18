import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { createPortal } from 'react-dom';
import {
  getSavingGoals,
  getSavingGoalById,
  createSavingGoal,
  updateSavingGoal,
  deleteSavingGoal,
  contributeToGoal,
  withdrawFromGoal,
} from '../api/savingGoalApi';
import { getTransactionSummary } from '../api/transactionApi';
import ConfirmModal from '../components/ConfirmModal';
import CustomDatePicker from '../components/CustomDatePicker';
import CustomSelect from '../components/CustomSelect';
import WarningPopup from '../components/WarningPopup';
import { useModalLock } from '../hooks/useModalLock';

const formatMoney = (amount) => {
  return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(amount || 0);
};

const formatDate = (dateStr) => {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return dateStr;
  return d.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' });
};

const formatDateTime = (dtStr) => {
  if (!dtStr) return '';
  const d = new Date(dtStr);
  if (isNaN(d.getTime())) return dtStr;
  return `${d.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' })} ${d.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })}`;
};

const createRequestKey = () => {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
};

const apiMessage = (error) => {
  const detail = error?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map((i) => i.msg).filter(Boolean).join(' ');
  if (!error?.response) {
    return navigator.onLine
      ? 'Không thể kết nối đến máy chủ. Vui lòng kiểm tra lại kết nối mạng.'
      : 'Thiết bị đang mất kết nối mạng.';
  }
  if (error.response.status >= 500) return 'Máy chủ gặp lỗi khi xử lý. Vui lòng thử lại sau.';
  return `Yêu cầu thất bại (HTTP ${error.response.status}).`;
};

const STATUS_LABELS = {
  active: { label: 'Đang tích lũy', badgeClass: 'goal-status-active', icon: '⚡' },
  completed: { label: 'Đã hoàn thành', badgeClass: 'goal-status-completed', icon: '🎉' },
  cancelled: { label: 'Đã tạm dừng', badgeClass: 'goal-status-cancelled', icon: '⏸' },
};

const SORT_OPTIONS = [
  { value: 'created_desc', label: 'Mới tạo nhất' },
  { value: 'percent_desc', label: 'Tiến độ cao nhất' },
  { value: 'percent_asc', label: 'Tiến độ thấp nhất' },
  { value: 'deadline_asc', label: 'Hạn chót gần nhất' },
  { value: 'target_desc', label: 'Mục tiêu lớn nhất' },
];

const SavingGoals = () => {
  const [data, setData] = useState({
    total_target_amount: 0,
    total_current_amount: 0,
    total_goals_count: 0,
    active_goals_count: 0,
    completed_goals_count: 0,
    items: [],
  });

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [toastMessage, setToastMessage] = useState('');
  const [availableBalance, setAvailableBalance] = useState(0);

  // Filters & Sorting
  const [statusFilter, setStatusFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState('created_desc');

  // Modals state
  const [goalModalOpen, setGoalModalOpen] = useState(false);
  const [editingGoal, setEditingGoal] = useState(null);
  const [depositModalOpen, setDepositModalOpen] = useState(false);
  const [activeDepositGoal, setActiveDepositGoal] = useState(null);
  const [withdrawModalOpen, setWithdrawModalOpen] = useState(false);
  const [activeWithdrawGoal, setActiveWithdrawGoal] = useState(null);
  const [historyModalOpen, setHistoryModalOpen] = useState(null);
  const [goalToDelete, setGoalToDelete] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [warningPopup, setWarningPopup] = useState({ message: '', focusId: '' });

  // Goal Form state
  const [formName, setFormName] = useState('');
  const [formTargetAmount, setFormTargetAmount] = useState('');
  const [formDeadline, setFormDeadline] = useState('');
  const [formInitialDeposit, setFormInitialDeposit] = useState('');
  const [formStatus, setFormStatus] = useState('active');
  const [formErrors, setFormErrors] = useState({});

  // Deposit Form state
  const [depositAmount, setDepositAmount] = useState('');
  const [depositNote, setDepositNote] = useState('');
  const [depositError, setDepositError] = useState('');

  // Withdrawal Form state
  const [withdrawAmount, setWithdrawAmount] = useState('');
  const [withdrawNote, setWithdrawNote] = useState('');
  const [withdrawError, setWithdrawError] = useState('');
  const [withdrawIdempotencyKey, setWithdrawIdempotencyKey] = useState('');

  const showWarning = useCallback((message, focusId = '') => {
    setWarningPopup({ message, focusId });
  }, []);

  const closeWarning = useCallback(() => {
    const focusId = warningPopup.focusId;
    setWarningPopup({ message: '', focusId: '' });
    window.requestAnimationFrame(() => {
      if (focusId) document.getElementById(focusId)?.focus();
    });
  }, [warningPopup.focusId]);

  // Auto dismiss toast
  useEffect(() => {
    if (!toastMessage) return;
    const timer = setTimeout(() => setToastMessage(''), 3500);
    return () => clearTimeout(timer);
  }, [toastMessage]);

  // Fetch Goals & Balance
  const fetchGoals = useCallback(async (isMounted = true, isInitial = false) => {
    try {
      if (isInitial) {
        setLoading(true);
      }
      setError('');
      const [goalsRes, summaryRes] = await Promise.allSettled([
        getSavingGoals(),
        getTransactionSummary(),
      ]);

      if (isMounted) {
        if (goalsRes.status === 'fulfilled') {
          setData(goalsRes.value);
        } else {
          setError(apiMessage(goalsRes.reason));
        }
        if (summaryRes.status === 'fulfilled') {
          setAvailableBalance(Number(summaryRes.value?.available_balance || 0));
        }
      }
    } catch (err) {
      if (isMounted) {
        setError(apiMessage(err));
      }
    } finally {
      if (isMounted) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    let isMounted = true;
    fetchGoals(isMounted, true);
    return () => {
      isMounted = false;
    };
  }, [fetchGoals]);

  // Handle Goal Modal open/close
  const openCreateModal = () => {
    setEditingGoal(null);
    setFormName('');
    setFormTargetAmount('');
    setFormDeadline('');
    setFormInitialDeposit('');
    setFormStatus('active');
    setFormErrors({});
    setWarningPopup({ message: '', focusId: '' });
    setGoalModalOpen(true);
  };

  const openEditModal = (goal) => {
    if (goal.status === 'completed' || goal.progress_percentage >= 100) {
      setToastMessage('Mục tiêu đã hoàn thành không thể chỉnh sửa.');
      setTimeout(() => setToastMessage(''), 3000);
      return;
    }
    setEditingGoal(goal);
    setFormName(goal.name || '');
    setFormTargetAmount(String(goal.target_amount || ''));
    setFormDeadline(goal.deadline ? goal.deadline.substring(0, 10) : '');
    setFormInitialDeposit('');
    setFormStatus(goal.status || 'active');
    setFormErrors({});
    setWarningPopup({ message: '', focusId: '' });
    setGoalModalOpen(true);
  };

  const closeGoalModal = useCallback(() => {
    if (submitting) return;
    setGoalModalOpen(false);
    setEditingGoal(null);
  }, [submitting]);

  useModalLock(goalModalOpen, closeGoalModal);

  // Handle Deposit Modal open/close
  const openDepositModal = (goal) => {
    setActiveDepositGoal(goal);
    setDepositAmount('');
    setDepositNote('');
    setDepositError('');
    setWarningPopup({ message: '', focusId: '' });
    setDepositModalOpen(true);
    // Refresh balance in background
    getTransactionSummary()
      .then((res) => setAvailableBalance(Number(res?.available_balance || 0)))
      .catch(() => {});
  };

  const closeDepositModal = useCallback(() => {
    if (submitting) return;
    setDepositModalOpen(false);
    setActiveDepositGoal(null);
  }, [submitting]);

  useModalLock(depositModalOpen, closeDepositModal);

  // Handle Withdrawal Modal open/close
  const openWithdrawModal = (goal) => {
    setActiveWithdrawGoal(goal);
    setWithdrawAmount('');
    setWithdrawNote('');
    setWithdrawError('');
    setWithdrawIdempotencyKey(createRequestKey());
    setWarningPopup({ message: '', focusId: '' });
    setWithdrawModalOpen(true);
    getTransactionSummary()
      .then((res) => setAvailableBalance(Number(res?.available_balance || 0)))
      .catch(() => {});
  };

  const closeWithdrawModal = useCallback(() => {
    if (submitting) return;
    setWithdrawModalOpen(false);
    setActiveWithdrawGoal(null);
  }, [submitting]);

  useModalLock(withdrawModalOpen, closeWithdrawModal);

  // Handle History Modal open/close
  const openHistoryModal = async (goal) => {
    try {
      const fullGoal = await getSavingGoalById(goal.id);
      setHistoryModalOpen(fullGoal);
    } catch {
      setHistoryModalOpen(goal);
    }
  };

  const closeHistoryModal = useCallback(() => {
    setHistoryModalOpen(null);
  }, []);

  useModalLock(!!historyModalOpen, closeHistoryModal);

  // Form Validation
  const validateGoalForm = () => {
    const errors = {};
    if (!formName.trim()) {
      errors.name = 'Vui lòng nhập tên mục tiêu tiết kiệm.';
    } else if (formName.trim().length > 100) {
      errors.name = 'Tên mục tiêu không được vượt quá 100 ký tự.';
    }

    const targetVal = parseFloat(formTargetAmount);
    if (!formTargetAmount || isNaN(targetVal) || targetVal <= 0) {
      errors.target_amount = 'Số tiền mục tiêu phải lớn hơn 0.';
    }

    if (formInitialDeposit) {
      const initVal = parseFloat(formInitialDeposit);
      if (isNaN(initVal) || initVal < 0) {
        errors.initial_deposit = 'Số tiền nạp ban đầu không được âm.';
      } else if (!isNaN(targetVal) && initVal > targetVal) {
        errors.initial_deposit = 'Số tiền nạp ban đầu không thể lớn hơn số tiền mục tiêu.';
      } else if (!editingGoal && initVal > availableBalance) {
        errors.initial_deposit = `Số tiền nạp ban đầu vượt quá số dư khả dụng hiện có (${formatMoney(availableBalance)}).`;
      }
    }

    if (formDeadline) {
      const selected = new Date(formDeadline);
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      if (isNaN(selected.getTime())) {
        errors.deadline = 'Ngày hạn chót không hợp lệ.';
      } else if (!editingGoal && selected < today) {
        errors.deadline = 'Hạn chót phải từ ngày hôm nay trở đi.';
      }
    }

    setFormErrors(errors);
    const firstErrorKey = Object.keys(errors)[0];
    if (firstErrorKey) {
      const focusIds = {
        name: 'goal-name',
        target_amount: 'goal-target-amount',
        initial_deposit: 'goal-initial-deposit',
        deadline: 'goal-deadline',
      };
      showWarning(errors[firstErrorKey], focusIds[firstErrorKey]);
      return false;
    }
    return true;
  };

  // Submit Create / Edit Goal
  const handleSaveGoal = async (e) => {
    e.preventDefault();
    if (!validateGoalForm()) return;

    setSubmitting(true);

    try {
      if (editingGoal) {
        const payload = {
          name: formName.trim(),
          target_amount: parseFloat(formTargetAmount),
          deadline: formDeadline || null,
          status: formStatus,
        };
        const updated = await updateSavingGoal(editingGoal.id, payload);
        setToastMessage(`Đã cập nhật mục tiêu "${updated.name}" thành công.`);
      } else {
        const payload = {
          name: formName.trim(),
          target_amount: parseFloat(formTargetAmount),
          deadline: formDeadline || null,
          initial_deposit: formInitialDeposit ? parseFloat(formInitialDeposit) : 0,
        };
        const created = await createSavingGoal(payload);
        setToastMessage(`Đã tạo mục tiêu "${created.name}" thành công.`);
      }

      closeGoalModal();
      await fetchGoals();
    } catch (err) {
      showWarning(apiMessage(err), editingGoal ? 'goal-name' : 'goal-initial-deposit');
    } finally {
      setSubmitting(false);
    }
  };

  // Submit Deposit
  const handleDepositSubmit = async (e) => {
    e.preventDefault();
    const amountVal = parseFloat(depositAmount);
    if (!depositAmount || isNaN(amountVal) || amountVal <= 0) {
      const message = 'Vui lòng nhập số tiền nạp hợp lệ lớn hơn 0.';
      setDepositError(message);
      showWarning(message, 'deposit-amount');
      return;
    }

    if (amountVal > availableBalance) {
      const message = `Số tiền nạp (${formatMoney(amountVal)}) vượt quá số dư khả dụng hiện có (${formatMoney(availableBalance)}).`;
      setDepositError(message);
      showWarning(message, 'deposit-amount');
      return;
    }

    const remainingNeeded = Number(activeDepositGoal?.remaining_amount || 0);
    if (amountVal > remainingNeeded) {
      const message = `Số tiền nạp (${formatMoney(amountVal)}) vượt quá số tiền còn thiếu của mục tiêu (${formatMoney(remainingNeeded)}).`;
      setDepositError(message);
      showWarning(message, 'deposit-amount');
      return;
    }

    setSubmitting(true);
    setDepositError('');

    try {
      const payload = {
        amount: amountVal,
        note: depositNote.trim() || undefined,
      };
      const updatedGoal = await contributeToGoal(activeDepositGoal.id, payload);
      setToastMessage(
        updatedGoal.status === 'completed'
          ? `🎉 Chúc mừng! Bạn đã hoàn thành mục tiêu "${updatedGoal.name}"!`
          : `Đã nạp ${formatMoney(amountVal)} vào mục tiêu "${updatedGoal.name}".`
      );
      closeDepositModal();
      await fetchGoals();
    } catch (err) {
      const message = apiMessage(err);
      setDepositError(message);
      showWarning(message, 'deposit-amount');
    } finally {
      setSubmitting(false);
    }
  };

  // Submit Withdrawal
  const handleWithdrawSubmit = async (e) => {
    e.preventDefault();
    const amountVal = parseFloat(withdrawAmount);
    if (!withdrawAmount || isNaN(amountVal) || amountVal <= 0) {
      const message = 'Vui lòng nhập số tiền rút hợp lệ lớn hơn 0.';
      setWithdrawError(message);
      showWarning(message, 'withdraw-amount');
      return;
    }

    const currentAmount = Number(activeWithdrawGoal?.current_amount || 0);
    if (amountVal > currentAmount) {
      const message = `Số tiền rút (${formatMoney(amountVal)}) vượt quá số tiền đang tích lũy (${formatMoney(currentAmount)}).`;
      setWithdrawError(message);
      showWarning(message, 'withdraw-amount');
      return;
    }

    setSubmitting(true);
    setWithdrawError('');

    try {
      const payload = {
        amount: amountVal,
        note: withdrawNote.trim() || undefined,
        idempotency_key: withdrawIdempotencyKey,
      };
      const updatedGoal = await withdrawFromGoal(activeWithdrawGoal.id, payload);
      setToastMessage(
        activeWithdrawGoal.status === 'cancelled'
          ? `Đã ghi nhận rút ${formatMoney(amountVal)} từ mục tiêu "${updatedGoal.name}".`
          : `Đã rút ${formatMoney(amountVal)} từ mục tiêu "${updatedGoal.name}" về số dư khả dụng.`
      );
      closeWithdrawModal();
      await fetchGoals();
    } catch (err) {
      const message = apiMessage(err);
      setWithdrawError(message);
      showWarning(message, 'withdraw-amount');
    } finally {
      setSubmitting(false);
    }
  };

  // Handle Delete Confirmation
  const handleDeleteConfirm = async () => {
    if (!goalToDelete) return;
    setSubmitting(true);
    try {
      await deleteSavingGoal(goalToDelete.id);
      setToastMessage(`Đã xóa mục tiêu "${goalToDelete.name}".`);
      setGoalToDelete(null);
      await fetchGoals();
    } catch (err) {
      setError(apiMessage(err));
      setGoalToDelete(null);
    } finally {
      setSubmitting(false);
    }
  };

  // Filter and Sort goals (Instant in-memory filtering with zero flicker)
  const filteredGoals = useMemo(() => {
    let result = [...data.items];

    // Status filter
    if (statusFilter !== 'all') {
      result = result.filter((g) => g.status === statusFilter);
    }

    // Search query
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      result = result.filter((g) => g.name.toLowerCase().includes(q));
    }

    // Sort
    return result.sort((a, b) => {
      if (sortBy === 'created_desc') {
        return new Date(b.created_at) - new Date(a.created_at);
      }
      if (sortBy === 'percent_desc') {
        return (b.progress_percentage || 0) - (a.progress_percentage || 0);
      }
      if (sortBy === 'percent_asc') {
        return (a.progress_percentage || 0) - (b.progress_percentage || 0);
      }
      if (sortBy === 'target_desc') {
        return Number(b.target_amount) - Number(a.target_amount);
      }
      if (sortBy === 'deadline_asc') {
        if (!a.deadline) return 1;
        if (!b.deadline) return -1;
        return new Date(a.deadline) - new Date(b.deadline);
      }
      return new Date(b.created_at) - new Date(a.created_at);
    });
  }, [data.items, statusFilter, searchQuery, sortBy]);

  const overallProgress = useMemo(() => {
    const target = Number(data.total_target_amount) || 0;
    const current = Number(data.total_current_amount) || 0;
    if (target <= 0) return 0;
    return Math.min(100, Math.round((current / target) * 1000) / 10);
  }, [data.total_target_amount, data.total_current_amount]);

  const historyItems = useMemo(() => {
    if (!historyModalOpen) return [];
    const deposits = (historyModalOpen.contributions || []).map((item) => ({
      ...item,
      movementType: 'deposit',
    }));
    const withdrawals = (historyModalOpen.withdrawals || []).map((item) => ({
      ...item,
      movementType: 'withdrawal',
    }));
    return [...deposits, ...withdrawals].sort(
      (a, b) => new Date(b.created_at) - new Date(a.created_at)
    );
  }, [historyModalOpen]);

  return (
    <div className="saving-goals-container">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="toast-notification" role="status" aria-live="polite">
          <span>{toastMessage}</span>
        </div>
      )}

      {/* 1. Hero Header - Clean 2-column layout matching other pages */}
      <section className="budget-hero-section category-hero">
        <div className="budget-hero-info">
          <span className="eyebrow">Quản lý tài chính</span>
          <h1>Mục tiêu tiết kiệm</h1>
          <p>Lên kế hoạch và theo dõi tiến độ tích lũy tài chính cho các mục tiêu tương lai.</p>
        </div>
        <div className="budget-hero-actions">
          <button
            type="button"
            className="btn-primary add-category-button add-budget-hero-btn"
            onClick={openCreateModal}
          >
            <span className="btn-icon">⚡</span>
            Tạo mục tiêu
          </button>
        </div>
      </section>

      {/* Summary KPI Cards (Bento) */}
      <section className="saving-summary-grid" aria-label="Thống kê tổng quan mục tiêu tiết kiệm">
        <div className="saving-summary-card">
          <div className="summary-card-header">
            <span className="summary-icon">🎯</span>
            <span className="summary-title">Tổng tiền mục tiêu</span>
          </div>
          <div className="summary-value">{formatMoney(data.total_target_amount)}</div>
          <div className="summary-subtext">Mục tiêu từ {data.total_goals_count} kế hoạch</div>
        </div>

        <div className="saving-summary-card">
          <div className="summary-card-header">
            <span className="summary-icon">💰</span>
            <span className="summary-title">Đã tích lũy</span>
          </div>
          <div className="summary-value text-emerald">{formatMoney(data.total_current_amount)}</div>
          <div className="summary-subtext">
            Còn thiếu {formatMoney(Math.max(0, Number(data.total_target_amount) - Number(data.total_current_amount)))}
          </div>
        </div>

        <div className="saving-summary-card">
          <div className="summary-card-header">
            <span className="summary-icon">📈</span>
            <span className="summary-title">Tiến độ chung</span>
          </div>
          <div className="summary-value text-amber">{overallProgress}%</div>
          <div className="summary-progress-track">
            <div
              className="summary-progress-bar"
              style={{ width: `${overallProgress}%` }}
              role="progressbar"
              aria-valuenow={overallProgress}
              aria-valuemin="0"
              aria-valuemax="100"
            />
          </div>
        </div>

        <div className="saving-summary-card">
          <div className="summary-card-header">
            <span className="summary-icon">🏆</span>
            <span className="summary-title">Trạng thái</span>
          </div>
          <div className="summary-status-row">
            <span className="status-pill active-pill" title="Đang tích lũy">
              ⚡ {data.active_goals_count} đang chạy
            </span>
            <span className="status-pill completed-pill" title="Đã hoàn thành">
              🎉 {data.completed_goals_count} hoàn thành
            </span>
          </div>
          <div className="summary-subtext">Tổng {data.total_goals_count} mục tiêu</div>
        </div>
      </section>

      {/* Toolbar & Filters */}
      <section className="saving-toolbar" aria-label="Bộ lọc và tìm kiếm">
        <div className="saving-status-tabs" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={statusFilter === 'all'}
            className={`status-tab ${statusFilter === 'all' ? 'active' : ''}`}
            onClick={() => setStatusFilter('all')}
          >
            Tất cả ({data.total_goals_count})
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={statusFilter === 'active'}
            className={`status-tab ${statusFilter === 'active' ? 'active' : ''}`}
            onClick={() => setStatusFilter('active')}
          >
            Đang tích lũy ({data.active_goals_count})
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={statusFilter === 'completed'}
            className={`status-tab ${statusFilter === 'completed' ? 'active' : ''}`}
            onClick={() => setStatusFilter('completed')}
          >
            Đã hoàn thành ({data.completed_goals_count})
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={statusFilter === 'cancelled'}
            className={`status-tab ${statusFilter === 'cancelled' ? 'active' : ''}`}
            onClick={() => setStatusFilter('cancelled')}
          >
            Tạm dừng
          </button>
        </div>

        <div className="saving-search-sort">
          <div className="saving-search-box">
            <span className="search-icon">🔍</span>
            <input
              type="text"
              placeholder="Tìm theo tên mục tiêu..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              aria-label="Tìm kiếm mục tiêu"
            />
            {searchQuery && (
              <button
                type="button"
                className="search-clear-btn"
                onClick={() => setSearchQuery('')}
                aria-label="Xóa từ khóa tìm kiếm"
              >
                ✕
              </button>
            )}
          </div>

          <div className="saving-sort-box">
            <CustomSelect
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              options={SORT_OPTIONS}
            />
          </div>
        </div>
      </section>

      {/* Error state */}
      {error && (
        <div className="saving-error-banner" role="alert">
          <span>⚠️ {error}</span>
          <button type="button" onClick={() => fetchGoals(true, true)}>Thử lại</button>
        </div>
      )}

      {/* Loading Skeleton */}
      {loading && (
        <div className="saving-goals-grid">
          {[1, 2, 3].map((n) => (
            <div key={n} className="saving-goal-card skeleton-card">
              <div className="skeleton-line title" />
              <div className="skeleton-line value" />
              <div className="skeleton-line bar" />
            </div>
          ))}
        </div>
      )}

      {/* Empty State: Total data is empty */}
      {!loading && !error && data.items.length === 0 && (
        <div className="budget-empty-wrapper">
          <div className="budget-empty-card">
            <div className="empty-mascot-circle">🎯</div>
            <h3>Chưa có mục tiêu tiết kiệm nào</h3>
            <p>
              Hãy bắt đầu bằng việc đặt ra mục tiêu tiết kiệm để tích lũy tài chính vững vàng.
            </p>
            <button
              type="button"
              className="btn-primary empty-create-btn"
              onClick={openCreateModal}
            >
              <span className="btn-icon">⚡</span>
              Tạo mục tiêu đầu tiên
            </button>
          </div>
        </div>
      )}

      {/* Empty State: Filter or Search matched 0 items */}
      {!loading && !error && data.items.length > 0 && filteredGoals.length === 0 && (
        <div className="budget-empty-wrapper">
          <div className="budget-empty-card" style={{ padding: '36px 24px' }}>
            <span style={{ fontSize: '2.5rem' }}>🔍</span>
            <h3>Không tìm thấy mục tiêu phù hợp</h3>
            <p>
              Không có mục tiêu nào khớp với bộ lọc hoặc từ khóa tìm kiếm hiện tại.
            </p>
            <button
              type="button"
              className="btn-secondary"
              style={{ marginTop: '8px' }}
              onClick={() => {
                setStatusFilter('all');
                setSearchQuery('');
              }}
            >
              Đặt lại bộ lọc
            </button>
          </div>
        </div>
      )}

      {/* Goals Grid */}
      {!loading && !error && filteredGoals.length > 0 && (
        <section className="saving-goals-grid" aria-label="Danh sách mục tiêu tiết kiệm">
          {filteredGoals.map((goal) => {
            const statusConfig = STATUS_LABELS[goal.status] || STATUS_LABELS.active;
            const isCompleted = goal.status === 'completed' || goal.progress_percentage >= 100;
            const isCancelled = goal.status === 'cancelled';
            const percent = Math.min(100, Math.max(0, goal.progress_percentage || 0));

            return (
              <article
                key={goal.id}
                className={`saving-goal-card ${isCompleted ? 'card-completed' : ''} ${isCancelled ? 'card-cancelled' : ''}`}
              >
                <div className="goal-card-header">
                  <div className="goal-title-wrap">
                    <span className="goal-icon-badge">{isCompleted ? '🏆' : '🎯'}</span>
                    <h3 className="goal-name" title={goal.name}>{goal.name}</h3>
                  </div>
                  <div className="goal-actions-dropdown">
                    {!isCompleted && (
                      <button
                        type="button"
                        className="btn-icon-action"
                        title="Sửa mục tiêu"
                        aria-label={`Sửa ${goal.name}`}
                        onClick={() => openEditModal(goal)}
                      >
                        ✏️
                      </button>
                    )}
                    <button
                      type="button"
                      className="btn-icon-action btn-icon-delete"
                      title="Xóa mục tiêu"
                      aria-label={`Xóa ${goal.name}`}
                      onClick={() => setGoalToDelete(goal)}
                    >
                      🗑️
                    </button>
                  </div>
                </div>

                <div className="goal-badges-row">
                  <span className={`goal-status-badge ${statusConfig.badgeClass}`}>
                    {statusConfig.icon} {statusConfig.label}
                  </span>

                  {goal.deadline ? (
                    <span
                      className={`goal-deadline-badge ${
                        goal.days_remaining !== null && goal.days_remaining < 0
                          ? 'deadline-overdue'
                          : goal.days_remaining !== null && goal.days_remaining <= 7
                          ? 'deadline-urgent'
                          : ''
                      }`}
                    >
                      {goal.days_remaining !== null && goal.days_remaining < 0
                        ? `⚠️ Quá hạn (${formatDate(goal.deadline)})`
                        : goal.days_remaining !== null && goal.days_remaining === 0
                        ? '⏳ Hạn hôm nay'
                        : goal.days_remaining !== null
                        ? `⏳ Còn ${goal.days_remaining} ngày`
                        : `📅 ${formatDate(goal.deadline)}`}
                    </span>
                  ) : (
                    <span className="goal-deadline-badge deadline-none">
                      ♾️ Không giới hạn
                    </span>
                  )}
                </div>

                <div className="goal-amounts-grid">
                  <div className="amount-col">
                    <span className="amount-label">Đã tích lũy</span>
                    <span className="amount-current">{formatMoney(goal.current_amount)}</span>
                  </div>
                  <div className="amount-col text-right">
                    <span className="amount-label">Mục tiêu</span>
                    <span className="amount-target">{formatMoney(goal.target_amount)}</span>
                  </div>
                </div>

                <div className="goal-progress-section">
                  <div className="progress-info-row">
                    <span className="progress-label">Tiến độ</span>
                    <span className="progress-percent font-semibold">{goal.progress_percentage}%</span>
                  </div>
                  <div className="goal-progress-track">
                    <div
                      className={`goal-progress-fill ${isCompleted ? 'fill-completed' : ''}`}
                      style={{ width: `${percent}%` }}
                      role="progressbar"
                      aria-valuenow={percent}
                      aria-valuemin="0"
                      aria-valuemax="100"
                    />
                  </div>
                  <div className="progress-remaining-text">
                    {isCompleted && percent >= 100 ? (
                      <span className="text-emerald font-medium">🎉 Đã hoàn thành 100% mục tiêu!</span>
                    ) : isCompleted ? (
                      <span className="text-emerald font-medium">
                        ✓ Đã hoàn thành • Hiện còn {formatMoney(goal.current_amount)} trong mục tiêu
                      </span>
                    ) : (
                      <span>Còn thiếu: <strong>{formatMoney(goal.remaining_amount)}</strong></span>
                    )}
                  </div>
                </div>

                <div className="goal-card-footer">
                  <button
                    type="button"
                    className="btn-secondary btn-goal-history"
                    onClick={() => openHistoryModal(goal)}
                  >
                    📜 Lịch sử
                  </button>
                  <button
                    type="button"
                    className="btn-secondary btn-goal-withdraw"
                    disabled={Number(goal.current_amount || 0) <= 0}
                    onClick={() => openWithdrawModal(goal)}
                  >
                    − Rút tiền
                  </button>
                  <button
                    type="button"
                    className="btn-primary btn-goal-deposit"
                    disabled={isCancelled || isCompleted}
                    onClick={() => openDepositModal(goal)}
                  >
                    {isCompleted ? '✓ Đã hoàn thành' : '+ Nạp tiền'}
                  </button>
                </div>
              </article>
            );
          })}
        </section>
      )}

      {/* ==========================================
          MODAL: CREATE / EDIT GOAL
      ========================================== */}
      {goalModalOpen && createPortal(
        <div
          className="modal-backdrop saving-modal-backdrop"
          role="presentation"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) closeGoalModal();
          }}
        >
          <div
            className="category-modal budget-modal saving-goal-modal"
            role="dialog"
            aria-labelledby="goal-modal-title"
            aria-modal="true"
          >
            <div className="modal-header">
              <div className="modal-title-wrap">
                <span className="modal-icon-badge">{editingGoal ? '✏️' : '🎯'}</span>
                <div>
                  <span className="eyebrow">Mục tiêu tài chính</span>
                  <h2 id="goal-modal-title">
                    {editingGoal ? 'Chỉnh sửa mục tiêu tiết kiệm' : 'Tạo mục tiêu tiết kiệm mới'}
                  </h2>
                </div>
              </div>
              <button
                type="button"
                className="modal-close"
                onClick={closeGoalModal}
                disabled={submitting}
                aria-label="Đóng cửa sổ"
              >
                ×
              </button>
            </div>

            <form onSubmit={handleSaveGoal} className="txn-form" noValidate>
              <label className="txn-form-field">
                <span>Tên mục tiêu <em>*</em></span>
                <input
                  id="goal-name"
                  type="text"
                  placeholder="Ví dụ: Mua laptop mới, Quỹ du lịch, Mua xe..."
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  maxLength={100}
                  className={formErrors.name ? 'input-error' : ''}
                  aria-invalid={Boolean(formErrors.name)}
                  required
                />
              </label>

              <div className="txn-form-row txn-form-row-2col">
                <label className="txn-form-field">
                  <span>Số tiền mục tiêu (VNĐ) <em>*</em></span>
                  <input
                    id="goal-target-amount"
                    type="number"
                    placeholder="Ví dụ: 20000000"
                    value={formTargetAmount}
                    onChange={(e) => setFormTargetAmount(e.target.value)}
                    min="1"
                    step="any"
                    className={formErrors.target_amount ? 'input-error' : ''}
                    aria-invalid={Boolean(formErrors.target_amount)}
                    required
                  />
                  {formTargetAmount && Number(formTargetAmount) > 0 && (
                    <span className="input-helper-text">
                      💡 Tương đương: <strong>{formatMoney(formTargetAmount)}</strong>
                    </span>
                  )}
                </label>

                <div className="txn-form-field">
                  <span>Hạn chót hoàn thành</span>
                  <CustomDatePicker
                    id="goal-deadline"
                    value={formDeadline}
                    hasError={Boolean(formErrors.deadline)}
                    onChange={(e) => setFormDeadline(e.target.value)}
                    minDate={new Date().toISOString().substring(0, 10)}
                    placeholderText="Chọn hạn chót (dd/mm/yyyy)"
                  />
                </div>
              </div>

              {!editingGoal ? (
                <label className="txn-form-field">
                  <div className="label-row-preview">
                    <span>Số tiền nạp ban đầu (VNĐ, tùy chọn)</span>
                    <span className="label-amount-preview text-muted">
                      Khả dụng: <strong>{formatMoney(availableBalance)}</strong>
                    </span>
                  </div>
                  <input
                    id="goal-initial-deposit"
                    type="number"
                    placeholder={`Tối đa khả dụng: ${formatMoney(availableBalance)}`}
                    value={formInitialDeposit}
                    onChange={(e) => setFormInitialDeposit(e.target.value)}
                    min="0"
                    step="any"
                    className={formErrors.initial_deposit ? 'input-error' : ''}
                    aria-invalid={Boolean(formErrors.initial_deposit)}
                  />
                  {formInitialDeposit && Number(formInitialDeposit) > 0 && (
                    <span className="input-helper-text">
                      💡 Tương đương: <strong>{formatMoney(formInitialDeposit)}</strong>
                    </span>
                  )}
                </label>
              ) : (
                <label className="txn-form-field">
                  <span>Trạng thái mục tiêu</span>
                  <select
                    id="goal-status"
                    value={formStatus}
                    onChange={(e) => setFormStatus(e.target.value)}
                  >
                    <option value="active">⚡ Đang tích lũy</option>
                    <option value="completed">🎉 Đã hoàn thành</option>
                    <option value="cancelled">⏸ Tạm dừng / Hủy</option>
                  </select>
                </label>
              )}

              <div className="txn-form-actions">
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={closeGoalModal}
                  disabled={submitting}
                >
                  Hủy
                </button>
                <button
                  type="submit"
                  className="btn-primary"
                  disabled={submitting}
                >
                  {submitting ? 'Đang lưu...' : editingGoal ? 'Cập nhật' : 'Tạo mục tiêu'}
                </button>
              </div>
            </form>
          </div>
        </div>,
        document.body
      )}

      {/* ==========================================
          MODAL: QUICK DEPOSIT MONEY
      ========================================== */}
      {depositModalOpen && activeDepositGoal && createPortal(
        <div
          className="modal-backdrop saving-modal-backdrop"
          role="presentation"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) closeDepositModal();
          }}
        >
          <div
            className="category-modal budget-modal saving-deposit-modal"
            role="dialog"
            aria-labelledby="deposit-modal-title"
            aria-modal="true"
          >
            <div className="modal-header">
              <div className="modal-title-wrap">
                <span className="modal-icon-badge">💰</span>
                <div>
                  <span className="eyebrow">Tích lũy tài chính</span>
                  <h2 id="deposit-modal-title">Nạp tiền tiết kiệm</h2>
                </div>
              </div>
              <button
                type="button"
                className="modal-close"
                onClick={closeDepositModal}
                disabled={submitting}
                aria-label="Đóng cửa sổ"
              >
                ×
              </button>
            </div>

            <div className="budget-modal-category-preview saving-deposit-preview-card">
              <div className="deposit-preview-icon preview-icon-box">🎯</div>
              <div className="deposit-preview-info preview-text">
                <strong>{activeDepositGoal.name}</strong>
                <div className="deposit-preview-stats">
                  <span>Hiện có: <strong className="text-emerald">{formatMoney(activeDepositGoal.current_amount)}</strong></span>
                  <span>/ Mục tiêu: <strong>{formatMoney(activeDepositGoal.target_amount)}</strong></span>
                </div>
                <div className="deposit-preview-progress">
                  <div
                    className="deposit-progress-fill"
                    style={{
                      width: `${Math.min(
                        100,
                        (Number(activeDepositGoal.current_amount || 0) /
                          Number(activeDepositGoal.target_amount || 1)) *
                          100
                      )}%`,
                    }}
                  />
                </div>
              </div>
            </div>

            <div className="deposit-balance-hint-card">
              <div className="balance-hint-left">
                <span className="hint-icon">💼</span>
                <div>
                  <div className="hint-title">Số dư ví khả dụng:</div>
                  <div className={`hint-value ${availableBalance <= 0 ? 'text-danger' : 'text-emerald'}`}>
                    {formatMoney(availableBalance)}
                  </div>
                </div>
              </div>
              <div className="balance-hint-actions">
                {availableBalance > 0 && (
                  <button
                    type="button"
                    className="btn-use-max-balance"
                    onClick={() => {
                      const maxCanDeposit = Math.min(availableBalance, Number(activeDepositGoal.remaining_amount));
                      setDepositAmount(String(maxCanDeposit));
                    }}
                  >
                    Nạp theo ví ({formatMoney(Math.min(availableBalance, Number(activeDepositGoal.remaining_amount)))})
                  </button>
                )}
                {Number(activeDepositGoal.remaining_amount) > 0 && (
                  <button
                    type="button"
                    className="btn-fill-target-goal"
                    onClick={() => setDepositAmount(String(activeDepositGoal.remaining_amount))}
                  >
                    Nạp đủ thiếu ({formatMoney(activeDepositGoal.remaining_amount)})
                  </button>
                )}
              </div>
            </div>

            <form onSubmit={handleDepositSubmit} className="txn-form" noValidate>
              <label className="txn-form-field">
                <span>Số tiền muốn nạp (VNĐ) <em>*</em></span>
                <input
                  id="deposit-amount"
                  type="number"
                  placeholder="Nhập số tiền..."
                  value={depositAmount}
                  onChange={(e) => {
                    setDepositAmount(e.target.value);
                    if (depositError) setDepositError('');
                  }}
                  min="1"
                  step="any"
                  className={depositError ? 'input-error' : ''}
                  aria-invalid={Boolean(depositError)}
                  autoFocus
                  required
                />
                {depositAmount && Number(depositAmount) > 0 && (
                  <span className="input-helper-text">
                    💡 Tương đương: <strong>{formatMoney(depositAmount)}</strong>
                  </span>
                )}
              </label>

              <label className="txn-form-field">
                <span>Ghi chú (tùy chọn)</span>
                <input
                  id="deposit-note"
                  type="text"
                  placeholder="Ví dụ: Trích từ tiền thưởng, Lì xì tết, Tiết kiệm tuần..."
                  value={depositNote}
                  onChange={(e) => setDepositNote(e.target.value)}
                  maxLength={255}
                />
              </label>

              <div className="txn-form-actions">
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={closeDepositModal}
                  disabled={submitting}
                >
                  Hủy
                </button>
                <button
                  type="submit"
                  className="btn-primary btn-deposit-confirm"
                  disabled={submitting}
                >
                  {submitting ? 'Đang xử lý...' : 'Xác nhận nạp tiền'}
                </button>
              </div>
            </form>
          </div>
        </div>,
        document.body
      )}

      {/* ==========================================
          MODAL: WITHDRAW SAVED MONEY
      ========================================== */}
      {withdrawModalOpen && activeWithdrawGoal && createPortal(
        <div
          className="modal-backdrop saving-modal-backdrop"
          role="presentation"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) closeWithdrawModal();
          }}
        >
          <div
            className="category-modal budget-modal saving-withdraw-modal"
            role="dialog"
            aria-labelledby="withdraw-modal-title"
            aria-modal="true"
          >
            <div className="modal-header">
              <div className="modal-title-wrap">
                <span className="modal-icon-badge">💸</span>
                <div>
                  <span className="eyebrow">Điều chỉnh khoản tiết kiệm</span>
                  <h2 id="withdraw-modal-title">Rút tiền tiết kiệm</h2>
                </div>
              </div>
              <button
                type="button"
                className="modal-close"
                onClick={closeWithdrawModal}
                disabled={submitting}
                aria-label="Đóng cửa sổ"
              >
                ×
              </button>
            </div>

            <div className="budget-modal-category-preview saving-deposit-preview-card saving-withdraw-preview-card">
              <div className="deposit-preview-icon preview-icon-box">🎯</div>
              <div className="deposit-preview-info preview-text">
                <strong>{activeWithdrawGoal.name}</strong>
                <div className="deposit-preview-stats">
                  <span>Đang tích lũy: <strong className="text-emerald">{formatMoney(activeWithdrawGoal.current_amount)}</strong></span>
                </div>
              </div>
            </div>

            <div className="withdraw-balance-hint-card">
              {activeWithdrawGoal.status === 'cancelled' ? (
                <p>
                  Mục tiêu đang tạm dừng nên khoản tiết kiệm này đã nằm trong số dư khả dụng.
                  Rút tiền sẽ giảm số tích lũy và lưu lại lịch sử, không cộng số dư lần hai.
                </p>
              ) : (
                <div>
                  <span>Số dư khả dụng sau khi rút</span>
                  <strong>
                    {formatMoney(availableBalance + Math.min(
                      Number(withdrawAmount || 0),
                      Number(activeWithdrawGoal.current_amount || 0)
                    ))}
                  </strong>
                </div>
              )}
            </div>

            <form onSubmit={handleWithdrawSubmit} className="txn-form" noValidate>
              <label className="txn-form-field">
                <span>Số tiền muốn rút (VNĐ) <em>*</em></span>
                <input
                  id="withdraw-amount"
                  type="number"
                  placeholder="Nhập số tiền muốn rút..."
                  value={withdrawAmount}
                  onChange={(e) => {
                    setWithdrawAmount(e.target.value);
                    if (withdrawError) setWithdrawError('');
                  }}
                  min="1"
                  max={Number(activeWithdrawGoal.current_amount || 0)}
                  step="any"
                  className={withdrawError ? 'input-error' : ''}
                  aria-invalid={Boolean(withdrawError)}
                  autoFocus
                  required
                />
                {withdrawAmount && Number(withdrawAmount) > 0 && (
                  <span className="input-helper-text withdraw-helper-text">
                    Sẽ rút: <strong>{formatMoney(withdrawAmount)}</strong>
                  </span>
                )}
              </label>

              <button
                type="button"
                className="btn-withdraw-all"
                onClick={() => setWithdrawAmount(String(activeWithdrawGoal.current_amount))}
              >
                Rút toàn bộ {formatMoney(activeWithdrawGoal.current_amount)}
              </button>

              <label className="txn-form-field">
                <span>Ghi chú (tùy chọn)</span>
                <input
                  id="withdraw-note"
                  type="text"
                  placeholder="Ví dụ: Chi phí khẩn cấp, chuyển sang mục tiêu khác..."
                  value={withdrawNote}
                  onChange={(e) => setWithdrawNote(e.target.value)}
                  maxLength={255}
                />
              </label>

              <div className="txn-form-actions">
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={closeWithdrawModal}
                  disabled={submitting}
                >
                  Hủy
                </button>
                <button
                  type="submit"
                  className="btn-primary btn-withdraw-confirm"
                  disabled={submitting}
                >
                  {submitting ? 'Đang xử lý...' : 'Xác nhận rút tiền'}
                </button>
              </div>
            </form>
          </div>
        </div>,
        document.body
      )}

      {/* ==========================================
          MODAL: CONTRIBUTION HISTORY TIMELINE
      ========================================== */}
      {historyModalOpen && createPortal(
        <div
          className="modal-backdrop saving-modal-backdrop"
          role="presentation"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) closeHistoryModal();
          }}
        >
          <div
            className="category-modal budget-modal saving-history-modal"
            role="dialog"
            aria-labelledby="history-modal-title"
            aria-modal="true"
          >
            <div className="modal-header">
              <div className="modal-title-wrap">
                <span className="modal-icon-badge">📜</span>
                <div>
                  <span className="eyebrow">Nhật ký tiết kiệm</span>
                  <h2 id="history-modal-title">Lịch sử nạp và rút tiền</h2>
                </div>
              </div>
              <button
                type="button"
                className="modal-close"
                onClick={closeHistoryModal}
                aria-label="Đóng cửa sổ"
              >
                ×
              </button>
            </div>

            <div className="saving-history-hero">
              <div className="history-hero-title">🎯 {historyModalOpen.name}</div>
              <div className="history-hero-stats">
                <div className="history-stat-box">
                  <span className="stat-label">Tổng tích lũy</span>
                  <span className="stat-value text-emerald">{formatMoney(historyModalOpen.current_amount)}</span>
                </div>
                <div className="history-stat-box">
                  <span className="stat-label">Mục tiêu</span>
                  <span className="stat-value">{formatMoney(historyModalOpen.target_amount)}</span>
                </div>
                <div className="history-stat-box">
                  <span className="stat-label">Biến động</span>
                  <span className="stat-value">{historyItems.length}</span>
                </div>
              </div>
            </div>

            <div className="history-timeline-body">
              {historyItems.length === 0 ? (
                <div className="history-empty">
                  <span className="empty-icon">📝</span>
                  <p>Chưa có lịch sử nạp hoặc rút tiền cho mục tiêu này.</p>
                </div>
              ) : (
                <div className="contribution-timeline">
                  {historyItems.map((item) => (
                    <div key={`${item.movementType}-${item.id}`} className={`timeline-item ${item.movementType}`}>
                      <div className={`timeline-dot ${item.movementType}`} />
                      <div className="timeline-content">
                        <div className="timeline-header">
                          <span className={`timeline-amount ${item.movementType === 'withdrawal' ? 'text-danger' : 'text-emerald'}`}>
                            {item.movementType === 'withdrawal' ? '−' : '+'}{formatMoney(item.amount)}
                          </span>
                          <span className="timeline-date">{formatDateTime(item.created_at)}</span>
                        </div>
                        <div className="timeline-meta">
                          <span className={`timeline-source-badge ${item.movementType === 'withdrawal' ? 'withdrawal' : ''}`}>
                            {item.movementType === 'withdrawal'
                              ? 'Rút tiền'
                              : item.source === 'income_allocation'
                              ? 'Trích từ thu nhập'
                              : 'Nạp thủ công'}
                          </span>
                          {item.note && <span className="timeline-note">“{item.note}”</span>}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="txn-form-actions">
              <button
                type="button"
                className="btn-primary"
                onClick={closeHistoryModal}
                style={{ width: '100%' }}
              >
                Đóng
              </button>
            </div>
          </div>
        </div>,
        document.body
      )}

      {/* ==========================================
          MODAL: DELETE CONFIRMATION
      ========================================== */}
      {goalToDelete && (
        <ConfirmModal
          isOpen={true}
          title="Xóa mục tiêu tiết kiệm?"
          message={`Bạn có chắc chắn muốn xóa mục tiêu "${goalToDelete.name}"? Toàn bộ lịch sử nạp tiền liên quan sẽ bị xóa.`}
          confirmText="Xóa mục tiêu"
          isDanger={true}
          onConfirm={handleDeleteConfirm}
          onCancel={() => setGoalToDelete(null)}
        />
      )}
      <WarningPopup
        isOpen={Boolean(warningPopup.message)}
        message={warningPopup.message}
        onClose={closeWarning}
      />
    </div>
  );
};

export default SavingGoals;
