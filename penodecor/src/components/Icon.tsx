type IconName =
  | "home"
  | "catalog"
  | "cart"
  | "orders"
  | "profile"
  | "search"
  | "chevron"
  | "back"
  | "close"
  | "feather"
  | "spark"
  | "clock"
  | "ruler";

const paths: Record<IconName, string> = {
  home: "M4 11.5 12 5l8 6.5V20a1 1 0 0 1-1 1h-5v-5H10v5H5a1 1 0 0 1-1-1v-8.5z",
  catalog: "M4 4h7v7H4V4zm9 0h7v7h-7V4zM4 13h7v7H4v-7zm9 0h7v7h-7v-7z",
  cart: "M6 7h15l-1.4 8.2a1 1 0 0 1-1 .8H9.2a1 1 0 0 1-1-.8L6.2 4H3M9 20.5a1.2 1.2 0 1 0 0-2.4 1.2 1.2 0 0 0 0 2.4zm8 0a1.2 1.2 0 1 0 0-2.4 1.2 1.2 0 0 0 0 2.4z",
  orders: "M7 3.5h10a1 1 0 0 1 1 1V20l-2.2-1.4L13.5 20l-2.3-1.4L9 20l-2.2-1.4L4.5 20V4.5a1 1 0 0 1 1-1H7zm1.5 5h7M8.5 12h7M8.5 15.5h4",
  profile: "M12 12a3.4 3.4 0 1 0 0-6.8A3.4 3.4 0 0 0 12 12zm-6.2 7.2a6.2 6.2 0 0 1 12.4 0",
  search: "M11 18a7 7 0 1 1 0-14 7 7 0 0 1 0 14zm5.2-1.8 3.6 3.6",
  chevron: "M9 6l6 6-6 6",
  back: "M15 6l-6 6 6 6",
  close: "M7 7l10 10M17 7 7 17",
  feather: "M5 19c6 0 12-6 14-14-6 1-12 6-14 14zm2.5-2.5c2-2 5-4 8.5-5",
  spark: "M12 3l1.4 5.2L18 9.6l-4.6 1.4L12 16l-1.4-5L6 9.6l4.6-1.4L12 3zM18 15l.6 2 2 .6-2 .6-.6 2-.6-2-2-.6 2-.6.6-2z",
  clock: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zm0-13v5l3 2",
  ruler: "M4 16.5 16.5 4l3.5 3.5L7.5 20 4 16.5zm4.2-1.2 1.6-1.6m1.3 1.3 1.6-1.6m1.3 1.3 1.6-1.6",
};

export function Icon({ name, className = "h-6 w-6" }: { name: IconName; className?: string }) {
  const fillIcons = name === "home" || name === "catalog";
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true">
      <path
        d={paths[name]}
        fill={fillIcons ? "currentColor" : "none"}
        stroke="currentColor"
        strokeWidth={fillIcons ? 0 : 1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
