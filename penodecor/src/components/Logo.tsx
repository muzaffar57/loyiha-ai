import { Link } from "react-router-dom";
import { brand } from "../data/site";

export function Logo() {
  return (
    <Link to="/" className="inline-flex min-h-12 items-center rounded-xl">
      <img
        src="/logo.jpg"
        alt={`${brand.name} — ${brand.tagline}`}
        className="w-auto max-w-[11rem] rounded-xl bg-white object-contain object-left"
        style={{ height: "3.5rem" }}
      />
    </Link>
  );
}
