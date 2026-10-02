import { Link } from "react-router-dom";
import { Button } from "../components/Button";
import { EmptyState } from "../components/EmptyState";
import { PageHeader } from "../components/PageHeader";
import { useCart } from "../lib/useCart";

export function CartPage() {
  const { lines, count, removeLine } = useCart();

  return (
    <div className="lg:pt-8">
      <PageHeader title={count > 0 ? `Savat (${count})` : "Savat"} />
      {lines.length === 0 ? (
        <div className="mt-4">
          <EmptyState
            title="Savat bo‘sh"
            text="Mahsulot qo‘shilganda tanlov shu qurilmada saqlanadi va sahifa yangilansa ham yo‘qolmaydi. Hozircha katalogda narxli mahsulot yo‘q."
            action={<Button to="/katalog">Katalogni ochish</Button>}
          />
        </div>
      ) : (
        <ul className="mt-4 grid gap-3">
          {lines.map((line) => (
            <li key={line.id} className="rounded-2xl border border-line p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="font-semibold">{line.title}</p>
                  {line.detail ? <p className="mt-1 text-sm text-muted">{line.detail}</p> : null}
                  <p className="mt-2 text-sm">Soni: {line.quantity}</p>
                  <p className="mt-1 text-sm text-muted">
                    {line.unitPriceLabel ? `Saqlangan narx: ${line.unitPriceLabel}` : "Narx buyurtma tasdig‘ida belgilanadi."}
                  </p>
                </div>
                <button type="button" onClick={() => removeLine(line.id)} className="min-h-11 shrink-0 text-sm font-semibold text-danger">
                  Olib tashlash
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
      <p className="mt-6 text-sm leading-6 text-muted">
        Buyurtmani yuborish keyingi bosqichda ochiladi. Yuborilgan buyurtma avtomatik tasdiqlanmaydi.
        {lines.length > 0 ? (
          <>
            {" "}
            <Link to="/katalog" className="font-semibold text-brand">
              Katalogga qaytish
            </Link>
          </>
        ) : null}
      </p>
    </div>
  );
}
