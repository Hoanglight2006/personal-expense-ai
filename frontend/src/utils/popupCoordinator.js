const POPUP_OPEN_EVENT = 'finai:popup-open';

export const announcePopupOpen = (popupId) => {
  if (typeof window === 'undefined') return;
  window.dispatchEvent(new CustomEvent(POPUP_OPEN_EVENT, { detail: popupId }));
};

export const subscribeToPopupOpen = (listener) => {
  if (typeof window === 'undefined') return () => {};
  window.addEventListener(POPUP_OPEN_EVENT, listener);
  return () => window.removeEventListener(POPUP_OPEN_EVENT, listener);
};
