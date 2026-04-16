import { NextRequest, NextResponse } from "next/server";

const backendBaseUrl = process.env.API_PROXY_BASE_URL ?? "http://gateway";

async function proxy(request: NextRequest, pathSegments: string[]) {
  const url = new URL(request.url);
  const targetPath = pathSegments.join("/").endsWith("/") ? pathSegments.join("/") : `${pathSegments.join("/")}/`;
  const target = new URL(`${backendBaseUrl}/${targetPath}`);
  target.search = url.search;

  const headers = new Headers(request.headers);
  headers.delete("host");

  const init: RequestInit = {
    method: request.method,
    headers,
  };

  if (!["GET", "HEAD"].includes(request.method)) {
    init.body = await request.arrayBuffer();
  }

  const response = await fetch(target, init);
  const responseHeaders = new Headers(response.headers);
  responseHeaders.delete("content-encoding");
  responseHeaders.delete("transfer-encoding");

  return new NextResponse(response.body, {
    status: response.status,
    headers: responseHeaders,
  });
}

export async function GET(request: NextRequest, { params }: { params: { path: string[] } }) {
  return proxy(request, params.path);
}

export async function POST(request: NextRequest, { params }: { params: { path: string[] } }) {
  return proxy(request, params.path);
}

export async function PUT(request: NextRequest, { params }: { params: { path: string[] } }) {
  return proxy(request, params.path);
}

export async function PATCH(request: NextRequest, { params }: { params: { path: string[] } }) {
  return proxy(request, params.path);
}

export async function DELETE(request: NextRequest, { params }: { params: { path: string[] } }) {
  return proxy(request, params.path);
}

export async function OPTIONS(request: NextRequest, { params }: { params: { path: string[] } }) {
  return proxy(request, params.path);
}
