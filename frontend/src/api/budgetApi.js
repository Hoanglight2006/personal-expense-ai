import api from './axios';

/**
 * Fetch monthly budgets and summary totals for a specific period.
 * @param {{ month?: number, year?: number }} params
 * @param {AbortSignal} [signal]
 */
export const getBudgets = async (params = {}, signal) => {
  const response = await api.get('/budgets', { params, signal });
  return response.data;
};

/**
 * Fetch budget alerts (warning >= 80% or exceeded >= 100%) for a period.
 * @param {{ month?: number, year?: number }} params
 * @param {AbortSignal} [signal]
 */
export const getBudgetAlerts = async (params = {}, signal) => {
  const response = await api.get('/budgets/alerts', { params, signal });
  return response.data;
};

/**
 * Fetch details of a single budget.
 * @param {number} budgetId
 * @param {AbortSignal} [signal]
 */
export const getBudgetById = async (budgetId, signal) => {
  const response = await api.get(`/budgets/${budgetId}`, { signal });
  return response.data;
};

/**
 * Create a new monthly budget for an expense category.
 * @param {{ category_id: number, amount: string|number, month: number, year: number }} payload
 */
export const createBudget = async (payload) => {
  const response = await api.post('/budgets', payload);
  return response.data;
};

/**
 * Update the budget amount.
 * @param {number} budgetId
 * @param {{ amount: string|number }} payload
 */
export const updateBudget = async (budgetId, payload) => {
  const response = await api.patch(`/budgets/${budgetId}`, payload);
  return response.data;
};

/**
 * Delete a budget record permanently.
 * @param {number} budgetId
 */
export const deleteBudget = async (budgetId) => {
  const response = await api.delete(`/budgets/${budgetId}`);
  return response.data;
};
