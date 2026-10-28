import { useState, useEffect } from 'react';
import { getMe } from '../api/authApi';
import { AuthContext } from './auth-context';

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchUser = async () => {
      const token = localStorage.getItem('access_token');
      if (token) {
        try {
          const userData = await getMe();
          setUser(userData);
        } catch (error) {
          console.error("Lỗi xác thực token", error);
          localStorage.removeItem('access_token');
          setUser(null);
        }
      }
      setLoading(false);
    };

    fetchUser();
  }, []);

  useEffect(() => {
    const handleUnauthorized = () => {
      try {
        Object.keys(localStorage).forEach((key) => {
          if (key.startsWith('finai_chat_')) {
            localStorage.removeItem(key);
          }
        });
      } catch {
        // ignore
      }
      setUser(null);
    };
    window.addEventListener('auth:unauthorized', handleUnauthorized);
    return () => window.removeEventListener('auth:unauthorized', handleUnauthorized);
  }, []);

  const login = (token) => {
    localStorage.setItem('access_token', token);
  };

  const logout = () => {
    try {
      Object.keys(localStorage).forEach((key) => {
        if (key.startsWith('finai_chat_')) {
          localStorage.removeItem(key);
        }
      });
    } catch {
      // ignore
    }
    localStorage.removeItem('access_token');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, setUser, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
};
