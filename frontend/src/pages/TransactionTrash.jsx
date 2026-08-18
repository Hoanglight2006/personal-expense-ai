import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import TransactionCard from '../components/TransactionCard';
import ConfirmModal from '../components/ConfirmModal';
import CustomSelect from '../components/CustomSelect';
import {
  getTransactionTrash,
  restoreTransaction as apiRestore,
  deleteTransactionPermanently as apiDeletePermanently,
} from '../api/transactionApi';

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

const TransactionTrash = () => {
  const [transactions, setTransactions] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const [sort, setSort] = useState('date_desc');
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [busyId, setBusyId] = useState(null);
  const [txnToDelete, setTxnToDelete] = useState(null);

  const loadTrash = useCallback(async (signal) => {
    setLoading(true);
    setError('');
    try {
      const data = await getTransactionTrash({ sort, page, page_size: pageSize }, signal);
      setTransactions(data.items);
      setTotalCount(data.total_count);
    } catch (err) {
      if (err.code !== 'ERR_CANCELED') setError(apiMessage(err));
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, [sort, page, pageSize]);

  useEffect(() => {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => loadTrash(controller.signal), 50);
    return () => { window.clearTimeout(timeout); controller.abort(); };
  }, [loadTrash]);

  // Reset page when sort changes
  useEffect(() => { setPage(1); }, [sort]);

  useEffect(() => {
    if (!success) return;
    const t = window.setTimeout(() => setSuccess(''), 4000);
    return () => window.clearTimeout(t);
  }, [success]);

  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));

  const handleRestore = async (txn) => {
    if (busyId) return;
    setBusyId(txn.id);
    setError('');
    try {
      const res = await apiRestore(txn.id);
      setTransactions((prev) => prev.filter((t) => t.id !== txn.id));
      setTotalCount((prev) => prev - 1);
      if (res.category_warning) {
        setSuccess(res.category_warning);
      } else {
        setSuccess('Đã khôi phục giao dịch.');
      }
    } catch (err) {
      setError(apiMessage(err));
    } finally {
      setBusyId(null);
    }
  };

  const handleDeletePermanently = (txn) => {
    setTxnToDelete(txn);
  };

  const confirmDeletePermanently = async () => {
    if (!txnToDelete || busyId) return;
    const txn = txnToDelete;
    setTxnToDelete(null);
    setBusyId(txn.id);
    setError('');
    try {
      await apiDeletePermanently(txn.id);
      setTransactions((prev) => prev.filter((t) => t.id !== txn.id));
      setTotalCount((prev) => prev - 1);
      setSuccess('Đã xóa vĩnh viễn giao dịch.');
    } catch (err) {
      setError(apiMessage(err));
    } finally {
      setBusyId(null);
    }
  };

  const sortOptions = [
    { value: 'date_desc', label: 'Mới nhất' },
    { value: 'date_asc', label: 'Cũ nhất' },
    { value: 'amount_desc', label: 'Số tiền cao' },
    { value: 'amount_asc', label: 'Số tiền thấp' }
  ];

  return (
    <div className="fade-in">
      <main className="txn-page">
        <section className="txn-hero">
          <div>
            <Link to="/transactions" className="eyebrow" style={{ textDecoration: 'none' }}>
              ← Quay lại Giao dịch
            </Link>
            <h1>Thùng rác giao dịch</h1>
            <p>Các giao dịch đã xóa có thể được khôi phục hoặc xóa vĩnh viễn tại đây.</p>
          </div>
        </section>

        <section className="txn-toolbar" aria-label="Bộ lọc thùng rác">
          <div className="toolbar-row txn-toolbar-row-2" style={{ gridTemplateColumns: '1fr auto' }}>
            <label>
              <span>Sắp xếp</span>
              <CustomSelect value={sort} onChange={(e) => setSort(e.target.value)} options={sortOptions} />
            </label>
            <div className="txn-count-display">
              <span className="txn-count-label">Giao dịch đã xóa</span>
              <strong>{totalCount}</strong>
            </div>
          </div>
        </section>

        {success && <div className="message message-success page-message" role="status">{success}</div>}
        {error && <div className="message message-error page-message" role="alert">{error}</div>}

        {loading && transactions.length > 0 && (
          <div className="txn-refreshing" role="status">
            <span className="loading-spinner" />Đang cập nhật…
          </div>
        )}

        {loading && transactions.length === 0 ? (
          <div className="txn-state" aria-live="polite"><span className="loading-spinner" />Đang tải thùng rác...</div>
        ) : transactions.length === 0 ? (
          <div className="txn-state empty-state">
            <span className="empty-state-icon">🗑️</span>
            <h2>Thùng rác trống</h2>
            <p>Chưa có giao dịch nào bị xóa.</p>
            <Link to="/transactions" className="btn-secondary">Quay lại Giao dịch</Link>
          </div>
        ) : (
          <>
            <section className="txn-list" aria-label="Danh sách thùng rác">
              {transactions.map((txn) => (
                <TransactionCard
                  key={txn.id}
                  transaction={txn}
                  isTrashView
                  onRestore={handleRestore}
                  onDeletePermanently={handleDeletePermanently}
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
        
        <ConfirmModal
          isOpen={!!txnToDelete}
          title="Xóa vĩnh viễn?"
          message={`Hành động này không thể hoàn tác. Toàn bộ dữ liệu của giao dịch này sẽ bị xóa khỏi hệ thống.`}
          confirmText="Xóa vĩnh viễn"
          isDanger={true}
          onConfirm={confirmDeletePermanently}
          onCancel={() => setTxnToDelete(null)}
        />
      </main>
    </div>
  );
};

export default TransactionTrash;
