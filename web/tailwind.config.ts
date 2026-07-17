import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Warm, editorial palette — deliberately not the dark-cyber look competitors use.
        bone: "#F7F4EC", // off-white background
        ink: "#1F1B16", // warm near-black text
        zombie: {
          DEFAULT: "#7BA05B", // sickly-but-cute desaturated green
          dark: "#5C7B41",
          light: "#A8C48A",
          wash: "#EAF0E1",
        },
        rot: "#B4553B", // warm alert/danger for "left" owners and stale activity
        dusk: "#6B6558", // muted secondary text
      },
      fontFamily: {
        display: ["var(--font-display)", "Georgia", "serif"],
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
      },
      keyframes: {
        drift: {
          "0%, 100%": { transform: "translateY(0) rotate(-2deg)" },
          "50%": { transform: "translateY(-10px) rotate(2deg)" },
        },
        "cursor-loop": {
          "0%": { transform: "translate(0, 0)" },
          "20%": { transform: "translate(60px, 18px)" },
          "40%": { transform: "translate(28px, 44px)" },
          "60%": { transform: "translate(84px, 30px)" },
          "80%": { transform: "translate(40px, 8px)" },
          "100%": { transform: "translate(0, 0)" },
        },
        "click-pulse": {
          "0%, 88%, 100%": { transform: "scale(1)", opacity: "0" },
          "92%": { transform: "scale(1)", opacity: "0.6" },
          "96%": { transform: "scale(2.2)", opacity: "0" },
        },
        blink: {
          "0%, 92%, 100%": { transform: "scaleY(1)" },
          "96%": { transform: "scaleY(0.1)" },
        },
      },
      animation: {
        drift: "drift 6s ease-in-out infinite",
        "cursor-loop": "cursor-loop 7s ease-in-out infinite",
        "click-pulse": "click-pulse 7s ease-in-out infinite",
        blink: "blink 4s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
