import React from 'react';
import { Link } from 'react-router';
import { Button } from './ui/button';

function LandingPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 text-center">
      <h1 className="text-3xl font-bold">Welcome to OpenGuard</h1>
      <p className="text-muted-foreground">Your moderation dashboard.</p>
      <Button asChild>
        <Link to="/dashboard">Go to Dashboard</Link>
      </Button>
    </div>
  );
}

export default LandingPage;
