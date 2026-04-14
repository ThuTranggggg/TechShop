import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatPrice(value: number | string, currency = "VND") {
  const numeric = typeof value === "string" ? Number(value) : value;
  return new Intl.NumberFormat("vi-VN", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(numeric || 0);
}
