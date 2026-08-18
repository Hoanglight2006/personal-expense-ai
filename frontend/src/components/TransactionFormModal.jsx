import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { PAYMENT_METHODS } from '../constants/paymentMethods';
import { scanImage, getTransactionSummary } from '../api/transactionApi';
import { getSavingGoals } from '../api/savingGoalApi';
import CustomDatePicker from './CustomDatePicker';
import CustomSelect from './CustomSelect';
import WarningPopup from './WarningPopup';
import { useModalLock } from '../hooks/useModalLock';

const pad = (v) => String(v).padStart(2, '0');
const todayValue = () => {
  const d = new Date();
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
};

const formatMoney = (amount) => {
  return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(amount || 0);
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
  categoriesReady = true,
}) => {
  useModalLock(true, onClose);
  const isEdit = transaction !== null && transaction !== undefined;
  const overlayRef = useRef(null);

  const initialValues = useMemo(() => {
    if (prefillData) {
      return {
        amount: prefillData.amount || '',
        type: prefillData.type || '',
        category_id: prefillData.category_id || '',
        transaction_date: prefillData.transaction_date || todayValue(),
        description: prefillData.description || '',
        payment_method: prefillData.payment_method || 'cash',
      };
    }
    if (isEdit) {
      return {
        amount: transaction.amount || '',
        type: transaction.type || '',
        category_id: transaction.category_id || '',
        transaction_date: transaction.transaction_date || '',
        description: transaction.description || '',
        payment_method: transaction.payment_method || 'cash',
      };
    }
    return {
      amount: '',
      type: '',
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
  const [warningPopup, setWarningPopup] = useState('');
  const fileInputRef = useRef(null);
  const modalRef = useRef(null);

  // Saving goal allocation state for income transactions
  const [activeGoals, setActiveGoals] = useState([]);
  const [selectedGoalId, setSelectedGoalId] = useState('');
  const [allocationAmount, setAllocationAmount] = useState('');
  const [availableBalance, setAvailableBalance] = useState(null);
  const goalsRequestedRef = useRef(false);
  const componentMountedRef = useRef(true);
  const isIncomeTransaction = form.type === 'income'
    || (!form.type && categories?.some(
      (category) => String(category.id) === String(form.category_id) && category.type === 'income',
    ));

  useEffect(() => {
    componentMountedRef.current = true;
    return () => {
      componentMountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    let mounted = true;
    getTransactionSummary()
      .then((res) => {
        if (mounted && res && res.available_balance !== undefined) {
          setAvailableBalance(Number(res.available_balance));
        }
      })
      .catch(() => {});
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    if (isEdit || !isIncomeTransaction || goalsRequestedRef.current) return undefined;

    goalsRequestedRef.current = true;
    getSavingGoals()
      .then((res) => {
        if (componentMountedRef.current) {
          const items = res?.items || [];
          setActiveGoals(items.filter((g) => g.status === 'active' && Number(g.remaining_amount) > 0));
        }
      })
      .catch(() => {});
    return undefined;
  }, [isEdit, isIncomeTransaction]);

  useEffect(() => {
    setForm(initialValues);
    setErrors({});
    setSelectedGoalId('');
    setAllocationAmount('');
  }, [initialValues]);

  useEffect(() => {
    if (apiError || scanError) setWarningPopup(apiError || scanError);
  }, [apiError, scanError]);

  const closeWarningPopup = useCallback(() => {
    setWarningPopup('');
    window.requestAnimationFrame(() => {
      const invalidField = modalRef.current?.querySelector('.input-error, .custom-select--has-error');
      const amountField = modalRef.current?.querySelector('input[type="number"]');
      const targetField = invalidField || amountField;
      targetField?.scrollIntoView?.({ block: 'center' });
      targetField?.focus?.({ preventScroll: true });
    });
  }, []);

  const categorySelectOptions = useMemo(() => {
    if (!categories) return [];

    const formatCatOption = (c) => ({
      value: c.id,
      label: `${c.name}${!c.is_active ? ' (đã ẩn)' : ''}`,
      icon: c.icon,
      color: c.color,
      type: c.type,
    });

    const isCurrentCategory = (c) => isEdit && transaction && String(c.id) === String(transaction.category_id);
    const visibleCats = categories.filter((c) => c.is_active || isCurrentCategory(c));

    if (form.type === 'expense') {
      return [
        { value: '', label: 'Chọn danh mục chi tiêu...' },
        ...visibleCats.filter((c) => c.type === 'expense').map(formatCatOption)
      ];
    }
    if (form.type === 'income') {
      return [
        { value: '', label: 'Chọn danh mục thu nhập...' },
        ...visibleCats.filter((c) => c.type === 'income').map(formatCatOption)
      ];
    }

    const expenseCats = visibleCats.filter((c) => c.type === 'expense').map(formatCatOption);
    const incomeCats = visibleCats.filter((c) => c.type === 'income').map(formatCatOption);

    return [
      {
        label: '💸 Chi tiêu',
        options: expenseCats,
      },
      {
        label: '💰 Thu nhập',
        options: incomeCats,
      },
    ];
  }, [categories, isEdit, transaction, form.type]);

  const validate = useCallback(() => {
    const errs = {};
    const amount = parseFloat(form.amount);

    if (!form.category_id) {
      errs.category_id = 'Vui lòng chọn danh mục giao dịch.';
    }
    if (!form.amount || Number.isNaN(amount) || amount <= 0) {
      errs.amount = 'Vui lòng nhập số tiền lớn hơn 0.';
    }
    
    let currentType = form.type;
    if (!currentType && form.category_id) {
      const cat = categories?.find((c) => String(c.id) === String(form.category_id));
      if (cat?.type) currentType = cat.type;
    }
    if (!currentType) errs.type = 'Vui lòng chọn loại giao dịch.';
    if (!form.transaction_date) errs.transaction_date = 'Vui lòng chọn ngày giao dịch.';
    if (!form.payment_method) errs.payment_method = 'Vui lòng chọn phương thức thanh toán.';
    if (form.description && form.description.length > 255) {
      errs.description = 'Ghi chú tối đa 255 ký tự.';
    }

    // Strict available balance check for expenses
    if (currentType === 'expense' && availableBalance !== null && !isNaN(amount) && amount > 0) {
      if (!isEdit) {
        if (amount > availableBalance) {
          errs.amount = `Số tiền chi tiêu (${formatMoney(amount)}) vượt quá số dư khả dụng hiện có (${formatMoney(availableBalance)}). Vui lòng thêm thu nhập trước khi chi tiêu.`;
        }
      } else if (transaction) {
        if (transaction.type === 'expense') {
          const delta = amount - (Number(transaction.amount) || 0);
          if (delta > 0 && delta > availableBalance) {
            errs.amount = `Số tiền chi tiêu tăng thêm (${formatMoney(delta)}) vượt quá số dư khả dụng hiện có (${formatMoney(availableBalance)}).`;
          }
        } else if (transaction.type === 'income') {
          const totalImpact = (Number(transaction.amount) || 0) + amount;
          if (totalImpact > availableBalance) {
            errs.amount = `Chuyển từ thu nhập sang chi tiêu (${formatMoney(totalImpact)}) vượt quá số dư khả dụng hiện có (${formatMoney(availableBalance)}).`;
          }
        }
      }
    }

    if (!isEdit && currentType === 'income' && selectedGoalId) {
      const allocVal = parseFloat(allocationAmount);
      if (!allocationAmount || isNaN(allocVal) || allocVal <= 0) {
        errs.allocation = 'Vui lòng nhập số tiền trích hợp lệ lớn hơn 0.';
      } else if (amount && allocVal > amount) {
        errs.allocation = 'Số tiền trích không được vượt quá số tiền thu nhập.';
      } else {
        const targetGoal = activeGoals.find((g) => String(g.id) === String(selectedGoalId));
        if (targetGoal && allocVal > Number(targetGoal.remaining_amount)) {
          errs.allocation = `Số tiền trích (${formatMoney(allocVal)}) vượt quá số tiền còn thiếu (${formatMoney(targetGoal.remaining_amount)}).`;
        }
      }
    }

    const errKeys = Object.keys(errs);
    if (errKeys.length > 0) {
      setErrors(errs);
      setWarningPopup(errs[errKeys[0]]);
      return false;
    }

    setErrors({});
    return true;
  }, [form, categories, isEdit, transaction, selectedGoalId, allocationAmount, activeGoals, availableBalance]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (submitting || !categoriesReady || !validate()) return;
    const cat = categories?.find((c) => String(c.id) === String(form.category_id));
    const finalType = form.type || cat?.type || 'expense';
    const payload = {
      amount: form.amount,
      type: finalType,
      category_id: Number(form.category_id),
      transaction_date: form.transaction_date,
      description: form.description || null,
      payment_method: form.payment_method,
    };
    if (!isEdit && finalType === 'income' && selectedGoalId && allocationAmount && parseFloat(allocationAmount) > 0) {
      payload.saving_goal_id = Number(selectedGoalId);
      payload.saving_goal_amount = parseFloat(allocationAmount);
    }
    onSubmit(payload);
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

  return createPortal(
    <div className="modal-backdrop" ref={overlayRef} onMouseDown={handleOverlayClick}>
      <div className="category-modal txn-form-modal" ref={modalRef} role="dialog" aria-label={isEdit ? 'Sửa giao dịch' : 'Thêm giao dịch'}>
        <div className="modal-header">
          <div className="modal-header-title-row">
            <h2>{isEdit ? 'Sửa giao dịch' : 'Thêm giao dịch'}</h2>
            <button type="button" className="modal-close" onClick={onClose} aria-label="Đóng">✕</button>
          </div>
          {!isEdit && (
            <div className="modal-header-tools">
              <button
                type="button"
                className="btn-secondary btn-sm btn-modal-tool"
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
                }}
              />
              <button
                type="button"
                className="btn-secondary btn-sm btn-modal-tool"
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
            </div>
          )}
        </div>

        {(scanning || isExcelLoading) && (
          <div className="txn-processing-overlay" aria-live="polite">
            <div className="txn-processing-card">
              <div className="txn-clean-spinner" />
              
              <h3 className="txn-processing-title">
                {scanning ? 'Đang đọc thông tin hóa đơn...' : 'Đang xử lý tệp Excel...'}
              </h3>
              
              <p className="txn-processing-desc">
                {scanning
                  ? 'Hệ thống đang tự động trích xuất số tiền, ngày và phân loại giao dịch.'
                  : 'Đang đọc các dòng giao dịch và đối chiếu dữ liệu sao kê.'}
              </p>
            </div>
          </div>
        )}

        <form className="txn-form" onSubmit={handleSubmit} noValidate>
          <div className="txn-form-row">
            <label className="txn-form-field">
              <span>Danh mục <em>*</em></span>
              <CustomSelect
                value={form.category_id}
                hasError={!!errors.category_id}
                onChange={(e) => {
                  const catId = e.target.value;
                  const updates = { category_id: catId };
                  const cat = categories?.find(c => String(c.id) === String(catId));
                  if (cat && cat.type) {
                    updates.type = cat.type;
                  }
                  setForm((p) => ({ ...p, ...updates }));
                  if (errors.category_id) setErrors((p) => ({ ...p, category_id: '' }));
                }}
                options={categorySelectOptions}
              />
            </label>
          </div>

          <div className="txn-form-row txn-form-row-2col">
            <label className="txn-form-field">
              <div className="label-row-preview">
                <span>Số tiền <em>*</em></span>
                {form.type === 'expense' && availableBalance !== null && (
                  <span className="label-amount-preview text-muted" style={{ fontSize: '0.8rem' }}>
                    Khả dụng: <strong className={availableBalance <= 0 ? 'text-danger' : 'text-emerald'}>{formatMoney(availableBalance)}</strong>
                  </span>
                )}
              </div>
              <input
                type="number"
                step="any"
                min="0"
                value={form.amount}
                onChange={handleChange('amount')}
                onWheel={(e) => e.currentTarget.blur()}
                placeholder="0.00"
                className={errors.amount ? 'input-error' : ''}
                aria-invalid={Boolean(errors.amount)}
              />
              {form.amount && !Number.isNaN(parseFloat(form.amount)) && parseFloat(form.amount) > 0 && (
                <span className="input-helper-text">
                  💡 Tương đương: <strong>{formatMoney(parseFloat(form.amount))}</strong>
                </span>
              )}
            </label>
            <label className="txn-form-field">
              <span>Ngày <em>*</em></span>
              <CustomDatePicker
                value={form.transaction_date}
                hasError={Boolean(errors.transaction_date)}
                onChange={(e) => {
                  setForm((p) => ({ ...p, transaction_date: e.target.value }));
                  if (errors.transaction_date) setErrors((p) => ({ ...p, transaction_date: '' }));
                }}
              />
            </label>
          </div>

          <div className="txn-form-row txn-form-row-2col">
            <label className="txn-form-field">
              <span>Loại giao dịch <em>*</em></span>
              <div className="txn-type-toggle" role="group">
                <button
                  type="button"
                  className={`txn-type-btn ${form.type === 'expense' ? 'active expense' : ''}`}
                  onClick={() => {
                    setForm((prev) => {
                      let updatedCategory = prev.category_id;
                      if (updatedCategory) {
                        const cat = categories?.find((c) => String(c.id) === String(updatedCategory));
                        if (cat && cat.type !== 'expense') {
                          updatedCategory = '';
                        }
                      }
                      return { ...prev, type: 'expense', category_id: updatedCategory };
                    });
                    if (errors.type) setErrors((p) => ({ ...p, type: '' }));
                  }}
                >Chi</button>
                <button
                  type="button"
                  className={`txn-type-btn ${form.type === 'income' ? 'active income' : ''}`}
                  onClick={() => {
                    setForm((prev) => {
                      let updatedCategory = prev.category_id;
                      if (updatedCategory) {
                        const cat = categories?.find((c) => String(c.id) === String(updatedCategory));
                        if (cat && cat.type !== 'income') {
                          updatedCategory = '';
                        }
                      }
                      return { ...prev, type: 'income', category_id: updatedCategory };
                    });
                    if (errors.type) setErrors((p) => ({ ...p, type: '' }));
                  }}
                >Thu</button>
              </div>
            </label>
            <label className="txn-form-field">
              <span>Phương thức thanh toán</span>
              <CustomSelect
                value={form.payment_method}
                hasError={Boolean(errors.payment_method)}
                onChange={(e) => setForm((p) => ({ ...p, payment_method: e.target.value }))}
                options={PAYMENT_METHODS.map((m) => ({ value: m.value, label: m.label }))}
              />
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
              aria-invalid={Boolean(errors.description)}
            />
          </label>

          {/* Income Saving Goal Allocation Section */}
          {!isEdit && isIncomeTransaction && (
            <div className="income-goal-allocation-card">
              <div className="allocation-header-row">
                <div className="allocation-header-title">
                  <span className="allocation-icon">🎯</span>
                  <strong>Trích vào mục tiêu tiết kiệm</strong>
                  <span className="text-muted text-xs">(tùy chọn)</span>
                </div>
                {activeGoals.length > 0 ? (
                  <span className="allocation-badge-count">{activeGoals.length} mục tiêu đang chạy</span>
                ) : (
                  <span className="allocation-badge-none">Chưa có mục tiêu</span>
                )}
              </div>

              {activeGoals.length > 0 ? (
                <div className="allocation-body-simple">
                  <label className="txn-form-field">
                    <span>Chọn mục tiêu muốn trích:</span>
                    <CustomSelect
                      value={selectedGoalId}
                      onChange={(e) => {
                        const newGoalId = e.target.value;
                        setSelectedGoalId(newGoalId);
                        if (!newGoalId) {
                          setAllocationAmount('');
                        }
                      }}
                      options={[
                        { value: '', label: '-- Không trích (Mặc định) --' },
                        ...activeGoals.map((g) => ({
                          value: g.id,
                          label: `${g.name} (còn thiếu ${formatMoney(g.remaining_amount)})`,
                        })),
                      ]}
                    />
                  </label>

                  {selectedGoalId && (
                    <>
                      <div className="allocation-quick-section">
                        <span className="allocation-quick-label">Gợi ý trích nhanh từ thu nhập:</span>
                        <div className="allocation-quick-chips">
                          {[0.1, 0.2, 0.3].map((rate) => {
                            const baseAmount = parseFloat(form.amount) || 0;
                            const calcVal = Math.round(baseAmount * rate);
                            return (
                              <button
                                key={rate}
                                type="button"
                                className="quick-chip-btn"
                                disabled={!baseAmount || baseAmount <= 0}
                                onClick={() => setAllocationAmount(String(calcVal))}
                              >
                                {rate * 100}% {baseAmount > 0 ? `(${formatMoney(calcVal)})` : ''}
                              </button>
                            );
                          })}
                          {activeGoals.find((g) => String(g.id) === String(selectedGoalId)) && (
                            <button
                              type="button"
                              className="quick-chip-btn quick-chip-fill"
                              onClick={() => {
                                const g = activeGoals.find((goal) => String(goal.id) === String(selectedGoalId));
                                if (g) setAllocationAmount(String(g.remaining_amount));
                              }}
                            >
                              🎯 Đủ thiếu ({formatMoney(activeGoals.find((g) => String(g.id) === String(selectedGoalId)).remaining_amount)})
                            </button>
                          )}
                        </div>
                      </div>

                      <label className="txn-form-field">
                        <span>Số tiền trích vào mục tiêu (VNĐ) <em>*</em></span>
                        <input
                          type="number"
                          placeholder="Nhập số tiền trích..."
                          value={allocationAmount}
                          onChange={(e) => {
                            setAllocationAmount(e.target.value);
                            if (errors.allocation) setErrors((p) => ({ ...p, allocation: '' }));
                          }}
                          min="1"
                          step="any"
                          onWheel={(e) => e.currentTarget.blur()}
                          className={errors.allocation ? 'input-error' : ''}
                          aria-invalid={Boolean(errors.allocation)}
                        />
                        {allocationAmount && Number(allocationAmount) > 0 && (
                          <span className="input-helper-text">
                            💡 Tương đương: <strong>{formatMoney(allocationAmount)}</strong>
                          </span>
                        )}
                      </label>
                    </>
                  )}
                </div>
              ) : (
                <div className="allocation-empty-note">
                  <span>💡 Bạn chưa có mục tiêu tiết kiệm nào đang hoạt động. Tạo mục tiêu ở trang <strong>Tiết kiệm</strong> để sử dụng tính năng trích tiền tự động.</span>
                </div>
              )}
            </div>
          )}

          <div className="txn-form-actions">
            <button type="button" className="btn-secondary" onClick={onClose} disabled={submitting}>
              Hủy
            </button>
            <button type="submit" className="btn-primary" disabled={submitting || !categoriesReady}>
              {submitting ? 'Đang lưu...' : isEdit ? 'Cập nhật' : 'Thêm giao dịch'}
            </button>
          </div>
        </form>
      </div>
      <WarningPopup
        isOpen={Boolean(warningPopup)}
        message={warningPopup}
        onClose={closeWarningPopup}
      />
    </div>,
    document.body
  );
};

export default TransactionFormModal;
