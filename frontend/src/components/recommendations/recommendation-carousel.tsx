import { Product } from "@/types/models";
import { ProductCard } from "@/components/products/product-card";

export function RecommendationCarousel({ products, title = "Gợi ý cho bạn" }: { products: Product[]; title?: string }) {
  return (
    <section>
      <h3 className="mb-4 text-xl font-bold">{title}</h3>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {products.map((p) => <ProductCard key={p.id} product={p} />)}
      </div>
    </section>
  );
}
