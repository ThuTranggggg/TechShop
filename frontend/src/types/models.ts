export type Product = {
  id: string;
  name: string;
  slug: string;
  short_description?: string;
  description?: string;
  brand?: string;
  brand_name?: string;
  category?: string;
  category_name?: string;
  base_price: number;
  currency: string;
  status?: string;
  thumbnail_url?: string;
  media?: Array<{ id: string; media_url: string; alt_text?: string; sort_order?: number; is_primary?: boolean }>;
  variants?: Array<{ id: string; name: string; price_override?: number; attributes?: Record<string, string> }>;
  attributes?: Record<string, string>;
};

export type Cart = {
  id: string;
  item_count: number;
  total_quantity: number;
  subtotal_amount: number;
  currency: string;
  items: Array<{
    id: string;
    product_id: string;
    variant_id?: string | null;
    product_name: string;
    brand_name?: string;
    thumbnail_url?: string;
    quantity: number;
    unit_price: number;
    line_total: number;
    status: string;
  }>;
};

export type Order = {
  id: string;
  order_number: string;
  status: string;
  payment_status: string;
  fulfillment_status?: string;
  totals?: { grand_total: number; subtotal: number; shipping_fee: number; currency: string };
  payment_reference?: string;
  shipment_reference?: string;
  created_at?: string;
  items?: Array<{ id: string; product_name: string; quantity: number; unit_price: number; line_total: number }>;
};
