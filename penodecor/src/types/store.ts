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

export type PriceComponent = {
  code: string;
  label: string;
  amount: string | null;
  detail: string | null;
};

export type PriceQuoteResult = {
  status: "PRICED" | "MANUAL_QUOTE_REQUIRED";
  currency: string;
  unit_price: string | null;
  subtotal: string | null;
  total: string | null;
  components: PriceComponent[];
  requires_manual_quote: boolean;
  warnings: string[];
  applied: Record<string, string>;
};

export type PriceCalculateRequest = {
  product_id: number;
  quantity: number;
  trim?: {
    size: "S" | "M" | "L";
    components: Array<"cornice" | "jamb" | "sill">;
    extra_meters?: Record<string, string>;
    addons?: string[];
  };
  pilaster?: {
    width_cm: string;
    thickness_cm: string;
    length_m: string;
    capital?: string | null;
    base?: string | null;
  };
  round_column?: {
    existing_diameter_cm?: string | null;
    circumference_cm?: string | null;
    final_diameter_cm: string;
    height_m: string;
    coating?: boolean;
    capital?: string | null;
    base?: string | null;
    model?: string | null;
  };
  cornice?: {
    width_cm: string;
    length_m: string;
    coating?: boolean;
  };
  shohona?: {
    length_m?: string | null;
    size_note?: string | null;
    coating?: boolean;
    model?: string | null;
  };
};
