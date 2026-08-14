import React, { useState, useRef, useEffect } from 'react';
import { sendChatMessage } from '../api/chatApi';

const botAvatar = '/finai-winged-coin-favicon.png';

const WELCOME_MESSAGE = {
  role: 'assistant',
  content: 'Xin chào! 👋 Mình là FinAI, trợ lý chi tiêu cá nhân của bạn. Hãy hỏi mình bất cứ điều gì về tài chính nhé! 💰',
};

const ChatPopup = ({ isOpen, onClose }) => {
  const [messages, setMessages] = useState([WELCOME_MESSAGE]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Auto scroll to bottom when new messages arrive
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isTyping]);

  // Focus input when popup opens
  useEffect(() => {
    if (isOpen && inputRef.current) {
      setTimeout(() => inputRef.current?.focus(), 300);
    }
  }, [isOpen]);

  const handleSend = async () => {
    const trimmed = input.trim();
    if (!trimmed || isTyping) return;

    const userMsg = { role: 'user', content: trimmed };
    const updatedMessages = [...messages, userMsg];
    setMessages(updatedMessages);
    setInput('');
    setIsTyping(true);

    try {
      // Build conversation_history for API (exclude welcome message)
      const history = updatedMessages
        .filter((m) => m !== WELCOME_MESSAGE)
        .map((m) => ({ role: m.role, content: m.content }));

      const data = await sendChatMessage({
        message: trimmed,
        conversation_history: history.slice(0, -1), // Exclude current message
      });

      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: data.reply },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'Xin lỗi, mình đang gặp sự cố. Vui lòng thử lại sau! 🙏',
        },
      ]);
    } finally {
      setIsTyping(false);
    }
  };

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
        <button className="chat-popup-close" onClick={onClose} aria-label="Đóng chat">
          ✕
        </button>
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
              {msg.content}
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
