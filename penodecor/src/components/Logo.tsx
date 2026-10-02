import { Link } from "react-router-dom";
import { brand } from "../data/site";

export function Logo({ light = false }: { light?: boolean }) {
  return (
    <Link to="/" className="inline-flex min-h-12 items-center gap-2 rounded-xl pr-2">
      <span className={`grid h-10 w-10 place-items-center rounded-xl ${light ? "bg-white text-brand" : "bg-brand text-white"}`}>
        <svg viewBox="0 0 24 24" className="h-6 w-6" aria-hidden="true">
          <path fill="currentColor" d="M3 18V11l9-6 9 6v7H3zm4-2h4v-4H7v4zm6 0h4v-4h-4v4z" />
        </svg>
      </span>
      <span className="leading-tight">
        <span className={`block text-base font-semibold tracking-tight ${light ? "text-white" : "text-brand"}`}>{brand.name}</span>
        <span className={`block text-xs ${light ? "text-white/75" : "text-muted"}`}>{brand.tagline}</span>
      </span>
    </Link>
  );
}
