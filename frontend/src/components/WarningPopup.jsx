import { useId, useLayoutEffect, useRef } from 'react';
import { createPortal } from 'react-dom';

const WarningPopup = ({
  isOpen,
  title = 'Không thể thực hiện',
  message,
  onClose,
  closeText = 'Đã hiểu',
}) => {
  const titleId = useId();
  const messageId = useId();
  const closeButtonRef = useRef(null);
  const previousFocusRef = useRef(null);

  useLayoutEffect(() => {
    if (!isOpen) return undefined;
    previousFocusRef.current = document.activeElement;
    closeButtonRef.current?.focus({ preventScroll: true });

    const handleKeyDown = (event) => {
      if (event.key !== 'Escape') return;
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();
      onClose();
    };
    window.addEventListener('keydown', handleKeyDown, true);

    return () => {
      window.removeEventListener('keydown', handleKeyDown, true);
      previousFocusRef.current?.focus?.({ preventScroll: true });
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return createPortal(
    <div
      className="warning-popup-backdrop"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <section
        className="warning-popup"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={messageId}
      >
        <div className="warning-popup-icon" aria-hidden="true">!</div>
        <div className="warning-popup-content">
          <h2 id={titleId}>{title}</h2>
          <p id={messageId}>{message}</p>
        </div>
        <button
          ref={closeButtonRef}
          type="button"
          className="btn-primary warning-popup-close"
          onClick={onClose}
        >
          {closeText}
        </button>
      </section>
    </div>,
    document.body,
  );
};

export default WarningPopup;
