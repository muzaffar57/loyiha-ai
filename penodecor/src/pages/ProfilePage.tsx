import { Link } from "react-router-dom";
import { Icon } from "../components/Icon";
import { PageHeader } from "../components/PageHeader";
import { companyPhone } from "../data/site";

const links = [
  { to: "/buyurtmalar", label: "Mening buyurtmalarim", hint: "Holat va raqam" },
  { to: "/savat", label: "Savat", hint: "Tanlangan mahsulotlar" },
  { to: "/kompaniya", label: "Biz haqimizda", hint: "Kompaniya" },
  { to: "/yetkazish", label: "Yetkazish va to‘lov", hint: "Qanday olib ketiladi" },
  { to: "/savol-javob", label: "Ko‘p so‘raladigan savollar", hint: "Yordam" },
  { to: "/maxfiylik", label: "Maxfiylik siyosati", hint: "Ma’lumotlar" },
  { to: "/shartlar", label: "Foydalanish shartlari", hint: "Qoidalar" },
];

export function ProfilePage() {
  return (
    <div className="lg:pt-8">
      <PageHeader title="Profil" />
      <section className="mt-2 flex items-center gap-3 rounded-3xl bg-mist p-4">
        <span className="grid h-14 w-14 place-items-center rounded-full bg-brand text-white">
          <Icon name="profile" className="h-7 w-7" />
        </span>
        <div>
          <p className="text-lg font-semibold">Mehmon</p>
          <p className="text-sm leading-5 text-muted">Buyurtma uchun ro‘yxatdan o‘tish shart emas. Hisob ixtiyoriy.</p>
        </div>
      </section>

      <section className="mt-4 rounded-3xl border border-line p-4">
        <h2 className="text-sm font-semibold text-muted">Aloqa</h2>
        {companyPhone ? (
          <a href={`tel:${companyPhone}`} className="mt-2 inline-flex min-h-12 items-center text-base font-semibold text-brand">
            {companyPhone}
          </a>
        ) : (
          <p className="mt-2 text-sm leading-6">
            Qo‘ng‘iroq raqami hali kiritilmagan. U administrator sozlamasidan olinadi, saytga qo‘lda yozilmaydi.
          </p>
        )}
      </section>

      <ul className="mt-4 overflow-hidden rounded-3xl border border-line">
        {links.map((item) => (
          <li key={item.to} className="border-b border-line last:border-b-0">
            <Link to={item.to} className="flex min-h-14 items-center justify-between gap-3 px-4 py-3">
              <span>
                <span className="block font-semibold">{item.label}</span>
                <span className="block text-sm text-muted">{item.hint}</span>
              </span>
              <Icon name="chevron" className="h-5 w-5 text-muted" />
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
