import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { createPortal } from 'react-dom';
import { getBudgets, createBudget, updateBudget, deleteBudget } from '../api/budgetApi';
import { getCategories } from '../api/categoryApi';
import { getTransactionSummary } from '../api/transactionApi';
import CategoryIcon from '../components/CategoryIcon';
import CustomSelect from '../components/CustomSelect';
import ConfirmModal from '../components/ConfirmModal';
import AiBudgetTab from '../components/AiBudgetTab';
import { useModalLock } from '../hooks/useModalLock';

const formatMoney = (amount) => {
  return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(amount || 0);
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

const Budgets = () => {
  const today = useMemo(() => new Date(), []);
  const [currentMonth, setCurrentMonth] = useState(today.getMonth() + 1);
  const [currentYear, setCurrentYear] = useState(today.getFullYear());
  const [activeTab, setActiveTab] = useState('manage'); // 'manage' | 'aiSuggest'

  const [budgetData, setBudgetData] = useState({
    month: today.getMonth() + 1,
    year: today.getFullYear(),
    total_budget: 0,
    total_spent: 0,
    total_remaining: 0,
    items: [],
  });

  const [categories, setCategories] = useState([]);
  const [availableBalance, setAvailableBalance] = useState(null);
  const [initialLoading, setInitialLoading] = useState(true);
  const [isFetching, setIsFetching] = useState(false);
  const [error, setError] = useState('');
  const [toastMessage, setToastMessage] = useState('');

  // Filters and Sort State
  const [statusFilter, setStatusFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState('percent_desc');

  // Modals state
  const [modalOpen, setModalOpen] = useState(false);
  const [editingBudget, setEditingBudget] = useState(null);
  const [budgetToDelete, setBudgetToDelete] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [modalError, setModalError] = useState('');

  // Form state
  const [formCategory, setFormCategory] = useState('');
  const [formAmount, setFormAmount] = useState('');
  const [formMonth, setFormMonth] = useState(currentMonth);
  const [formYear, setFormYear] = useState(currentYear);
  const [formErrors, setFormErrors] = useState({});

  const overlayRef = useRef(null);

  const closeModal = useCallback(() => {
    if (submitting) return;
    setModalOpen(false);
    setEditingBudget(null);
  }, [submitting]);

  useModalLock(modalOpen, closeModal);

  // Auto dismiss toast
  useEffect(() => {
    if (!toastMessage) return;
    const timer = setTimeout(() => setToastMessage(''), 3500);
    return () => clearTimeout(timer);
  }, [toastMessage]);

  // Load active expense categories once
  useEffect(() => {
    let cancelled = false;
    getCategories({ status: 'active', type: 'expense' })
      .then((data) => {
        if (!cancelled) setCategories(data.items || []);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  // Fetch budgets with smooth non-blocking transition
  const fetchBudgets = useCallback(async (signal) => {
    setIsFetching(true);
    setError('');
    try {
      const [data, sumData] = await Promise.all([
        getBudgets({ month: currentMonth, year: currentYear }, signal),
        getTransactionSummary(signal).catch(() => null),
      ]);
      setBudgetData({
        month: data.month,
        year: data.year,
        total_budget: Number(data.total_budget || 0),
        total_spent: Number(data.total_spent || 0),
        total_remaining: Number(data.total_remaining || 0),
        items: data.items || [],
      });
      if (sumData && sumData.available_balance !== undefined) {
        setAvailableBalance(Number(sumData.available_balance || 0));
      }
    } catch (err) {
      if (err.code !== 'ERR_CANCELED') {
        setError(apiMessage(err));
      }
    } finally {
      setIsFetching(false);
      setInitialLoading(false);
    }
  }, [currentMonth, currentYear]);

  useEffect(() => {
    const controller = new AbortController();
    fetchBudgets(controller.signal);
    return () => controller.abort();
  }, [fetchBudgets]);

  // Month navigation handlers (instant & stable)
  const handlePrevMonth = () => {
    if (currentMonth === 1) {
      setCurrentMonth(12);
      setCurrentYear((y) => y - 1);
    } else {
      setCurrentMonth((m) => m - 1);
    }
  };

  const handleNextMonth = () => {
    if (currentMonth === 12) {
      setCurrentMonth(1);
      setCurrentYear((y) => y + 1);
    } else {
      setCurrentMonth((m) => m + 1);
    }
  };

  const handleResetToCurrentMonth = () => {
    setCurrentMonth(today.getMonth() + 1);
    setCurrentYear(today.getFullYear());
  };

  const isCurrentCalendarMonth =
    currentMonth === today.getMonth() + 1 && currentYear === today.getFullYear();

  // Days calculations
  const daysInMonth = useMemo(() => new Date(currentYear, currentMonth, 0).getDate(), [currentMonth, currentYear]);
  const daysRemaining = useMemo(() => {
    if (isCurrentCalendarMonth) {
      return Math.max(1, daysInMonth - today.getDate() + 1);
    }
    return daysInMonth;
  }, [isCurrentCalendarMonth, daysInMonth, today]);

  const dailySafeSpend = useMemo(() => {
    if (budgetData.total_remaining <= 0 || daysRemaining <= 0) return 0;
    return Math.round(budgetData.total_remaining / daysRemaining);
  }, [budgetData.total_remaining, daysRemaining]);

  // Category select options: Filter out expense categories already budgeted in this period
  const budgetedCategoryIds = useMemo(() => {
    return new Set(budgetData.items.map((b) => b.category_id));
  }, [budgetData.items]);

  const availableCategories = useMemo(() => {
    return categories.filter((c) => c.type === 'expense' && c.is_active && !budgetedCategoryIds.has(c.id));
  }, [categories, budgetedCategoryIds]);

  const categorySelectOptions = useMemo(() => [
    { value: '', label: 'Chọn danh mục chi tiêu...' },
    ...availableCategories.map((c) => ({
      value: c.id,
      label: c.name,
      icon: c.icon,
      color: c.color,
      type: c.type,
    })),
  ], [availableCategories]);

  const monthSelectOptions = useMemo(
    () => Array.from({ length: 12 }, (_, index) => ({
      value: index + 1,
      label: `Tháng ${String(index + 1).padStart(2, '0')}`,
    })),
    [],
  );

  const yearSelectOptions = useMemo(
    () => Array.from({ length: 7 }, (_, index) => {
      const year = today.getFullYear() - 1 + index;
      return { value: year, label: `Năm ${year}` };
    }),
    [today],
  );

  // Open create modal
  const openCreateModal = () => {
    setEditingBudget(null);
    setFormCategory('');
    setFormAmount('');
    setFormMonth(currentMonth);
    setFormYear(currentYear);
    setFormErrors({});
    setModalError('');
    setModalOpen(true);
  };

  // Open edit modal
  const openEditModal = (budget) => {
    setEditingBudget(budget);
    setFormCategory(String(budget.category_id || ''));
    setFormAmount(String(budget.amount || ''));
    setFormMonth(budget.month);
    setFormYear(budget.year);
    setFormErrors({});
    setModalError('');
    setModalOpen(true);
  };


  const validateForm = () => {
    const errs = {};
    const amountNum = parseFloat(formAmount);
    if (!formAmount || Number.isNaN(amountNum) || amountNum <= 0) {
      errs.amount = 'Hạn mức ngân sách phải lớn hơn 0.';
    } else {
      const projectedTotal = editingBudget
        ? Math.max(0, (budgetData.total_budget || 0) - (editingBudget.amount || 0) + amountNum)
        : (budgetData.total_budget || 0) + amountNum;
      if (availableBalance !== null && projectedTotal > availableBalance) {
        errs.amount = `Tổng ngân sách không được vượt quá số dư khả dụng (${formatMoney(availableBalance)}).`;
      }
    }
    if (!editingBudget && !formCategory) {
      errs.category = 'Vui lòng chọn danh mục chi tiêu.';
    }
    setFormErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validateForm() || submitting) return;

    setSubmitting(true);
    setModalError('');
    try {
      if (editingBudget) {
        await updateBudget(editingBudget.id, {
          amount: parseFloat(formAmount),
        });
        setToastMessage('Đã cập nhật hạn mức ngân sách thành công.');
      } else {
        await createBudget({
          category_id: Number(formCategory),
          amount: parseFloat(formAmount),
          month: Number(formMonth),
          year: Number(formYear),
        });
        setToastMessage('Đã thiết lập ngân sách thành công.');
      }
      setModalOpen(false);
      fetchBudgets();
    } catch (err) {
      setModalError(apiMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  const confirmDelete = async () => {
    if (!budgetToDelete) return;
    try {
      await deleteBudget(budgetToDelete.id);
      setToastMessage('Đã xóa ngân sách thành công.');
      setBudgetToDelete(null);
      fetchBudgets();
    } catch (err) {
      setError(apiMessage(err));
      setBudgetToDelete(null);
    }
  };

  // Summary statistics
  const warningCount = useMemo(() => {
    return budgetData.items.filter((b) => b.status === 'warning').length;
  }, [budgetData.items]);

  const exceededCount = useMemo(() => {
    return budgetData.items.filter((b) => b.status === 'exceeded').length;
  }, [budgetData.items]);

  const normalCount = useMemo(() => {
    return budgetData.items.filter((b) => b.status === 'normal').length;
  }, [budgetData.items]);

  const overallSpentPercent = budgetData.total_budget > 0
    ? Math.round((budgetData.total_spent / budgetData.total_budget) * 100)
    : 0;

  const targetTotalBudget = useMemo(() => {
    const val = parseFloat(formAmount) || 0;
    if (editingBudget) {
      return Math.max(0, (budgetData.total_budget || 0) - (editingBudget.amount || 0) + val);
    }
    return (budgetData.total_budget || 0) + val;
  }, [formAmount, editingBudget, budgetData.total_budget]);

  // Filtered and Sorted items
  const filteredAndSortedItems = useMemo(() => {
    let result = [...budgetData.items];

    // Filter by status
    if (statusFilter !== 'all') {
      result = result.filter((item) => item.status === statusFilter);
    }

    // Filter by search keyword
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      result = result.filter((item) => item.category?.name?.toLowerCase().includes(q));
    }

    // Sorting
    result.sort((a, b) => {
      if (sortBy === 'percent_desc') return (b.percentage_used || 0) - (a.percentage_used || 0);
      if (sortBy === 'percent_asc') return (a.percentage_used || 0) - (b.percentage_used || 0);
      if (sortBy === 'amount_desc') return (b.amount || 0) - (a.amount || 0);
      if (sortBy === 'spent_desc') return (b.spent_amount || 0) - (a.spent_amount || 0);
      if (sortBy === 'name_asc') return (a.category?.name || '').localeCompare(b.category?.name || '', 'vi');
      return 0;
    });

    return result;
  }, [budgetData.items, statusFilter, searchQuery, sortBy]);

  const sortOptions = useMemo(() => [
    { value: 'percent_desc', label: 'Tỷ lệ dùng cao nhất' },
    { value: 'percent_asc', label: 'Tỷ lệ dùng thấp nhất' },
    { value: 'amount_desc', label: 'Hạn mức lớn nhất' },
    { value: 'spent_desc', label: 'Chi tiêu nhiều nhất' },
    { value: 'name_asc', label: 'Tên danh mục (A–Z)' },
  ], []);

  return (
    <div className="budget-page">
      {/* Toast Notification */}
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

      {/* 1. Hero Header - Clean 2-column layout */}
      <section className="budget-hero-section">
        <div className="budget-hero-info">
          <span className="eyebrow">Quản lý tài chính</span>
          <h1>Quản lý Ngân sách</h1>
          <p>Thiết lập hạn mức chi tiêu theo tháng và nhận cảnh báo tự động khi chạm ngưỡng an toàn.</p>
        </div>

        <div className="budget-hero-actions">
          <button
            type="button"
            className="btn-primary add-budget-hero-btn"
            onClick={openCreateModal}
          >
            <span className="btn-icon">⚡</span>
            Thiết lập ngân sách
          </button>
        </div>
      </section>

      {/* 2. Unified Tab Navigation */}
      <section className="budget-tabs-bar-section">
        <div className="budget-unified-tabs" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === 'manage'}
            className={`budget-tab-item ${activeTab === 'manage' ? 'active' : ''}`}
            onClick={() => setActiveTab('manage')}
          >
            <span className="budget-tab-icon">📋</span> Quản Lý Ngân Sách
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === 'aiSuggest'}
            className={`budget-tab-item tab-ai-highlight ${activeTab === 'aiSuggest' ? 'active' : ''}`}
            onClick={() => setActiveTab('aiSuggest')}
          >
            <span className="budget-tab-icon">✨</span> AI Gợi Ý Ngân Sách
          </button>
        </div>
      </section>

      {activeTab === 'aiSuggest' ? (
        <AiBudgetTab
          currentMonth={currentMonth}
          currentYear={currentYear}
          onApplied={(targetMonth, targetYear) => {
            if (targetMonth && targetYear) {
              setCurrentMonth(targetMonth);
              setCurrentYear(targetYear);
            }
            fetchBudgets();
            setActiveTab('manage');
            setToastMessage('Đã áp dụng thành công ngân sách gợi ý từ AI!');
          }}
        />
      ) : (
        <>
          {error && <div className="message message-error">{error}</div>}

          {/* 2. Executive Overview Dashboard Panel */}
          <section className={`budget-overview-panel ${isFetching ? 'is-refreshing' : ''}`}>
        <div className="overview-main-metric">
          <div className="overview-metric-header">
            <div className="metric-header-left">
              <span className="overview-panel-tag">TỔNG TIẾN ĐỘ THÁNG {currentMonth}/{currentYear}</span>
              <h2>{formatMoney(budgetData.total_spent)} <span className="overview-total-budget">/ {formatMoney(budgetData.total_budget)}</span></h2>
            </div>
            <div className="metric-header-right">
              <div className={`overall-health-badge ${overallSpentPercent >= 100 ? 'health-danger' : overallSpentPercent >= 80 ? 'health-warning' : 'health-normal'}`}>
                <span className="health-dot" />
                <span>{overallSpentPercent}% Đã dùng</span>
              </div>
            </div>
          </div>

          {/* Master Progress Bar */}
          <div className="overview-progress-bar-wrap">
            <div className="overview-progress-track">
              <div
                className={`overview-progress-fill ${overallSpentPercent >= 100 ? 'fill-exceeded' : overallSpentPercent >= 80 ? 'fill-warning' : 'fill-normal'}`}
                style={{ width: `${Math.min(overallSpentPercent, 100)}%` }}
              >
                <span className="progress-shimmer" />
              </div>
            </div>
            <div className="overview-milestones">
              <span>0% Bắt đầu</span>
              <span>50%</span>
              <span className="milestone-warn">80% Cảnh báo</span>
              <span className="milestone-danger">100% Hạn mức</span>
            </div>
          </div>
        </div>

        {/* 4 Executive Quick Insight Cards (Split Remaining & Daily Safe Spend) */}
        <div className="overview-sub-metrics">
          {/* 1. Total Month Remaining */}
          <div className="sub-metric-card">
            <div className="sub-metric-icon icon-remain">💳</div>
            <div className="sub-metric-info">
              <span className="sub-metric-label">Còn lại tháng {currentMonth}</span>
              <strong className={`sub-metric-val ${budgetData.total_remaining >= 0 ? 'text-success' : 'text-error'}`}>
                {budgetData.total_remaining < 0 ? '-' : ''}{formatMoney(Math.abs(budgetData.total_remaining))}
              </strong>
              <span className="sub-metric-sub">
                {budgetData.total_budget === 0
                  ? 'Chưa thiết lập hạn mức'
                  : budgetData.total_remaining > 0
                  ? `Còn dư ${Math.max(0, 100 - overallSpentPercent)}% hạn mức`
                  : budgetData.total_remaining === 0
                  ? 'Đã dùng 100% hạn mức'
                  : `Vượt hạn mức ${overallSpentPercent - 100}%`}
              </span>
            </div>
          </div>

          {/* 2. Daily Safe Spend (Clarified) */}
          <div className="sub-metric-card">
            <div className="sub-metric-icon icon-daily">🗓️</div>
            <div className="sub-metric-info">
              <span className="sub-metric-label">Hạn mức mỗi ngày</span>
              <strong className={`sub-metric-val ${dailySafeSpend > 0 ? 'text-primary' : budgetData.total_remaining <= 0 ? 'text-error' : ''}`}>
                {formatMoney(dailySafeSpend)} <span className="sub-metric-unit">/ ngày</span>
              </strong>
              <span className="sub-metric-sub">
                {isCurrentCalendarMonth
                  ? budgetData.total_remaining > 0
                    ? `Phân bổ cho ${daysRemaining} ngày còn lại (tháng ${currentMonth})`
                    : 'Đã hết hạn mức an toàn'
                  : `Tháng ${currentMonth}/${currentYear} đã kết thúc`}
              </span>
            </div>
          </div>

          {/* 3. Budgeted Categories */}
          <div className="sub-metric-card">
            <div className="sub-metric-icon icon-category">🎯</div>
            <div className="sub-metric-info">
              <span className="sub-metric-label">Danh mục thiết lập</span>
              <strong className="sub-metric-val text-primary">{budgetData.items.length} danh mục</strong>
              <span className="sub-metric-sub">Đang theo dõi tự động</span>
            </div>
          </div>

          {/* 4. Health & Alert Status */}
          <div className="sub-metric-card">
            <div className="sub-metric-icon icon-health">📊</div>
            <div className="sub-metric-info">
              <span className="sub-metric-label">Tình trạng cảnh báo</span>
              <div className="health-chips-strip">
                {exceededCount > 0 && <span className="chip-pill chip-pill-danger">🔴 {exceededCount} Vượt</span>}
                {warningCount > 0 && <span className="chip-pill chip-pill-warning">🟡 {warningCount} Cảnh báo</span>}
                {normalCount > 0 && <span className="chip-pill chip-pill-normal">🟢 {normalCount} An toàn</span>}
                {budgetData.items.length === 0 && <span className="chip-pill chip-pill-dim">Chưa có dữ liệu</span>}
              </div>
              <span className="sub-metric-sub">
                {exceededCount === 0 && warningCount === 0 && budgetData.items.length > 0
                  ? '100% danh mục an toàn 🌟'
                  : exceededCount > 0 ? 'Có danh mục cần rà soát' : 'Theo dõi chi tiêu đều đặn'}
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* 3. Dedicated Toolbar with Rock-Solid Month Selector & Filters */}
      <section className="budget-toolbar-section">
        {/* Left: Stable Non-Jumping Month Selector */}
        <div className="budget-month-nav-group">
          <div className="budget-month-pill-selector">
            <button
              type="button"
              className="btn-month-nav"
              onClick={handlePrevMonth}
              aria-label="Tháng trước"
              title="Xem tháng trước"
            >
              ◀
            </button>
            <div className="month-current-view">
              <span className="month-icon">📅</span>
              <span className="month-title">Tháng {currentMonth} / {currentYear}</span>
            </div>
            <button
              type="button"
              className="btn-month-nav"
              onClick={handleNextMonth}
              aria-label="Tháng sau"
              title="Xem tháng sau"
            >
              ▶
            </button>
          </div>

          {!isCurrentCalendarMonth && (
            <button
              type="button"
              className="btn-return-today"
              onClick={handleResetToCurrentMonth}
              title="Quay lại tháng hiện tại"
            >
              Hôm nay
            </button>
          )}

          {isFetching && <span className="budget-fetching-dot" title="Đang đồng bộ..." />}
        </div>

        {/* Middle: Filter Tabs */}
        {budgetData.items.length > 0 && (
          <div className="budget-filter-tabs" role="tablist">
            <button
              type="button"
              role="tab"
              aria-selected={statusFilter === 'all'}
              className={`filter-tab-pill ${statusFilter === 'all' ? 'active' : ''}`}
              onClick={() => setStatusFilter('all')}
            >
              Tất cả <span className="tab-counter">{budgetData.items.length}</span>
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={statusFilter === 'warning'}
              className={`filter-tab-pill tab-warning ${statusFilter === 'warning' ? 'active' : ''}`}
              onClick={() => setStatusFilter('warning')}
            >
              Cảnh báo {warningCount > 0 && <span className="tab-counter warn">{warningCount}</span>}
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={statusFilter === 'exceeded'}
              className={`filter-tab-pill tab-danger ${statusFilter === 'exceeded' ? 'active' : ''}`}
              onClick={() => setStatusFilter('exceeded')}
            >
              Vượt mức {exceededCount > 0 && <span className="tab-counter danger">{exceededCount}</span>}
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={statusFilter === 'normal'}
              className={`filter-tab-pill tab-normal ${statusFilter === 'normal' ? 'active' : ''}`}
              onClick={() => setStatusFilter('normal')}
            >
              An toàn <span className="tab-counter">{normalCount}</span>
            </button>
          </div>
        )}

        {/* Right: Search & Sort */}
        {budgetData.items.length > 0 && (
          <div className="budget-search-sort-controls">
            <div className="budget-search-box">
              <span className="search-icon">🔍</span>
              <input
                type="search"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Tìm danh mục..."
                className="budget-search-input"
              />
              {searchQuery && (
                <button
                  type="button"
                  className="search-clear-btn"
                  onClick={() => setSearchQuery('')}
                  aria-label="Xóa tìm kiếm"
                >
                  ✕
                </button>
              )}
            </div>

            <div className="budget-sort-box">
              <CustomSelect
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                options={sortOptions}
              />
            </div>
          </div>
        )}
      </section>

      {/* 4. Main Content Area - Smooth Transitions */}
      {initialLoading ? (
        <div className="dashboard-loading">
          <div className="spinner" />
          <p>Đang tải kế hoạch ngân sách...</p>
        </div>
      ) : budgetData.items.length === 0 ? (
        <div className="budget-empty-wrapper">
          <div className="budget-empty-card">
            <div className="empty-mascot-circle">🎯</div>
            <h3>Chưa có ngân sách cho Tháng {currentMonth}/{currentYear}</h3>
            <p>
              Thiết lập hạn mức chi tiêu theo danh mục để kiểm soát tài chính cá nhân hiệu quả và nhận cảnh báo tự động khi gần chạm ngưỡng.
            </p>
            <button
              type="button"
              className="btn-primary empty-create-btn"
              onClick={openCreateModal}
            >
              <span className="btn-icon">⚡</span>
              Thiết lập ngân sách ngay
            </button>
          </div>
        </div>
      ) : filteredAndSortedItems.length === 0 ? (
        <div className="budget-filter-empty">
          <span className="empty-filter-icon">🔍</span>
          <h3>Không tìm thấy danh mục phù hợp</h3>
          <p>Hãy thử xóa từ khóa tìm kiếm hoặc đổi bộ lọc trạng thái.</p>
          <button
            type="button"
            className="btn-secondary btn-sm"
            onClick={() => {
              setSearchQuery('');
              setStatusFilter('all');
            }}
          >
            Đặt lại bộ lọc
          </button>
        </div>
      ) : (
        <div className={`budget-cards-grid ${isFetching ? 'is-refreshing' : ''}`}>
          {filteredAndSortedItems.map((item) => {
            const isExceeded = item.status === 'exceeded';
            const isWarning = item.status === 'warning';
            const progressPercent = Math.min(Number(item.percentage_used) || 0, 100);

            return (
              <div
                key={item.id}
                className={`budget-item-card ${isExceeded ? 'card-exceeded' : isWarning ? 'card-warning' : 'card-normal'}`}
              >
                {/* Top Card Header */}
                <div className="budget-card-header">
                  <div className="budget-category-info">
                    <div className="category-icon-wrapper" style={{ '--cat-color': item.category?.color || '#D69A23' }}>
                      <CategoryIcon
                        icon={item.category?.icon || 'other'}
                        color={item.category?.color || '#D69A23'}
                      />
                    </div>
                    <div className="budget-category-text">
                      <h3 className="budget-category-name">{item.category?.name || 'Danh mục'}</h3>
                      <span className="budget-period-sub">Hạn mức tháng {item.month}/{item.year}</span>
                    </div>
                  </div>

                  <div className="budget-status-badge-wrap">
                    {isExceeded && (
                      <span className="budget-status-badge badge-exceeded">
                        <span className="badge-dot" />
                        Vượt mức ({item.percentage_used}%)
                      </span>
                    )}
                    {isWarning && (
                      <span className="budget-status-badge badge-warning">
                        <span className="badge-dot" />
                        Cảnh báo 80% ({item.percentage_used}%)
                      </span>
                    )}
                    {!isExceeded && !isWarning && (
                      <span className="budget-status-badge badge-normal">
                        <span className="badge-dot" />
                        An toàn ({item.percentage_used}%)
                      </span>
                    )}
                  </div>
                </div>

                {/* Amounts Comparison Row */}
                <div className="budget-amount-row">
                  <div className="amount-col">
                    <span className="amount-label">Đã chi tiêu</span>
                    <strong className={`amount-value ${isExceeded ? 'text-error' : isWarning ? 'text-warning' : 'text-dark'}`}>
                      {formatMoney(item.spent_amount)}
                    </strong>
                  </div>
                  <div className="amount-col text-right">
                    <span className="amount-label">Hạn mức</span>
                    <strong className="amount-value text-muted-dark">{formatMoney(item.amount)}</strong>
                  </div>
                </div>

                {/* Progress Bar */}
                <div className="budget-progress-container">
                  <div className="budget-progress-bar">
                    <div
                      className={`budget-progress-fill ${isExceeded ? 'fill-exceeded' : isWarning ? 'fill-warning' : 'fill-normal'}`}
                      style={{ width: `${progressPercent}%` }}
                    >
                      <span className="progress-shimmer" />
                    </div>
                  </div>
                </div>

                {/* Remaining / Over Indicator */}
                <div className="budget-remaining-row">
                  {isExceeded ? (
                    <span className="remaining-alert-text text-error">
                      <span className="alert-icon">⚠️</span> Bội chi {formatMoney(Math.abs(item.remaining_amount))}
                    </span>
                  ) : (
                    <span className="remaining-safe-text">
                      Khả dụng: <strong className="text-success">{formatMoney(item.remaining_amount)}</strong>
                    </span>
                  )}
                  <span className="remaining-percent-label">{item.percentage_used}%</span>
                </div>

                {/* Card Action Buttons */}
                <div className="budget-card-actions">
                  <button
                    type="button"
                    className="btn-card-edit"
                    onClick={() => openEditModal(item)}
                    title="Chỉnh sửa hạn mức"
                  >
                    <span className="btn-icon">✏️</span> Sửa hạn mức
                  </button>
                  <button
                    type="button"
                    className="btn-card-delete"
                    onClick={() => setBudgetToDelete(item)}
                    title="Xóa ngân sách"
                  >
                    <span className="btn-icon">🗑️</span> Xóa
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

        </>
      )}

      {/* Add / Edit Budget Modal */}
      {modalOpen && createPortal(
        <div
          className="modal-backdrop"
          ref={overlayRef}
          onMouseDown={(e) => {
            if (e.target === overlayRef.current) closeModal();
          }}
        >
          <div
            className="category-modal budget-modal"
            role="dialog"
            aria-label={editingBudget ? 'Sửa hạn mức ngân sách' : 'Thiết lập ngân sách mới'}
          >
            <div className="modal-header">
              <div className="modal-title-wrap">
                <span className="modal-icon-badge">{editingBudget ? '✏️' : '🎯'}</span>
                <h2>{editingBudget ? 'Sửa hạn mức ngân sách' : 'Thiết lập ngân sách mới'}</h2>
              </div>
              <button
                type="button"
                className="modal-close"
                onClick={closeModal}
                aria-label="Đóng"
              >
                ✕
              </button>
            </div>

            {modalError && <div className="message message-error">{modalError}</div>}

            <form onSubmit={handleSubmit} className="txn-form">
              {editingBudget ? (
                <div className="budget-modal-category-preview">
                  <div className="preview-icon-box" style={{ '--cat-color': editingBudget.category?.color || '#D69A23' }}>
                    <CategoryIcon
                      icon={editingBudget.category?.icon || 'other'}
                      color={editingBudget.category?.color || '#D69A23'}
                    />
                  </div>
                  <div className="preview-text">
                    <strong>{editingBudget.category?.name}</strong>
                    <span>Áp dụng: Tháng {editingBudget.month}/{editingBudget.year}</span>
                  </div>
                </div>
              ) : (
                <>
                  <label className="txn-form-field">
                    <span>Danh mục chi tiêu <em>*</em></span>
                    <CustomSelect
                      value={formCategory}
                      onChange={(e) => {
                        setFormCategory(e.target.value);
                        if (formErrors.category) setFormErrors((p) => ({ ...p, category: '' }));
                      }}
                      options={categorySelectOptions}
                      placeholder="Chọn danh mục chi tiêu..."
                    />
                    {formErrors.category && <span className="field-error">{formErrors.category}</span>}
                  </label>

                  <div className="txn-form-row txn-form-row-2col">
                    <label className="txn-form-field">
                      <span>Tháng áp dụng <em>*</em></span>
                      <CustomSelect
                        value={formMonth}
                        onChange={(e) => setFormMonth(Number(e.target.value))}
                        options={monthSelectOptions}
                        placeholder="Chọn tháng"
                      />
                    </label>

                    <label className="txn-form-field">
                      <span>Năm <em>*</em></span>
                      <CustomSelect
                        value={formYear}
                        onChange={(e) => setFormYear(Number(e.target.value))}
                        options={yearSelectOptions}
                        placeholder="Chọn năm"
                      />
                    </label>
                  </div>
                </>
              )}

              <label className="txn-form-field">
                <span>Hạn mức ngân sách (VNĐ) <em>*</em></span>
                <input
                  type="number"
                  step="any"
                  min="0"
                  value={formAmount}
                  onChange={(e) => {
                    setFormAmount(e.target.value);
                    if (formErrors.amount) setFormErrors((p) => ({ ...p, amount: '' }));
                  }}
                  onWheel={(e) => e.currentTarget.blur()}
                  placeholder="Ví dụ: 1000000"
                  className={formErrors.amount ? 'input-error' : ''}
                />
                {formErrors.amount && <span className="field-error">{formErrors.amount}</span>}
                {formAmount && !Number.isNaN(parseFloat(formAmount)) && parseFloat(formAmount) > 0 && (
                  <span className="input-helper-text">
                    💡 Tương đương: <strong>{formatMoney(parseFloat(formAmount))}</strong>
                  </span>
                )}
              </label>

              {availableBalance !== null && targetTotalBudget > availableBalance && parseFloat(formAmount) > 0 && (
                <div className="budget-balance-warning-banner is-required" role="alert">
                  <div className="warning-banner-top">
                    <span className="warning-banner-icon">⚠️</span>
                    <div className="warning-banner-body">
                      <strong>Ngân sách vượt số dư khả dụng</strong>
                      <p>
                        Tổng ngân sách dự kiến tháng {formMonth} (<strong>{formatMoney(targetTotalBudget)}</strong>) đang cao hơn số dư khả dụng hiện có (<strong>{formatMoney(availableBalance)}</strong>).
                        Bạn phải giảm hạn mức để tổng ngân sách không vượt quá số dư trước khi lưu.
                      </p>
                    </div>
                  </div>
                </div>
              )}

              <div className="txn-form-actions">
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={closeModal}
                  disabled={submitting}
                >
                  Hủy
                </button>
                <button
                  type="submit"
                  className="btn-primary"
                  disabled={submitting || (availableBalance !== null && targetTotalBudget > availableBalance)}
                >
                  {submitting ? 'Đang lưu...' : editingBudget ? 'Cập nhật hạn mức' : 'Tạo ngân sách'}
                </button>
              </div>
            </form>
          </div>
        </div>,
        document.body
      )}

      {/* Delete Confirmation Modal */}
      <ConfirmModal
        isOpen={!!budgetToDelete}
        title="Xóa ngân sách danh mục?"
        message={`Bạn có chắc chắn muốn xóa ngân sách của danh mục “${budgetToDelete?.category?.name}” cho Tháng ${budgetToDelete?.month}/${budgetToDelete?.year} không? Các giao dịch chi tiêu trước đây vẫn được giữ nguyên vẹn.`}
        confirmText="Xóa ngân sách"
        onConfirm={confirmDelete}
        onCancel={() => setBudgetToDelete(null)}
      />
    </div>
  );
};

export default Budgets;
