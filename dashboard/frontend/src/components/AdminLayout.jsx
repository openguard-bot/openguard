import React from "react";
import { NavLink, Outlet } from "react-router-dom";
import {
  Home,
  Server,
  Settings,
  BarChart,
  MessageSquare,
} from "lucide-react";

const AdminSidebar = () => (
  <aside className="w-64 bg-gray-800 text-white p-4">
    <h2 className="text-2xl font-bold mb-4">Admin Panel</h2>
    <nav>
      <ul>
        <li>
          <NavLink
            to="/admin/dashboard"
            className={({ isActive }) =>
              `flex items-center p-2 rounded-md ${
                isActive ? "bg-gray-700" : "hover:bg-gray-700"
              }`
            }
          >
            <Home className="mr-2" />
            Dashboard
          </NavLink>
        </li>
        <li>
          <NavLink
            to="/admin/guilds"
            className={({ isActive }) =>
              `flex items-center p-2 rounded-md ${
                isActive ? "bg-gray-700" : "hover:bg-gray-700"
              }`
            }
          >
            <Server className="mr-2" />
            Guilds
          </NavLink>
        </li>
      </ul>
    </nav>
  </aside>
);

const AdminLayout = () => {
  return (
    <div className="flex h-screen">
      <AdminSidebar />
      <main className="flex-1 p-6 bg-gray-100 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  );
};

export default AdminLayout;