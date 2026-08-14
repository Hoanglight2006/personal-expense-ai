import api from './axios';

/**
 * Send a chat message to the FinAI assistant.
 * @param {{ message: string, conversation_history: Array }} data
 * @returns {Promise<{ reply: string }>}
 */
export const sendChatMessage = async (data) => {
  const response = await api.post('/chat/message', data);
  return response.data;
};
