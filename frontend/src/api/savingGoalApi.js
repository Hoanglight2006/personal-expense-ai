import api from './axios';

/**
 * Fetch list of saving goals with summary stats.
 * @param {{ status?: 'active' | 'completed' | 'cancelled' }} params
 * @param {AbortSignal} [signal]
 */
export const getSavingGoals = async (params = {}, signal) => {
  const response = await api.get('/saving-goals', { params, signal });
  return response.data;
};

/**
 * Fetch detailed saving goal by ID including contribution history.
 * @param {number} goalId
 * @param {AbortSignal} [signal]
 */
export const getSavingGoalById = async (goalId, signal) => {
  const response = await api.get(`/saving-goals/${goalId}`, { signal });
  return response.data;
};

/**
 * Create a new saving goal.
 * @param {{ name: string, target_amount: string|number, deadline?: string, initial_deposit?: string|number }} payload
 */
export const createSavingGoal = async (payload) => {
  const response = await api.post('/saving-goals', payload);
  return response.data;
};

/**
 * Update an existing saving goal (name, target_amount, deadline, status).
 * @param {number} goalId
 * @param {{ name?: string, target_amount?: string|number, deadline?: string, status?: string }} payload
 */
export const updateSavingGoal = async (goalId, payload) => {
  const response = await api.patch(`/saving-goals/${goalId}`, payload);
  return response.data;
};

/**
 * Make a deposit / contribution towards a saving goal.
 * @param {number} goalId
 * @param {{ amount: string|number, note?: string }} payload
 */
export const contributeToGoal = async (goalId, payload) => {
  const response = await api.post(`/saving-goals/${goalId}/contribute`, payload);
  return response.data;
};

/**
 * Delete a saving goal permanently.
 * @param {number} goalId
 */
export const deleteSavingGoal = async (goalId) => {
  const response = await api.delete(`/saving-goals/${goalId}`);
  return response.data;
};
