/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"IBM Plex Sans"', "system-ui", "sans-serif"],
      },
      colors: {
        bg: "#FFFFFF",
        sidebar: "#F4F6F6",
        panel: "#FBFCFC",
        line: "#E1E6E6",
        field: "#CDD5D5",
        text: "#111827",
        muted: "#4B5563",
        accent: "#0F766E",
        "accent-soft": "#DCEFED",
        "accent-dark": "#0A4D48",
        row: "#EEF7F6",
        poster: "#E3E8E8",
        error: "#B42318",
        "error-bg": "#FDF1EF",
      },
      borderRadius: {
        field: "6px",
      },
    },
  },
  plugins: [],
};
