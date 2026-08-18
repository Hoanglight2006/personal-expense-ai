import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import TransactionCard from '../components/TransactionCard';
import TransactionFormModal from '../components/TransactionFormModal';
import ExcelPreviewModal from '../components/ExcelPreviewModal';
import ConfirmModal from '../components/ConfirmModal';
import CustomDatePicker from '../components/CustomDatePicker';
import CustomSelect from '../components/CustomSelect';
import {
  getTransactions,
  createTransaction as apiCreate,
  updateTransaction as apiUpdate,
  trashTransaction as apiTrash,
  duplicateTransaction as apiDuplicate,
  parseExcel as apiParseExcel,
  importTransactions as apiImportTransactions,
} from '../api/transactionApi';
import { getCategories } from '../api/categoryApi';
import { PAYMENT_METHODS } from '../constants/paymentMethods';

const pad = (v) => String(v).padStart(2, '0');
const todayValue = () => {
  const d = new Date();
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
};

const formatMoney = (amount) => {
  return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(amount || 0);
};

const TYPE_OPTIONS = [
  { value: '', label: 'Tất cả' },
  { value: 'expense', label: 'Chi' },
  { value: 'income', label: 'Thu' },
];

const SORT_OPTIONS = [
  { value: 'date_desc', label: 'Mới nhất' },
  { value: 'date_asc', label: 'Cũ nhất' },
  { value: 'amount_desc', label: 'Số tiền cao' },
  { value: 'amount_asc', label: 'Số tiền thấp' },
];

const SEARCH_DEBOUNCE_MS = 250;

const apiMessage = (error) => {
  const detail = error?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map((i) => i.msg).filter(Boolean).join(' ');
  if (!error?.response) {
    return navigator.onLine
      ? 'Không thể kết nối đến máy chủ.'
      : 'Thiết bị đang mất kết nối mạng.';
  }
  if (error.response.status >= 500) return 'Máy chủ gặp lỗi. Vui lòng thử lại.';
  return `Yêu cầu thất bại (HTTP ${error.response.status}).`;
};

