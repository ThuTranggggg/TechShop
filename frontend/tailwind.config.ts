import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        card: "hsl(var(--card))",
        muted: "hsl(var(--muted))",
        border: "hsl(var(--border))",
        primary: "hsl(var(--primary))",
        accent: "hsl(var(--accent))",
        success: "hsl(var(--success))",
        warning: "hsl(var(--warning))",
        danger: "hsl(var(--danger))"
      },
      fontFamily: {
        sans: ["IBM Plex Sans", "sans-serif"],
        display: ["Sora", "sans-serif"],
      },
      borderRadius: {
        xl: "1rem",
        '2xl': "1.5rem",
        '3xl': "2rem",
      },
      boxShadow: {
        soft: "0 14px 40px -24px rgba(47, 28, 18, 0.25)",
        card: "0 18px 40px -26px rgba(47, 28, 18, 0.24)",
        premium: "0 28px 70px -34px rgba(24, 41, 39, 0.32)",
      },
      keyframes: {
        shimmer: {
          "100%": { transform: "translateX(100%)" }
        }
      },
      animation: {
        shimmer: "shimmer 1.5s infinite"
      }
    }
  },
  plugins: []
};

export default config;
