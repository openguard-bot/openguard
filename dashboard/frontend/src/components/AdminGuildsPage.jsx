import React, { useState, useEffect } from "react";
import axios from "axios";
import { Link } from "react-router-dom";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "./ui/table";
import { Button } from "./ui/button";

const AdminGuildsPage = () => {
  const [guilds, setGuilds] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchGuilds = async () => {
      try {
        const response = await axios.get("/api/admin/guilds");
        setGuilds(response.data);
      } catch (error) {
        console.error("Failed to fetch guilds:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchGuilds();
  }, []);

  if (loading) {
    return <div>Loading guilds...</div>;
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Guild Management</h1>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Icon</TableHead>
            <TableHead>Name</TableHead>
            <TableHead>ID</TableHead>
            <TableHead>Owner ID</TableHead>
            <TableHead>Members</TableHead>
            <TableHead>Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {guilds.map((guild) => (
            <TableRow key={guild.id}>
              <TableCell>
                {guild.icon && (
                  <img
                    src={`https://cdn.discordapp.com/icons/${guild.id}/${guild.icon}.png`}
                    alt={guild.name}
                    className="w-10 h-10 rounded-full"
                  />
                )}
              </TableCell>
              <TableCell>{guild.name}</TableCell>
              <TableCell>{guild.id}</TableCell>
              <TableCell>{guild.owner_id}</TableCell>
              <TableCell>{guild.member_count}</TableCell>
              <TableCell>
                <Link to={`guilds/${guild.id}`}>
                  <Button>Manage</Button>
                </Link>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
};

export default AdminGuildsPage;