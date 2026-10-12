import { Link } from "react-router-dom";
import { brand } from "../data/site";

export function Logo() {
  return (
    <Link to="/" className="inline-flex min-h-12 items-center rounded-xl">
      <img src="/logo.jpg" alt={`${brand.name} — ${brand.tagline}`} className="h-14 w-auto" />
    </Link>
  );
}
