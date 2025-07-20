import React, { useState, useEffect, useCallback } from "react";
import axios from "axios";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "./ui/table";
import { Button } from "./ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "./ui/dialog";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { toast } from "sonner";

const AdminRawDBPage = () => {
  const [tables, setTables] = useState([]);
  const [selectedTable, setSelectedTable] = useState(null);
  const [tableData, setTableData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [editingRow, setEditingRow] = useState(null);
  const [pkColumn, setPkColumn] = useState(null);
  const [healthStatus, setHealthStatus] = useState(null);

  useEffect(() => {
    const fetchTables = async () => {
      try {
        const response = await axios.get("/api/admin/db/tables");
        setTables(response.data);
      } catch (error) {
        console.error("Failed to fetch tables:", error);
        const errorMessage = error.response?.data?.detail || error.message || "Failed to fetch tables";
        toast.error(`Error: ${errorMessage}`);
      }
    };
    fetchTables();
  }, []);

  const fetchTableData = useCallback(async (tableName) => {
    setLoading(true);
    setSelectedTable(tableName);
    try {
      const response = await axios.get(`/api/admin/db/tables/${tableName}`);
      setTableData(response.data);
      if (response.data.length > 0) {
        // A simple heuristic to find a primary key.
        // A more robust solution would be to get this from the backend.
        const potentialPks = ["id", "user_id", "guild_id"];
        const foundPk = potentialPks.find(pk => pk in response.data[0]);
        setPkColumn(foundPk);
      }
    } catch (error) {
      console.error(`Failed to fetch data for table ${tableName}:`, error);
      const errorMessage = error.response?.data?.detail || error.message || `Failed to fetch data for table ${tableName}`;
      toast.error(`Error: ${errorMessage}`);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleRowChange = (e) => {
    const { name, value } = e.target;
    setEditingRow((prev) => ({ ...prev, [name]: value }));
  };

  const handleSave = async () => {
    if (!editingRow || !selectedTable || !pkColumn) return;

    const pkValue = editingRow[pkColumn];
    try {
      await axios.put(
        `/api/admin/db/tables/${selectedTable}/${pkValue}`,
        { row_data: editingRow }
      );
      toast.success("Row updated successfully.");
      setEditingRow(null);
      fetchTableData(selectedTable); // Refresh data
    } catch (error) {
      console.error("Failed to update row:", error);
      toast.error("Failed to update row.");
    }
  };

  const testHealthCheck = async () => {
    try {
      const response = await axios.get("/api/admin/health");
      setHealthStatus(response.data);
      toast.success("Health check passed!");
    } catch (error) {
      console.error("Health check failed:", error);
      const errorMessage = error.response?.data?.detail || error.message || "Health check failed";
      toast.error(`Health check failed: ${errorMessage}`);
      setHealthStatus({ status: "error", error: errorMessage });
    }
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Raw Database Access</h1>

      {/* Health Check Section */}
      <div className="mb-4 p-4 border rounded">
        <div className="flex items-center gap-4 mb-2">
          <Button onClick={testHealthCheck} variant="outline">
            Test Database Connection
          </Button>
          {healthStatus && (
            <span className={`text-sm ${healthStatus.status === 'healthy' ? 'text-green-600' : 'text-red-600'}`}>
              Status: {healthStatus.status}
              {healthStatus.database && ` | DB: ${healthStatus.database}`}
              {healthStatus.user_infractions_count !== undefined && ` | User Infractions: ${healthStatus.user_infractions_count}`}
            </span>
          )}
        </div>
      </div>

      <div className="flex space-x-2 mb-4">
        {tables.map((table) => (
          <Button
            key={table}
            variant={selectedTable === table ? "default" : "outline"}
            onClick={() => fetchTableData(table)}
          >
            {table}
          </Button>
        ))}
      </div>

      {loading && <div>Loading data...</div>}

      {selectedTable && !loading && (
        <Card>
          <CardHeader>
            <CardTitle>Table: {selectedTable}</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  {tableData.length > 0 &&
                    Object.keys(tableData[0]).map((key) => (
                      <TableHead key={key}>{key}</TableHead>
                    ))}
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {tableData.map((row, index) => (
                  <TableRow key={index}>
                    {Object.entries(row).map(([key, value]) => (
                      <TableCell key={key}>
                        {typeof value === "boolean" ? String(value) : value}
                      </TableCell>
                    ))}
                    <TableCell>
                      <Dialog>
                        <DialogTrigger asChild>
                          <Button
                            variant="outline"
                            onClick={() => setEditingRow(row)}
                          >
                            Edit
                          </Button>
                        </DialogTrigger>
                        <DialogContent>
                          <DialogHeader>
                            <DialogTitle>Edit Row</DialogTitle>
                          </DialogHeader>
                          <div className="space-y-4">
                            {editingRow &&
                              Object.entries(editingRow).map(
                                ([key, value]) => (
                                  <div key={key}>
                                    <Label htmlFor={key}>{key}</Label>
                                    <Input
                                      id={key}
                                      name={key}
                                      value={value}
                                      onChange={handleRowChange}
                                      disabled={key === pkColumn}
                                    />
                                  </div>
                                )
                              )}
                          </div>
                          <Button onClick={handleSave} className="mt-4">
                            Save
                          </Button>
                        </DialogContent>
                      </Dialog>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default AdminRawDBPage;