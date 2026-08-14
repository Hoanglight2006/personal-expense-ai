import React from 'react';
import Select from 'react-select';

const CustomSelect = ({ value, onChange, options, disabled, placeholder }) => {
  // value is expected to be a string
  // options is an array of { value: string, label: string }
  const selectedOption = options.find((opt) => opt.value === value) || null;

  const handleChange = (selected) => {
    // Mimic standard e.target.value for drop-in replacement
    if (selected) {
      onChange({ target: { value: selected.value } });
    } else {
      onChange({ target: { value: '' } });
    }
  };

  return (
    <Select
      value={selectedOption}
      onChange={handleChange}
      options={options}
      isDisabled={disabled}
      placeholder={placeholder || "Chọn..."}
      className="custom-select-container"
      classNamePrefix="custom-select"
      isSearchable={false}
      menuPortalTarget={document.body}
      menuPosition="fixed"
      styles={{
        menuPortal: base => ({ ...base, zIndex: 9999 })
      }}
    />
  );
};

export default CustomSelect;
