/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  trailingSlash: true,
  skipTrailingSlashRedirect: true,
  async rewrites() {
    const backendBaseUrl = process.env.API_PROXY_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8080";

    return [
      { source: "/user/:path*", destination: `${backendBaseUrl}/user/:path*` },
      { source: "/product/:path*", destination: `${backendBaseUrl}/product/:path*` },
      { source: "/cart/:path*", destination: `${backendBaseUrl}/cart/:path*` },
      { source: "/order/:path*", destination: `${backendBaseUrl}/order/:path*` },
      { source: "/payment/:path*", destination: `${backendBaseUrl}/payment/:path*` },
      { source: "/shipping/:path*", destination: `${backendBaseUrl}/shipping/:path*` },
      { source: "/inventory/:path*", destination: `${backendBaseUrl}/inventory/:path*` },
      { source: "/ai/:path*", destination: `${backendBaseUrl}/ai/:path*` },
    ];
  },
};

module.exports = nextConfig;
