import axiosClient from './axios';

/**
 * Fetch monthly financial trends.
 * @param {number} months - Number of months to query (default 6)
 * @param {AbortSignal} [signal]
 */
export const getMonthlyTrend = async (months = 6, signal) => {
  const response = await axiosClient.get('/ai/trend', {
    params: { months },
    signal,
  });
  return response.data;
};

/**
 * Generate AI Monthly Spending Report following REQUIREMENTS.md.
 * @param {string} month - Format 'YYYY-MM'
 * @param {string} [focus='comprehensive'] - Focus: 'comprehensive', 'saving', or 'risk'
 * @param {AbortSignal} [signal]
 */
export const generateMonthlyReport = async (month, focus = 'comprehensive', signal) => {
  const response = await axiosClient.post(
    '/ai/monthly-report',
    { month, focus },
    { signal },
  );
  return response.data;
};

/**
 * Get AI Budget Recommendations based on historical spend.
 * @param {string} [month] - Format 'YYYY-MM' (optional target month)
 * @param {number} [lookbackMonths=3] - Lookback months count (1, 3, 6)
 * @param {AbortSignal} [signal]
 */
export const getBudgetRecommendations = async (month, lookbackMonths = 3, signal) => {
  const params = {};
  if (month) params.month = month;
  if (lookbackMonths) params.lookback_months = lookbackMonths;

  const response = await axiosClient.get('/ai/budget-recommendations', {
    params,
    signal,
  });
  return response.data;
};

/**
 * Apply batch AI Budget Recommendations into user's budget table.
 * @param {Object} payload - { target_month, target_year, recommendations: [{ category_id, amount }] }
 * @param {AbortSignal} [signal]
 */
export const applyBudgetRecommendations = async (payload, signal) => {
  const response = await axiosClient.post(
    '/ai/apply-budget-recommendations',
    payload,
    { signal },
  );
  return response.data;
};
