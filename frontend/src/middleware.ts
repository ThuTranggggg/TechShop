import { NextRequest, NextResponse } from "next/server";

const protectedPaths = ["/cart", "/checkout", "/orders", "/chat", "/profile", "/admin"];

export function middleware(request: NextRequest) {
  const token = request.cookies.get("techshop_access")?.value;
  const path = request.nextUrl.pathname;

  if (protectedPaths.some((p) => path.startsWith(p)) && !token) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/cart/:path*", "/checkout/:path*", "/orders/:path*", "/chat/:path*", "/profile/:path*", "/admin/:path*"],
};
