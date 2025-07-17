import { useState, useEffect } from "react";
import axios from "axios";
import { useAuth } from "./useAuth";

export const useAdmin = () => {
  const { user } = useAuth();
  const [isAdmin, setIsAdmin] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkAdminStatus = async () => {
      if (!user) {
        setLoading(false);
        return;
      }

      try {
        const response = await axios.get("/api/owners");
        const ownerIds = response.data;
        setIsAdmin(ownerIds.includes(parseInt(user.id)));
      } catch (error) {
        console.error("Failed to fetch owner IDs:", error);
        setIsAdmin(false);
      } finally {
        setLoading(false);
      }
    };

    checkAdminStatus();
  }, [user]);

  return { isAdmin, loading };
};