import type { ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { Icon } from "./Icon";

export function PageHeader({
  title,
  back = false,
  action,
}: {
  title: string;
  back?: boolean;
  action?: ReactNode;
}) {
  const navigate = useNavigate();
  return (
    <header className="sticky top-0 z-20 flex items-center gap-2 bg-canvas/95 px-2 py-1 backdrop-blur lg:static lg:bg-transparent lg:px-0">
      {back ? (
        <button
          type="button"
          onClick={() => navigate(-1)}
          className="grid h-12 w-12 place-items-center rounded-full text-ink"
          aria-label="Orqaga"
        >
          <Icon name="back" />
        </button>
      ) : (
        <span className="w-2" />
      )}
      <h1 className="min-w-0 flex-1 truncate text-lg font-semibold">{title}</h1>
      {action}
    </header>
  );
}
