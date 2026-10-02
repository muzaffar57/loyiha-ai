export type CategoryGroup = {
  id: string;
  label: string;
  description: string;
};

export type Category = {
  slug: string;
  title: string;
  summary: string;
  note: string;
  groups: CategoryGroup[];
};

export const categories: Category[] = [
  {
    slug: "rom-va-eshik",
    title: "Rom va eshik bezaklari",
    summary: "Deraza va eshik komplektlari, alohida elementlar va qo‘shimcha bezaklar.",
    note: "Qo‘shimcha uzunlik alohida hisoblanadi. Narxni administrator kiritadi.",
    groups: [
      {
        id: "barchasi",
        label: "Barchasi",
        description: "Deraza romlari, eshik bezaklari va alohida elementlar shu bo‘limda chiqadi.",
      },
      {
        id: "deraza",
        label: "Deraza romlari",
        description: "Deraza atrofi uchun komplektlar. O‘lchamlar mahsulot sahifasida tanlanadi.",
      },
      {
        id: "eshik",
        label: "Eshik bezaklari",
        description: "Eshik uchun komplektlar. En, balandlik va qoplama keyinroq serverda hisoblanadi.",
      },
      {
        id: "element",
        label: "Alohida elementlar",
        description: "Komplektga kirmaydigan qismlar va qo‘shimcha bezaklar.",
      },
    ],
  },
  {
    slug: "pilastrlar",
    title: "Pilastrlar va ustunlar",
    summary: "Kapitel, tana va baza. Tana metr hisobida, en va qalinlik bo‘yicha.",
    note: "Har bir en va qalinlik juftligining narxini administrator belgilaydi.",
    groups: [
      {
        id: "barchasi",
        label: "Barchasi",
        description: "Kapitel, tana va baza shu katalogda jamlanadi.",
      },
      {
        id: "kapitel",
        label: "Kapitel",
        description: "Ustunning yuqori qismi.",
      },
      {
        id: "tana",
        label: "Tana",
        description: "Tana metr hisobida sotiladi. En va qalinlik kombinatsiyasi administrator narxlariga tayanadi.",
      },
      {
        id: "baza",
        label: "Baza",
        description: "Ustunning pastki qismi.",
      },
    ],
  },
  {
    slug: "yumaloq-ustunlar",
    title: "Yumaloq ustunlar",
    summary: "Mavjud quvur diametri yoki aylanasi va kerakli tashqi diametr bo‘yicha.",
    note: "Balandlik, soni, kapitel, baza va qoplama koeffitsiyenti serverda hisoblanadi.",
    groups: [
      {
        id: "barchasi",
        label: "Barchasi",
        description: "Yumaloq ustun tanasi hamda ixtiyoriy kapitel va baza.",
      },
      {
        id: "tana",
        label: "Tana",
        description: "Mavjud quvur o‘lchami va yakuniy tashqi diametr bo‘yicha buyurtma.",
      },
      {
        id: "kapitel-baza",
        label: "Kapitel va baza",
        description: "Ixtiyoriy yuqori va pastki qismlar.",
      },
    ],
  },
  {
    slug: "shift-karnizlari",
    title: "Shift karnizlari va belbog‘lar",
    summary: "Mijoz en va uzunlikni tanlaydi. Narx tayanch en va asosiy narxdan kelib chiqadi.",
    note: "En bo‘yicha mutanosib narx keyingi bosqichda serverda hisoblanadi.",
    groups: [
      {
        id: "barchasi",
        label: "Barchasi",
        description: "Shift karnizlari va belbog‘lar.",
      },
      {
        id: "karniz",
        label: "Shift karnizi",
        description: "En va uzunlik mijoz tomonidan kiritiladi.",
      },
      {
        id: "belbog",
        label: "Belbog‘",
        description: "Belbog‘ ham en va uzunlik bo‘yicha buyurtma qilinadi.",
      },
    ],
  },
  {
    slug: "shohona-karnizlar",
    title: "Shohona karnizlar",
    summary: "Galereya va individual narx so‘rovi. Narxni administrator qo‘yadi.",
    note: "Mijoz taklif etilgan narxni tasdiqlagandan keyin buyurtma yakunlanadi.",
    groups: [
      {
        id: "barchasi",
        label: "Barchasi",
        description: "Shohona karnizlar uchun avval namuna, so‘ng narx so‘rovi.",
      },
    ],
  },
];

export function findCategory(slug: string | undefined): Category | undefined {
  return categories.find((category) => category.slug === slug);
}

export function filterCategories(query: string): Category[] {
  const needle = query.trim().toLocaleLowerCase("uz");
  if (!needle) return categories;
  return categories.filter((category) => {
    const haystack = [category.title, category.summary, category.note, ...category.groups.map((group) => group.label)]
      .join(" ")
      .toLocaleLowerCase("uz");
    return haystack.includes(needle);
  });
}
