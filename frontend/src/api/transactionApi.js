import api from './axios';

export const getTransactions = async (params, signal) => {
  const response = await api.get('/transactions', { params, signal });
  return response.data;
};

export const getTransactionTrash = async (params, signal) => {
  const response = await api.get('/transactions/trash', { params, signal });
  return response.data;
};

export const getTransaction = async (id) => {
  const response = await api.get(`/transactions/${id}`);
  return response.data;
};

export const createTransaction = async (payload) => {
  const response = await api.post('/transactions', payload);
  return response.data;
};

export const updateTransaction = async (id, payload) => {
  const response = await api.patch(`/transactions/${id}`, payload);
  return response.data;
};

export const trashTransaction = async (id) => {
  const response = await api.post(`/transactions/${id}/trash`);
  return response.data;
};

export const restoreTransaction = async (id) => {
  const response = await api.post(`/transactions/${id}/restore`);
  return response.data;
};

export const deleteTransactionPermanently = async (id) => {
  const response = await api.delete(`/transactions/${id}`);
  return response.data;
};

export const duplicateTransaction = async (id) => {
  const response = await api.post(`/transactions/${id}/duplicate`);
  return response.data;
};

export const scanImage = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post('/transactions/scan-image', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

export const parseExcel = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post('/transactions/parse-excel', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

export const importTransactions = async (payload) => {
  const response = await api.post('/transactions/import', payload);
  return response.data;
};
