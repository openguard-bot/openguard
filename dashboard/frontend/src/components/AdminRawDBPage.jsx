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
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "./ui/alert-dialog";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { toast } from "sonner";

const AdminRawDBPage = () => {
  const [tables, setTables] = useState([]);
  const [selectedTable, setSelectedTable] = useState(null);
  const [tableData, setTableData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [editingRow, setEditingRow] = useState(null);
  const [deletingRow, setDeletingRow] = useState(null);
  const [pkColumns, setPkColumns] = useState([]);

  useEffect(() => {
    const fetchTables = async () => {
      try {
        const response = await axios.get("/api/admin/db/tables");
        setTables(response.data);
      } catch (error) {
        console.error("Failed to fetch tables:", error);
        toast.error("Failed to fetch tables.");
      }
    };
    fetchTables();
  }, []);

  const fetchTableData = useCallback(async (tableName) => {
    setLoading(true);
    setSelectedTable(tableName);
    setPkColumns([]); // Reset PK columns on table change
    try {
      const [dataRes, pkRes] = await Promise.all([
        axios.get(`/api/admin/db/tables/${tableName}`),
        axios.get(`/api/admin/db/tables/${tableName}/pk`),
      ]);
      setTableData(dataRes.data);
      setPkColumns(pkRes.data);
    } catch (error) {
      console.error(`Failed to fetch data for table ${tableName}:`, error);
      toast.error(`Failed to fetch data or PK for table ${tableName}.`);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleRowChange = (e) => {
    const { name, value } = e.target;
    setEditingRow((prev) => ({ ...prev, [name]: value }));
  };

  const handleSave = async () => {
    if (!editingRow || !selectedTable || pkColumns.length === 0) return;

    const pkValues = pkColumns.reduce((acc, pk) => {
      acc[pk] = editingRow[pk];
      return acc;
    }, {});

    const rowData = { ...editingRow };
    // Remove pk values from the main row data if they are not editable
    pkColumns.forEach(pk => delete rowData[pk]);

    try {
      await axios.put(`/api/admin/db/tables/${selectedTable}/row`, {
        pk_values: pkValues,
        row_data: rowData,
      });
      toast.success("Row updated successfully.");
      setEditingRow(null);
      fetchTableData(selectedTable); // Refresh data
    } catch (error) {
      console.error("Failed to update row:", error);
      toast.error(
        `Failed to update row: ${error.response?.data?.detail || error.message}`
      );
    }
  };

  const handleDelete = async () => {
    if (!deletingRow || !selectedTable || pkColumns.length === 0) return;

    const pkValues = pkColumns.reduce((acc, pk) => {
      acc[pk] = deletingRow[pk];
      return acc;
    }, {});

    try {
      await axios.delete(`/api/admin/db/tables/${selectedTable}/row`, {
        data: { pk_values: pkValues },
      });
      toast.success("Row deleted successfully.");
      setDeletingRow(null);
      fetchTableData(selectedTable); // Refresh data
    } catch (error) {
      console.error("Failed to delete row:", error);
      toast.error(
        `Failed to delete row: ${error.response?.data?.detail || error.message}`
      );
    }
  };

  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold mb-4">Raw Database Access</h1>
      <div className="flex flex-wrap gap-2 mb-4">
        {tables.map((table) => (
          <Button
            key={table}
            variant={selectedTable === table ? "solid" : "outline"}
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
            <div className="overflow-x-auto">
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
                          {typeof value === "object" && value !== null
                            ? JSON.stringify(value, null, 2)
                            : typeof value === "boolean"
                            ? String(value)
                            : value}
                        </TableCell>
                      ))}
                      <TableCell className="flex gap-2">
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
                                        value={
                                          typeof value === "object" &&
                                          value !== null
                                            ? JSON.stringify(value)
                                            : value
                                        }
                                        onChange={handleRowChange}
                                        disabled={pkColumns.includes(key)}
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
                        <AlertDialog>
                          <AlertDialogTrigger asChild>
                            <Button
                              variant="destructive"
                              onClick={() => {
                                if (pkColumns.length > 0) {
                                  setDeletingRow(row);
                                } else {
                                  toast.error(
                                    "Primary key not identified, cannot delete."
                                  );
                                }
                              }}
                            >
                              Delete
                            </Button>
                          </AlertDialogTrigger>
                          <AlertDialogContent>
                            <AlertDialogHeader>
                              <AlertDialogTitle>
                                Are you absolutely sure?
                              </AlertDialogTitle>
                              <AlertDialogDescription>
                                This action cannot be undone. This will
                                permanently delete the row from the database.
                              </AlertDialogDescription>
                            </AlertDialogHeader>
                            <AlertDialogFooter>
                              <AlertDialogCancel
                                onClick={() => setDeletingRow(null)}
                              >
                                Cancel
                              </AlertDialogCancel>
                              <AlertDialogAction onClick={handleDelete}>
                                Continue
                              </AlertDialogAction>
                            </AlertDialogFooter>
                          </AlertDialogContent>
                        </AlertDialog>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default AdminRawDBPage;