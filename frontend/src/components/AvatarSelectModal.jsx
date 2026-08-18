import React, { useRef, useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { AVATAR_PRESETS } from '../constants/avatarPresets';
import { useModalLock } from '../hooks/useModalLock';

const AvatarSelectModal = ({
  isOpen,
  currentAvatarUrl,
  username,
  onClose,
  onSavePreset,
  onUploadFile,
  onResetDefault,
  loading = false,
}) => {
  const overlayRef = useRef(null);
  const fileInputRef = useRef(null);

  useModalLock(isOpen, onClose);

  const [activeTab, setActiveTab] = useState('preset'); // 'preset' | 'upload'
  const [selectedPreset, setSelectedPreset] = useState(currentAvatarUrl || '');
  const [uploadFile, setUploadFile] = useState(null);
  const [uploadPreview, setUploadPreview] = useState('');
  const [uploadError, setUploadError] = useState('');
  const [isDragOver, setIsDragOver] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setSelectedPreset(currentAvatarUrl || '');
      setUploadFile(null);
      setUploadPreview('');
      setUploadError('');
    }
  }, [isOpen, currentAvatarUrl]);

  if (!isOpen) return null;

  const initialLetter = username?.trim()?.[0]?.toUpperCase() || 'U';

  const handlePresetSelect = (preset) => {
    setSelectedPreset(preset.url);
    setUploadFile(null);
    setUploadPreview('');
    setUploadError('');
  };

  const handleFileChange = (file) => {
    setUploadError('');
    if (!file) return;

    const validTypes = ['image/jpeg', 'image/png', 'image/webp', 'image/gif', 'image/jpg'];
    if (!validTypes.includes(file.type)) {
      setUploadError('Định dạng ảnh không hợp lệ. Vui lòng chọn ảnh JPG, PNG, WEBP hoặc GIF.');
      return;
    }

    if (file.size > 2 * 1024 * 1024) {
      setUploadError('Dung lượng ảnh vượt quá giới hạn 2MB.');
      return;
    }

    setUploadFile(file);
    const reader = new FileReader();
    reader.onload = (e) => {
      setUploadPreview(e.target.result);
    };
    reader.readAsDataURL(file);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileChange(e.dataTransfer.files[0]);
    }
  };

  const handleSave = async () => {
    if (activeTab === 'upload' && uploadFile) {
      await onUploadFile(uploadFile);
    } else if (activeTab === 'preset' && selectedPreset) {
      await onSavePreset(selectedPreset);
    } else if (!selectedPreset && !uploadFile) {
      await onResetDefault();
    }
  };

  const handleReset = async () => {
    setSelectedPreset('');
    setUploadFile(null);
    setUploadPreview('');
    await onResetDefault();
  };

  return createPortal(
    <div
      className="modal-backdrop avatar-modal-backdrop"
      ref={overlayRef}
      onMouseDown={(e) => {
        if (e.target === overlayRef.current && !loading) onClose();
      }}
      role="presentation"
    >
      <div
        className="avatar-select-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="avatar-modal-title"
      >
        <div className="modal-header">
          <div>
            <span className="eyebrow">Cá nhân hóa hồ sơ FinAI</span>
            <h2 id="avatar-modal-title">Chọn ảnh đại diện</h2>
            <p>Chọn linh vật 3D tài chính FinAI hoặc tự tải ảnh chân dung từ máy tính.</p>
          </div>
          <button
            type="button"
            className="modal-close"
            onClick={onClose}
            disabled={loading}
            aria-label="Đóng"
          >
            ×
          </button>
        </div>

        {/* Tab Switcher */}
        <div className="avatar-tab-nav">
          <button
            type="button"
            className={`avatar-tab-btn ${activeTab === 'preset' ? 'active' : ''}`}
            onClick={() => setActiveTab('preset')}
          >
            ✨ Linh vật 3D FinAI
          </button>
          <button
            type="button"
            className={`avatar-tab-btn ${activeTab === 'upload' ? 'active' : ''}`}
            onClick={() => setActiveTab('upload')}
          >
            📁 Tải ảnh từ thiết bị
          </button>
        </div>

        {/* Tab 1: Preset Mascot Grid */}
        {activeTab === 'preset' && (
          <div className="avatar-preset-tab-content">
            <div className="avatar-presets-grid">
              {AVATAR_PRESETS.map((preset) => {
                const isSelected = selectedPreset === preset.url;
                return (
                  <button
                    key={preset.id}
                    type="button"
                    className={`avatar-preset-card ${isSelected ? 'selected' : ''}`}
                    onClick={() => handlePresetSelect(preset)}
                    style={{ background: preset.bgGradient }}
                    aria-label={`Chọn ${preset.name}`}
                  >
                    <div className="preset-avatar-img-wrap">
                      <img
                        src={preset.url}
                        alt={preset.name}
                        className="preset-avatar-img"
                        width="50"
                        height="50"
                        loading="eager"
                        decoding="async"
                      />
                    </div>
                    <span className="preset-avatar-name">{preset.name}</span>
                    <span className="preset-avatar-tag">{preset.tag}</span>
                    {isSelected && <span className="preset-check-badge">✓</span>}
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Tab 2: Custom Image Upload */}
        {activeTab === 'upload' && (
          <div className="avatar-upload-tab-content">
            <div
              className={`avatar-dropzone ${isDragOver ? 'drag-over' : ''} ${uploadPreview ? 'has-preview' : ''}`}
              onDragOver={(e) => {
                e.preventDefault();
                setIsDragOver(true);
              }}
              onDragLeave={() => setIsDragOver(false)}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="image/png,image/jpeg,image/webp,image/gif,image/jpg"
                style={{ display: 'none' }}
                onChange={(e) => handleFileChange(e.target.files?.[0])}
              />

              {uploadPreview ? (
                <div className="upload-preview-container">
                  <div className="upload-preview-circle">
                    <img src={uploadPreview} alt="Xem trước ảnh tải lên" />
                  </div>
                  <p className="upload-preview-hint">Bấm vào để chọn ảnh khác</p>
                </div>
              ) : (
                <div className="dropzone-prompt">
                  <span className="dropzone-icon">📷</span>
                  <strong>Kéo thả ảnh vào đây hoặc bấm để chọn tệp</strong>
                  <p>Hỗ trợ định dạng JPG, PNG, WEBP, GIF (Tối đa 2MB)</p>
                </div>
              )}
            </div>

            {uploadError && (
              <div className="message message-error" role="alert">
                ⚠️ {uploadError}
              </div>
            )}
          </div>
        )}

        {/* Modal Footer Actions */}
        <div className="avatar-modal-footer">
          <button
            type="button"
            className="btn-ghost-danger"
            onClick={handleReset}
            disabled={loading || (!currentAvatarUrl && !selectedPreset && !uploadFile)}
            title="Sử dụng chữ cái đầu làm đại diện"
          >
            🔄 Về chữ cái mặc định ({initialLetter})
          </button>

          <div className="modal-actions-right">
            <button
              type="button"
              className="btn-secondary"
              onClick={onClose}
              disabled={loading}
            >
              Hủy
            </button>
            <button
              type="button"
              className="btn-primary"
              onClick={handleSave}
              disabled={loading || (activeTab === 'upload' && !uploadFile && !selectedPreset)}
            >
              {loading ? 'Đang lưu...' : 'Lưu ảnh đại diện'}
            </button>
          </div>
        </div>
      </div>
    </div>,
    document.body
  );
};

export default AvatarSelectModal;