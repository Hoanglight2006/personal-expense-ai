import api from './axios';

export const getCategories = async (params, signal) => {
  const response = await api.get('/categories', { params, signal });
  return response.data;
};

export const getCategoryStatistics = async (params, signal) => {
  const response = await api.get('/categories/statistics', { params, signal });
  return response.data;
};

export const createCategory = async (payload) => {
  const response = await api.post('/categories', payload);
  return response.data;
};

export const createDefaultCategories = async () => {
  const response = await api.post('/categories/defaults');
  return response.data;
};

export const updateCategory = async (categoryId, payload) => {
  const response = await api.patch(`/categories/${categoryId}`, payload);
  return response.data;
};

export const hideCategory = async (categoryId) => {
  const response = await api.post(`/categories/${categoryId}/hide`);
  return response.data;
};

export const restoreCategory = async (categoryId) => {
  const response = await api.post(`/categories/${categoryId}/restore`);
  return response.data;
};

export const deleteCategory = async (categoryId, signal) => {
  const response = await api.delete(`/categories/${categoryId}`, { signal });
  return response.data;
};
