import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AuthContext } from '../context/auth-context';
import Profile from './Profile';
import { changePassword, updateProfile, uploadAvatar } from '../api/authApi';

vi.mock('../api/authApi', () => ({
  updateProfile: vi.fn(),
  changePassword: vi.fn(),
  uploadAvatar: vi.fn(),
}));

const user = {
  id: 1,
  username: 'tester',
  email: 'tester@example.com',
  avatar_url: null,
  created_at: '2026-08-16T00:00:00',
};

const renderProfile = (customUser = user, setUser = vi.fn()) => render(
  <AuthContext.Provider value={{ user: customUser, setUser }}>
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
    renderProfile(user, setUser);

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

  it('opens avatar select modal and updates avatar with a 3D mascot preset', async () => {
    const setUser = vi.fn();
    const updated = { ...user, avatar_url: '/assets/coin_3d.png' };
    updateProfile.mockResolvedValue(updated);
    renderProfile(user, setUser);

    // Click on avatar edit badge
    const editBtn = screen.getByLabelText('Thay đổi ảnh đại diện');
    fireEvent.click(editBtn);

    // Modal should be visible
    expect(screen.getByRole('dialog', { name: 'Chọn ảnh đại diện' })).toBeInTheDocument();

    // Select the first preset
    const presetCard = screen.getByLabelText(/Chọn FinAI Coin 3D/i);
    fireEvent.click(presetCard);

    // Click Save
    const saveBtn = screen.getByRole('button', { name: 'Lưu ảnh đại diện' });
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(updateProfile).toHaveBeenCalledWith(
        expect.objectContaining({
          avatar_url: expect.any(String),
        })
      );
      expect(setUser).toHaveBeenCalledWith(updated);
    });
  });

  it('uploads a custom image file from device', async () => {
    const setUser = vi.fn();
    const updated = { ...user, avatar_url: '/static/avatars/custom.png' };
    uploadAvatar.mockResolvedValue(updated);
    renderProfile(user, setUser);

    // Open modal
    fireEvent.click(screen.getByLabelText('Thay đổi ảnh đại diện'));

    // Switch to Upload tab
    fireEvent.click(screen.getByRole('button', { name: /Tải ảnh từ thiết bị/i }));

    // Upload mock file
    const file = new File(['dummy content'], 'avatar.png', { type: 'image/png' });
    const fileInput = document.querySelector('input[type="file"]');
    fireEvent.change(fileInput, { target: { files: [file] } });

    // Click Save
    const saveBtn = screen.getByRole('button', { name: 'Lưu ảnh đại diện' });
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(uploadAvatar).toHaveBeenCalledWith(file);
      expect(setUser).toHaveBeenCalledWith(updated);
    });
  });
});
