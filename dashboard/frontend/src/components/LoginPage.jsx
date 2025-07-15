import React from 'react';
import { Button } from './ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from './ui/card';
import { FaDiscord } from 'react-icons/fa';

const LoginPage = () => {
  const API_BASE_URL = import.meta.env.VITE_REACT_APP_API_URL || '';

  const handleLogin = () => {
    window.location.href = `${API_BASE_URL}/api/login`;
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gray-100 dark:bg-gray-900">
      <Card className="w-full max-w-sm">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl font-bold">Welcome!</CardTitle>
          <CardDescription>
            Login with Discord to manage your servers.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button onClick={handleLogin} className="w-full" size="lg">
            <FaDiscord className="mr-2 h-5 w-5" />
            Login with Discord
          </Button>
        </CardContent>
      </Card>
    </div>
  );
};

export default LoginPage;
