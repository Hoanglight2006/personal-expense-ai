import api from './axios';

export const registerUser = async (username, email, password) => {
  const response = await api.post('/auth/register', { username, email, password });
  return response.data;
};

export const loginUser = async (identifier, password) => {
  const formData = new URLSearchParams();
  formData.append('username', identifier);
  formData.append('password', password);

  const response = await api.post('/auth/login', formData, {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
  });
  return response.data;
};

export const getMe = async () => {
  const response = await api.get('/auth/me');
  return response.data;
};

export const updateProfile = async (profile) => {
  const response = await api.patch('/auth/me', profile);
  return response.data;
};

export const changePassword = async (currentPassword, newPassword) => {
  const response = await api.post('/auth/change-password', {
    current_password: currentPassword,
    new_password: newPassword,
  });
  return response.data;
};

export const requestPasswordReset = async (email) => {
  const response = await api.post('/auth/forgot-password', { email });
  return response.data;
};

export const resetPassword = async (token, password) => {
  const response = await api.post('/auth/reset-password', { token, password });
  return response.data;
};

export const uploadAvatar = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post('/auth/avatar/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};
