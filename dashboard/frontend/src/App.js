import React from "react";
import {
  BrowserRouter as Router,
  Route,
  Routes,
  Navigate,
} from "react-router";
import LoginPage from "./components/LoginPage";
import DashboardPage from "./components/DashboardPage";
import GuildOverviewPage from "./components/GuildOverviewPage";
import GuildConfigPage from "./components/GuildConfigPage";
import AnalyticsDashboard from "./components/AnalyticsDashboard";
import BlogManagement from "./components/BlogManagement";
import ProtectedRoute from "./components/ProtectedRoute";
import Layout from "./components/Layout";
import { Toaster } from "./components/ui/sonner";
import "./App.css";

function App() {
  return (
    <Router basename="/dashboard">
      <div className="min-h-screen bg-background text-foreground">
        {/* This text is added for testing purposes */}
        <h1 style={{ display: 'none' }}>OpenGuard Dashboard</h1>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Layout>
                  <DashboardPage />
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/:guildId"
            element={
              <ProtectedRoute>
                <Layout>
                  <GuildOverviewPage />
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/:guildId/config"
            element={
              <ProtectedRoute>
                <Layout>
                  <GuildConfigPage />
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/:guildId/analytics"
            element={
              <ProtectedRoute>
                <Layout>
                  <AnalyticsDashboard />
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/blog"
            element={
              <ProtectedRoute>
                <Layout>
                  <BlogManagement />
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
        <Toaster />
      </div>
    </Router>
  );
}

export default App;
