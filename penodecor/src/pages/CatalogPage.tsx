import { useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { CategoryArt } from "../components/CategoryArt";
import { EmptyState } from "../components/EmptyState";
import { Icon } from "../components/Icon";
import { PageHeader } from "../components/PageHeader";
import { SearchField } from "../components/SearchField";
import { filterCategories } from "../data/categories";

export function CatalogPage() {
  const [params, setParams] = useSearchParams();
  const initial = params.get("q") ?? "";
  const [query, setQuery] = useState(initial);
  const results = useMemo(() => filterCategories(query), [query]);

  function applySearch() {
    const trimmed = query.trim();
    if (trimmed) setParams({ q: trimmed });
    else setParams({});
  }

  return (
    <div className="lg:pt-8">
      <PageHeader title="Katalog" />
      <div className="mt-2">
        <SearchField
          id="catalog-search"
          value={query}
          onChange={setQuery}
          onSubmit={applySearch}
          label="Bo‘limlarni qidirish"
          placeholder="Bo‘lim yoki material"
        />
      </div>
      <p className="mt-3 text-sm text-muted">
        {results.length} ta bo‘lim. Mahsulot narxlari administrator kiritgach shu yerda ochiladi.
      </p>
      {results.length === 0 ? (
        <div className="mt-4">
          <EmptyState
            title="Bo‘lim topilmadi"
            text="Boshqa so‘z bilan qidiring yoki butun katalogni oching."
            action={
              <button
                type="button"
                className="inline-flex min-h-12 items-center rounded-full bg-mist px-5 text-sm font-semibold"
                onClick={() => {
                  setQuery("");
                  setParams({});
                }}
              >
                Tozalash
              </button>
            }
          />
        </div>
      ) : (
        <ul className="mt-4 grid gap-3 lg:grid-cols-2">
          {results.map((category) => (
            <li key={category.slug}>
              <Link
                to={`/katalog/${category.slug}`}
                className="flex min-h-[5.5rem] items-center gap-3 rounded-2xl border border-line bg-canvas p-2 pr-3"
              >
                <span className="h-20 w-20 shrink-0 overflow-hidden rounded-xl">
                  <CategoryArt slug={category.slug} />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block font-semibold leading-5">{category.title}</span>
                  <span className="mt-1 block text-sm leading-5 text-muted">{category.summary}</span>
                </span>
                <Icon name="chevron" className="h-5 w-5 shrink-0 text-muted" />
              </Link>
            </li>
          ))}
        </ul>
      )}
      <p className="mt-6 text-sm leading-6 text-muted">
        Rustovka mahsulotlari keyinroq administrator orqali qo‘shiladi. Hozircha alohida bo‘lim ochilmagan.
      </p>
    </div>
  );
}
