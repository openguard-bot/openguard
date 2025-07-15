import { useContext } from 'react';
import { AuthContext } from '../contexts/AuthContextDeclaration';

export const useAuth = () => useContext(AuthContext);