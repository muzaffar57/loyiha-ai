import { NavLink } from "react-router-dom";
import { useCart } from "../lib/useCart";
import { Icon } from "./Icon";

const items = [
  { to: "/", label: "Bosh sahifa", icon: "home" as const, end: true },
  { to: "/katalog", label: "Katalog", icon: "catalog" as const, end: false },
  { to: "/savat", label: "Savat", icon: "cart" as const, end: false },
  { to: "/buyurtmalar", label: "Buyurtmalar", icon: "orders" as const, end: false },
  { to: "/profil", label: "Profil", icon: "profile" as const, end: false },
];

export function BottomNav() {
  const { count } = useCart();

  return (
    <nav
      aria-label="Asosiy"
      className="fixed inset-x-0 bottom-0 z-30 border-t border-line bg-canvas lg:hidden"
      style={{ paddingBottom: "var(--safe-bottom)" }}
    >
      <ul className="mx-auto flex max-w-lg">
        {items.map((item) => (
          <li key={item.to} className="flex-1">
            <NavLink
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `relative flex min-h-[var(--nav-height)] flex-col items-center justify-center gap-0.5 px-1 text-[11px] font-semibold ${
                  isActive ? "text-brand" : "text-muted"
                }`
              }
            >
              <Icon name={item.icon} className="h-6 w-6" />
              <span className="max-w-full truncate">{item.label}</span>
              {item.to === "/savat" && count > 0 ? (
                <span className="absolute top-1.5 right-[calc(50%-1.4rem)] grid min-w-5 place-items-center rounded-full bg-brand px-1 text-[10px] leading-5 text-white">
                  {count > 99 ? "99+" : count}
                </span>
              ) : null}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}

export function DesktopNav() {
  const { count } = useCart();
  return (
    <header className="sticky top-0 z-30 hidden border-b border-line bg-canvas/95 backdrop-blur lg:block">
      <div className="mx-auto flex h-16 max-w-6xl items-center gap-6 px-8">
        <span className="text-lg font-semibold text-brand">PenodecorPro</span>
        <nav aria-label="Asosiy" className="flex flex-1 items-center gap-1">
          {items.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `inline-flex min-h-11 items-center rounded-full px-3 text-sm font-semibold ${
                  isActive ? "bg-brand-soft text-brand" : "text-muted hover:text-ink"
                }`
              }
            >
              {item.label}
              {item.to === "/savat" && count > 0 ? ` (${count})` : ""}
            </NavLink>
          ))}
        </nav>
      </div>
    </header>
  );
}
