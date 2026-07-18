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
        // Dark, moody palette — near-black canvas, off-white text, one purple accent.
        // Token names are kept from the old light theme so class names carry over;
        // only the values changed (bone = dark canvas, ink = light text, etc.).
        bone: "#0E0D10", // near-black page canvas (faint cool cast)
        surface: {
          DEFAULT: "#17151C", // raised panel / card
          light: "#211D2A", // hover / second elevation
        },
        edge: "#2A2633", // hairline borders on dark
        ink: "#ECEAE4", // primary near-white text
        dusk: "#9E97AC", // muted secondary text (lavender-gray)
        zombie: {
          DEFAULT: "#8B5CF6", // the zombie: a cute, glowing violet
          dark: "#7C3AED", // deeper violet for buttons / active (white text ~4.6:1)
          light: "#B79CF2", // highlights, borders
          deep: "#6D28D9", // outlines / mascot linework
          wash: "#211A33", // dark violet fill for chips / badges
        },
        rot: {
          DEFAULT: "#E5645A", // warm alert red, legible on dark
          dark: "#C4453B",
        },
      },
      fontFamily: {
        display: ["var(--font-display)", "Georgia", "serif"],
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
      },
      boxShadow: {
        // Soft violet glow for the moody hero / mascot.
        glow: "0 0 40px -8px rgba(139, 92, 246, 0.45)",
        "glow-sm": "0 0 20px -6px rgba(139, 92, 246, 0.4)",
      },
      keyframes: {
        // Idle undead sway — a slow lean side to side, like shuffling in place.
        shuffle: {
          "0%, 100%": { transform: "translateY(0) rotate(-2.5deg)" },
          "50%": { transform: "translateY(-6px) rotate(2.5deg)" },
        },
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
        "glow-pulse": {
          "0%, 100%": { opacity: "0.5" },
          "50%": { opacity: "0.9" },
        },
      },
      animation: {
        shuffle: "shuffle 4.5s ease-in-out infinite",
        drift: "drift 6s ease-in-out infinite",
        "cursor-loop": "cursor-loop 7s ease-in-out infinite",
        "click-pulse": "click-pulse 7s ease-in-out infinite",
        "glow-pulse": "glow-pulse 5s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
