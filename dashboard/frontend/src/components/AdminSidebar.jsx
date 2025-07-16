import React from "react";
import { NavLink } from "react-router-dom";
import { Home, Server } from "lucide-react";

const AdminSidebar = ({ isOpen, toggleSidebar }) => {
  return (
    <aside
      className={`bg-gray-800 text-white w-64 p-4 transition-transform transform ${
        isOpen ? "translate-x-0" : "-translate-x-full"
      } md:translate-x-0 md:relative fixed h-full z-20`}
    >
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
              onClick={toggleSidebar}
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
              onClick={toggleSidebar}
            >
              <Server className="mr-2" />
              Guilds
            </NavLink>
          </li>
        </ul>
      </nav>
    </aside>
  );
};

export default AdminSidebar;