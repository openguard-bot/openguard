import React, { useState, useEffect } from "react";
import { useTheme } from "next-themes";
import { useAuth } from "../contexts/AuthContext";
import { Switch } from "./ui/switch";
import { Label } from "./ui/label";
import { Button } from "./ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "./ui/dropdown-menu";
import { Avatar, AvatarFallback, AvatarImage } from "./ui/avatar";
import { Edit, Menu } from "lucide-react";
import { useNavigate } from "react-router";

const Navbar = ({ toggleSidebar }) => {
  const { theme = "system", setTheme } = useTheme();
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const isDark = theme === "dark";
  const [blogAdmins, setBlogAdmins] = useState([]);

  useEffect(() => {
    const fetchOwners = async () => {
      try {
        const response = await fetch("/api/owners");
        if (response.ok) {
          const data = await response.json();
          setBlogAdmins(data);
        }
      } catch (error) {
        console.error("Failed to fetch owners:", error);
      }
    };

    fetchOwners();
  }, []);

  // Check if user is authorized to manage blog posts
  const isBlogAdmin = user && blogAdmins.includes(parseInt(user.id));

  return (
    <nav className="flex items-center justify-between border-b px-4 py-2">
      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          size="icon"
          className="md:hidden"
          onClick={toggleSidebar}
        >
          <Menu className="h-6 w-6" />
        </Button>
        <h1 className="text-xl font-semibold">Discord Dashboard</h1>
      </div>
      <div className="flex items-center gap-4">
        {isBlogAdmin && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate("/dashboard/blog")}
            className="flex items-center gap-2"
          >
            <Edit className="h-4 w-4" />
            Manage Blog
          </Button>
        )}
        <div className="flex items-center gap-2">
          <Label htmlFor="theme-toggle">Dark Mode</Label>
          <Switch
            id="theme-toggle"
            checked={isDark}
            onCheckedChange={(checked) => setTheme(checked ? "dark" : "light")}
          />
        </div>
        {user && (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="relative h-8 w-8 rounded-full">
                <Avatar className="h-8 w-8">
                  <AvatarImage
                    src={`https://cdn.discordapp.com/avatars/${user.id}/${user.avatar}.png`}
                    alt={user.username}
                  />
                  <AvatarFallback>{user.username.charAt(0)}</AvatarFallback>
                </Avatar>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent className="w-56" align="end" forceMount>
              <DropdownMenuLabel className="font-normal">
                <div className="flex flex-col space-y-1">
                  <p className="text-sm font-medium leading-none">
                    {user.username}
                  </p>
                  <p className="text-muted-foreground text-xs leading-none">
                    {user.email}
                  </p>
                </div>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={logout}>Log out</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </div>
    </nav>
  );
};

export default Navbar;
