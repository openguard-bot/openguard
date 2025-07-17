import React from "react";
import { NavLink } from "react-router-dom";
import { ScrollArea } from "./ui/scroll-area";
import { Home, Server, Database, FileText } from "lucide-react";

const AdminSidebar = ({ isOpen, toggleSidebar }) => {

  return (
    <div
      className={`fixed inset-y-0 left-0 z-50 w-64 transform bg-background p-4 transition-transform duration-300 ease-in-out md:relative md:z-auto md:translate-x-0 ${
        isOpen ? "translate-x-0" : "-translate-x-full"
      }`}
    >
      <div className="flex items-center justify-between p-4">
        <h2 className="text-xl font-semibold">Admin Panel</h2>
      </div>
      <ScrollArea className="flex-1">
        <nav className="p-2">
          <ul>
            <li>
              <NavLink
                to="/admin/dashboard"
                className={({ isActive }) =>
                  `flex items-center gap-2 rounded-md p-2 transition-colors hover:bg-muted ${
                    isActive ? "bg-muted" : ""
                  }`
                }
                onClick={toggleSidebar}
              >
                <Home className="h-5 w-5" />
                <span className="truncate">Dashboard</span>
              </NavLink>
            </li>
            <li>
              <NavLink
                to="/admin/guilds"
                className={({ isActive }) =>
                  `flex items-center gap-2 rounded-md p-2 transition-colors hover:bg-muted ${
                    isActive ? "bg-muted" : ""
                  }`
                }
                onClick={toggleSidebar}
              >
                <Server className="h-5 w-5" />
                <span className="truncate">Guilds</span>
              </NavLink>
            </li>
            <li>
              <NavLink
                to="/admin/blog"
                className={({ isActive }) =>
                  `flex items-center gap-2 rounded-md p-2 transition-colors hover:bg-muted ${
                    isActive ? "bg-muted" : ""
                  }`
                }
                onClick={toggleSidebar}
              >
                <FileText className="h-5 w-5" />
                <span className="truncate">Blog Management</span>
              </NavLink>
            </li>
            <li>
              <NavLink
                to="/admin/raw-db"
                className={({ isActive }) =>
                  `flex items-center gap-2 rounded-md p-2 transition-colors hover:bg-muted ${
                    isActive ? "bg-muted" : ""
                  }`
                }
                onClick={toggleSidebar}
              >
                <Database className="h-5 w-5" />
                <span className="truncate">Raw DB</span>
              </NavLink>
            </li>
          </ul>
        </nav>
      </ScrollArea>
    </div>
  );
};

export default AdminSidebar;