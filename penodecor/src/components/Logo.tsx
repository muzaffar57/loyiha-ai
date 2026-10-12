import { Link } from "react-router-dom";
import { brand } from "../data/site";

export function Logo() {
  return (
    <Link to="/" className="inline-flex items-center gap-2" aria-label={`${brand.name} — ${brand.tagline}`}>
      <img src="/logo-mark.png" alt="" className="w-auto" style={{ height: "2.45rem" }} />
      <span className="min-w-0 text-left leading-none">
        <span className="block text-[1.02rem] font-extrabold tracking-tight text-brand">
          PenoDecor<span className="text-accent">Pro</span>
        </span>
        <span className="mt-1 block text-[8px] font-semibold tracking-[0.13em] text-[#8b95a3] uppercase">Zamonaviy fasad dekorlari</span>
      </span>
    </Link>
  );
}
