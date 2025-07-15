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
    <div className="flex min-h-screen flex-col items-center justify-center">
      <Card className="w-full max-w-md py-16 px-12 flex flex-col items-center justify-center">
        <CardHeader className="flex flex-col items-center text-center">
          <CardTitle className="text-4xl font-bold text-center">Welcome!</CardTitle>
          <CardDescription className="text-center whitespace-nowrap text-lg">
            Login with Discord to manage your servers.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button onClick={handleLogin} className="w-full h-14 text-lg" size="lg">
            <FaDiscord/>
            Login with Discord
          </Button>
        </CardContent>
      </Card>
    </div>
  );
};

export default LoginPage;
