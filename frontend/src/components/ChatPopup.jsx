import React, { useState, useRef, useEffect, useContext } from 'react';
import { sendChatMessage } from '../api/chatApi';
import { AuthContext } from '../context/auth-context';

const botAvatar = '/finai-winged-coin-favicon.png';

const WELCOME_MESSAGE = {
  role: 'assistant',
  content: 'Xin chào! 👋 Mình là FinAI, trợ lý chi tiêu cá nhân của bạn. Hãy hỏi mình bất cứ điều gì về tài chính nhé! 💰',
};

const QUICK_SUGGESTIONS = [
  'Tháng này tôi chi nhiều nhất vào đâu?',
  'Quy tắc 50/30/20 là gì?',
  'Cách chia tiền 6 chiếc lọ?',
  'Quỹ khẩn cấp nên để bao nhiêu?',
  'Tình hình ngân sách tháng này?',
  'Gợi ý cách tiết kiệm tiền',
];

const getChatStorageKey = (userId) => (userId ? `finai_chat_${userId}` : 'finai_chat_guest');

const loadInitialMessages = (storageKey) => {
  try {
    const saved = localStorage.getItem(storageKey);
    if (saved) {
      const parsed = JSON.parse(saved);
      if (Array.isArray(parsed) && parsed.length > 0) {
        return parsed;
      }
    }
  } catch (err) {
    console.error('Không thể đọc lịch sử chat từ localStorage', err);
  }
  return [WELCOME_MESSAGE];
};

