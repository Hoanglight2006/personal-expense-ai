import { useCallback, useDeferredValue, useEffect, useMemo, useState } from 'react';
import CategoryCard from '../components/CategoryCard';
import CategoryFormModal from '../components/CategoryFormModal';
import CustomSelect from '../components/CustomSelect';
import {
  createCategory,
  createDefaultCategories,
  getCategories,
  hideCategory,
  restoreCategory,
  updateCategory,
  deleteCategory,
} from '../api/categoryApi';
import { preloadCategoryIconAssets } from '../constants/categoryIcons';
import { decimalToCents } from '../utils/money';
import ConfirmModal from '../components/ConfirmModal';

const apiMessage = (error) => {
  const detail = error?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map((item) => item.msg).filter(Boolean).join(' ');
  if (!error?.response) {
    return navigator.onLine
      ? 'Không thể kết nối đến máy chủ. Hãy kiểm tra backend hoặc cấu hình mạng.'
      : 'Thiết bị đang mất kết nối mạng.';
  }
  if (error.response.status >= 500) {
    return 'Máy chủ gặp lỗi khi xử lý danh mục. Vui lòng thử lại.';
  }
  return `Yêu cầu danh mục thất bại (HTTP ${error.response.status}).`;
};

const Categories = () => {
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('active');
  const [typeFilter, setTypeFilter] = useState('all');
  const [sort, setSort] = useState('amount_desc');
  const [editing, setEditing] = useState(undefined);
  const [categoryToHide, setCategoryToHide] = useState(null);
  const [categoryToDelete, setCategoryToDelete] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [modalError, setModalError] = useState('');
  const [busyId, setBusyId] = useState(null);
  const [creatingDefaults, setCreatingDefaults] = useState(false);
  const deferredSearch = useDeferredValue(search);

  const loadCategories = useCallback(async (signal) => {
    setLoading(true);
    setError('');
    try {
      const data = await getCategories({ status: 'all' }, signal);
      setCategories(data.items || []);
    } catch (requestError) {
      if (requestError.code !== 'ERR_CANCELED') setError(apiMessage(requestError));
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, []);

  const visibleCategories = useMemo(() => {
    const normalizedSearch = deferredSearch.trim().normalize('NFKC').toLocaleLowerCase('vi');
    const filtered = categories.filter((category) => {
      if (status === 'active' && !category.is_active) return false;
      if (status === 'hidden' && category.is_active) return false;
      if (typeFilter !== 'all' && category.type !== typeFilter) return false;
      if (!normalizedSearch) return true;
      return category.name.normalize('NFKC').toLocaleLowerCase('vi').includes(normalizedSearch);
    });
    return filtered.toSorted((first, second) => {
      if (sort === 'name_asc') return first.name.localeCompare(second.name, 'vi');
      if (sort === 'name_desc') return second.name.localeCompare(first.name, 'vi');
      
      const firstAmount = decimalToCents(first.total_amount);
      const secondAmount = decimalToCents(second.total_amount);
      if (firstAmount === secondAmount) return first.name.localeCompare(second.name, 'vi');
      const direction = firstAmount > secondAmount ? 1 : -1;
      return sort === 'amount_asc' ? direction : -direction;
    });
  }, [categories, deferredSearch, status, typeFilter, sort]);

  const mergeCategoryMetadata = useCallback((saved) => {
    setCategories((current) => current.map((category) => (
      category.id === saved.id
        ? {
          ...category,
          name: saved.name,
          icon: saved.icon,
          color: saved.color,
          is_active: saved.is_active,
          is_default: saved.is_default,
          updated_at: saved.updated_at,
        }
        : category
    )));
  }, []);

  useEffect(() => {
    const preload = () => preloadCategoryIconAssets();
    if ('requestIdleCallback' in window) {
      const idleId = window.requestIdleCallback(preload, { timeout: 1200 });
      return () => window.cancelIdleCallback(idleId);
    }
    const timeout = window.setTimeout(preload, 300);
    return () => window.clearTimeout(timeout);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => loadCategories(controller.signal), 80);
    return () => {
      window.clearTimeout(timeout);
      controller.abort();
    };
  }, [loadCategories]);

  useEffect(() => {
    if (!success) return undefined;
    const timeout = window.setTimeout(() => setSuccess(''), 3500);
    return () => window.clearTimeout(timeout);
  }, [success]);

  const openCreate = useCallback(() => {
    setModalError('');
    setEditing(null);
  }, []);

  const openEdit = useCallback((category) => {
    setModalError('');
    setEditing(category);
  }, []);

  const closeModal = () => {
    if (!submitting) setEditing(undefined);
  };

  const submitCategory = async (payload) => {
    if (submitting) return;
    setSubmitting(true);
    setModalError('');
    try {
      if (editing) {
        const saved = await updateCategory(editing.id, payload);
        mergeCategoryMetadata(saved);
        setSuccess('Đã cập nhật danh mục.');
      } else {
        const saved = await createCategory(payload);
        setCategories((current) => [...current, saved]);
        setSuccess('Đã thêm danh mục mới.');
      }
      setEditing(undefined);
    } catch (requestError) {
      setModalError(apiMessage(requestError));
    } finally {
      setSubmitting(false);
    }
  };

  const handleHide = useCallback((category) => {
    setCategoryToHide(category);
  }, []);

  const handleDelete = useCallback((category) => {
    setCategoryToDelete(category);
  }, []);

  const confirmHide = async () => {
    if (!categoryToHide || busyId) return;
    const category = categoryToHide;
    setCategoryToHide(null);
    setBusyId(category.id);
    setError('');
    try {
      const saved = await hideCategory(category.id);
      mergeCategoryMetadata(saved);
      setSuccess('Đã ẩn danh mục.');
    } catch (requestError) {
      setError(apiMessage(requestError));
    } finally {
      setBusyId(null);
    }
  };

  const confirmDelete = async () => {
    if (!categoryToDelete || busyId) return;
    const category = categoryToDelete;
    setCategoryToDelete(null);
    setBusyId(category.id);
    setError('');
    try {
      await deleteCategory(category.id);
      setCategories((current) => current.filter((c) => c.id !== category.id));
      setSuccess('Đã xóa danh mục vĩnh viễn.');
    } catch (requestError) {
      setError(apiMessage(requestError));
    } finally {
      setBusyId(null);
    }
  };

  const handleRestore = useCallback(async (category) => {
    if (busyId) return;
    setBusyId(category.id);
    setError('');
    try {
      const saved = await restoreCategory(category.id);
      mergeCategoryMetadata(saved);
      setSuccess('Đã khôi phục danh mục.');
    } catch (requestError) {
      setError(apiMessage(requestError));
    } finally {
      setBusyId(null);
    }
  }, [busyId, mergeCategoryMetadata]);

  const handleCreateDefaults = async () => {
    if (creatingDefaults) return;
    setCreatingDefaults(true);
    setError('');
    try {
      const created = await createDefaultCategories();
      if (created.length > 0) {
        setCategories((current) => [...current, ...created]);
      }
      setSuccess(created.length > 0
        ? `Đã thêm ${created.length} danh mục gợi ý.`
        : 'Các danh mục gợi ý đã tồn tại. Nếu chưa thấy, hãy xem bộ lọc “Đã ẩn”.');
    } catch (requestError) {
      setError(apiMessage(requestError));
    } finally {
      setCreatingDefaults(false);
    }
  };

  const hasFilters = Boolean(search || status !== 'active' || typeFilter !== 'all');
  const filteredEmpty = hasFilters || categories.length > 0;

  const statusOptions = [
    { value: 'active', label: 'Đang sử dụng' },
    { value: 'hidden', label: 'Đã ẩn' },
    { value: 'all', label: 'Tất cả trạng thái' }
  ];

  const typeOptions = [
    { value: 'all', label: 'Tất cả thu/chi' },
    { value: 'expense', label: 'Khoản chi' },
    { value: 'income', label: 'Khoản thu' }
  ];

  const sortOptions = [
    { value: 'amount_desc', label: 'Chi/Thu nhiều nhất' },
    { value: 'amount_asc', label: 'Chi/Thu ít nhất' },
    { value: 'name_asc', label: 'Tên A–Z' },
    { value: 'name_desc', label: 'Tên Z–A' }
  ];

  return (
    <main className="category-page">
      <section className="category-hero">
        <div>
          <span className="eyebrow">Không gian tài chính của bạn</span>
          <h1>Quản lý danh mục</h1>
          <p>Tổ chức các khoản thu chi cho dòng tiền cá nhân.</p>
        </div>
        <button type="button" className="btn-primary add-category-button" onClick={openCreate}>+ Thêm danh mục</button>
      </section>

      <section className="category-toolbar" aria-label="Bộ lọc danh mục">
        <div className="toolbar-row">
          <label className="search-field">
            <span>Tìm kiếm</span>
            <input type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Nhập tên danh mục..." />
          </label>
          <label>
            <span>Loại</span>
            <CustomSelect value={typeFilter} onChange={(event) => setTypeFilter(event.target.value)} options={typeOptions} />
          </label>
          <label>
            <span>Trạng thái</span>
            <CustomSelect value={status} onChange={(event) => setStatus(event.target.value)} options={statusOptions} />
          </label>
          <label>
            <span>Sắp xếp</span>
            <CustomSelect value={sort} onChange={(event) => setSort(event.target.value)} options={sortOptions} />
          </label>
        </div>
      </section>

      {success && <div className="message message-success page-message" role="status">{success}</div>}
      {error && <div className="message message-error page-message" role="alert">{error}</div>}

      {loading && categories.length === 0 ? (
        <div className="category-state" aria-live="polite"><span className="loading-spinner" />Đang tải danh mục...</div>
      ) : visibleCategories.length === 0 ? (
        <div className="category-state empty-state">
          <span className="empty-state-icon">◎</span>
          <h2>{filteredEmpty ? 'Không có kết quả phù hợp' : 'Chưa có danh mục nào'}</h2>
          <p>{filteredEmpty ? 'Hãy thử điều chỉnh từ khóa hoặc bộ lọc.' : 'Tạo danh mục đầu tiên để bắt đầu quản lý thu chi.'}</p>
          {!filteredEmpty && (
            <div className="empty-state-actions">
              <button type="button" className="btn-primary empty-add-button" onClick={handleCreateDefaults} disabled={creatingDefaults}>
                {creatingDefaults ? 'Đang tạo...' : 'Dùng bộ danh mục gợi ý'}
              </button>
              <button type="button" className="btn-secondary" onClick={openCreate} disabled={creatingDefaults}>Tạo tùy chỉnh</button>
            </div>
          )}
        </div>
      ) : (
        <section className="category-grid" aria-label="Danh sách danh mục">
          {visibleCategories.map((category, index) => (
            <CategoryCard
              key={category.id}
              category={category}
              index={index}
              onEdit={openEdit}
              onHide={handleHide}
              onRestore={handleRestore}
              onDelete={handleDelete}
              busy={busyId === category.id}
            />
          ))}
        </section>
      )}

      {editing !== undefined && (
        <CategoryFormModal
          category={editing}
          submitting={submitting}
          apiError={modalError}
          onClose={() => setEditing(undefined)}
          onSubmit={submitCategory}
        />
      )}

      <ConfirmModal
        isOpen={!!categoryToHide}
        title="Ẩn danh mục?"
        message={`Ẩn danh mục “${categoryToHide?.name}”? Các giao dịch cũ sử dụng danh mục này vẫn được giữ nguyên.`}
        confirmText="Ẩn danh mục"
        onConfirm={confirmHide}
        onCancel={() => setCategoryToHide(null)}
      />

      <ConfirmModal
        isOpen={!!categoryToDelete}
        title="Xóa vĩnh viễn danh mục?"
        message={`Bạn có chắc chắn muốn xóa danh mục “${categoryToDelete?.name}” không? Các giao dịch cũ thuộc danh mục này vẫn được giữ lại.`}
        confirmText="Xóa danh mục"
        onConfirm={confirmDelete}
        onCancel={() => setCategoryToDelete(null)}
      />
    </main>
  );
};

export default Categories;
