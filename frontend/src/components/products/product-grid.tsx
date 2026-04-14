import { Product } from "@/types/models";
import { ProductCard } from "@/components/products/product-card";

export function ProductGrid({ products }: { products: Product[] }) {
  return <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 xl:grid-cols-3">{products.map((p) => <ProductCard key={p.id} product={p} />)}</div>;
}
