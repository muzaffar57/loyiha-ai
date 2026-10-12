const covers: Record<string, string> = {
  "rom-va-eshik": "/home/rom-va-eshik.jpg",
  pilastrlar: "/home/pilastrlar.jpg",
  "shift-karnizlari": "/home/shift-karnizlari.jpg",
  "yumaloq-ustunlar": "/home/yumaloq-ustunlar.jpg",
  "shohona-karnizlar": "/home/shohona-karnizlar.jpg",
  "tayyor-mahsulotlar": "/home/tayyor-mahsulotlar.jpg",
};

const homeOrder = [
  "rom-va-eshik",
  "pilastrlar",
  "shift-karnizlari",
  "yumaloq-ustunlar",
  "shohona-karnizlar",
  "tayyor-mahsulotlar",
];

export function categoryCover(slug: string, remoteUrl: string | null): string | null {
  return remoteUrl ?? covers[slug] ?? null;
}

export function sortHomeCategories<T extends { slug: string }>(items: T[]): T[] {
  const rank = (slug: string) => {
    const index = homeOrder.indexOf(slug);
    return index === -1 ? homeOrder.length : index;
  };
  return [...items].sort((a, b) => rank(a.slug) - rank(b.slug));
}
