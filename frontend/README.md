# TechShop Frontend

Storefront UI demo-ready cho hệ microservices TechShop.

## Stack
- Next.js 14 App Router
- TypeScript
- Tailwind CSS
- TanStack Query
- Zustand
- React Hook Form + Zod
- Framer Motion (mở rộng sẵn)

## Chạy local
```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```
Mặc định chạy `http://localhost:3000`.

## Chạy Docker
```bash
docker compose up --build frontend gateway
```
Truy cập qua gateway: `http://localhost:8080`.

## Env
- `NEXT_PUBLIC_API_BASE_URL`: base URL gateway (vd `http://localhost:8080`)
- `NEXT_PUBLIC_APP_NAME`: tên app

## Cấu trúc thư mục
- `src/app`: pages App Router
- `src/components`: UI reusable blocks
- `src/services/api`: API integration layer theo service
- `src/store`: client UI store
- `src/types`: shared models
- `src/lib`: helpers/config

## Pages
- `/` home + search + recommendations
- `/login`
- `/products`
- `/products/[id]`
- `/cart`
- `/checkout`
- `/orders`
- `/orders/[id]`
- `/chat`

## API integrations
- User: login, me, addresses
- Product: list/detail/categories/brands
- Cart: current, summary, add/update/remove, checkout-preview
- Order: create from cart, list/detail/timeline
- Payment: mock webhooks
- Shipping: detail/tracking
- AI: recommendations, chat session, ask

## Auth/session strategy
- Access token lưu cookie `techshop_access` để middleware guard route.
- Refresh token lưu localStorage.

## Design decisions
- Giao diện premium, sạch, nhiều whitespace.
- Component hóa cho product/cart/order/chat.
- Error/empty/loading states rõ ràng.
- Mobile-first, filter/search dễ thao tác.

## Limitations
- Chat widget chưa render rich cards từ `related_products` nâng cao.
- Payment mock đang dùng endpoint webhook đơn giản cho demo.
- Chưa có SSR auth hydration vì ưu tiên thin frontend.

## Hướng mở rộng
- Thêm shadcn component primitives đầy đủ.
- Add analytics events (search/view/click) sang AI events API.
- Rich recommendation reasons UI + inline product cards trong chat.
- Refresh token auto-flow chuẩn production.
