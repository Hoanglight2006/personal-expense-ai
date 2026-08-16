import { render } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import CustomDatePicker from './CustomDatePicker';
import CustomSelect from './CustomSelect';

describe('popup coordination', () => {
  it('keeps only the latest datepicker or select popup open', async () => {
    const user = userEvent.setup();
    const { container } = render(
      <>
        <CustomDatePicker value="2026-08-16" onChange={vi.fn()} />
        <CustomSelect
          value=""
          onChange={vi.fn()}
          options={[
            { value: '', label: 'Tất cả' },
            { value: 'expense', label: 'Chi' },
          ]}
        />
      </>,
    );

    await user.click(container.querySelector('.custom-datepicker-input'));
    expect(document.querySelector('.react-datepicker')).toBeInTheDocument();

    await user.click(container.querySelector('.custom-select__control'));
    expect(document.querySelector('.custom-select__menu')).toBeInTheDocument();
    expect(document.querySelector('.react-datepicker')).not.toBeInTheDocument();

    await user.click(container.querySelector('.custom-datepicker-input'));
    expect(document.querySelector('.react-datepicker')).toBeInTheDocument();
    expect(document.querySelector('.custom-select__menu')).not.toBeInTheDocument();
  });
});
