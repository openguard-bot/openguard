import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { AuthContext } from './AuthContextDeclaration';

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchUser = async () => {
      try {
        const response = await axios.get('/api/users/@me');
        setUser(response.data);
      } catch (error) { // Renamed 'err' to 'error'
        // This is expected if the user is not logged in
        setUser(null);
        console.error("Failed to fetch user:", error); // Log the error for debugging
      } finally {
        setLoading(false);
      }
    };

    fetchUser();
  }, []);

  const logout = async () => {
    try {
      await axios.get('/api/auth/logout');
      setUser(null);
      window.location.href = '/login';
    } catch (error) { // Renamed 'err' to 'error'
      console.error('Failed to logout', error); // Log the error for debugging
    }
  };

  const value = {
    user,
    isAuthenticated: !loading && user,
    loading,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};