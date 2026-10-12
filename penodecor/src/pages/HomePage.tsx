import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { CategoryArt } from "../components/CategoryArt";
import { EmptyState } from "../components/EmptyState";
import { Icon } from "../components/Icon";
import { Logo } from "../components/Logo";
import { SearchField } from "../components/SearchField";
import { categoryCover, sortHomeCategories } from "../data/categoryCovers";
import { listCategories, mediaUrl } from "../lib/storeApi";
import type { StoreCategory } from "../types/store";
import { useCart } from "../lib/useCart";
import { useStoreResource, type StoreLoad } from "../lib/useStoreResource";

const homeLabels: Record<string, { icon: "window" | "column" | "cornice" | "layers"; lines: [string, string] }> = {
  "rom-va-eshik": { icon: "window", lines: ["Rom va eshik", "bezaklari"] },
  pilastrlar: { icon: "column", lines: ["Pilastrlar", "va ustunlar"] },
  "shift-karnizlari": { icon: "cornice", lines: ["Shift karnizlari", "va belbog‘lar"] },
  "yumaloq-ustunlar": { icon: "column", lines: ["Yumaloq", "ustunlar"] },
  "shohona-karnizlar": { icon: "cornice", lines: ["Shohona", "karnizlar"] },
  "tayyor-mahsulotlar": { icon: "layers", lines: ["Tayyor", "mahsulotlar"] },
};

function homeLabel(slug: string, name: string) {
  const known = homeLabels[slug];
  if (known) return known;
  const words = name.trim().split(/\s+/);
  const mid = Math.max(1, Math.ceil(words.length / 2));
  return { icon: "layers" as const, lines: [words.slice(0, mid).join(" "), words.slice(mid).join(" ")] as [string, string] };
}

const features = [
  { icon: "diamond" as const, label: "Yengil va mustahkam" },
  { icon: "spark" as const, label: "Zamonaviy dizayn" },
  { icon: "clock" as const, label: "Tez ishlab chiqarish" },
  { icon: "truck" as const, label: "O‘lchovli buyurtma" },
];

const menuLinks = [
  { to: "/", label: "Bosh sahifa" },
  { to: "/katalog", label: "Katalog" },
  { to: "/savat", label: "Savat" },
  { to: "/buyurtmalar", label: "Buyurtmalar" },
  { to: "/profil", label: "Profil" },
  { to: "/kompaniya", label: "Biz haqimizda" },
];

function FillImage({ src, position = "center" }: { src: string; position?: string }) {
  return (
    <img
      src={src}
      alt=""
      className="absolute inset-0 w-full object-cover"
      style={{ height: "100%", maxWidth: "none", objectPosition: position }}
    />
  );
}

function HomeCatalog({ state, onRetry }: { state: StoreLoad<{ items: StoreCategory[] }>; onRetry: () => void }) {
  const items = state.status === "ready" ? sortHomeCategories(state.data.items) : [];

  return (
    <section className="mt-6">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h2 className="text-lg font-bold text-ink">Katalog bo‘limlari</h2>
        <Link to="/katalog" className="inline-flex min-h-11 items-center gap-1 text-sm font-semibold text-accent">
          Hammasi <span aria-hidden="true">→</span>
        </Link>
      </div>
      {state.status === "loading" ? <div className="h-40 animate-pulse rounded-3xl bg-white" aria-busy="true" /> : null}
      {state.status === "error" ? (
        <EmptyState
          title="Katalog yuklanmadi"
          text={state.message}
          action={
            <button type="button" className="inline-flex min-h-12 items-center rounded-full bg-brand px-5 text-sm font-semibold text-white" onClick={onRetry}>
              Qayta urinish
            </button>
          }
        />
      ) : null}
      {state.status === "ready" ? (
        <ul className="grid grid-cols-2 gap-3 lg:grid-cols-3">
          {items.map((category) => {
            const src = categoryCover(category.slug, mediaUrl(category.image));
            const label = homeLabel(category.slug, category.name);
            return (
              <li key={category.slug}>
                <Link to={`/katalog/${category.slug}`} className="block overflow-hidden rounded-2xl bg-white shadow-[var(--shadow-card)]">
                  <div className="relative aspect-[2/3] bg-white">
                    {src ? (
                      <img src={src} alt="" className="absolute inset-0 w-full object-cover" style={{ height: "100%", maxWidth: "none" }} />
                    ) : (
                      <CategoryArt slug={category.slug} />
                    )}
                    <div className="absolute inset-x-1.5 bottom-1.5 flex items-center overflow-hidden rounded-2xl bg-white shadow-[0_6px_16px_rgba(23,34,53,0.14)] lg:inset-x-3 lg:bottom-3">
                      <span className="relative grid h-10 w-8 shrink-0 place-items-center bg-brand text-white lg:h-14 lg:w-14">
                        <span className="absolute top-0 right-0 h-full w-2 bg-accent lg:w-3" style={{ clipPath: "polygon(100% 0, 100% 100%, 0 100%)" }} />
                        <Icon name={label.icon} className="relative h-4 w-4 lg:h-6 lg:w-6" />
                      </span>
                      <span className="min-w-0 flex-1 px-1 text-[9px] leading-[1.15] font-bold tracking-tight text-brand uppercase lg:px-3 lg:text-sm lg:leading-5">
                        <span className="block whitespace-nowrap">{label.lines[0]}</span>
                        {label.lines[1] ? <span className="block whitespace-nowrap">{label.lines[1]}</span> : null}
                      </span>
                      <span className="mr-1 grid h-6 w-6 shrink-0 place-items-center rounded-full bg-accent text-white lg:mr-2 lg:h-9 lg:w-9">
                        <Icon name="chevron" className="h-3.5 w-3.5 lg:h-5 lg:w-5" />
                      </span>
                    </div>
                  </div>
                </Link>
              </li>
            );
          })}
        </ul>
      ) : null}
    </section>
  );
}

