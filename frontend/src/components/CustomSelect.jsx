import React, { useEffect, useId, useMemo, useState } from 'react';
import Select, { components } from 'react-select';
import { announcePopupOpen, subscribeToPopupOpen } from '../utils/popupCoordinator';

const CustomOption = (props) => {
  const { data } = props;
  return (
    <components.Option {...props}>
      <div className="custom-select-option-content">
        <span className="custom-select-option-label">{data.label}</span>
        {data.type && (
          <span className={`custom-select-type-tag ${data.type}`}>
            {data.type === 'expense' ? 'Chi' : 'Thu'}
          </span>
        )}
      </div>
    </components.Option>
  );
};

const CustomSingleValue = (props) => {
  const { data } = props;
  return (
    <components.SingleValue {...props}>
      <div className="custom-select-single-value-content">
        <span className="custom-select-option-label">{data.label}</span>
      </div>
    </components.SingleValue>
  );
};

const CustomGroupHeading = (props) => {
  const isExpense = String(props.children || '').includes('Chi');
  return (
    <components.GroupHeading {...props}>
      <div className={`custom-select-group-header ${isExpense ? 'expense-group' : 'income-group'}`}>
        {props.children}
      </div>
    </components.GroupHeading>
  );
};

const CustomSelect = ({
  value,
  onChange,
  options,
  disabled,
  placeholder,
  isSearchable = false,
  menuIsOpen,
  onMenuOpen,
  onMenuClose,
}) => {
  const popupId = useId();
  const [internalMenuOpen, setInternalMenuOpen] = useState(false);
  const isControlled = typeof menuIsOpen === 'boolean';
  const effectiveMenuOpen = isControlled ? menuIsOpen : internalMenuOpen;

  useEffect(() => {
    if (isControlled) return undefined;
    return subscribeToPopupOpen((event) => {
      if (event.detail !== popupId) setInternalMenuOpen(false);
    });
  }, [isControlled, popupId]);

  // Flatten options for lookup (supports both flat and grouped options)
  const flatOptions = useMemo(() => {
    if (!options) return [];
    return options.flatMap((opt) => (opt.options ? opt.options : [opt]));
  }, [options]);

  const selectedOption = flatOptions.find((opt) => String(opt.value) === String(value)) || null;

  const handleChange = (selected) => {
    // Mimic standard e.target.value for drop-in replacement
    if (selected) {
      onChange({ target: { value: selected.value } });
    } else {
      onChange({ target: { value: '' } });
    }
  };

  const handleMenuOpen = () => {
    announcePopupOpen(popupId);
    if (!isControlled) setInternalMenuOpen(true);
    onMenuOpen?.();
  };

  const handleMenuClose = () => {
    if (!isControlled) setInternalMenuOpen(false);
    onMenuClose?.();
  };

  return (
    <Select
      value={selectedOption}
      onChange={handleChange}
      options={options}
      isDisabled={disabled}
      placeholder={placeholder || 'Chọn...'}
      className="custom-select-container"
      classNamePrefix="custom-select"
      isSearchable={isSearchable}
      closeMenuOnSelect={true}
      blurInputOnSelect={true}
      menuIsOpen={effectiveMenuOpen}
      onMenuOpen={handleMenuOpen}
      onMenuClose={handleMenuClose}
      menuPortalTarget={document.body}
      menuPosition="fixed"
      components={{
        Option: CustomOption,
        SingleValue: CustomSingleValue,
        GroupHeading: CustomGroupHeading,
      }}
      styles={{
        menuPortal: (base) => ({ ...base, zIndex: 99999 }),
      }}
    />
  );
};

export default CustomSelect;
