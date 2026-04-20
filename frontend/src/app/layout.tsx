import "./globals.css";
import { ReactNode } from "react";
import type { Metadata } from "next";
import { Providers } from "@/components/providers";
import { AuthBootstrap } from "@/components/auth/auth-bootstrap";
import { AppHeader } from "@/components/layout/app-header";
import { AppFooter } from "@/components/layout/app-footer";
import { ChatWidget } from "@/components/chat/chat-widget";

export const metadata: Metadata = {
  title: "TechShop | AI Commerce Demo",
  description: "TechShop là website demo thương mại điện tử kết hợp catalog sản phẩm, kho tri thức và RAG chatbot cho tư vấn mua sắm.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="vi">
      <body>
        <Providers>
          <AuthBootstrap />
          <div className="ambient-wrap min-h-screen">
            <a href="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-[60] focus:rounded-xl focus:bg-slate-900 focus:px-4 focus:py-2 focus:text-sm focus:text-white">
              Bỏ qua đến nội dung chính
            </a>
            <AppHeader />
            <main id="main-content" className="container-app py-8 lg:py-10">{children}</main>
            <AppFooter />
            <ChatWidget />
          </div>
        </Providers>
      </body>
    </html>
  );
}
