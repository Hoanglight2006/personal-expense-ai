import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AuthContext } from '../context/auth-context';
import Profile from './Profile';
import { changePassword, updateProfile } from '../api/authApi';

vi.mock('../api/authApi', () => ({
  updateProfile: vi.fn(),
  changePassword: vi.fn(),
}));

const user = {
  id: 1,
  username: 'tester',
  email: 'tester@example.com',
  created_at: '2026-08-16T00:00:00',
};

const renderProfile = (setUser = vi.fn()) => render(
  <AuthContext.Provider value={{ user, setUser }}>
    <MemoryRouter>
      <Profile />
    </MemoryRouter>
  </AuthContext.Provider>,
);

describe('Profile', () => {
  beforeEach(() => vi.clearAllMocks());

  it('updates profile information and auth context', async () => {
    const setUser = vi.fn();
    const updated = { ...user, username: 'tester-new' };
    updateProfile.mockResolvedValue(updated);
    renderProfile(setUser);

    fireEvent.change(screen.getByLabelText('Tên đăng nhập'), { target: { value: 'tester-new' } });
    fireEvent.click(screen.getByRole('button', { name: 'Lưu thay đổi' }));

    await waitFor(() => expect(updateProfile).toHaveBeenCalledWith({
      username: 'tester-new',
      email: 'tester@example.com',
    }));
    expect(setUser).toHaveBeenCalledWith(updated);
    expect(await screen.findByText('Thông tin hồ sơ đã được cập nhật.')).toBeInTheDocument();
  });

  it('validates password confirmation before calling the API', () => {
    renderProfile();
    fireEvent.change(screen.getByLabelText('Mật khẩu hiện tại'), { target: { value: 'oldpassword' } });
    fireEvent.change(screen.getByLabelText('Mật khẩu mới'), { target: { value: 'newpassword123' } });
    fireEvent.change(screen.getByLabelText('Xác nhận mật khẩu mới'), { target: { value: 'different123' } });
    fireEvent.click(screen.getByRole('button', { name: 'Cập nhật mật khẩu' }));

    expect(screen.getByText('Mật khẩu xác nhận không khớp.')).toBeInTheDocument();
    expect(changePassword).not.toHaveBeenCalled();
  });
});
