import React, { useContext, useEffect, useMemo, useState, useRef } from 'react';
import { AuthContext } from '../context/auth-context';
import { changePassword, updateProfile, uploadAvatar } from '../api/authApi';
import { useModalLock } from '../hooks/useModalLock';
import AvatarSelectModal from '../components/AvatarSelectModal';
import { getAvatarSrc } from '../utils/avatar';

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const errorMessage = (error, fallback) => {
  const detail = error?.response?.data?.detail;
  if (typeof detail === 'string') {
    if (detail === 'Username or email already exists.') return 'Tên đăng nhập hoặc email đã được sử dụng.';
    return detail;
  }
  if (Array.isArray(detail)) return detail[0]?.msg || fallback;
  return fallback;
};

const formatMemberDate = (value) => {
  if (!value) return 'Chưa cập nhật';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'Chưa cập nhật';
  try {
    return new Intl.DateTimeFormat('vi-VN', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    }).format(date);
  } catch {
    return 'Chưa cập nhật';
  }
};

/**
 * Tính toán Hạng chi tiêu & Danh hiệu tương ứng theo số tháng tuân thủ tài chính
 */
const getUserFinancialRank = (createdAt) => {
  if (!createdAt) {
    return {
      rankName: 'Hạng Đồng: Mầm Non',
      rankIcon: '🌱',
      badgeTitle: '🪙 Bạn nhỏ quản chi chăm chỉ ✨',
      level: 1,
    };
  }

  const createdDate = new Date(createdAt);
  const now = new Date();
  if (Number.isNaN(createdDate.getTime())) {
    return {
      rankName: 'Hạng Đồng: Mầm Non',
      rankIcon: '🌱',
      badgeTitle: '🪙 Bạn nhỏ quản chi chăm chỉ ✨',
      level: 1,
    };
  }

  const diffMonths = (now.getFullYear() - createdDate.getFullYear()) * 12 + (now.getMonth() - createdDate.getMonth());

  if (diffMonths >= 6) {
    return {
      rankName: 'Hạng Kim Cương: Tự Do',
      rankIcon: '💎',
      badgeTitle: '👑 Huyền thoại chi tiêu thông thái 💎',
      level: 4,
    };
  }
  if (diffMonths >= 3) {
    return {
      rankName: 'Hạng Vàng: Bậc Thầy',
      rankIcon: '🥇',
      badgeTitle: '🏆 Chuyên gia quản lý tài chính 🌟',
      level: 3,
    };
  }
  if (diffMonths >= 1) {
    return {
      rankName: 'Hạng Bạc: Kỷ Luật',
      rankIcon: '🥈',
      badgeTitle: '⭐ Tay hòm chìa khóa thông thái 🗝️',
      level: 2,
    };
  }

  return {
    rankName: 'Hạng Đồng: Mầm Non',
    rankIcon: '🌱',
    badgeTitle: '🪙 Bạn nhỏ quản chi chăm chỉ ✨',
    level: 1,
  };
};

