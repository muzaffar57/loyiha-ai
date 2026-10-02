export function CategoryArt({ slug }: { slug: string }) {
  if (slug === "pilastrlar") {
    return (
      <svg viewBox="0 0 80 80" className="h-full w-full" aria-hidden="true">
        <rect width="80" height="80" fill="#F5F6F4" />
        <path d="M28 18h24l-3 6H31l-3-6z" fill="#173D32" />
        <rect x="33" y="24" width="14" height="34" fill="#173D32" />
        <path d="M26 58h28l-2 6H28l-2-6z" fill="#173D32" />
      </svg>
    );
  }
  if (slug === "yumaloq-ustunlar") {
    return (
      <svg viewBox="0 0 80 80" className="h-full w-full" aria-hidden="true">
        <rect width="80" height="80" fill="#F5F6F4" />
        <ellipse cx="40" cy="18" rx="14" ry="5" fill="#173D32" />
        <path d="M26 18h28v44H26z" fill="#2C5C4C" />
        <ellipse cx="40" cy="62" rx="14" ry="5" fill="#173D32" />
        <path d="M40 18v44" stroke="#F5F6F4" strokeWidth="1" opacity="0.4" />
      </svg>
    );
  }
  if (slug === "shift-karnizlari") {
    return (
      <svg viewBox="0 0 80 80" className="h-full w-full" aria-hidden="true">
        <rect width="80" height="80" fill="#F5F6F4" />
        <path d="M10 28h60v6H10z" fill="#173D32" />
        <path d="M14 34h52c0 8-6 10-10 10H24c-4 0-10-2-10-10z" fill="#2C5C4C" />
        <path d="M18 44c4 6 8 8 22 8s18-2 22-8" fill="none" stroke="#173D32" strokeWidth="2" />
      </svg>
    );
  }
  if (slug === "shohona-karnizlar") {
    return (
      <svg viewBox="0 0 80 80" className="h-full w-full" aria-hidden="true">
        <rect width="80" height="80" fill="#F5F6F4" />
        <path d="M8 24h64v8H8z" fill="#173D32" />
        <path d="M12 32c4 14 10 18 28 18s24-4 28-18H12z" fill="#2C5C4C" />
        <circle cx="22" cy="40" r="2" fill="#F5F6F4" />
        <circle cx="40" cy="42" r="2" fill="#F5F6F4" />
        <circle cx="58" cy="40" r="2" fill="#F5F6F4" />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 80 80" className="h-full w-full" aria-hidden="true">
      <rect width="80" height="80" fill="#F5F6F4" />
      <path d="M18 28h44l-4 8H22l-4-8z" fill="#173D32" />
      <rect x="24" y="36" width="32" height="26" fill="none" stroke="#173D32" strokeWidth="3" />
      <path d="M34 36v26M46 36v26M24 48h32" stroke="#173D32" strokeWidth="2" />
    </svg>
  );
}

export function FacadeArt() {
  return (
    <svg viewBox="0 0 280 320" className="h-full w-full" aria-hidden="true">
      <rect width="280" height="320" fill="#1d4a3d" />
      <path d="M70 86h140l-8 18H78L70 86z" fill="#f4f1ea" />
      <rect x="86" y="104" width="108" height="150" fill="#f7f5f0" />
      <rect x="104" y="124" width="28" height="46" fill="#173D32" />
      <rect x="148" y="124" width="28" height="46" fill="#173D32" />
      <path d="M100 124h36l-4 8h-28l-4-8zm44 0h36l-4 8h-28l-4-8z" fill="#f4f1ea" />
      <rect x="126" y="186" width="28" height="68" fill="#173D32" />
      <path d="M64 254h152v10H64z" fill="#f4f1ea" />
      <rect x="58" y="264" width="18" height="40" fill="#efeae2" />
      <rect x="204" y="264" width="18" height="40" fill="#efeae2" />
      <path d="M52 258h30l-3 8H55l-3-8zm146 0h30l-3 8h-24l-3-8z" fill="#f7f5f0" />
    </svg>
  );
}