export function HomePage() {
  const navigate = useNavigate();
  const { count } = useCart();
  const [query, setQuery] = useState("");
  const [panel, setPanel] = useState<"menu" | "filter" | null>(null);
  const [attempt, setAttempt] = useState(0);
  const categories = useStoreResource(`home-categories:${attempt}`, () => listCategories());

  useEffect(() => {
    if (!panel) return;
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") setPanel(null);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [panel]);

  function openSearch() {
    const trimmed = query.trim();
    navigate(trimmed ? `/katalog?q=${encodeURIComponent(trimmed)}` : "/katalog");
  }

  return (
    <div className="-mx-4 lg:mx-0" style={{ marginTop: "calc(var(--safe-top) * -1)" }}>
      <header className="sticky top-0 z-20 bg-white lg:hidden" style={{ paddingTop: "var(--safe-top)" }}>
        <div className="relative flex h-14 items-center justify-between px-2">
          <button type="button" className="grid h-11 w-11 place-items-center text-brand" aria-label="Menyu" onClick={() => setPanel("menu")}>
            <Icon name="menu" className="h-6 w-6" />
          </button>
          <div className="pointer-events-none absolute inset-x-14 inset-y-0 flex items-center justify-center">
            <div className="pointer-events-auto">
              <Logo />
            </div>
          </div>
          <Link to="/savat" aria-label={count > 0 ? `Savat, ${count} ta` : "Savat"} className="relative grid h-11 w-11 place-items-center text-brand">
            <Icon name="cart" className="h-6 w-6" />
            {count > 0 ? (
              <span className="absolute top-1 right-0.5 grid min-w-5 place-items-center rounded-full bg-accent px-1 text-[10px] leading-5 font-bold text-white">
                {count > 99 ? "99+" : count}
              </span>
            ) : null}
          </Link>
        </div>
      </header>

      <div className="px-4 pt-3 pb-2 lg:px-0 lg:pt-8">
        <SearchField
          id="home-search"
          value={query}
          onChange={setQuery}
          onSubmit={openSearch}
          onFilter={() => setPanel("filter")}
          label="Katalogdan qidirish"
          placeholder="Katalogdan qidirish..."
        />

        <section className="relative mt-3 h-[19.5rem] overflow-hidden rounded-[1.6rem] shadow-[var(--shadow-card)]">
          <FillImage src="/home/hero.jpg" position="72% center" />
          <div className="absolute inset-0 bg-gradient-to-r from-[#193458] via-[#193458]/88 to-[#193458]/10" />
          <div className="relative flex h-full flex-col justify-end p-5 pb-8 text-white">
            <p className="text-[11px] font-bold tracking-[0.16em] text-accent uppercase">Zamonaviy fasadlar</p>
            <h1 className="mt-2 max-w-[16rem] text-[1.7rem] leading-[1.12] font-extrabold text-balance">
              Fasad uchun sifatli dekorativ <span className="text-accent">bezaklar</span>
            </h1>
            <p className="mt-2 max-w-[16rem] text-sm leading-5 text-white/85">Uyingizga nafislik va mustahkamlik qo‘shing.</p>
            <Link to="/katalog" className="mt-4 inline-flex min-h-11 w-fit items-center gap-2 rounded-full bg-accent px-5 text-sm font-semibold text-white hover:bg-[#d46522]">
              Katalogni ko‘rish <span aria-hidden="true">→</span>
            </Link>
          </div>
          <div className="absolute bottom-3 left-0 flex w-full justify-center gap-1.5" aria-hidden="true">
            <span className="h-1.5 w-1.5 rounded-full bg-white" />
            <span className="h-1.5 w-1.5 rounded-full bg-white/45" />
            <span className="h-1.5 w-1.5 rounded-full bg-white/45" />
          </div>
        </section>

        <ul className="mt-4 grid grid-cols-4 gap-2">
          {features.map((feature) => (
            <li key={feature.label} className="flex min-h-[6.5rem] flex-col items-center justify-start rounded-2xl bg-white px-1 py-3 text-center shadow-[var(--shadow-card)]">
              <span className="grid h-10 w-10 place-items-center rounded-full bg-[#f3f5f8] text-accent">
                <Icon name={feature.icon} className="h-5 w-5" />
              </span>
              <span className="mt-2 text-[10px] leading-3 font-medium text-ink">{feature.label}</span>
            </li>
          ))}
        </ul>

        <HomeCatalog state={categories} onRetry={() => setAttempt((value) => value + 1)} />

        <section className="relative mt-4 h-36 overflow-hidden rounded-[1.6rem] shadow-[var(--shadow-card)]">
          <FillImage src="/home/promo.jpg" position="right center" />
          <div className="absolute inset-0 bg-gradient-to-r from-[#193458] via-[#193458]/82 to-[#193458]/15" />
          <div className="relative flex h-full max-w-[16rem] flex-col justify-center px-5 text-white">
            <p className="text-base leading-5 font-bold">Individual loyihalar uchun maxsus yechimlar</p>
            <Link to="/kompaniya" className="mt-3 inline-flex min-h-10 w-fit items-center gap-2 rounded-full bg-accent px-4 text-sm font-semibold text-white hover:bg-[#d46522]">
              Batafsil <span aria-hidden="true">→</span>
            </Link>
          </div>
        </section>
      </div>

      {panel ? (
        <div className="fixed inset-0 z-40">
          <button type="button" className="absolute inset-0 bg-[#172235]/45" aria-label="Yopish" onClick={() => setPanel(null)} />
          <div
            role="dialog"
            aria-modal="true"
            aria-label={panel === "menu" ? "Menyu" : "Bo‘limlar"}
            className={
              panel === "menu"
                ? "absolute top-0 bottom-0 left-0 flex w-[min(18rem,86vw)] flex-col bg-white p-4 shadow-xl"
                : "absolute inset-x-0 bottom-0 max-h-[78vh] overflow-auto rounded-t-3xl bg-white p-4 shadow-xl"
            }
            style={
              panel === "menu"
                ? { paddingTop: "calc(var(--safe-top) + 1rem)", paddingBottom: "calc(var(--safe-bottom) + 1rem)" }
                : { paddingBottom: "calc(var(--safe-bottom) + 2rem)" }
            }
          >
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-lg font-bold">{panel === "menu" ? "Menyu" : "Bo‘limlar"}</h2>
              <button type="button" className="grid h-11 w-11 place-items-center rounded-full text-ink" aria-label="Yopish" onClick={() => setPanel(null)}>
                <Icon name="close" />
              </button>
            </div>
            {panel === "menu" ? (
              <ul>
                {menuLinks.map((item) => (
                  <li key={item.to} className="border-b border-line last:border-b-0">
                    <Link to={item.to} onClick={() => setPanel(null)} className="flex min-h-12 items-center text-base font-semibold">
                      {item.label}
                    </Link>
                  </li>
                ))}
              </ul>
            ) : null}
            {panel === "filter" && categories.status === "loading" ? <p className="text-sm text-muted">Yuklanmoqda...</p> : null}
            {panel === "filter" && categories.status === "error" ? <p className="text-sm text-muted">{categories.message}</p> : null}
            {panel === "filter" && categories.status === "ready" ? (
              <ul>
                {sortHomeCategories(categories.data.items).map((category) => (
                  <li key={category.slug} className="border-b border-line last:border-b-0">
                    <Link to={`/katalog/${category.slug}`} onClick={() => setPanel(null)} className="flex min-h-12 items-center justify-between gap-3 text-base font-semibold">
                      {category.name}
                      <Icon name="chevron" className="h-5 w-5 text-muted" />
                    </Link>
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
        </div>
      ) : null}
    </div>
  );
}