const PasswordInput = ({
  id,
  label,
  value,
  onChange,
  onBlur,
  autoComplete,
  placeholder,
  error,
}) => {
  const [visible, setVisible] = useState(false);

  return (
    <div className={`profile-field ${error ? 'has-error' : ''}`}>
      <label className="profile-field-label" htmlFor={id}>
        {label}
      </label>
      <div className="profile-password-input">
        <span className="profile-input-icon" aria-hidden="true">🔒</span>
        <input
          id={id}
          type={visible ? 'text' : 'password'}
          value={value}
          onChange={onChange}
          onBlur={onBlur}
          autoComplete={autoComplete}
          placeholder={placeholder || '••••••••'}
          className={error ? 'input-error' : ''}
          required
        />
        <button
          type="button"
          className="profile-eye-toggle"
          onClick={() => setVisible((current) => !current)}
          aria-label={visible ? `Ẩn ${label.toLowerCase()}` : `Hiện ${label.toLowerCase()}`}
          title={visible ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'}
        >
          {visible ? '🙈' : '👁️'}
        </button>
      </div>
      {error && (
        <span className="profile-inline-error" role="alert">
          <span className="error-dot" aria-hidden="true">•</span> {error}
        </span>
      )}
    </div>
  );
};

/* Success Pop-up Modal Component */
const SuccessModal = ({ isOpen, title, message, type = 'profile', onClose }) => {
  const overlayRef = useRef(null);
  useModalLock(isOpen, onClose);

  useEffect(() => {
    if (!isOpen) return;
    const timer = setTimeout(() => {
      onClose();
    }, 3600);
    return () => clearTimeout(timer);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      className="modal-backdrop profile-modal-backdrop"
      ref={overlayRef}
      onMouseDown={(e) => {
        if (e.target === overlayRef.current) onClose();
      }}
      role="dialog"
      aria-modal="true"
    >
      <div className="profile-success-modal">
        <button
          type="button"
          className="profile-modal-close"
          onClick={onClose}
          aria-label="Đóng thông báo"
        >
          ✕
        </button>
        <div className="profile-modal-icon-wrap">
          <div className="profile-modal-icon">
            {type === 'password' ? '🔑' : '✨'}
          </div>
          <span className="profile-modal-check">✓</span>
        </div>

        <h3 className="profile-modal-title">{title}</h3>
        <p className="profile-modal-message">{message}</p>

        <div className="profile-modal-actions">
          <button
            type="button"
            className="btn-primary profile-modal-btn"
            onClick={onClose}
            autoFocus
          >
            Tuyệt vời
          </button>
        </div>
      </div>
    </div>
  );
};

const Profile = () => {
  const { user, setUser } = useContext(AuthContext);

  // Forms state
  const [profileForm, setProfileForm] = useState({ username: '', email: '' });
  const [passwordForm, setPasswordForm] = useState({ current: '', next: '', confirm: '' });

  // Touched state for real-time validation
  const [profileTouched, setProfileTouched] = useState({ username: false, email: false });
  const [passwordTouched, setPasswordTouched] = useState({ current: false, next: false, confirm: false });

  // API level errors
  const [profileApiError, setProfileApiError] = useState('');
  const [passwordApiError, setPasswordApiError] = useState('');

  const [savingProfile, setSavingProfile] = useState(false);
  const [savingPassword, setSavingPassword] = useState(false);
  const [avatarModalOpen, setAvatarModalOpen] = useState(false);
  const [savingAvatar, setSavingAvatar] = useState(false);
  const [avatarLoadFailed, setAvatarLoadFailed] = useState(false);

  useEffect(() => {
    setAvatarLoadFailed(false);
  }, [user?.avatar_url]);

  // Success Modal State
  const [modalState, setModalState] = useState({
    isOpen: false,
    title: '',
    message: '',
    type: 'profile',
  });

  useEffect(() => {
    setProfileForm({ username: user?.username || '', email: user?.email || '' });
  }, [user]);

  // Real-time financial rank
  const userRank = useMemo(() => getUserFinancialRank(user?.created_at), [user?.created_at]);

  // Real-time validation errors for profile
  const usernameError = useMemo(() => {
    const val = profileForm.username.trim();
    if (!profileTouched.username && val === (user?.username || '')) return '';
    if (val.length === 0) return 'Tên đăng nhập không được để trống.';
    if (val.length < 3) return 'Tên đăng nhập phải có ít nhất 3 ký tự.';
    return '';
  }, [profileForm.username, profileTouched.username, user]);

  const emailError = useMemo(() => {
    const val = profileForm.email.trim();
    if (!profileTouched.email && val === (user?.email || '')) return '';
    if (val.length === 0) return 'Email không được để trống.';
    if (!EMAIL_REGEX.test(val)) return 'Email không đúng định dạng (ví dụ: user@example.com).';
    return '';
  }, [profileForm.email, profileTouched.email, user]);

  // Real-time validation errors for password
  const nextPasswordError = useMemo(() => {
    if (!passwordTouched.next && passwordForm.next.length === 0) return '';
    if (passwordForm.next.length === 0) return 'Vui lòng nhập mật khẩu mới.';
    if (passwordForm.next.length < 8) return 'Mật khẩu mới phải có ít nhất 8 ký tự.';
    return '';
  }, [passwordForm.next, passwordTouched.next]);

  const confirmPasswordError = useMemo(() => {
    if (!passwordTouched.confirm && passwordForm.confirm.length === 0) return '';
    if (passwordForm.confirm.length === 0) return 'Vui lòng xác nhận mật khẩu mới.';
    if (passwordForm.next !== passwordForm.confirm) return 'Mật khẩu xác nhận không khớp.';
    return '';
  }, [passwordForm.next, passwordForm.confirm, passwordTouched.confirm]);

  const profileChanged = useMemo(
    () => profileForm.username.trim() !== (user?.username || '') || profileForm.email.trim().toLowerCase() !== (user?.email || ''),
    [profileForm, user],
  );

  const hasProfileFormError = Boolean(usernameError || emailError);
  const hasPasswordFormError = Boolean(nextPasswordError || confirmPasswordError);

  const closeModal = () => {
    setModalState((prev) => ({ ...prev, isOpen: false }));
  };

  const handleProfileChange = (field, value) => {
    setProfileTouched((prev) => ({ ...prev, [field]: true }));
    setProfileApiError('');
    setProfileForm((prev) => ({ ...prev, [field]: value }));
  };

  const handlePasswordChange = (field, value) => {
    setPasswordTouched((prev) => ({ ...prev, [field]: true }));
    setPasswordApiError('');
    setPasswordForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSavePresetAvatar = async (presetUrl) => {
    setSavingAvatar(true);
    try {
      const updated = await updateProfile({ avatar_url: presetUrl });
      setUser(updated);
      setAvatarModalOpen(false);
      setModalState({
        isOpen: true,
        title: 'Đổi ảnh đại diện thành công!',
        message: 'Linh vật FinAI đã được chọn làm ảnh đại diện của bạn.',
        type: 'profile',
      });
    } catch (err) {
      setProfileApiError(errorMessage(err, 'Không thể cập nhật ảnh đại diện. Vui lòng thử lại.'));
    } finally {
      setSavingAvatar(false);
    }
  };

  const handleUploadAvatar = async (file) => {
    setSavingAvatar(true);
    try {
      const updated = await uploadAvatar(file);
      setUser(updated);
      setAvatarModalOpen(false);
      setModalState({
        isOpen: true,
        title: 'Tải ảnh đại diện thành công!',
        message: 'Ảnh chân dung đã được tải lên và lưu làm đại diện tài khoản.',
        type: 'profile',
      });
    } catch (err) {
      setProfileApiError(errorMessage(err, 'Không thể tải ảnh đại diện lên. Vui lòng thử lại.'));
    } finally {
      setSavingAvatar(false);
    }
  };

  const handleResetDefaultAvatar = async () => {
    setSavingAvatar(true);
    try {
      const updated = await updateProfile({ avatar_url: '' });
      setUser(updated);
      setAvatarModalOpen(false);
      setModalState({
        isOpen: true,
        title: 'Đặt lại thành công!',
        message: 'Ảnh đại diện đã được hoàn về chữ cái mặc định.',
        type: 'profile',
      });
    } catch (err) {
      setProfileApiError(errorMessage(err, 'Không thể đặt lại ảnh đại diện. Vui lòng thử lại.'));
    } finally {
      setSavingAvatar(false);
    }
  };

  const submitProfile = async (event) => {
    event.preventDefault();
    setProfileTouched({ username: true, email: true });
    setProfileApiError('');

    const username = profileForm.username.trim();
    const email = profileForm.email.trim().toLowerCase();

    if (username.length < 3 || !EMAIL_REGEX.test(email)) {
      return;
    }

    setSavingProfile(true);
    try {
      const updated = await updateProfile({ username, email });
      setUser(updated);
      setModalState({
        isOpen: true,
        title: 'Cập nhật thành công!',
        message: 'Thông tin hồ sơ đã được cập nhật.',
        type: 'profile',
      });
    } catch (error) {
      setProfileApiError(errorMessage(error, 'Không thể cập nhật hồ sơ. Vui lòng thử lại.'));
    } finally {
      setSavingProfile(false);
    }
  };

  const submitPassword = async (event) => {
    event.preventDefault();
    setPasswordTouched({ current: true, next: true, confirm: true });
    setPasswordApiError('');

    if (passwordForm.next.length < 8) {
      return;
    }
    if (passwordForm.next !== passwordForm.confirm) {
      return;
    }

    setSavingPassword(true);
    try {
      const result = await changePassword(passwordForm.current, passwordForm.next);
      setPasswordForm({ current: '', next: '', confirm: '' });
      setPasswordTouched({ current: false, next: false, confirm: false });
      setModalState({
        isOpen: true,
        title: 'Đổi mật khẩu thành công!',
        message: result.message || 'Đổi mật khẩu thành công.',
        type: 'password',
      });
    } catch (error) {
      setPasswordApiError(errorMessage(error, 'Không thể đổi mật khẩu. Vui lòng thử lại.'));
    } finally {
      setSavingPassword(false);
    }
  };

  const initial = user?.username?.trim()?.[0]?.toUpperCase() || 'U';

  return (
    <div className="profile-page">
      {/* Avatar Selection Modal */}
      <AvatarSelectModal
        isOpen={avatarModalOpen}
        currentAvatarUrl={user?.avatar_url}
        username={user?.username}
        loading={savingAvatar}
        onClose={() => setAvatarModalOpen(false)}
        onSavePreset={handleSavePresetAvatar}
        onUploadFile={handleUploadAvatar}
        onResetDefault={handleResetDefaultAvatar}
      />

      {/* Success Modal Dialog */}
      <SuccessModal
        isOpen={modalState.isOpen}
        title={modalState.title}
        message={modalState.message}
        type={modalState.type}
        onClose={closeModal}
      />

      {/* Main Header */}
      <header className="profile-hero">
        <div className="profile-hero-title-group">
          <span className="profile-eyebrow">Tài khoản & Thiết lập</span>
          <h1>Hồ sơ người dùng</h1>
          <p>Quản lý thông tin tài khoản và xem cấp bậc kỷ luật tài chính của bạn.</p>
        </div>
      </header>

      {/* Bento Hero Summary Banner */}
      <section className="profile-summary-bento" aria-label="Tổng quan tài khoản">
        <div className="profile-summary-left">
          <div className="profile-avatar-wrapper" onClick={() => setAvatarModalOpen(true)} title="Bấm để thay đổi ảnh đại diện">
            <div className="profile-summary-avatar" aria-hidden="true">
              {user?.avatar_url && !avatarLoadFailed ? (
                <img
                  src={getAvatarSrc(user.avatar_url)}
                  alt={user.username || 'Avatar'}
                  className="profile-avatar-img-element"
                  onError={() => setAvatarLoadFailed(true)}
                />
              ) : (
                initial
              )}
            </div>
            <button
              type="button"
              className="profile-avatar-edit-badge"
              aria-label="Thay đổi ảnh đại diện"
              onClick={(e) => {
                e.stopPropagation();
                setAvatarModalOpen(true);
              }}
            >
              📷
            </button>
            <span className="profile-avatar-badge" title="Tài khoản đang hoạt động"></span>
          </div>

          <div className="profile-summary-copy">
            <div className="profile-badge-tag cute-badge">
              {userRank.badgeTitle}
            </div>
            <h2>{user?.username || 'Người dùng'}</h2>
            <p className="profile-summary-email">{user?.email || 'Chưa cập nhật email'}</p>
          </div>
        </div>

        <div className="profile-summary-meta">
          <div className="profile-meta-item">
            <span className="profile-meta-icon" aria-hidden="true">📅</span>
            <div>
              <span className="profile-meta-label">Ngày cùng FinAI</span>
              <strong className="profile-meta-value">{formatMemberDate(user?.created_at)}</strong>
            </div>
          </div>
          <div className="profile-meta-item" title="Cứ mỗi tháng duy trì thói quen chi tiêu tốt, bạn sẽ được thăng hạng!">
            <span className="profile-meta-icon" aria-hidden="true">{userRank.rankIcon}</span>
            <div>
              <span className="profile-meta-label">Cấp bậc tài chính</span>
              <strong className="profile-meta-value text-cute">{userRank.rankName}</strong>
            </div>
          </div>
        </div>
      </section>

      {/* Action Panels */}
      <div className="profile-panels">
        {/* Panel 1: Profile Info */}
        <section className="profile-panel">
          <div className="profile-panel-heading">
            <span className="profile-panel-icon info-icon">✏️</span>
            <div>
              <h2>Thông tin cá nhân</h2>
              <p>Cập nhật tên đăng nhập và email nhận diện tài khoản.</p>
            </div>
          </div>

          <form className="profile-form" onSubmit={submitProfile} noValidate>
            <div className={`profile-field ${usernameError ? 'has-error' : ''}`}>
              <label className="profile-field-label" htmlFor="profile-username">
                Tên đăng nhập
              </label>
              <div className="profile-input-wrapper">
                <span className="profile-input-icon" aria-hidden="true">👤</span>
                <input
                  id="profile-username"
                  type="text"
                  maxLength="50"
                  value={profileForm.username}
                  onChange={(e) => handleProfileChange('username', e.target.value)}
                  onBlur={() => setProfileTouched((prev) => ({ ...prev, username: true }))}
                  autoComplete="username"
                  placeholder="Nhập tên đăng nhập"
                  className={usernameError ? 'input-error' : ''}
                  required
                />
              </div>
              {usernameError && (
                <span className="profile-inline-error" role="alert">
                  <span className="error-dot" aria-hidden="true">•</span> {usernameError}
                </span>
              )}
            </div>

            <div className={`profile-field ${emailError ? 'has-error' : ''}`}>
              <label className="profile-field-label" htmlFor="profile-email">
                Email
              </label>
              <div className="profile-input-wrapper">
                <span className="profile-input-icon" aria-hidden="true">✉️</span>
                <input
                  id="profile-email"
                  type="email"
                  value={profileForm.email}
                  onChange={(e) => handleProfileChange('email', e.target.value)}
                  onBlur={() => setProfileTouched((prev) => ({ ...prev, email: true }))}
                  autoComplete="email"
                  placeholder="name@example.com"
                  className={emailError ? 'input-error' : ''}
                  required
                />
              </div>
              {emailError && (
                <span className="profile-inline-error" role="alert">
                  <span className="error-dot" aria-hidden="true">•</span> {emailError}
                </span>
              )}
            </div>

            {profileApiError && (
              <div className="profile-feedback error" role="alert">
                <span className="feedback-icon" aria-hidden="true">⚠️</span>
                <span>{profileApiError}</span>
              </div>
            )}

            <button
              type="submit"
              className="btn-primary profile-submit"
              disabled={!profileChanged || hasProfileFormError || savingProfile}
            >
              {savingProfile ? 'Đang lưu…' : 'Lưu thay đổi'}
            </button>
          </form>
        </section>

        {/* Panel 2: Password Update */}
        <section className="profile-panel">
          <div className="profile-panel-heading">
            <span className="profile-panel-icon security-icon">🔐</span>
            <div>
              <h2>Đổi mật khẩu</h2>
              <p>Mật khẩu an toàn cần có ít nhất 8 ký tự.</p>
            </div>
          </div>

          <form className="profile-form" onSubmit={submitPassword} noValidate>
            <PasswordInput
              id="current-password"
              label="Mật khẩu hiện tại"
              value={passwordForm.current}
              onChange={(e) => handlePasswordChange('current', e.target.value)}
              onBlur={() => setPasswordTouched((prev) => ({ ...prev, current: true }))}
              autoComplete="current-password"
              placeholder="Nhập mật khẩu hiện tại"
            />
            <PasswordInput
              id="new-password"
              label="Mật khẩu mới"
              value={passwordForm.next}
              onChange={(e) => handlePasswordChange('next', e.target.value)}
              onBlur={() => setPasswordTouched((prev) => ({ ...prev, next: true }))}
              autoComplete="new-password"
              placeholder="Tối thiểu 8 ký tự"
              error={nextPasswordError}
            />
            <PasswordInput
              id="confirm-new-password"
              label="Xác nhận mật khẩu mới"
              value={passwordForm.confirm}
              onChange={(e) => handlePasswordChange('confirm', e.target.value)}
              onBlur={() => setPasswordTouched((prev) => ({ ...prev, confirm: true }))}
              autoComplete="new-password"
              placeholder="Nhập lại mật khẩu mới"
              error={confirmPasswordError}
            />

            {passwordApiError && (
              <div className="profile-feedback error" role="alert">
                <span className="feedback-icon" aria-hidden="true">⚠️</span>
                <span>{passwordApiError}</span>
              </div>
            )}

            <button
              type="submit"
              className="btn-primary profile-submit"
              disabled={hasPasswordFormError || savingPassword || !passwordForm.current || !passwordForm.next || !passwordForm.confirm}
            >
              {savingPassword ? 'Đang cập nhật…' : 'Cập nhật mật khẩu'}
            </button>
          </form>
        </section>
      </div>
    </div>
  );
};

export default Profile;
