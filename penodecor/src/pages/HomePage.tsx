import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "../components/Button";
import { CategoryArt, FacadeArt } from "../components/CategoryArt";
import { EmptyState } from "../components/EmptyState";
import { Icon } from "../components/Icon";
import { Logo } from "../components/Logo";
import { SearchField } from "../components/SearchField";
import { categories } from "../data/categories";

const features = [
  { icon: "feather" as const, label: "Yengil va mustahkam" },
  { icon: "spark" as const, label: "Zamonaviy dizayn" },
  { icon: "clock" as const, label: "Tez ishlab chiqarish" },
  { icon: "ruler" as const, label: "O‘lchovli buyurtma" },
];

export function HomePage() {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");

  function openSearch() {
    const trimmed = query.trim();
    navigate(trimmed ? `/katalog?q=${encodeURIComponent(trimmed)}` : "/katalog");
  }

  return (
    <div className="pt-2 lg:pt-8">
      <div className="flex items-center justify-between lg:hidden">
        <Logo />
      </div>

      <div className="mt-3 lg:mt-0">
        <SearchField
          id="home-search"
          value={query}
          onChange={setQuery}
          onSubmit={openSearch}
          label="Katalogdan qidirish"
          placeholder="Katalogdan qidirish"
        />
      </div>

      <div className="mt-4 grid gap-4 lg:mt-8 lg:grid-cols-[1.4fr_0.8fr] lg:items-start">
        <section className="overflow-hidden rounded-3xl bg-brand text-white shadow-[var(--shadow-card)]">
          <div className="grid sm:min-h-[300px] sm:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)]">
            <div className="order-1 h-40 sm:order-2 sm:h-auto">
              <FacadeArt />
            </div>
            <div className="order-2 flex flex-col justify-end gap-3 p-5 sm:order-1 sm:p-7">
              <h1 className="text-[1.65rem] leading-tight font-semibold text-balance">Fasad uchun sifatli dekorativ bezaklar</h1>
              <p className="text-sm leading-6 text-white/80">Uyingizga nafislik va mustahkamlik qo‘shing.</p>
              <Button to="/katalog" variant="onDark" className="max-w-full self-start">
                Katalogni ko‘rish
              </Button>
            </div>
          </div>
        </section>

        <section className="grid grid-cols-2 gap-2 min-[380px]:grid-cols-4 lg:grid-cols-2">
          {features.map((feature) => (
            <div key={feature.label} className="flex min-h-24 flex-col items-center justify-center gap-2 rounded-2xl bg-mist px-2 py-3 text-center">
              <span className="grid h-10 w-10 place-items-center rounded-full bg-brand-soft text-brand">
                <Icon name={feature.icon} className="h-5 w-5" />
              </span>
              <span className="text-xs leading-4 font-medium text-ink">{feature.label}</span>
            </div>
          ))}
        </section>
      </div>

      <section className="mt-8">
        <div className="mb-3 flex items-end justify-between gap-3">
          <h2 className="text-lg font-semibold">Katalog</h2>
          <Button to="/katalog" variant="ghost" className="min-h-11 px-3">
            Hammasi
          </Button>
        </div>
        <ul className="grid grid-cols-2 gap-3 lg:grid-cols-3">
          {categories.slice(0, 4).map((category) => (
            <li key={category.slug}>
              <Link to={`/katalog/${category.slug}`} className="block overflow-hidden rounded-2xl border border-line bg-canvas">
                <div className="aspect-[4/3] overflow-hidden">
                  <CategoryArt slug={category.slug} />
                </div>
                <div className="p-3">
                  <p className="text-sm font-semibold leading-5">{category.title}</p>
                  <p className="mt-1 line-clamp-2 text-xs leading-5 text-muted">{category.summary}</p>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      </section>

      <section className="mt-8">
        <h2 className="mb-3 text-lg font-semibold">Mashhur mahsulotlar</h2>
        <EmptyState
          title="Mahsulotlar hali kiritilmagan"
          text="Narx va mahsulot kartochkalari administrator tomonidan qo‘shiladi. Hozircha katalog bo‘limlarini ko‘rishingiz mumkin."
          action={
            <Button to="/katalog" variant="secondary">
              Bo‘limlarni ochish
            </Button>
          }
        />
      </section>
    </div>
  );
}
