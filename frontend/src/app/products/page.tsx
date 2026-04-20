"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ProductGrid } from "@/components/products/product-grid";
import { SearchBar } from "@/components/products/search-bar";
import { ProductFilterSidebar } from "@/components/products/product-filter-sidebar";
import { ProductSortBar } from "@/components/products/product-sort-bar";
import { EmptyState } from "@/components/ui/empty-state";
import { LoadingSkeletons } from "@/components/ui/loading-skeletons";
import { getBrands, getCategories, getProducts } from "@/services/api/products";
import { getRecommendations, trackAiEvent } from "@/services/api/ai";
import { RecommendationCarousel } from "@/components/recommendations/recommendation-carousel";
import { getAccessToken } from "@/services/auth";
import { extractUserIdFromJwt } from "@/lib/jwt";

export default function ProductsPage() {
  const token = getAccessToken();
  const userId = token ? extractUserIdFromJwt(token) : undefined;
  const [params, setParams] = useState<Record<string, string>>({ page_size: "12", ordering: "-published_at" });
  const { data: productsData, isLoading } = useQuery({ queryKey: ["products", params], queryFn: () => getProducts(params) });
  const { data: categoriesData } = useQuery({ queryKey: ["categories"], queryFn: getCategories });
  const { data: brandsData } = useQuery({ queryKey: ["brands"], queryFn: getBrands });

  const categories = useMemo(
    () => (categoriesData?.results ?? []).filter((category) => Number(category.children_count ?? 0) === 0),
    [categoriesData],
  );
  const productGroups = useMemo(() => brandsData?.results ?? [], [brandsData]);
  const products = productsData?.results ?? [];
  const { data: recData } = useQuery({
    queryKey: ["products-recommendations", products.length],
    enabled: products.length > 0,
    queryFn: () =>
      getRecommendations({
        products: products.slice(0, 8).map((p) => ({
          id: p.id,
          name: p.name,
          brand: p.brand_name,
          category: p.category_name,
          price: p.base_price,
          thumbnail_url: p.thumbnail_url,
        })),
        limit: 4,
      }),
  });
  const recProducts = products.filter((p) => recData?.products?.some((r) => r.product_id === p.id));

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-[300px_1fr]">
      <ProductFilterSidebar categories={categories} productGroups={productGroups} onChange={(value) => setParams((prev) => ({ ...prev, ...value }))} />
      <section className="space-y-5">
        <div className="rounded-3xl border border-border/80 bg-card p-4 shadow-soft">
          <h1 className="font-display text-3xl font-extrabold text-slate-900">Catalog sản phẩm</h1>
          <p className="mt-1 text-sm text-slate-600">Lọc theo thương hiệu, danh mục và mức giá để chọn món phù hợp nhất.</p>
        </div>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <SearchBar
            onSubmit={(q) => {
              setParams((prev) => ({ ...prev, search: q }));
              trackAiEvent({ event_type: "search", user_id: userId, keyword: q, metadata: { source: "products_page" } }).catch(() => undefined);
            }}
          />
          <ProductSortBar onSort={(ordering) => setParams((prev) => ({ ...prev, ordering }))} />
        </div>
        {isLoading ? (
          <LoadingSkeletons lines={8} />
        ) : products.length ? (
          <ProductGrid products={products} />
        ) : (
          <EmptyState title="Không có sản phẩm" description="Thử đổi bộ lọc hoặc từ khóa khác." />
        )}
        {recProducts.length ? <RecommendationCarousel products={recProducts} title="Gợi ý cho bạn" /> : null}
      </section>
    </div>
  );
}
