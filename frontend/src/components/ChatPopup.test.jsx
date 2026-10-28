import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import ChatPopup from './ChatPopup';
import { AuthContext } from '../context/auth-context';
import * as chatApi from '../api/chatApi';

vi.mock('../api/chatApi', () => ({
  sendChatMessage: vi.fn(),
}));

describe('ChatPopup session persistence and user interactions', () => {
  const mockUser = { id: 42, username: 'tester', email: 'test@example.com' };

  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  const renderWithAuth = (props = {}, user = mockUser) => {
    return render(
      <AuthContext.Provider value={{ user, setUser: vi.fn(), login: vi.fn(), logout: vi.fn(), loading: false }}>
        <ChatPopup isOpen={true} onClose={vi.fn()} {...props} />
      </AuthContext.Provider>
    );
  };

  it('renders welcome message when localStorage is empty', () => {
    renderWithAuth();
    expect(screen.getByText(/Xin chào! 👋 Mình là FinAI/i)).toBeInTheDocument();
    // Clear chat button should NOT be visible when only welcome message exists
    expect(screen.queryByTitle(/Đoạn chat mới/i)).not.toBeInTheDocument();
  });

  it('restores chat history from localStorage on mount', () => {
    const savedMessages = [
      { role: 'assistant', content: 'Xin chào! 👋 Mình là FinAI' },
      { role: 'user', content: 'Tháng này tôi chi bao nhiêu tiền?' },
      { role: 'assistant', content: 'Tổng chi tiêu tháng này của bạn là 3.500.000 đ.' },
    ];
    localStorage.setItem('finai_chat_42', JSON.stringify(savedMessages));

    renderWithAuth();

    expect(screen.getByText('Tháng này tôi chi bao nhiêu tiền?')).toBeInTheDocument();
    expect(screen.getByText('Tổng chi tiêu tháng này của bạn là 3.500.000 đ.')).toBeInTheDocument();
    // Clear button should be visible because there is conversation history
    expect(screen.getByTitle(/Đoạn chat mới/i)).toBeInTheDocument();
  });

  it('saves new user query and AI reply to localStorage', async () => {
    chatApi.sendChatMessage.mockResolvedValueOnce({
      reply: 'Bạn đã tiết kiệm được 2.000.000 đ trong tháng này!',
    });

    renderWithAuth();

    const input = screen.getByPlaceholderText(/Hỏi FinAI về chi tiêu/i);
    const sendBtn = screen.getByLabelText(/Gửi tin nhắn/i);

    await userEvent.type(input, 'Tôi đã tiết kiệm được bao nhiêu?');
    fireEvent.click(sendBtn);

    expect(screen.getByText('Tôi đã tiết kiệm được bao nhiêu?')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('Bạn đã tiết kiệm được 2.000.000 đ trong tháng này!')).toBeInTheDocument();
    });

    // Check localStorage was updated with the new conversation
    const saved = JSON.parse(localStorage.getItem('finai_chat_42'));
    expect(saved).toHaveLength(3); // welcome + user + assistant
    expect(saved[1].content).toBe('Tôi đã tiết kiệm được bao nhiêu?');
    expect(saved[2].content).toBe('Bạn đã tiết kiệm được 2.000.000 đ trong tháng này!');
  });

  it('clears conversation history when clicking clear chat button', () => {
    const savedMessages = [
      { role: 'assistant', content: 'Xin chào!' },
      { role: 'user', content: 'Xin chào FinAI' },
      { role: 'assistant', content: 'Chào bạn, mình có thể giúp gì?' },
    ];
    localStorage.setItem('finai_chat_42', JSON.stringify(savedMessages));

    renderWithAuth();

    expect(screen.getByText('Xin chào FinAI')).toBeInTheDocument();
    const clearBtn = screen.getByTitle(/Đoạn chat mới/i);

    fireEvent.click(clearBtn);

    // Messages reset to only welcome message
    expect(screen.queryByText('Xin chào FinAI')).not.toBeInTheDocument();
    expect(screen.getByText(/Xin chào! 👋 Mình là FinAI/i)).toBeInTheDocument();
    expect(localStorage.getItem('finai_chat_42')).toBeNull();
  });

  it('removes chat history on auth logout', async () => {
    localStorage.setItem('finai_chat_42', JSON.stringify([{ role: 'user', content: 'hello' }]));
    localStorage.setItem('access_token', 'fake-token');

    const TestLogoutComponent = () => {
      const { logout } = React.useContext(AuthContext);
      return <button onClick={logout}>Đăng xuất</button>;
    };

    const { AuthProvider } = await import('../context/AuthContext');

    render(
      <AuthProvider>
        <TestLogoutComponent />
      </AuthProvider>
    );

    fireEvent.click(screen.getByText('Đăng xuất'));

    expect(localStorage.getItem('finai_chat_42')).toBeNull();
    expect(localStorage.getItem('access_token')).toBeNull();
  });
});
