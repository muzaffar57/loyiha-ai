export type AdminCategory = {
  id: number;
  parent_id: number | null;
  name: string;
  slug: string;
  description: string | null;
  image: string | null;
  is_active: boolean;
  sort_order: number;
};

export type AdminProduct = {
  id: number;
  category_id: number;
  name: string;
  slug: string;
  description: string | null;
  sku: string | null;
  images: string[];
  product_type: "made_to_order" | "ready_made";
  unit: "piece" | "meter" | "set";
  dimensions: string | null;
  is_active: boolean;
  is_featured: boolean;
  sort_order: number;
  selling_price: string | null;
  available_quantity: number | null;
};

export type AdminProductPage = {
  items: AdminProduct[];
  page: number;
  page_size: number;
  total: number;
};

export type AdminProfile = {
  id: number;
  full_name: string;
  email: string;
  is_active: boolean;
};

export type SyncStatus = {
  status: string;
  stale: boolean;
  currency: string;
  global_price_adjustment_percent: string;
  last_success_at: string | null;
  last_attempt_at: string | null;
  last_error: string | null;
  sheet_updated_at: string | null;
};

export type SyncResult = {
  status: string;
  updated_products: number;
};
