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
  | "ruler"
  | "menu"
  | "filter"
  | "diamond"
  | "truck"
  | "window"
  | "column"
  | "cornice"
  | "layers";

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
  menu: "M4 7h16M4 12h16M4 17h16",
  filter: "M4 7h16M4 12h16M4 17h16M8 5.2v3.6M15 10.2v3.6M11 15.2v3.6",
  diamond: "M12 3.2 20 12 12 20.8 4 12 12 3.2z",
  truck: "M3 7.5h10.5V16H3V7.5zM13.5 10h3.2L20 13.2V16h-6.5V10zM6.2 18.6a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3zm8.6 0a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3z",
  window: "M8 20V11a4 4 0 0 1 8 0v9M12 11.2V20M8 20h8",
  column: "M9 5.2h6M8.2 7.4h7.6M10 7.4v9.2M14 7.4v9.2M8 18.8h8",
  cornice: "M5.5 7h13M5.5 10.4c2.4 0 3 2.3 5.4 2.3h7.6M5.5 15h13M5.5 18h13",
  layers: "M6.5 6.2h11v3.1h-11zM6.5 10.45h11v3.1h-11zM6.5 14.7h11v3.1h-11z",
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
