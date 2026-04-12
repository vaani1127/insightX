import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "#0a0a0d",
        surface: "#111116",
        surface2: "#18181f",
        surface3: "#222230",
        border: "rgba(255,255,255,0.07)",
        purple: "#7c6df8",
        green: "#1fd98c",
        amber: "#f5a623",
        red: "#f05050",
        blue: "#4fa3f7",
        cyan: "#22d4d4",
        text: "#eeeef2",
        text2: "#a0a0b0",
        text3: "#6b6b80",
      },
      fontFamily: {
        sans: ["Syne", "sans-serif"],
        mono: ["IBM Plex Mono", "monospace"],
      },
      borderRadius: {
        sm: "6px",
        DEFAULT: "10px",
        lg: "14px",
        xl: "20px",
      },
    },
  },
  plugins: [],
};

export default config;
