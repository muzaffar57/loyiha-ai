import { Link } from "react-router-dom";
import { companyPhone } from "../data/site";
import { InfoPage } from "./InfoPage";

export function AboutPage() {
  return (
    <InfoPage title="Biz haqimizda">
      <p>
        PenodecorPro fasad uchun dekorativ bezaklar ishlab chiqaradi. Asosiy material — EPS ko‘pik va unga mos
        qoplamalar. Rom, eshik bezagi, pilastr, yumaloq ustun, shift karnizi va shohona karniz shu katalogda.
      </p>
      <p>
        Sayt avval telefon uchun qilingan. Keyinchalik shu backend orqali Android va iOS ilovalar ham ishlaydi.
        Narx, o‘lcham va buyurtma hisobi serverda saqlanadi.
      </p>
    </InfoPage>
  );
}

export function DeliveryPage() {
  return (
    <InfoPage title="Yetkazish va to‘lov">
      <p>Yetkazib berish yoki ustaxonadan olib ketish buyurtma tasdiqlangach kelishiladi. Manzil mijoz ma’lumotidan olinadi.</p>
      <p>
        To‘lov holati buyurtma holatidan alohida. Oldindan to‘lov yoki yetkazilganda to‘lash mumkin. Onlayn to‘lov
        provayderi ulanmaguncha sayt to‘lov o‘tgan deb yozmaydi.
      </p>
      <p>
        {companyPhone
          ? `Savollar uchun: ${companyPhone}.`
          : "Telefon raqami administrator sozlamasida paydo bo‘ladi. Hozircha qo‘ng‘iroq tugmasi yo‘q."}
      </p>
    </InfoPage>
  );
}

export function FaqPage() {
  const items = [
    {
      q: "Ro‘yxatdan o‘tmasdan buyurtma bersa bo‘ladimi?",
      a: "Ha. Hisob ixtiyoriy. Buyurtma yuborish keyingi bosqichda ochiladi.",
    },
    {
      q: "Narxlar qayerda?",
      a: "Haqiqiy narxni administrator kiritadi. Sayt o‘zi narx o‘ylab topmaydi va hisobni brauzerda qilmaydi.",
    },
    {
      q: "Buyurtma yuborilishi tasdiq hisoblanadimi?",
      a: "Yo‘q. Yangi buyurtma “Tasdiqlash kutilmoqda” holatida turadi. Administrator mijoz bilan gaplashib tasdiqlaydi.",
    },
    {
      q: "Shohona karniz qanday buyurtma qilinadi?",
      a: "Avval namuna tanlanadi, so‘ng narx so‘rovi ketadi. Administrator narx qo‘yadi, mijoz shu narxni tasdiqlaydi.",
    },
  ];
  return (
    <InfoPage title="Savol-javob">
      {items.map((item) => (
        <section key={item.q}>
          <h2 className="text-base font-semibold">{item.q}</h2>
          <p className="mt-1 text-muted">{item.a}</p>
        </section>
      ))}
      <p>
        Boshqa savol bo‘lsa, <Link to="/profil" className="font-semibold text-brand">profil</Link>dagi aloqa bo‘limiga qarang.
      </p>
    </InfoPage>
  );
}

export function PrivacyPage() {
  return (
    <InfoPage title="Maxfiylik siyosati">
      <p>
        Buyurtma uchun ism, telefon va yetkazish manzili so‘raladi. Bu ma’lumot buyurtmani bajarish va tasdiqlash
        qo‘ng‘irog‘i uchun ishlatiladi.
      </p>
      <p>
        Savat shu qurilmaning brauzer xotirasida turadi, serverga mahsulot qo‘shish ulanmaguncha yuborilmaydi. Parol va
        tokenlar sahifada ochiq ko‘rsatilmaydi.
      </p>
      <p>Hisob ixtiyoriy. Mehmon buyurtmasi ham shu maxfiylik qoidasiga bo‘ysunadi.</p>
    </InfoPage>
  );
}

export function TermsPage() {
  return (
    <InfoPage title="Foydalanish shartlari">
      <p>
        Katalogdagi bo‘limlar mahsulot guruhlarini ko‘rsatadi. Narx, o‘lcham va qoplama administrator kiritgan
        qiymatlar va server hisobi bilan belgilanadi.
      </p>
      <p>
        Buyurtma yuborilishi shartnoma emas. Holat “Tasdiqlash kutilmoqda” bo‘lib turadi, toki administrator mijoz bilan
        bog‘lanib tasdiqlaguncha. To‘lov alohida yoziladi.
      </p>
      <p>Saytdan foydalanish O‘zbekiston qonunlariga muvofiq.</p>
    </InfoPage>
  );
}
