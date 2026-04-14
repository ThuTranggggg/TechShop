import "./globals.css";
import { ReactNode } from "react";
import { Providers } from "@/components/providers";
import { AppHeader } from "@/components/layout/app-header";
import { AppFooter } from "@/components/layout/app-footer";
import { ChatWidget } from "@/components/chat/chat-widget";

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="vi">
      <body>
        <Providers>
          <div className="ambient-wrap min-h-screen">
            <AppHeader />
            <main className="container-app py-8 lg:py-10">{children}</main>
            <AppFooter />
            <ChatWidget />
          </div>
        </Providers>
      </body>
    </html>
  );
}
