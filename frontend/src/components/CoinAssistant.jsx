import React, { useState, useEffect, useRef, useCallback } from 'react';
import ChatPopup from './ChatPopup';
import coinBody from '../assets/coin_3d_ver0.1.png';
import leftWing from '../assets/leftwing_coin_3d.png';
import rightWing from '../assets/rightwing_coin_3d.png';

const botAvatar = '/finai-winged-coin-favicon.png';

const RANDOM_BUBBLES = [
  "Hôm nay chi bao nhiêu rồi? 🤔",
  "Xem tóm tắt chi tiêu không? 💰",
  "Muốn tiết kiệm thêm không? ✨",
  "Chi nhiều nhất vào đâu nhỉ? 📊",
  "Mình giúp phân tích tài chính! 🧠",
  "Click mình để trò chuyện! 💬",
  "Đặt mục tiêu tiết kiệm chưa? 🎯",
  "Kiểm tra tài chính nào! 💪",
];

const CoinAssistant = () => {
  const [isMinimized, setIsMinimized] = useState(() => {
    return localStorage.getItem('finai_assistant_minimized') === 'true';
  });
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [bubble, setBubble] = useState(null);
  const [bubbleVisible, setBubbleVisible] = useState(false);
  const bubbleTimerRef = useRef(null);
  const hideTimerRef = useRef(null);

  const showRandomBubble = useCallback(() => {
    if (isChatOpen || isMinimized) return;
    const randomIdx = Math.floor(Math.random() * RANDOM_BUBBLES.length);
    setBubble(RANDOM_BUBBLES[randomIdx]);
    setBubbleVisible(true);

    hideTimerRef.current = setTimeout(() => {
      setBubbleVisible(false);
    }, 5000);
  }, [isChatOpen, isMinimized]);

  useEffect(() => {
    if (isMinimized || isChatOpen) {
      setBubbleVisible(false);
      return;
    }

    const initialTimer = setTimeout(() => {
      showRandomBubble();
    }, 8000);

    const scheduleNext = () => {
      const delay = 20000 + Math.random() * 15000;
      bubbleTimerRef.current = setTimeout(() => {
        showRandomBubble();
        scheduleNext();
      }, delay);
    };

    bubbleTimerRef.current = setTimeout(() => {
      scheduleNext();
    }, 10000);

    return () => {
      clearTimeout(initialTimer);
      clearTimeout(bubbleTimerRef.current);
      clearTimeout(hideTimerRef.current);
    };
  }, [showRandomBubble, isMinimized, isChatOpen]);

  useEffect(() => {
    if (isChatOpen || isMinimized) {
      setBubbleVisible(false);
    }
  }, [isChatOpen, isMinimized]);

  const handleCoinClick = () => {
    setIsChatOpen(true);
  };

  const handleCloseChat = () => {
    setIsChatOpen(false);
  };

  const handleMinimize = (e) => {
    e?.stopPropagation();
    setIsMinimized(true);
    setIsChatOpen(false);
    setBubbleVisible(false);
    localStorage.setItem('finai_assistant_minimized', 'true');
  };

  const handleRestore = () => {
    setIsMinimized(false);
    localStorage.setItem('finai_assistant_minimized', 'false');
  };

  return (
    <div className={`coin-assistant-container ${isMinimized ? 'minimized' : ''} ${isChatOpen ? 'chat-open' : ''}`}>
      {isChatOpen ? (
        /* Chat Popup appears right in place of the assistant */
        <ChatPopup isOpen={isChatOpen} onClose={handleCloseChat} onMinimize={handleMinimize} />
      ) : isMinimized ? (
        /* Minimized mini-button in corner */
        <button
          className="coin-minimized-btn"
          onClick={handleRestore}
          aria-label="Mở lại trợ lý FinAI"
          title="Mở trợ lý FinAI"
        >
          <img src={botAvatar} alt="FinAI" className="coin-minimized-icon" />
          <span className="coin-minimized-tooltip">FinAI</span>
        </button>
      ) : (
        /* Full Coin + Bubble wrapper — they move together */
        <div className="coin-flying-wrapper">
          {/* Speech Bubble — attached to coin, moves with it */}
          <div className={`coin-speech-bubble ${bubbleVisible ? 'visible' : ''}`}>
            <p>{bubble}</p>
            <div className="bubble-tail" />
          </div>

          {/* Coin Character Button & Hide button */}
          <div className="coin-character-wrapper">
            <button
              className="coin-hide-btn"
              onClick={handleMinimize}
              aria-label="Ẩn trợ lý"
              title="Ẩn trợ lý"
            >
              ✕
            </button>

            <button
              className="coin-character"
              onClick={handleCoinClick}
              aria-label="Mở trợ lý FinAI"
              title="FinAI — Trợ lý chi tiêu"
            >
              <div className="coin-body-wrapper">
                <img src={leftWing} alt="" className="coin-wing coin-wing-left" draggable={false} />
                <img src={coinBody} alt="FinAI" className="coin-body" draggable={false} />
                <img src={rightWing} alt="" className="coin-wing coin-wing-right" draggable={false} />
              </div>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default React.memo(CoinAssistant);
