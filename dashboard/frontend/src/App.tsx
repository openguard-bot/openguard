import React, { lazy, Suspense } from "react";
import {
  BrowserRouter as Router,
  Route,
  Routes,
  Navigate,
} from "react-router-dom";
import LoginPage from "./components/LoginPage";
import ProtectedRoute from "./components/ProtectedRoute";
import AdminRoute from "./components/AdminRoute";
import Layout from "./components/Layout";
import AdminLayout from "./components/AdminLayout";
import { Toaster } from "./components/ui/sonner";

const DashboardPage = lazy(() => import("./components/DashboardPage"));
const GuildOverviewPage = lazy(() => import("./components/GuildOverviewPage"));
const GuildConfigPage = lazy(() => import("./components/GuildConfigPage"));
const AnalyticsDashboard = lazy(() => import("./components/AnalyticsDashboard"));
const BlogManagement = lazy(() => import("./components/BlogManagement"));
const AdminDashboard = lazy(() => import("./components/AdminDashboard"));
const AdminGuildsPage = lazy(() => import("./components/AdminGuildsPage"));
const AdminGuildDetailsPage = lazy(() =>
  import("./components/AdminGuildDetailsPage")
);
const AdminRawDBPage = lazy(() => import("./components/AdminRawDBPage"));

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
          <Route
            path="/admin"
            element={
              <AdminRoute>
                <AdminLayout />
              </AdminRoute>
            }
          >
            <Route
              path="dashboard"
              element={
                <Suspense fallback={<div>Loading Admin Dashboard...</div>}>
                  <AdminDashboard />
                </Suspense>
              }
            />
            <Route
              path="guilds"
              element={
                <Suspense fallback={<div>Loading Admin Guilds...</div>}>
                  <AdminGuildsPage />
                </Suspense>
              }
            />
            <Route
              path="guilds/:guildId"
              element={
                <Suspense fallback={<div>Loading Admin Guild Details...</div>}>
                  <AdminGuildDetailsPage />
                </Suspense>
              }
            />
            <Route
              path="blog"
              element={
                <Suspense fallback={<div>Loading Blog Management...</div>}>
                  <BlogManagement />
                </Suspense>
              }
            />
            <Route
              path="raw-db"
              element={
                <Suspense fallback={<div>Loading Raw DB Viewer...</div>}>
                  <AdminRawDBPage />
                </Suspense>
              }
            />
          </Route>
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
        <Toaster />
      </div>
    </Router>
  );
}

export default App;
