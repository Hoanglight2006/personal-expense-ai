/**
 * Trả về URL đầy đủ cho ảnh đại diện (hỗ trợ cả đường dẫn tĩnh /static/... từ backend)
 */
export const getAvatarSrc = (url) => {
  if (!url) return '';
  if (
    url.startsWith('data:') ||
    url.startsWith('http://') ||
    url.startsWith('https://') ||
    url.startsWith('blob:')
  ) {
    return url;
  }
  if (url.startsWith('/static/')) {
    const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
    const backendOrigin = apiBase.replace(/\/api\/v1\/?$/, '');
    return `${backendOrigin}${url}`;
  }
  return url;
};
