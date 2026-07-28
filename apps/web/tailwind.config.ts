import type { Config } from "tailwindcss";

export default {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        app: "var(--bg-app)",
        surface: {
          DEFAULT: "var(--bg-surface)",
          raised: "var(--bg-surface-raised)",
          muted: "var(--bg-muted)",
          hover: "var(--bg-hover)",
        },
        border: {
          DEFAULT: "var(--border-default)",
          subtle: "var(--border-subtle)",
        },
        ink: {
          DEFAULT: "var(--text-primary)",
          secondary: "var(--text-secondary)",
          muted: "var(--text-muted)",
          inverse: "var(--text-inverse)",
        },
        accent: {
          DEFAULT: "var(--accent)",
          hover: "var(--accent-hover)",
          subtle: "var(--accent-subtle)",
        },
        pnl: {
          pos: "var(--pnl-pos)",
          neg: "var(--pnl-neg)",
          "pos-muted": "var(--pnl-pos-muted)",
          "neg-muted": "var(--pnl-neg-muted)",
        },
        chart: {
          portfolio: "var(--chart-portfolio)",
          benchmark: "var(--chart-benchmark)",
          excess: "var(--chart-excess)",
        },
      },
      borderRadius: {
        sm: "var(--radius-sm)",
        md: "var(--radius-md)",
        lg: "var(--radius-lg)",
      },
      maxWidth: {
        content: "var(--content-max)",
      },
      width: {
        nav: "var(--nav-width)",
        "nav-collapsed": "var(--nav-width-collapsed)",
      },
      height: {
        topbar: "var(--topbar-height)",
      },
    },
  },
  plugins: [],
} satisfies Config;
