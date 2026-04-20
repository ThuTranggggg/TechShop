const DEFAULT_IMAGE = "https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=960&q=80";

const PHONE_IMAGE = "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?auto=format&fit=crop&w=960&q=80";
const LAPTOP_IMAGE = "https://images.unsplash.com/photo-1498050108023-c5249f4df085?auto=format&fit=crop&w=960&q=80";
const TABLET_IMAGE = "https://images.unsplash.com/photo-1545239351-1141bd82e8a6?auto=format&fit=crop&w=960&q=80";
const AUDIO_IMAGE = "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=960&q=80";
const WATCH_IMAGE = "https://images.unsplash.com/photo-1546868871-7041f2a55e12?auto=format&fit=crop&w=960&q=80";
const FASHION_IMAGE = "https://images.unsplash.com/photo-1483985988355-763728e1935b?auto=format&fit=crop&w=960&q=80";
const BEAUTY_IMAGE = "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?auto=format&fit=crop&w=960&q=80";
const HOME_IMAGE = "https://images.unsplash.com/photo-1556911220-bff31c812dba?auto=format&fit=crop&w=960&q=80";
const BOOK_IMAGE = "https://images.unsplash.com/photo-1495446815901-a7297e633e8d?auto=format&fit=crop&w=960&q=80";
const GROCERY_IMAGE = "https://images.unsplash.com/photo-1490645935967-10de6ba17061?auto=format&fit=crop&w=960&q=80";
const SPORTS_IMAGE = "https://images.unsplash.com/photo-1517836357463-d25dfeac3438?auto=format&fit=crop&w=960&q=80";
const BABY_IMAGE = "https://images.unsplash.com/photo-1515488042361-ee00e0ddd4e4?auto=format&fit=crop&w=960&q=80";
const FURNITURE_IMAGE = "https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?auto=format&fit=crop&w=960&q=80";
const OFFICE_IMAGE = "https://images.unsplash.com/photo-1497032628192-86f99bcd76bc?auto=format&fit=crop&w=960&q=80";
const TOY_IMAGE = "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?auto=format&fit=crop&w=960&q=80";

function isPlaceholderThumbnail(url: string) {
  return /picsum\.photos|placeholder|seed\//i.test(url);
}

function normalize(text?: string) {
  return text?.toLowerCase().trim() ?? "";
}

function semanticFallback(product: ProductImageSource) {
  const brand = normalize(product.brand_name);
  const category = normalize(product.category_name);
  const name = normalize(product.name);
  const slug = normalize(product.slug);
  const productText = `${slug} ${name}`;

  if (brand.includes("apple") || brand.includes("samsung") || brand.includes("xiaomi") || productText.includes("phone") || productText.includes("mobile") || productText.includes("redmi") || productText.includes("galaxy") || productText.includes("iphone")) {
    return PHONE_IMAGE;
  }
  if (productText.includes("laptop") || category.includes("laptop")) return LAPTOP_IMAGE;
  if (productText.includes("tablet") || category.includes("tablet")) return TABLET_IMAGE;
  if (productText.includes("audio") || productText.includes("buds") || productText.includes("headphone") || productText.includes("earbud")) return AUDIO_IMAGE;
  if (productText.includes("watch") || productText.includes("wearable")) return WATCH_IMAGE;
  if (category.includes("fashion") || productText.includes("ao ") || productText.includes("quan") || productText.includes("dam") || productText.includes("giay") || productText.includes("dep") || productText.includes("mu")) return FASHION_IMAGE;
  if (category.includes("cosmetic") || category.includes("beauty") || productText.includes("serum") || productText.includes("cream") || productText.includes("lip") || productText.includes("foundation") || productText.includes("sunscreen")) return BEAUTY_IMAGE;
  if (category.includes("home") || productText.includes("kitchen") || productText.includes("appliance") || productText.includes("rice cooker") || productText.includes("vacuum") || productText.includes("fridge") || productText.includes("washing")) return HOME_IMAGE;
  if (productText.includes("book")) return BOOK_IMAGE;
  if (category.includes("grocery") || productText.includes("coffee") || productText.includes("snack") || productText.includes("granola") || productText.includes("nuts") || productText.includes("matcha")) return GROCERY_IMAGE;
  if (category.includes("sport") || productText.includes("yoga") || productText.includes("gym") || productText.includes("running") || productText.includes("camp")) return SPORTS_IMAGE;
  if (category.includes("baby") || productText.includes("baby") || productText.includes("newborn")) return BABY_IMAGE;
  if (category.includes("furniture") || productText.includes("desk") || productText.includes("chair") || productText.includes("table")) return FURNITURE_IMAGE;
  if (category.includes("office") || productText.includes("stationery") || productText.includes("planner") || productText.includes("pen") || productText.includes("notebook")) return OFFICE_IMAGE;
  if (category.includes("toy") || productText.includes("toy") || productText.includes("boardgame") || productText.includes("model")) return TOY_IMAGE;
  return DEFAULT_IMAGE;
}

type ProductImageSource = {
  slug?: string;
  name?: string;
  brand_name?: string;
  category_name?: string;
  thumbnail_url?: string | null;
};

export function getProductImageUrl(product: ProductImageSource) {
  const thumbnail = product.thumbnail_url?.trim();
  if (thumbnail && !isPlaceholderThumbnail(thumbnail)) {
    return thumbnail;
  }
  return semanticFallback(product);
}
