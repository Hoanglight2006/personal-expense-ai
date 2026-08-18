import { useEffect } from 'react';

/**
 * Custom hook to handle global modal interactions.
 * When modal is open:
 * 1. Leaves the root scrolling element untouched so sticky layout elements do not jump.
 * 2. Relies on the fixed, scrollable modal backdrop to contain pointer/touch scrolling.
 * 3. Listens for Escape key to close modal.
 */
export const useModalLock = (isOpen = true, onClose) => {
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && onClose) {
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose]);
};

export default useModalLock;