const Transactions = () => {

  // Data
  const [transactions, setTransactions] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [categories, setCategories] = useState([]);
  const [categoriesLoading, setCategoriesLoading] = useState(true);
  const [categoriesError, setCategoriesError] = useState('');
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Filters
  const [search, setSearch] = useState('');
  const [dateStart, setDateStart] = useState('');
  const [dateEnd, setDateEnd] = useState('');
  const [filterType, setFilterType] = useState('');
  const [filterCategory, setFilterCategory] = useState('');
  const [filterPayment, setFilterPayment] = useState('');
  const [sort, setSort] = useState('date_desc');
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [debouncedSearch, setDebouncedSearch] = useState('');

  // Modal
  const [modalOpen, setModalOpen] = useState(false);
  const [editingTxn, setEditingTxn] = useState(null);
  const [prefillData, setPrefillData] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [modalError, setModalError] = useState('');
  const [txnToDelete, setTxnToDelete] = useState(null);
  const [busyId, setBusyId] = useState(null);

  // Excel
  const [excelPreviewData, setExcelPreviewData] = useState(null);
  const [excelIdempotencyKey, setExcelIdempotencyKey] = useState('');
  const [excelImportError, setExcelImportError] = useState('');
  const [excelLoading, setExcelLoading] = useState(false);
  const errorRef = useRef(null);
  const loadErrorRef = useRef(null);
  const categoriesErrorRef = useRef(null);
  const transactionsAbortRef = useRef(null);
  const transactionsRequestSequenceRef = useRef(0);

  const loadCategories = useCallback(async (signal) => {
    setCategoriesLoading(true);
    setCategoriesError('');
    try {
      const data = await getCategories({ status: 'all' }, signal);
      setCategories(data.items || []);
    } catch (requestError) {
      if (requestError.code !== 'ERR_CANCELED') {
        setCategoriesError(apiMessage(requestError));
      }
    } finally {
      if (!signal?.aborted) setCategoriesLoading(false);
    }
  }, []);

  // Load categories once
  useEffect(() => {
    const controller = new AbortController();
    loadCategories(controller.signal);
    return () => controller.abort();
  }, [loadCategories]);

  useEffect(() => {
    const normalizedSearch = search.trim();
    if (normalizedSearch === debouncedSearch) return undefined;
    const timeout = window.setTimeout(() => {
      setDebouncedSearch(normalizedSearch);
      setPage(1);
    }, SEARCH_DEBOUNCE_MS);
    return () => window.clearTimeout(timeout);
  }, [search, debouncedSearch]);

  // Build params
  const queryParams = useMemo(() => {
    const params = { sort, page, page_size: pageSize };
    if (debouncedSearch) params.search = debouncedSearch;
    if (dateStart) params.date_start = dateStart;
    if (dateEnd) params.date_end = dateEnd;
    if (filterType) params.type = filterType;
    if (filterCategory) params.category_id = filterCategory;
    if (filterPayment) params.payment_method = filterPayment;
    return params;
  }, [debouncedSearch, dateStart, dateEnd, filterType, filterCategory, filterPayment, sort, page, pageSize]);

  const loadTransactions = useCallback(async () => {
    transactionsAbortRef.current?.abort();
    const controller = new AbortController();
    transactionsAbortRef.current = controller;
    const requestSequence = ++transactionsRequestSequenceRef.current;

    setLoading(true);
    setLoadError('');
    try {
      const data = await getTransactions(queryParams, controller.signal);
      if (requestSequence !== transactionsRequestSequenceRef.current) return;
      setTransactions(data.items);
      setTotalCount(data.total_count);
    } catch (err) {
      if (
        requestSequence === transactionsRequestSequenceRef.current
        && err.code !== 'ERR_CANCELED'
      ) {
        setLoadError(apiMessage(err));
      }
    } finally {
      if (requestSequence === transactionsRequestSequenceRef.current) {
        if (transactionsAbortRef.current === controller) {
          transactionsAbortRef.current = null;
        }
        setLoading(false);
      }
    }
  }, [queryParams]);

  useEffect(() => {
    loadTransactions();
    return () => {
      transactionsAbortRef.current?.abort();
      transactionsRequestSequenceRef.current += 1;
    };
  }, [loadTransactions]);

  // Success toast auto-clear
  useEffect(() => {
    if (!success) return;
    const t = window.setTimeout(() => setSuccess(''), 3500);
    return () => window.clearTimeout(t);
  }, [success]);

  useEffect(() => {
    const target = categoriesError
      ? categoriesErrorRef.current
      : loadError
        ? loadErrorRef.current
        : errorRef.current;
    if (!target || (!error && !loadError && !categoriesError)) return undefined;
    const frame = window.requestAnimationFrame(() => {
      target.scrollIntoView?.({ behavior: 'smooth', block: 'center' });
      target.focus({ preventScroll: true });
    });
    return () => window.cancelAnimationFrame(frame);
  }, [error, loadError, categoriesError]);

  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));

  // --- Actions ---
  const openCreate = useCallback(() => {
    setEditingTxn(null);
    setPrefillData(null);
    setModalOpen(true);
    setModalError('');
  }, []);

  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    if (location.state?.openAddModal) {
      openCreate();
      // Clear state so it doesn't reopen on refresh
      navigate(location.pathname, { replace: true, state: {} });
    }
  }, [location, navigate, openCreate]);

  const openEdit = useCallback((txn) => {
    setEditingTxn(txn);
    setPrefillData(null);
    setModalError('');
    setModalOpen(true);
  }, []);

  const openDuplicate = useCallback(async (txn) => {
    try {
      const data = await apiDuplicate(txn.id);
      setEditingTxn(null);
      setPrefillData({
        amount: data.amount,
        type: data.type,
        category_id: data.category_id,
        transaction_date: todayValue(),
        description: data.description || '',
        payment_method: data.payment_method,
      });
      setModalError('');
      setModalOpen(true);
    } catch (err) {
      setError(apiMessage(err));
    }
  }, []);

  const closeModal = () => {
    if (!submitting) {
      setModalOpen(false);
      setEditingTxn(null);
      setPrefillData(null);
    }
  };

  const handleSubmit = async (payload) => {
    if (submitting) return;
    setSubmitting(true);
    setModalError('');
    try {
      if (editingTxn) {
        await apiUpdate(editingTxn.id, payload);
        setSuccess('Đã cập nhật giao dịch.');
      } else {
        await apiCreate(payload);
        if (payload.saving_goal_id && payload.saving_goal_amount) {
          setSuccess(`Đã thêm giao dịch thu nhập và trích ${formatMoney(payload.saving_goal_amount)} vào mục tiêu tiết kiệm!`);
        } else {
          setSuccess('Đã thêm giao dịch mới.');
        }
      }
      setModalOpen(false);
      setEditingTxn(null);
      setPrefillData(null);
      // Reload
      loadTransactions();
    } catch (err) {
      setModalError(apiMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  const handleTrash = useCallback((txn) => {
    setTxnToDelete(txn);
  }, []);

  const confirmTrash = async () => {
    if (!txnToDelete || busyId) return;
    const txn = txnToDelete;
    setTxnToDelete(null);
    setBusyId(txn.id);
    setError('');
    try {
      await apiTrash(txn.id);
      setTransactions((prev) => prev.filter((t) => t.id !== txn.id));
      setTotalCount((prev) => prev - 1);
      setSuccess('Đã chuyển giao dịch vào thùng rác.');
    } catch (err) {
      setError(apiMessage(err));
    } finally {
      setBusyId(null);
    }
  };

  const categoryOptions = useMemo(() => [
    { value: '', label: 'Tất cả' },
    ...categories.map((c) => ({
      value: c.id,
      label: `${c.name}${c.is_active ? '' : ' (đã ẩn)'}`,
    }))
  ], [categories]);

  const paymentOptions = useMemo(() => [
    { value: '', label: 'Tất cả' },
    ...PAYMENT_METHODS.map((m) => ({ value: m.value, label: m.label }))
  ], []);

  const changeDateStart = useCallback((event) => {
    setDateStart(event.target.value);
    setPage(1);
  }, []);

  const changeDateEnd = useCallback((event) => {
    setDateEnd(event.target.value);
    setPage(1);
  }, []);

  const changeType = useCallback((event) => {
    setFilterType(event.target.value);
    setPage(1);
  }, []);

  const changeCategory = useCallback((event) => {
    setFilterCategory(event.target.value);
    setPage(1);
  }, []);

  const changePayment = useCallback((event) => {
    setFilterPayment(event.target.value);
    setPage(1);
  }, []);

  const changeSort = useCallback((event) => {
    setSort(event.target.value);
    setPage(1);
  }, []);

  const handleExcelUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = null; // reset

    setExcelLoading(true);
    setError('');
    setModalError('');
    try {
      const data = await apiParseExcel(file);
      setModalOpen(false);
      setExcelPreviewData(data.items);
      setExcelIdempotencyKey(crypto.randomUUID());
      setExcelImportError('');
    } catch (err) {
      setModalError(apiMessage(err));
    } finally {
      setExcelLoading(false);
    }
  };

  const handleConfirmExcel = async (validRows) => {
    setSubmitting(true);
    setExcelImportError('');
    try {
      const payload = {
        idempotency_key: excelIdempotencyKey,
        rows: validRows.map((r) => ({
          amount: r.amount,
          type: r.type,
          category_id: Number(r.category_id),
          transaction_date: r.transaction_date,
          description: r.description,
          payment_method: r.payment_method || 'bank_transfer',
        })),
      };
      const res = await apiImportTransactions(payload);
      setSuccess(`Nhập thành công ${res.success_count} giao dịch (thất bại: ${res.error_count}).`);
      setExcelPreviewData(null);
      setExcelIdempotencyKey('');
      loadTransactions();
    } catch (err) {
      setExcelImportError(apiMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fade-in">
      <main className="txn-page">
        <section className="txn-hero">
          <div>
            <span className="eyebrow">Quản lý tài chính</span>
            <h1>Giao dịch</h1>
            <p>Ghi nhận, tìm kiếm và quản lý mọi khoản thu chi.</p>
          </div>
          <div className="txn-hero-actions">
            <button type="button" className="btn-primary add-txn-button" onClick={openCreate} disabled={categoriesLoading || Boolean(categoriesError)}>+ Thêm giao dịch</button>
            <Link to="/transactions/trash" className="btn-secondary txn-trash-link">🗑️ Thùng rác</Link>
          </div>
        </section>

        <section className="txn-toolbar" aria-label="Bộ lọc giao dịch">
          <div className="toolbar-row txn-toolbar-row">
            <label className="search-field">
              <span>Tìm kiếm</span>
              <input type="search" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Tìm theo ghi chú..." />
            </label>
            <label>
              <span>Loại</span>
              <CustomSelect value={filterType} onChange={changeType} options={TYPE_OPTIONS} />
            </label>
            <label>
              <span>Danh mục</span>
              <CustomSelect value={filterCategory} onChange={changeCategory} options={categoryOptions} />
            </label>
            <label>
              <span>Thanh toán</span>
              <CustomSelect value={filterPayment} onChange={changePayment} options={paymentOptions} />
            </label>
          </div>
          <div className="toolbar-row txn-toolbar-row-2">
            <label>
              <span>Từ ngày</span>
              <CustomDatePicker value={dateStart} onChange={changeDateStart} />
            </label>
            <label>
              <span>Đến ngày</span>
              <CustomDatePicker value={dateEnd} onChange={changeDateEnd} />
            </label>
            <label>
              <span>Sắp xếp</span>
              <CustomSelect value={sort} onChange={changeSort} options={SORT_OPTIONS} />
            </label>
            <div className="txn-count-display">
              <span className="txn-count-label">Kết quả</span>
              <strong>{totalCount}</strong>
            </div>
          </div>
        </section>

        {success && <div className="message message-success page-message" role="status">{success}</div>}
        {error && <div ref={errorRef} className="message message-error page-message" role="alert" tabIndex={-1}>{error}</div>}
        {loadError && (
          <div ref={loadErrorRef} className="message message-error page-message" role="alert" tabIndex={-1}>
            <span>Không thể tải giao dịch: {loadError}</span>{' '}
            <button type="button" className="btn-secondary" onClick={() => loadTransactions()} disabled={loading}>
              {loading ? 'Đang thử lại...' : 'Thử lại'}
            </button>
          </div>
        )}
        {categoriesError && (
          <div ref={categoriesErrorRef} className="message message-error page-message" role="alert" tabIndex={-1}>
            <span>Không thể tải danh mục: {categoriesError}</span>{' '}
            <button type="button" className="btn-secondary" onClick={() => loadCategories()} disabled={categoriesLoading}>
              {categoriesLoading ? 'Đang thử lại...' : 'Thử lại'}
            </button>
          </div>
        )}

        {loading && transactions.length > 0 && (
          <div className="txn-refreshing" role="status">
            <span className="loading-spinner" />Đang cập nhật…
          </div>
        )}

        {loading && transactions.length === 0 ? (
          <div className="txn-state" aria-live="polite"><span className="loading-spinner" />Đang tải giao dịch...</div>
        ) : loadError && transactions.length === 0 ? null
        : transactions.length === 0 ? (
          <div className="txn-state empty-state">
            <span className="empty-state-icon">◎</span>
            <h2>{debouncedSearch || dateStart || dateEnd || filterType || filterCategory || filterPayment ? 'Không có kết quả phù hợp' : 'Chưa có giao dịch nào'}</h2>
            <p>{debouncedSearch || dateStart || dateEnd || filterType || filterCategory || filterPayment ? 'Hãy thử điều chỉnh bộ lọc.' : 'Thêm giao dịch đầu tiên để bắt đầu quản lý.'}</p>
            {!(debouncedSearch || dateStart || dateEnd || filterType || filterCategory || filterPayment) && (
              <button type="button" className="btn-primary" onClick={openCreate} disabled={categoriesLoading || Boolean(categoriesError)}>+ Thêm giao dịch</button>
            )}
          </div>
        ) : (
          <>
            <section className="txn-list" aria-label="Danh sách giao dịch">
              {transactions.map((txn) => (
                <TransactionCard
                  key={txn.id}
                  transaction={txn}
                  onEdit={openEdit}
                  onTrash={handleTrash}
                  onDuplicate={openDuplicate}
                  busy={busyId === txn.id}
                />
              ))}
            </section>
            {totalPages > 1 && (
              <nav className="txn-pagination" aria-label="Phân trang">
                <button type="button" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>‹ Trước</button>
                <span>Trang {page} / {totalPages}</span>
                <button type="button" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>Sau ›</button>
              </nav>
            )}
          </>
        )}

        {modalOpen && (
          <TransactionFormModal
            transaction={editingTxn}
            categories={categories}
            submitting={submitting}
            apiError={modalError}
            onClose={closeModal}
            onSubmit={handleSubmit}
            prefillData={prefillData}
            onExcelUpload={handleExcelUpload}
            isExcelLoading={excelLoading}
            categoriesReady={!categoriesLoading && !categoriesError}
          />
        )}

        {excelPreviewData && (
          <ExcelPreviewModal
            data={excelPreviewData}
            categories={categories}
            submitting={submitting}
            apiError={excelImportError}
            onCancel={() => {
              setExcelPreviewData(null);
              setExcelIdempotencyKey('');
              setExcelImportError('');
            }}
            onConfirm={handleConfirmExcel}
          />
        )}
        
        <ConfirmModal
          isOpen={!!txnToDelete}
          title="Chuyển vào thùng rác?"
          message={`Giao dịch sẽ được chuyển vào thùng rác và có thể khôi phục lại trong tương lai.`}
          confirmText="Chuyển vào thùng rác"
          onConfirm={confirmTrash}
          onCancel={() => setTxnToDelete(null)}
        />
      </main>
    </div>
  );
};

export default Transactions;
