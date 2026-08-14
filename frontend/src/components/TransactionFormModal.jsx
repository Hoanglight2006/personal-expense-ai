import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { PAYMENT_METHODS } from '../constants/paymentMethods';
import { scanImage } from '../api/transactionApi';
import CustomDatePicker from './CustomDatePicker';
import CustomSelect from './CustomSelect';

const pad = (v) => String(v).padStart(2, '0');
const todayValue = () => {
  const d = new Date();
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
};

const TransactionFormModal = ({
  transaction,
  categories,
  submitting,
  apiError,
  onClose,
  onSubmit,
  prefillData,
  onExcelUpload,
  isExcelLoading,
}) => {
  const isEdit = transaction !== null && transaction !== undefined;
  const overlayRef = useRef(null);

  const initialValues = useMemo(() => {
    if (prefillData) {
      return {
        amount: prefillData.amount || '',
        type: prefillData.type || 'expense',
        category_id: prefillData.category_id || '',
        transaction_date: prefillData.transaction_date || todayValue(),
        description: prefillData.description || '',
        payment_method: prefillData.payment_method || 'cash',
      };
    }
    if (isEdit) {
      return {
        amount: transaction.amount || '',
        type: transaction.type || 'expense',
        category_id: transaction.category_id || '',
        transaction_date: transaction.transaction_date || '',
        description: transaction.description || '',
        payment_method: transaction.payment_method || 'cash',
      };
    }
    return {
      amount: '',
      type: 'expense',
      category_id: '',
      transaction_date: todayValue(),
      description: '',
      payment_method: 'cash',
    };
  }, [isEdit, transaction, prefillData]);

  const [form, setForm] = useState(initialValues);
  const [errors, setErrors] = useState({});
  const [scanning, setScanning] = useState(false);
  const [scanError, setScanError] = useState('');
  const fileInputRef = useRef(null);

  useEffect(() => {
    setForm(initialValues);
    setErrors({});
  }, [initialValues]);

  const filteredCategories = useMemo(
    () => {
      if (!categories) return [];
      const result = categories.filter((c) => c.is_active);
      // If editing and current category is hidden, still show it
      if (isEdit && transaction?.category_id) {
        const current = categories.find((c) => c.id === transaction.category_id);
        if (current && !current.is_active && !result.some((c) => c.id === current.id)) {
          result.unshift(current);
        }
      }
      return result;
    },
    [categories, isEdit, transaction],
  );

  const categorySelectOptions = useMemo(() => [
    { value: '', label: 'Chọn danh mục...' },
    ...filteredCategories.map((c) => ({ value: c.id, label: `${c.name}${!c.is_active ? ' (đã ẩn)' : ''}` }))
  ], [filteredCategories]);

  const validate = useCallback(() => {
    const errs = {};
    const amount = parseFloat(form.amount);
    if (!form.amount || Number.isNaN(amount) || amount <= 0) {
      errs.amount = 'Số tiền phải lớn hơn 0.';
    }
    if (!form.type) errs.type = 'Vui lòng chọn loại giao dịch.';
    if (!form.category_id) errs.category_id = 'Vui lòng chọn danh mục.';
    if (!form.transaction_date) errs.transaction_date = 'Vui lòng chọn ngày.';
    if (!form.payment_method) errs.payment_method = 'Vui lòng chọn phương thức.';
    if (form.description && form.description.length > 255) {
      errs.description = 'Ghi chú tối đa 255 ký tự.';
    }
    setErrors(errs);
    return Object.keys(errs).length === 0;
  }, [form]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (submitting || !validate()) return;
    onSubmit({
      amount: form.amount,
      type: form.type,
      category_id: Number(form.category_id),
      transaction_date: form.transaction_date,
      description: form.description || null,
      payment_method: form.payment_method,
    });
  };

  const handleChange = (field) => (e) => {
    const value = e.target.value;
    setForm((prev) => ({ ...prev, [field]: value }));
    if (errors[field]) setErrors((prev) => ({ ...prev, [field]: undefined }));
  };

  const handleOverlayClick = (e) => {
    if (e.target === overlayRef.current) onClose();
  };

  useEffect(() => {
    const handleEsc = (e) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', handleEsc);
    return () => document.removeEventListener('keydown', handleEsc);
  }, [onClose]);

  const handleScanClick = () => {
    if (fileInputRef.current) fileInputRef.current.click();
  };

  const handleFileChange = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    // Clear the input value so the same file can be selected again
    e.target.value = null;

    setScanning(true);
    setScanError('');
    try {
      const data = await scanImage(file);
      setForm((prev) => ({
        ...prev,
        amount: data.amount || prev.amount,
        transaction_date: data.transaction_date || prev.transaction_date,
        description: data.description || prev.description,
        type: data.type || prev.type,
        payment_method: data.payment_method || prev.payment_method,
        category_id: data.category_id || prev.category_id,
      }));
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Lỗi khi quét ảnh.';
      setScanError(typeof msg === 'string' ? msg : 'Lỗi không xác định.');
    } finally {
      setScanning(false);
    }
  };

  return (
    <div className="modal-backdrop" ref={overlayRef} onMouseDown={handleOverlayClick}>
      <div className="category-modal txn-form-modal" role="dialog" aria-label={isEdit ? 'Sửa giao dịch' : 'Thêm giao dịch'}>
        <div className="modal-header">
          <h2>{isEdit ? 'Sửa giao dịch' : 'Thêm giao dịch'}</h2>
          <div className="modal-header-actions">
            {!isEdit && (
              <>
                <button
                  type="button"
                  className="btn-secondary btn-sm"
                  onClick={() => document.getElementById('txn-excel-input')?.click()}
                  disabled={submitting || scanning || isExcelLoading}
                  title="Nhập nhiều giao dịch từ file Excel"
                >
                  {isExcelLoading ? 'Đang xử lý...' : '📄 Nhập Excel'}
                </button>
                <input
                  id="txn-excel-input"
                  type="file"
                  accept=".xlsx,.xls"
                  style={{ display: 'none' }}
                  onChange={(e) => {
                    onExcelUpload(e);
                    onClose(); // Close modal after selecting file because preview modal will open
                  }}
                />
                <button
                  type="button"
                  className="btn-secondary btn-sm"
                  onClick={handleScanClick}
                  disabled={submitting || scanning || isExcelLoading}
                >
                  {scanning ? 'Đang quét...' : '📷 Quét hóa đơn'}
                </button>
                <input
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  ref={fileInputRef}
                  style={{ display: 'none' }}
                  onChange={handleFileChange}
                />
              </>
            )}
            <button type="button" className="modal-close" onClick={onClose} aria-label="Đóng">✕</button>
          </div>
        </div>

        {apiError && <div className="message message-error">{apiError}</div>}
        {scanError && <div className="message message-error">{scanError}</div>}

        <form className="txn-form" onSubmit={handleSubmit}>
          <div className="txn-form-row">
            <label className="txn-form-field">
              <span>Danh mục <em>*</em></span>
              <CustomSelect
                value={form.category_id}
                onChange={(e) => {
                  const catId = e.target.value;
                  const updates = { category_id: catId };
                  const cat = categories.find(c => String(c.id) === String(catId));
                  if (cat && cat.type) {
                    updates.type = cat.type;
                  }
                  setForm((p) => ({ ...p, ...updates }));
                  if (errors.category_id) setErrors((p) => ({ ...p, category_id: '' }));
                }}
                options={categorySelectOptions}
              />
              {errors.category_id && <span className="field-error">{errors.category_id}</span>}
            </label>
          </div>

          <div className="txn-form-row txn-form-row-2col">
            <label className="txn-form-field">
              <span>Số tiền <em>*</em></span>
              <input
                type="number"
                step="0.01"
                min="0.01"
                value={form.amount}
                onChange={handleChange('amount')}
                placeholder="0.00"
                className={errors.amount ? 'input-error' : ''}
              />
              {errors.amount && <span className="field-error">{errors.amount}</span>}
            </label>
            <label className="txn-form-field">
              <span>Ngày <em>*</em></span>
              <CustomDatePicker
                value={form.transaction_date}
                onChange={(e) => {
                  setForm((p) => ({ ...p, transaction_date: e.target.value }));
                  if (errors.transaction_date) setErrors((p) => ({ ...p, transaction_date: '' }));
                }}
              />
              {errors.transaction_date && <span className="field-error">{errors.transaction_date}</span>}
            </label>
          </div>

          <div className="txn-form-row txn-form-row-2col">
            <label className="txn-form-field">
              <span>Loại giao dịch <em>*</em></span>
              <div className="txn-type-toggle" role="group">
                <button
                  type="button"
                  className={`txn-type-btn ${form.type === 'expense' ? 'active expense' : ''}`}
                  onClick={() => setForm((p) => ({ ...p, type: 'expense' }))}
                >Chi</button>
                <button
                  type="button"
                  className={`txn-type-btn ${form.type === 'income' ? 'active income' : ''}`}
                  onClick={() => setForm((p) => ({ ...p, type: 'income' }))}
                >Thu</button>
              </div>
              {errors.type && <span className="field-error">{errors.type}</span>}
            </label>
            <label className="txn-form-field">
              <span>Phương thức thanh toán</span>
              <CustomSelect
                value={form.payment_method}
                onChange={(e) => setForm((p) => ({ ...p, payment_method: e.target.value }))}
                options={PAYMENT_METHODS.map((m) => ({ value: m.value, label: m.label }))}
              />
              {errors.payment_method && <span className="field-error">{errors.payment_method}</span>}
            </label>
          </div>

          <label className="txn-form-field">
            <span>Ghi chú</span>
            <input
              type="text"
              value={form.description}
              onChange={handleChange('description')}
              placeholder="Mô tả giao dịch..."
              maxLength={255}
              className={errors.description ? 'input-error' : ''}
            />
            {errors.description && <span className="field-error">{errors.description}</span>}
          </label>

          <div className="txn-form-actions">
            <button type="button" className="btn-secondary" onClick={onClose} disabled={submitting}>
              Hủy
            </button>
            <button type="submit" className="btn-primary" disabled={submitting}>
              {submitting ? 'Đang lưu...' : isEdit ? 'Cập nhật' : 'Thêm giao dịch'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default TransactionFormModal;
