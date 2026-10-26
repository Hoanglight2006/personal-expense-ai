import api from './axios';

export const getAdminUsers = async (params = {}) => {
  const response = await api.get('/admin/users', { params });
  return response.data;
};

export const listUsers = getAdminUsers;

export const toggleUserStatus = async (userId, isLocked) => {
  const response = await api.patch(`/admin/users/${userId}/status`, {
    is_locked: isLocked,
  });
  return response.data;
};

export const resetUserPassword = async (userId) => {
  const response = await api.post(`/admin/users/${userId}/reset-password`);
  return response.data;
};

export const createAdminUser = async (payload) => {
  const response = await api.post('/admin/users', payload);
  return response.data;
};

export const createUser = createAdminUser;

export const getAdminStats = async () => {
  const response = await api.get('/admin/stats');
  return response.data;
};

