import { useRef, useCallback } from 'react';

/**
 * Hook to safely handle backdrop dismissal for modals.
 * Prevents modal from closing when user starts a mouse drag/selection inside the modal
 * and releases the mouse cursor on the backdrop overlay.
 *
 * Modal only closes if BOTH mousedown and mouseup occur directly on the backdrop element.
 */
export const useBackdropDismiss = (onClose, disabled = false) => {
  const isBackdropMouseDown = useRef(false);

  const onMouseDown = useCallback((e) => {
    isBackdropMouseDown.current = e.target === e.currentTarget;
  }, []);

  const onMouseUp = useCallback((e) => {
    if (isBackdropMouseDown.current && e.target === e.currentTarget && !disabled && onClose) {
      onClose();
    }
    isBackdropMouseDown.current = false;
  }, [disabled, onClose]);

  return { onMouseDown, onMouseUp };
};

export default useBackdropDismiss;

