import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#172033",
        muted: "#667085",
        line: "#d9dee8",
        panel: "#f7f9fc",
        brand: "#126b7f",
        accent: "#8a5a00",
      },
      boxShadow: {
        soft: "0 8px 24px rgba(23, 32, 51, 0.08)",
      },
    },
  },
  plugins: [],
};

export default config;
