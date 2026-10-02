import { Button } from "../components/Button";
import { EmptyState } from "../components/EmptyState";
import { PageHeader } from "../components/PageHeader";

export function OrdersPage() {
  return (
    <div className="lg:pt-8">
      <PageHeader title="Buyurtmalarim" />
      <div className="mt-4">
        <EmptyState
          title="Buyurtmalar yo‘q"
          text="Buyurtma yuborilganda unga alohida raqam beriladi va holati “Tasdiqlash kutilmoqda” bo‘ladi. Administrator qo‘ng‘iroqdan keyin tasdiqlaydi. Hozircha buyurtma yuborish ulanmagan."
          action={<Button to="/katalog" variant="secondary">Katalogni ko‘rish</Button>}
        />
      </div>
    </div>
  );
}