const ChatPopup = ({ isOpen, onClose }) => {
  const { user } = useContext(AuthContext);
  const storageKey = getChatStorageKey(user?.id);

  const [messages, setMessages] = useState(() => loadInitialMessages(storageKey));
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const chipsContainerRef = useRef(null);

  // Sync to localStorage whenever messages change
  useEffect(() => {
    try {
      if (messages.length > 1 || (messages.length === 1 && messages[0].content !== WELCOME_MESSAGE.content)) {
        localStorage.setItem(storageKey, JSON.stringify(messages));
      } else {
        localStorage.removeItem(storageKey);
      }
    } catch (err) {
      console.error('Không thể lưu lịch sử chat vào localStorage', err);
    }
  }, [messages, storageKey]);

  // If user switches, reload initial messages for that user
  useEffect(() => {
    setMessages(loadInitialMessages(storageKey));
  }, [storageKey]);

  const handleClearChat = () => {
    setMessages([WELCOME_MESSAGE]);
    try {
      localStorage.removeItem(storageKey);
    } catch {
      // ignore
    }
  };

  const scrollChips = (offset) => {
    if (chipsContainerRef.current?.scrollBy) {
      chipsContainerRef.current.scrollBy({ left: offset, behavior: 'smooth' });
    }
  };

  // Auto scroll to bottom when new messages arrive
  useEffect(() => {
    if (messagesEndRef.current?.scrollIntoView) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isTyping]);

  // Focus input when popup opens
  useEffect(() => {
    if (isOpen && inputRef.current) {
      setTimeout(() => inputRef.current?.focus(), 300);
    }
  }, [isOpen]);

  const sendQuery = async (queryText) => {
    const trimmed = (queryText || input).trim();
    if (!trimmed || isTyping) return;

    const userMsg = { role: 'user', content: trimmed };
    const updatedMessages = [...messages, userMsg];
    setMessages(updatedMessages);
    setInput('');
    setIsTyping(true);

    try {
      // Build conversation_history for API (exclude welcome message)
      const history = updatedMessages
        .filter((m) => m.content !== WELCOME_MESSAGE.content)
        .map((m) => ({ role: m.role, content: m.content }));

      const data = await sendChatMessage({
        message: trimmed,
        conversation_history: history.slice(0, -1), // Exclude current message
      });

      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: data.reply,
          sources: data.rag_sources || [],
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'Xin lỗi, mình đang gặp sự cố kết nối AI. Vui lòng thử lại sau! 🙏',
        },
      ]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleSend = () => sendQuery(input);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="chat-popup">
      {/* Header */}
      <div className="chat-popup-header">
        <div className="chat-popup-avatar">
          <img src={botAvatar} alt="FinAI" />
        </div>
        <div className="chat-popup-title">
          <strong>FinAI</strong>
          <span>Trợ lý chi tiêu</span>
        </div>
        <div className="chat-popup-actions">
          {messages.length > 1 && (
            <button
              type="button"
              className="chat-popup-clear"
              onClick={handleClearChat}
              aria-label="Xóa lịch sử và bắt đầu đoạn chat mới"
              title="Đoạn chat mới"
            >
              🔄
            </button>
          )}
          <button type="button" className="chat-popup-close" onClick={onClose} aria-label="Đóng chat" title="Đóng cửa sổ chat">
            ✕
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="chat-popup-body">
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`chat-message ${msg.role === 'user' ? 'chat-message-user' : 'chat-message-bot'}`}
          >
            {msg.role === 'assistant' && (
              <div className="chat-message-avatar">
                <img src={botAvatar} alt="" />
              </div>
            )}
            <div className="chat-message-bubble">
              <div className="chat-message-text">{msg.content}</div>
              {msg.sources && msg.sources.length > 0 && (
                <div className="chat-rag-sources">
                  <span className="rag-sources-label">📚 Tham chiếu RAG:</span>
                  <div className="rag-sources-tags">
                    {msg.sources.map((src, sIdx) => {
                      const urlMatch = typeof src === 'string' && src.match(/(https?:\/\/[^\s)]+)/);
                      if (urlMatch) {
                        const url = urlMatch[1];
                        const label = src
                          .replace(/\(https?:\/\/[^\s)]+\)/, '')
                          .replace(/\[(.*?)\]\(.*?\)/, '$1')
                          .trim() || url;
                        return (
                          <a
                            key={sIdx}
                            href={url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="rag-source-tag rag-source-link"
                            title={`Mở bài viết gốc: ${url}`}
                          >
                            🔗 {label} ↗
                          </a>
                        );
                      }
                      return (
                        <span key={sIdx} className="rag-source-tag">
                          {src}
                        </span>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}
        {isTyping && (
          <div className="chat-message chat-message-bot">
            <div className="chat-message-avatar">
              <img src={botAvatar} alt="" />
            </div>
            <div className="chat-message-bubble chat-typing">
              <span className="typing-dot" />
              <span className="typing-dot" />
              <span className="typing-dot" />
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Quick Suggestion Chips (Compact row with navigation arrows) */}
      <div className="chat-quick-chips-wrapper">
        <button
          type="button"
          className="chip-nav-btn chip-nav-left"
          onClick={() => scrollChips(-150)}
          aria-label="Lướt sang trái"
          title="Lướt sang trái"
        >
          ‹
        </button>
        <div
          ref={chipsContainerRef}
          className="chat-quick-chips-track"
          onWheel={(e) => {
            if (e.deltaY !== 0) {
              e.currentTarget.scrollLeft += e.deltaY;
            }
          }}
        >
          {QUICK_SUGGESTIONS.map((chip, idx) => (
            <button
              key={idx}
              type="button"
              className="quick-chip-btn"
              onClick={() => sendQuery(chip)}
              disabled={isTyping}
            >
              {chip}
            </button>
          ))}
        </div>
        <button
          type="button"
          className="chip-nav-btn chip-nav-right"
          onClick={() => scrollChips(150)}
          aria-label="Lướt sang phải"
          title="Lướt sang phải"
        >
          ›
        </button>
      </div>

      {/* Input */}
      <div className="chat-popup-footer">
        <input
          ref={inputRef}
          type="text"
          className="chat-input"
          placeholder="Hỏi FinAI về chi tiêu..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          maxLength={500}
          disabled={isTyping}
        />
        <button
          className="chat-send-btn"
          onClick={handleSend}
          disabled={!input.trim() || isTyping}
          aria-label="Gửi tin nhắn"
        >
          ➤
        </button>
      </div>
    </div>
  );
};

export default ChatPopup;
