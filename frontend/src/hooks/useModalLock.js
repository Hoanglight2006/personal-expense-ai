import { useEffect } from 'react';

/**
 * Custom hook to lock body and html scrolling and trap interactions to the modal.
 * When modal is open:
 * 1. Locks document.body and document.documentElement scroll completely.
 * 2. Listens for Escape key to close modal.
 * 3. Prevents wheel scroll chaining from leaking into the background page.
 */
export const useModalLock = (isOpen = true, onClose) => {
  useEffect(() => {
    if (!isOpen) return;

    const originalBodyOverflow = document.body.style.overflow;
    const originalHtmlOverflow = document.documentElement.style.overflow;
    const originalBodyPosition = document.body.style.position;
    const originalBodyWidth = document.body.style.width;

    document.body.style.overflow = 'hidden';
    document.documentElement.style.overflow = 'hidden';

    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && onClose) {
        onClose();
      }
    };

    // Prevent wheel events outside modal content from scrolling background
    const handleWheel = (e) => {
      const modalBackdrop = e.target.closest('.modal-backdrop');
      const modalContent = e.target.closest('.category-modal, .budget-modal, .excel-preview-modal');
      
      // If wheel happened outside modal dialog (directly on backdrop), block it
      if (modalBackdrop && !modalContent) {
        e.preventDefault();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('wheel', handleWheel, { passive: false });

    return () => {
      document.body.style.overflow = originalBodyOverflow;
      document.documentElement.style.overflow = originalHtmlOverflow;
      document.body.style.position = originalBodyPosition;
      document.body.style.width = originalBodyWidth;
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('wheel', handleWheel);
    };
  }, [isOpen, onClose]);
};

export default useModalLock;
