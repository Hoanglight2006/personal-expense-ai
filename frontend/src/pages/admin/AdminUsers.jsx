import React, { useState, useEffect, useContext, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { listUsers, toggleUserStatus, resetUserPassword } from '../../api/adminApi';
import { AuthContext } from '../../context/auth-context';
import { getAvatarSrc } from '../../utils/avatar';
import useModalLock from '../../hooks/useModalLock';
import useBackdropDismiss from '../../hooks/useBackdropDismiss';
import AdminCreateUserModal from './AdminCreateUserModal';
import './admin.css';

// Memoized single user row to prevent 50+ rows re-rendering on modal toggle
const AdminUserRow = React.memo(({ user: u, isSelf, isBusy, onLockClick, onResetClick, formatDate }) => {
  const avatarSrc = getAvatarSrc(u.avatar_url);

  return (
    <tr>
      <td>
        <div className="admin-user-cell">
          {avatarSrc ? (
            <img src={avatarSrc} alt="" className="admin-user-avatar" />
          ) : (
            <div className="admin-user-avatar">
              {u.username?.[0]?.toUpperCase() || 'U'}
            </div>
          )}
          <div>
            <div style={{ fontWeight: '700', color: 'var(--text-color, #40352b)' }}>
              {u.username} {isSelf && <span style={{ fontSize: '11px', color: '#b45309' }}>(Bạn)</span>}
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-muted, #817367)' }}>
              {u.email}
            </div>
          </div>
        </div>
      </td>
      <td>
        <span className={`badge-role badge-role-${u.role}`}>
          {u.role === 'admin' ? '🛡️ Admin' : '👤 User'}
        </span>
      </td>
      <td>{formatDate(u.created_at)}</td>
      <td>
        <strong>{u.transactions_count || 0}</strong> giao dịch
      </td>
      <td>
        <span
          className={`badge-role ${
            u.is_locked ? 'badge-status-locked' : 'badge-status-active'
          }`}
        >
          {u.is_locked ? '🔒 Đã khóa' : '✅ Hoạt động'}
        </span>
      </td>
      <td style={{ textAlign: 'right' }}>
        <div style={{ display: 'inline-flex', gap: '8px', alignItems: 'center' }}>
          <button
            type="button"
            className={`btn-action ${u.is_locked ? 'btn-action-unlock' : 'btn-action-lock'}`}
            disabled={isSelf || isBusy}
            title={isSelf ? 'Bạn không thể tự khóa tài khoản của chính mình' : ''}
            onClick={() => onLockClick(u)}
          >
            {isBusy ? '⏳ Đang xử lý...' : u.is_locked ? '🔓 Mở khóa' : '🔒 Khóa'}
          </button>

          <button
            type="button"
            className="btn-action btn-action-reset"
            disabled={isBusy}
            onClick={() => onResetClick(u)}
            title="Tạo mật khẩu tạm thời cho người dùng khi họ quên hoặc mất quyền truy cập"
          >
            🔑 Cấp lại MK
          </button>
        </div>
      </td>
    </tr>
  );
});

const AdminUsersPage = () => {
  const { user: currentAdmin } = useContext(AuthContext);

  const [users, setUsers] = useState([]);
  const [total, setTotal] = useState(0);
  const [activeCount, setActiveCount] = useState(0);
  const [lockedCount, setLockedCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

  // Modals state
  const [lockModal, setLockModal] = useState({ open: false, user: null, action: 'lock' });
  const [resetModal, setResetModal] = useState({ open: false, user: null });
  const [tempPasswordModal, setTempPasswordModal] = useState({ open: false, user: null, tempPassword: '' });
  const [createUserModalOpen, setCreateUserModalOpen] = useState(false);
  const [createdSuccessModal, setCreatedSuccessModal] = useState({ open: false, user: null, password: '' });

  // Action loading tracker per user
  const [actionUserId, setActionUserId] = useState(null);
  const [toast, setToast] = useState(null);

  // Escape key bindings for active modal
  useModalLock(lockModal.open, () => setLockModal({ open: false, user: null, action: 'lock' }));
  useModalLock(resetModal.open, () => setResetModal({ open: false, user: null }));
  useModalLock(tempPasswordModal.open, () => setTempPasswordModal({ open: false, user: null, tempPassword: '' }));
  useModalLock(createdSuccessModal.open, () => setCreatedSuccessModal({ open: false, user: null, password: '' }));

  // Safe backdrop click dismiss handlers (only close if both mousedown and mouseup are on backdrop)
  const lockBackdrop = useBackdropDismiss(
    useCallback(() => setLockModal({ open: false, user: null, action: 'lock' }), []),
    actionUserId !== null
  );
  const resetBackdrop = useBackdropDismiss(
    useCallback(() => setResetModal({ open: false, user: null }), []),
    actionUserId !== null
  );
  const tempPwBackdrop = useBackdropDismiss(
    useCallback(() => setTempPasswordModal({ open: false, user: null, tempPassword: '' }), [])
  );
  const createdSuccessBackdrop = useBackdropDismiss(
    useCallback(() => setCreatedSuccessModal({ open: false, user: null, password: '' }), [])
  );

  const showToast = useCallback((message, type = 'success') => {
    setToast({ message, type });
    const timer = setTimeout(() => setToast(null), 3500);
    return () => clearTimeout(timer);
  }, []);

  const fetchUsers = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const isLockedParam =
        statusFilter === 'all' ? undefined : statusFilter === 'locked';

      const data = await listUsers({
        search: search.trim() || undefined,
        is_locked: isLockedParam,
        page: 1,
        page_size: 50,
      });

      setUsers(data.items || []);
      setTotal(data.total || 0);
      setActiveCount(data.active_count || 0);
      setLockedCount(data.locked_count || 0);
    } catch (err) {
      console.error('Lỗi khi tải danh sách người dùng:', err);
      setError('Không thể tải danh sách tài khoản người dùng.');
    } finally {
      setLoading(false);
    }
  }, [search, statusFilter]);

  const handleCreateUserSuccess = useCallback((createdUser, rawPassword) => {
    setCreateUserModalOpen(false);
    setCreatedSuccessModal({ open: true, user: createdUser, password: rawPassword });
    showToast(`Cấp thành công tài khoản ${createdUser.email}!`);
    fetchUsers();
  }, [showToast, fetchUsers]);

  useEffect(() => {
    const timer = setTimeout(fetchUsers, 250);
    return () => clearTimeout(timer);
  }, [fetchUsers]);

  // 1. Toggle Lock/Unlock
  const handleExecuteToggleStatus = async () => {
    const target = lockModal.user;
    if (!target) return;
    try {
      setActionUserId(target.id);
      const willLock = lockModal.action === 'lock';
      const updated = await toggleUserStatus(target.id, willLock);

      setUsers((prev) =>
        prev.map((u) => (u.id === updated.id ? { ...u, is_locked: updated.is_locked } : u))
      );

      if (willLock) {
        setLockedCount((c) => c + 1);
        setActiveCount((c) => Math.max(0, c - 1));
        showToast(`Đã khóa thành công tài khoản ${target.email}`);
      } else {
        setLockedCount((c) => Math.max(0, c - 1));
        setActiveCount((c) => c + 1);
        showToast(`Đã mở khóa thành công tài khoản ${target.email}`);
      }

      setLockModal({ open: false, user: null, action: 'lock' });
    } catch (err) {
      const msg = err.response?.data?.detail || 'Lỗi khi cập nhật trạng thái người dùng.';
      showToast(msg, 'error');
    } finally {
      setActionUserId(null);
    }
  };

  // 2. Reset Password
  const handleExecuteResetPassword = async () => {
    const target = resetModal.user;
    if (!target) return;
    try {
      setActionUserId(target.id);
      const res = await resetUserPassword(target.id);

      // Auto-unlock in UI if it was locked
      setUsers((prev) =>
        prev.map((u) => (u.id === target.id ? { ...u, is_locked: false } : u))
      );

      setResetModal({ open: false, user: null });
      setTempPasswordModal({
        open: true,
        user: target,
        tempPassword: res.temp_password,
      });
      showToast(`Đã cấp mật khẩu mới cho ${target.email}`);
    } catch (err) {
      const msg = err.response?.data?.detail || 'Lỗi khi cấp lại mật khẩu.';
      showToast(msg, 'error');
    } finally {
      setActionUserId(null);
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    showToast('Đã sao chép mật khẩu vào bộ nhớ đệm!');
  };

  const formatDate = useCallback((dateStr) => {
    if (!dateStr) return '—';
    try {
      return new Date(dateStr).toLocaleDateString('vi-VN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
      });
    } catch {
      return dateStr;
    }
  }, []);

  const handleLockClick = useCallback((u) => {
    setLockModal({ open: true, user: u, action: u.is_locked ? 'unlock' : 'lock' });
  }, []);

  const handleResetClick = useCallback((u) => {
    setResetModal({ open: true, user: u });
  }, []);

  return (
    <div className="admin-page">
      {/* Toast Notification */}
      {toast && (
        <div className={`admin-toast ${toast.type}`}>
          <span>{toast.type === 'error' ? '⚠️' : '✅'}</span>
          <span>{toast.message}</span>
        </div>
      )}

      {/* 1. Hero Banner */}
      <div className="admin-hero">
        <div className="admin-hero-content">
          <div className="admin-hero-tag">Quản Trị Người Dùng</div>
          <div className="admin-hero-title-row">
            <div className="admin-hero-icon-box" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                <circle cx="9" cy="7" r="4" />
                <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
                <path d="M16 3.13a4 4 0 0 1 0 7.75" />
              </svg>
            </div>
            <h1>Quản Lý Người Dùng & Sự Cố Tài Khoản</h1>
          </div>
          <p className="admin-hero-quote">
            Hỗ trợ mở khóa tài khoản và cấp lại mật khẩu tạm thời khi người dùng gặp sự cố
          </p>
        </div>
      </div>

      {/* 2. Search & Filter Toolbar */}
      <div className="admin-toolbar">
        <div style={{ flex: '1', minWidth: '260px' }}>
          <input
            type="search"
            className="admin-search-input"
            placeholder="🔍 Tìm theo username hoặc email người dùng..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <div className="admin-filter-tabs" style={{ margin: 0 }}>
          <button
            type="button"
            className={`admin-tab-pill ${statusFilter === 'all' ? 'active' : ''}`}
            onClick={() => setStatusFilter('all')}
          >
            Tất cả ({total})
          </button>
          <button
            type="button"
            className={`admin-tab-pill ${statusFilter === 'active' ? 'active' : ''}`}
            onClick={() => setStatusFilter('active')}
          >
            Hoạt động ({activeCount})
          </button>
          <button
            type="button"
            className={`admin-tab-pill ${statusFilter === 'locked' ? 'active' : ''}`}
            onClick={() => setStatusFilter('locked')}
          >
            Bị khóa ({lockedCount})
          </button>
        </div>

        <button
          type="button"
          className="btn-modal-submit"
          style={{ whiteSpace: 'nowrap', display: 'flex', alignItems: 'center', gap: '6px' }}
          onClick={() => setCreateUserModalOpen(true)}
        >
          <span>➕</span>
          <span>Cấp tài khoản mới</span>
        </button>
      </div>

      {/* 4. Error banner */}
      {error && (
        <div style={{ padding: '16px', background: '#fee2e2', color: '#991b1b', borderRadius: '16px', fontWeight: '600' }}>
          {error}
        </div>
      )}

      {/* 5. Users Table */}
      <div className="admin-table-container">
        {loading ? (
          <div style={{ textAlign: 'center', padding: '40px 20px', color: 'var(--text-muted, #817367)', fontWeight: '700' }}>
            ⏳ Đang tải danh sách người dùng...
          </div>
        ) : users.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '48px 20px', color: 'var(--text-muted, #817367)' }}>
            <div style={{ fontSize: '2rem', marginBottom: '8px' }}>🔍</div>
            <h3 style={{ margin: '0 0 6px 0', color: 'var(--text-color, #40352b)' }}>Không tìm thấy người dùng</h3>
            <p style={{ margin: 0, fontSize: '0.9rem' }}>Không có tài khoản nào phù hợp với bộ lọc tìm kiếm hiện tại.</p>
          </div>
        ) : (
          <table className="admin-table">
            <thead>
              <tr>
                <th>Người dùng</th>
                <th>Vai trò</th>
                <th>Ngày tạo</th>
                <th>Số giao dịch</th>
                <th>Trạng thái</th>
                <th style={{ textAlign: 'right' }}>Thao tác hỗ trợ</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <AdminUserRow
                  key={u.id}
                  user={u}
                  isSelf={u.id === currentAdmin?.id}
                  isBusy={actionUserId === u.id}
                  onLockClick={handleLockClick}
                  onResetClick={handleResetClick}
                  formatDate={formatDate}
                />
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Modal 1: Lock/Unlock Confirmation */}
      {lockModal.open && createPortal(
        <div
          className="admin-modal-backdrop"
          {...lockBackdrop}
          role="presentation"
        >
          <div className="admin-modal-content" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
            <div className="admin-modal-header">
              <h3>
                {lockModal.action === 'lock' ? '🔒 Xác nhận khóa tài khoản' : '🔓 Xác nhận mở khóa tài khoản'}
              </h3>
              <p>
                {lockModal.action === 'lock'
                  ? `Người dùng "${lockModal.user?.username}" (${lockModal.user?.email}) sẽ bị từ chối mọi phiên đăng nhập ngay lập tức.`
                  : `Người dùng "${lockModal.user?.username}" (${lockModal.user?.email}) sẽ có thể đăng nhập và sử dụng hệ thống bình thường.`}
              </p>
            </div>
            <div className="admin-modal-actions">
              <button
                type="button"
                className="btn-modal-cancel"
                onClick={() => setLockModal({ open: false, user: null, action: 'lock' })}
                disabled={actionUserId !== null}
              >
                Hủy bỏ
              </button>
              <button
                type="button"
                className="btn-modal-submit"
                style={{
                  background: lockModal.action === 'lock' ? '#ef4444' : '#10b981',
                  color: '#fff',
                }}
                onClick={handleExecuteToggleStatus}
                disabled={actionUserId !== null}
              >
                {actionUserId !== null ? 'Đang xử lý...' : lockModal.action === 'lock' ? 'Khóa tài khoản' : 'Mở khóa'}
              </button>
            </div>
          </div>
        </div>,
        document.body
      )}

      {/* Modal 2: Reset Password Confirmation */}
      {resetModal.open && createPortal(
        <div
          className="admin-modal-backdrop"
          {...resetBackdrop}
          role="presentation"
        >
          <div className="admin-modal-content" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
            <div className="admin-modal-header">
              <h3>🔑 Xác nhận cấp lại mật khẩu</h3>
              <p>
                Bạn có chắc chắn muốn tạo mật khẩu tạm thời cho tài khoản <strong>"{resetModal.user?.email}"</strong>? Mật khẩu cũ sẽ bị vô hiệu hóa ngay lập tức.
              </p>
            </div>
            <div className="admin-modal-actions">
              <button
                type="button"
                className="btn-modal-cancel"
                onClick={() => setResetModal({ open: false, user: null })}
                disabled={actionUserId !== null}
              >
                Hủy bỏ
              </button>
              <button
                type="button"
                className="btn-modal-submit"
                onClick={handleExecuteResetPassword}
                disabled={actionUserId !== null}
              >
                {actionUserId !== null ? '⏳ Đang tạo...' : 'Xác nhận cấp mới'}
              </button>
            </div>
          </div>
        </div>,
        document.body
      )}

      {/* Modal 3: Temporary Password Display */}
      {tempPasswordModal.open && createPortal(
        <div
          className="admin-modal-backdrop"
          {...tempPwBackdrop}
          role="presentation"
        >
          <div className="admin-modal-content" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
            <div className="admin-modal-header">
              <h3>🔑 Cấp mật khẩu thành công</h3>
              <p>
                Mật khẩu tạm thời cho tài khoản <strong>{tempPasswordModal.user?.email}</strong>:
              </p>
            </div>

            <div className="admin-temp-pw-box">
              {tempPasswordModal.tempPassword}
            </div>

            <p style={{ fontSize: '13px', color: '#b45309', margin: '0 0 16px 0', lineHeight: 1.5 }}>
              ⚠️ Vui lòng sao chép và gửi mật khẩu này cho người dùng. Người dùng có thể đăng nhập và đổi mật khẩu trong mục Hồ sơ.
            </p>

            <div className="admin-modal-actions">
              <button
                type="button"
                className="btn-modal-cancel"
                onClick={() => copyToClipboard(tempPasswordModal.tempPassword)}
              >
                📋 Sao chép
              </button>
              <button
                type="button"
                className="btn-modal-submit"
                onClick={() => setTempPasswordModal({ open: false, user: null, tempPassword: '' })}
              >
                Hoàn tất
              </button>
            </div>
          </div>
        </div>,
        document.body
      )}

      {/* Modal 4: Create User Modal */}
      <AdminCreateUserModal
        isOpen={createUserModalOpen}
        onClose={() => setCreateUserModalOpen(false)}
        onSuccess={handleCreateUserSuccess}
      />

      {/* Modal 5: Created Account Success Modal */}
      {createdSuccessModal.open && createPortal(
        <div
          className="admin-modal-backdrop"
          {...createdSuccessBackdrop}
          role="presentation"
        >
          <div className="admin-modal-content" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
            <div className="admin-modal-header">
              <h3>🎉 Cấp tài khoản thành công</h3>
              <p>
                Tài khoản mới đã được kích hoạt thành công trên hệ thống.
              </p>
            </div>

            <div style={{ background: '#fdfbf7', border: '1px solid #e7ded4', borderRadius: '16px', padding: '16px', margin: '16px 0', fontSize: '0.9rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ color: '#817367' }}>Tên người dùng:</span>
                <strong>{createdSuccessModal.user?.username}</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ color: '#817367' }}>Email:</span>
                <strong>{createdSuccessModal.user?.email}</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ color: '#817367' }}>Vai trò:</span>
                <span style={{ 
                  background: createdSuccessModal.user?.role === 'admin' ? '#fef3c7' : '#e0e7ff',
                  color: createdSuccessModal.user?.role === 'admin' ? '#92400e' : '#3730a3',
                  padding: '2px 8px',
                  borderRadius: '6px',
                  fontWeight: 700,
                  fontSize: '0.8rem',
                }}>
                  {createdSuccessModal.user?.role === 'admin' ? '🛡️ Quản trị viên' : '👤 Người dùng'}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '12px', paddingTop: '10px', borderTop: '1px dashed #d1c5b8' }}>
                <span style={{ color: '#817367' }}>Mật khẩu khởi tạo:</span>
                <code style={{ fontSize: '1rem', color: '#b45309', fontWeight: 800 }}>
                  {createdSuccessModal.password}
                </code>
              </div>
            </div>

            <p style={{ fontSize: '12px', color: '#817367', margin: '0 0 16px 0', lineHeight: 1.5 }}>
              💡 Bạn có thể sao chép thông tin đăng nhập trên để gửi cho người dùng.
            </p>

            <div className="admin-modal-actions">
              <button
                type="button"
                className="btn-modal-cancel"
                onClick={() => {
                  const info = `FinAI - Thông tin tài khoản:\nEmail: ${createdSuccessModal.user?.email}\nTên người dùng: ${createdSuccessModal.user?.username}\nMật khẩu: ${createdSuccessModal.password}\nVai trò: ${createdSuccessModal.user?.role}`;
                  copyToClipboard(info);
                }}
              >
                📋 Sao chép thông tin
              </button>
              <button
                type="button"
                className="btn-modal-submit"
                onClick={() => setCreatedSuccessModal({ open: false, user: null, password: '' })}
              >
                Đóng
              </button>
            </div>
          </div>
        </div>,
        document.body
      )}
    </div>
  );
};

export default AdminUsersPage;
