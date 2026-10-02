export type StoreCategory = {
  id: number;
  name: string;
  slug: string;
  description: string | null;
  image: string | null;
  sort_order: number;
  children: StoreCategory[];
};

export type StoreCategoryDetail = StoreCategory & {
  parent: { id: number; name: string; slug: string } | null;
};

export type StoreProduct = {
  id: number;
  name: string;
  slug: string;
  description: string | null;
  sku: string | null;
  images: string[];
  product_type: "made_to_order" | "ready_made";
  unit: "piece" | "meter" | "set";
  is_featured: boolean;
  category: { id: number; name: string; slug: string };
  dimensions: string | null;
  selling_price: string | null;
  available_quantity: number | null;
};

export type StoreProductPage = {
  items: StoreProduct[];
  page: number;
  page_size: number;
  total: number;
};
