import { NavLink, Outlet } from "react-router-dom";
import { useSyncExternalStore } from "react";
import { adminLogout } from "../lib/adminApi";
import { getAdminToken, subscribeAdminSession } from "../lib/adminSession";

const links = [
  { to: "/admin", label: "Dashboard", end: true },
  { to: "/admin/kategoriyalar", label: "Kategoriyalar", end: false },
  { to: "/admin/mahsulotlar", label: "Mahsulotlar", end: false },
  { to: "/admin/ombor", label: "Tayyor mahsulotlar ombori", end: false },
  { to: "/admin/narxsiz", label: "Narxsiz mahsulotlar", end: false },
  { to: "/admin/sinxron", label: "Google Sheets", end: false },
];

function useAdminToken(): string | null {
  return useSyncExternalStore(subscribeAdminSession, getAdminToken, getAdminToken);
}

export function AdminShell() {
  const token = useAdminToken();
  return (
    <div className="min-h-dvh overflow-x-hidden bg-mist text-ink">
      <header className="bg-brand text-white">
        <div className="mx-auto flex w-full max-w-5xl min-w-0 items-center justify-between gap-3 px-4 py-4">
          <div className="min-w-0">
            <p className="text-xs uppercase tracking-[0.16em] text-white/70">PenodecorPro</p>
            <h1 className="truncate text-lg font-semibold">Do‘kon administratori</h1>
          </div>
          <button
            type="button"
            className="shrink-0 rounded-full bg-white px-4 py-2 text-sm font-semibold text-brand"
            onClick={() => {
              if (token) adminLogout();
            }}
          >
            Chiqish
          </button>
        </div>
      </header>
      <div className="mx-auto w-full max-w-5xl min-w-0 px-4 py-4">
        <nav className="grid grid-cols-2 gap-2 lg:grid-cols-3" aria-label="Administrator bo‘limlari">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.end}
              className={({ isActive }) =>
                `min-w-0 rounded-2xl px-3 py-3 text-sm font-semibold break-words ${isActive ? "bg-brand text-white" : "bg-white text-ink"}`
              }
            >
              {link.label}
            </NavLink>
          ))}
        </nav>
        <main className="mt-4 min-w-0">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
