import React, { lazy, Suspense } from "react";
import {
  BrowserRouter as Router,
  Route,
  Routes,
  Navigate,
} from "react-router-dom";
import LoginPage from "./components/LoginPage";
import ProtectedRoute from "./components/ProtectedRoute";
import Layout from "./components/Layout";
import { Toaster } from "./components/ui/sonner";
import "./App.css";

const DashboardPage = lazy(() => import("./components/DashboardPage"));
const GuildOverviewPage = lazy(() => import("./components/GuildOverviewPage"));
const GuildConfigPage = lazy(() => import("./components/GuildConfigPage"));
const AnalyticsDashboard = lazy(() => import("./components/AnalyticsDashboard"));
const BlogManagement = lazy(() => import("./components/BlogManagement"));

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
                  <Suspense fallback={<div>Loading Dashboard...</div>}>
                    <DashboardPage />
                  </Suspense>
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/:guildId"
            element={
              <ProtectedRoute>
                <Layout>
                  <Suspense fallback={<div>Loading Guild Overview...</div>}>
                    <GuildOverviewPage />
                  </Suspense>
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/:guildId/config"
            element={
              <ProtectedRoute>
                <Layout>
                  <Suspense fallback={<div>Loading Guild Config...</div>}>
                    <GuildConfigPage />
                  </Suspense>
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/:guildId/analytics"
            element={
              <ProtectedRoute>
                <Layout>
                  <Suspense fallback={<div>Loading Analytics...</div>}>
                    <AnalyticsDashboard />
                  </Suspense>
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/blog"
            element={
              <ProtectedRoute>
                <Layout>
                  <Suspense fallback={<div>Loading Blog Management...</div>}>
                    <BlogManagement />
                  </Suspense>
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
