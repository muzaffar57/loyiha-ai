import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { CategoryArt } from "../components/CategoryArt";
import { EmptyState } from "../components/EmptyState";
import { PageHeader } from "../components/PageHeader";
import { SearchField } from "../components/SearchField";
import { findCategory } from "../data/categories";

export function CategoryPage() {
  const { slug } = useParams();
  const category = findCategory(slug);
  const [query, setQuery] = useState("");
  const [groupId, setGroupId] = useState(category?.groups[0]?.id ?? "barchasi");

  const groups = useMemo(() => {
    if (!category) return [];
    const needle = query.trim().toLocaleLowerCase("uz");
    if (!needle) return category.groups;
    return category.groups.filter((group) => group.label.toLocaleLowerCase("uz").includes(needle) || group.description.toLocaleLowerCase("uz").includes(needle));
  }, [category, query]);

  const active = groups.find((group) => group.id === groupId) ?? groups[0];

  if (!category) {
    return (
      <div className="lg:pt-8">
        <PageHeader title="Katalog" back />
        <div className="mt-4">
          <EmptyState title="Bo‘lim topilmadi" text="Bu manzilda katalog bo‘limi yo‘q." action={<Link to="/katalog" className="inline-flex min-h-12 items-center font-semibold text-brand">Katalogga qaytish</Link>} />
        </div>
      </div>
    );
  }

  return (
    <div className="lg:pt-8">
      <PageHeader title={category.title} back />
      <div className="mt-2 overflow-hidden rounded-3xl border border-line">
        <div className="h-36">
          <CategoryArt slug={category.slug} />
        </div>
      </div>
      <p className="mt-4 text-sm leading-6 text-muted">{category.summary}</p>
      <p className="mt-2 text-sm leading-6 text-ink">{category.note}</p>

      <div className="mt-4">
        <SearchField
          id="group-search"
          value={query}
          onChange={setQuery}
          label="Guruhlarni qidirish"
          placeholder="Qidirish"
        />
      </div>

      <div className="mt-3 flex max-w-full gap-2 overflow-x-auto pb-1" role="tablist" aria-label="Guruhlar">
        {groups.map((group) => {
          const selected = active?.id === group.id;
          return (
            <button
              key={group.id}
              type="button"
              role="tab"
              aria-selected={selected}
              onClick={() => setGroupId(group.id)}
              className={`min-h-11 shrink-0 rounded-full px-4 text-sm font-semibold ${
                selected ? "bg-brand text-white" : "bg-mist text-ink"
              }`}
            >
              {group.label}
            </button>
          );
        })}
      </div>

      {groups.length === 0 || !active ? (
        <div className="mt-4">
          <EmptyState title="Guruh topilmadi" text="Qidiruvni tozalab, barcha guruhlarni qayta ko‘ring." />
        </div>
      ) : (
        <div className="mt-4">
          <EmptyState
            title="0 ta mahsulot"
            text={`${active.label}: ${active.description} Kartochkalar va narxlar administrator kiritgach shu yerda chiqadi.`}
          />
        </div>
      )}
    </div>
  );
}
