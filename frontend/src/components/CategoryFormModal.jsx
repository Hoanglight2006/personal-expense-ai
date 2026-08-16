import { useEffect, useState } from 'react';
import { CATEGORY_COLORS, CATEGORY_PRESETS } from '../constants/categoryIcons';
import CategoryIcon from './CategoryIcon';
import { useModalLock } from '../hooks/useModalLock';

const DEFAULT_PRESET = CATEGORY_PRESETS[0];
const DEFAULT_FORM = {
  name: DEFAULT_PRESET.label,
  icon: DEFAULT_PRESET.value,
  color: DEFAULT_PRESET.color,
  type: DEFAULT_PRESET.type || 'expense',
};

const CategoryFormModal = ({ category, submitting, apiError, onClose, onSubmit }) => {
  useModalLock(true, onClose);
  const [form, setForm] = useState(DEFAULT_FORM);
  const [errors, setErrors] = useState({});

  useEffect(() => {
    setForm(category ? {
      name: category.name,
      icon: category.icon,
      color: category.color,
      type: category.type || 'expense',
    } : DEFAULT_FORM);
    setErrors({});
  }, [category]);

  const updateField = (event) => {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
    setErrors((current) => ({ ...current, [name]: '' }));
  };

  const selectPreset = (preset) => {
    setForm((current) => ({
      ...current,
      icon: preset.value,
      ...(category ? {} : { name: preset.label, color: preset.color, type: preset.type || 'expense' }),
    }));
    setErrors({});
  };

  const selectColor = (color) => {
    setForm((current) => ({ ...current, color }));
    setErrors((current) => ({ ...current, color: '' }));
  };

  const validate = () => {
    const nextErrors = {};
    const trimmedName = form.name.trim();
    if (!trimmedName) nextErrors.name = 'Tên danh mục không được để trống.';
    if (trimmedName.length > 50) nextErrors.name = 'Tên danh mục tối đa 50 ký tự.';
    if (!/^#[0-9A-Fa-f]{6}$/.test(form.color)) nextErrors.color = 'Màu phải có dạng #RRGGBB.';
    if (!CATEGORY_PRESETS.some((item) => item.value === form.icon)) nextErrors.icon = 'Biểu tượng không hợp lệ.';
    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    if (submitting || !validate()) return;
    onSubmit({ ...form, name: form.name.trim(), color: form.color.toUpperCase() });
  };

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={(event) => {
      if (event.target === event.currentTarget && !submitting) onClose();
    }}>
      <section className="category-modal category-modal-refined" role="dialog" aria-modal="true" aria-labelledby="category-modal-title">
        <div className="modal-header">
          <div>
            <span className="eyebrow">Cá nhân hóa không gian tài chính</span>
            <h2 id="category-modal-title">{category ? 'Chỉnh sửa danh mục' : 'Tạo danh mục mới'}</h2>
            <p>Chọn một gợi ý có sẵn rồi tùy chỉnh tên và màu theo sở thích.</p>
          </div>
          <button type="button" className="modal-close" onClick={onClose} disabled={submitting} aria-label="Đóng">×</button>
        </div>

        {apiError && <div className="message message-error" role="alert">{apiError}</div>}

        <form className="category-form" onSubmit={handleSubmit} noValidate>
          <fieldset className="preset-picker">
            <legend>Gợi ý danh mục</legend>
            <p>{category
              ? 'Chọn biểu tượng mới; tên và màu hiện tại sẽ được giữ nguyên.'
              : 'Nhấn vào một mẫu để điền nhanh tên, biểu tượng và màu sắc.'}</p>
            <div className="preset-options">
              {CATEGORY_PRESETS.map((preset) => (
                <button
                  type="button"
                  key={preset.value}
                  className={form.icon === preset.value ? 'preset-option selected' : 'preset-option'}
                  onClick={() => selectPreset(preset)}
                  aria-pressed={form.icon === preset.value}
                >
                  <CategoryIcon icon={preset.value} color={preset.color} />
                  <span>{preset.label}</span>
                </button>
              ))}
            </div>
            {errors.icon && <span className="field-error">{errors.icon}</span>}
          </fieldset>

          <div className="input-group category-type-field" style={{ marginBottom: '20px' }}>
            <div className="label-row">
              <label>Loại danh mục</label>
              <span className="input-helper">Khoản Thu hay Chi?</span>
            </div>
            <div className="txn-type-toggle" role="group">
              <button
                type="button"
                className={`txn-type-btn ${form.type === 'expense' ? 'active expense' : ''}`}
                onClick={() => setForm((p) => ({ ...p, type: 'expense' }))}
              >Dành cho Chi</button>
              <button
                type="button"
                className={`txn-type-btn ${form.type === 'income' ? 'active income' : ''}`}
                onClick={() => setForm((p) => ({ ...p, type: 'income' }))}
              >Dành cho Thu</button>
            </div>
          </div>

          <div className="input-group category-name-field">
            <div className="label-row">
              <label htmlFor="category-name">Tên hiển thị</label>
              <span className="input-helper">Tối đa 50 ký tự</span>
            </div>
            <input id="category-name" name="name" value={form.name} onChange={updateField} maxLength="50" />
            {errors.name && <span className="field-error">{errors.name}</span>}
          </div>

          <fieldset className="color-picker-panel">
            <legend>Màu nhận diện</legend>
            <p>Màu được dùng cho đường viền, nền icon và điểm nhấn trên thẻ.</p>
            <div className="color-picker-content">
              <div className="color-swatches" role="group" aria-label="Bảng màu gợi ý">
                {CATEGORY_COLORS.map((color) => (
                  <button
                    type="button"
                    key={color}
                    className={form.color.toUpperCase() === color ? 'color-swatch selected' : 'color-swatch'}
                    style={{ '--swatch-color': color }}
                    onClick={() => selectColor(color)}
                    aria-label={`Chọn màu ${color}`}
                    aria-pressed={form.color.toUpperCase() === color}
                  >
                    <span>✓</span>
                  </button>
                ))}
              </div>
              <label className="custom-color-field" htmlFor="category-color">
                <span>Tùy chỉnh</span>
                <input id="category-color" name="color" type="color" value={form.color} onChange={updateField} />
                <code>{form.color.toUpperCase()}</code>
              </label>
            </div>
            {errors.color && <span className="field-error">{errors.color}</span>}
          </fieldset>

          <div className="category-preview refined-preview" style={{ '--preview-color': form.color }}>
            <span>Xem trước thẻ</span>
            <div>
              <CategoryIcon icon={form.icon} color={form.color} />
              <strong>{form.name.trim() || 'Tên danh mục'}</strong>
              <small>Sẵn sàng sử dụng khi ghi giao dịch</small>
            </div>
          </div>

          <div className="modal-actions">
            <button type="button" className="btn-secondary" onClick={onClose} disabled={submitting}>Hủy</button>
            <button type="submit" className="btn-primary category-submit" disabled={submitting}>
              {submitting ? 'Đang lưu...' : category ? 'Lưu thay đổi' : 'Tạo danh mục'}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
};

export default CategoryFormModal;
