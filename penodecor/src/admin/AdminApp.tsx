import { Navigate } from "react-router-dom";
import { useSyncExternalStore } from "react";
import { AdminShell } from "./AdminShell";
import { getAdminToken, subscribeAdminSession } from "../lib/adminSession";

function useAdminToken(): string | null {
  return useSyncExternalStore(subscribeAdminSession, getAdminToken, getAdminToken);
}

export function RequireAdmin() {
  const token = useAdminToken();
  if (!token) return <Navigate to="/admin/login" replace />;
  return <AdminShell />;
}
