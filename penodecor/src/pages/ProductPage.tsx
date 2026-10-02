import { Link, useParams } from "react-router-dom";
import { EmptyState } from "../components/EmptyState";
import { PageHeader } from "../components/PageHeader";

export function ProductPage() {
  const { id } = useParams();
  return (
    <div className="lg:pt-8">
      <PageHeader title="Mahsulot" back />
      <div className="mt-4">
        <EmptyState
          title="Mahsulot topilmadi"
          text={`“${id ?? ""}” raqami bo‘yicha mahsulot yo‘q. Narxlar va o‘lchamlar administrator kiritgan mahsulotdan olinadi, qo‘lda yozilmaydi.`}
          action={
            <Link to="/katalog" className="inline-flex min-h-12 items-center font-semibold text-brand">
              Katalogga qaytish
            </Link>
          }
        />
      </div>
    </div>
  );
}
